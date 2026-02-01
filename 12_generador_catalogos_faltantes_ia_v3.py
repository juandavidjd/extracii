import os
import pandas as pd
import base64
import json
import time
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\img"
SCRAP_DIR = r"C:\scrap"

# Cliente OpenAI
try:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except:
    client = None
    print("⚠️ ADVERTENCIA: No se detectó API Key. Se usará solo data minada (sin IA).")

# Cache
CACHE_FILE = os.path.join(BASE_DIR, "vision_analysis_cache.json")
if os.path.exists(CACHE_FILE):
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f: CACHE = json.load(f)
    except: CACHE = {}
else:
    CACHE = {}

def guardar_cache():
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f: json.dump(CACHE, f, indent=2)
    except: pass

# ================= UTILIDADES =================

def encontrar_archivo(nombre_archivo):
    """Busca el archivo en C:\img o C:\scrap."""
    rutas = [
        os.path.join(BASE_DIR, nombre_archivo),
        os.path.join(SCRAP_DIR, nombre_archivo)
    ]
    for r in rutas:
        if os.path.exists(r): return r
    return None

def cargar_referencias(nombre_archivo_csv, posibles_col_archivo, posibles_col_desc):
    """Carga referencias intentando varias columnas posibles."""
    refs = {}
    ruta_real = encontrar_archivo(nombre_archivo_csv)
    
    if ruta_real:
        print(f"   ✅ Referencia encontrada: {os.path.basename(ruta_real)}")
        try:
            # Leer CSV con detección de formato
            try: 
                df = pd.read_csv(ruta_real, encoding='utf-8-sig', on_bad_lines='skip', sep=None, engine='python')
            except: 
                df = pd.read_csv(ruta_real, encoding='latin-1', sep=None, engine='python', on_bad_lines='skip')
            
            # Normalizar columnas
            df.columns = [c.strip() for c in df.columns]
            cols = df.columns
            
            # Buscar la columna correcta
            col_archivo = next((c for c in cols if c in posibles_col_archivo), None)
            col_desc = next((c for c in cols if c in posibles_col_desc), None)
            
            if col_archivo and col_desc:
                for _, row in df.iterrows():
                    f = str(row[col_archivo]).strip().lower()
                    d = str(row[col_desc]).strip()
                    if len(d) > 2: 
                        refs[f] = d
                print(f"      -> {len(refs)} items cargados.")
            else:
                print(f"   ⚠️ No encontré columnas clave en {nombre_archivo_csv}.")
                print(f"      Columnas disponibles: {list(cols)}")
        except Exception as e:
            print(f"   ⚠️ Error leyendo CSV: {e}")
    else:
        print(f"   ❌ NO SE ENCONTRÓ EL CSV: {nombre_archivo_csv}")
        
    return refs

def analizar_imagen_ia(ruta_img, contexto_nombre=""):
    if not client: return {}
    try:
        file_hash = f"{os.path.basename(ruta_img)}_{os.path.getsize(ruta_img)}"
        if file_hash in CACHE: return CACHE[file_hash]

        with open(ruta_img, "rb") as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')

        prompt = f"""
        Analiza esta imagen de repuesto. Contexto: "{contexto_nombre}".
        Responde JSON:
        {{
            "tipo_contenido": "repuesto",
            "nombre_comercial": "Nombre tecnico",
            "sistema": "Motor/Frenos"
        }}
        """
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres experto en repuestos. Responde JSON."},
                {"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}
            ],
            max_tokens=150,
            response_format={"type": "json_object"}
        )
        data = json.loads(resp.choices[0].message.content)
        CACHE[file_hash] = data
        return data
    except: return {}

# ================= CONFIGURACIÓN DE LOTES (CORREGIDA) =================

LOTES_A_PROCESAR = [
    {
        "nombre": "DFG",
        "carpeta": os.path.join(BASE_DIR, "FOTOS_COMPETENCIA_DFG"),
        "referencia": "Base_Datos_DFG.csv", # <--- CORREGIDO
        "salida": os.path.join(BASE_DIR, "catalogo_kaiqi_imagenes_DFG.csv"),
        # Posibles nombres de columna
        "cols_archivo": ["Imagen_Final", "Imagen_SEO", "Filename_Original"], 
        "cols_desc": ["Nombre_Producto", "Descripcion", "Nombre_Asignado"]
    },
    {
        "nombre": "ARMOTOS",
        "carpeta": os.path.join(BASE_DIR, "FOTOS_COMPETENCIA_ARMOTOS"),
        "referencia": "Base_Datos_Armotos.csv", # <--- CORREGIDO
        "salida": os.path.join(BASE_DIR, "catalogo_kaiqi_imagenes_ARMOTOS.csv"),
        "cols_archivo": ["Imagen_SEO", "Imagen_Final", "Filename"], 
        "cols_desc": ["Nombre_Producto", "Descripcion"]
    },
    {
        "nombre": "ARMOTOSS",
        "carpeta": os.path.join(BASE_DIR, "FOTOS_COMPETENCIA_ARMOTOSS"),
        "referencia": "Base_Datos_Armotoss.csv", # <--- CORREGIDO
        "salida": os.path.join(BASE_DIR, "catalogo_kaiqi_imagenes_ARMOTOSS.csv"),
        "cols_archivo": ["Imagen_Final", "Imagen_Original"], 
        "cols_desc": ["Descripcion", "Nombre_Producto"]
    }
]

# ================= MOTOR PRINCIPAL =================

def procesar_lote(lote):
    print(f"\n🚀 Iniciando Lote: {lote['nombre']}...")
    
    carpeta = lote['carpeta']
    if not os.path.exists(carpeta):
        print(f"   ❌ Carpeta de fotos no encontrada: {lote['carpeta']}")
        return

    # 1. Cargar Referencias
    referencias = cargar_referencias(lote['referencia'], lote['cols_archivo'], lote['cols_desc'])

    imagenes = [f for f in os.listdir(carpeta) if f.lower().endswith(('.jpg', '.png', '.jpeg', '.webp'))]
    print(f"   🔍 Imágenes a procesar: {len(imagenes)}")

    resultados = []
    
    def worker(img_file):
        ruta_completa = os.path.join(carpeta, img_file)
        
        # A. Buscar en Referencias
        nombre_ref = referencias.get(img_file.lower(), "")
        # Bounding box search (si el nombre de archivo contiene parte del nombre)
        if not nombre_ref:
            for k, v in referencias.items():
                if img_file.lower() in k or k in img_file.lower():
                    nombre_ref = v
                    break
        
        # B. IA
        data_ia = {}
        if not nombre_ref or client: 
            data_ia = analizar_imagen_ia(ruta_completa, nombre_ref)
        
        nombre_final = data_ia.get("nombre_comercial", nombre_ref)
        if not nombre_final: nombre_final = os.path.splitext(img_file)[0]
        
        return {
            "Filename_Original": img_file,
            "Es_Moto_o_Motocarguero": True,
            "Tipo_Contenido": data_ia.get("tipo_contenido", "repuesto"),
            "Identificacion_Repuesto": nombre_final,
            "Componente_Taxonomia": nombre_final.split()[0],
            "Sistema": data_ia.get("sistema", ""),
            "Nombre_Comercial_Catalogo": nombre_final,
            "Tags_Sugeridos": "KAIQI_ECOSYSTEM",
            "Necesita_Modelo_Grande": False
        }

    with ThreadPoolExecutor(max_workers=8) as executor:
        for i, res in enumerate(executor.map(worker, imagenes)):
            resultados.append(res)
            if i % 50 == 0: print(f"   ... {i}/{len(imagenes)}", end="\r")

    if resultados:
        df = pd.DataFrame(resultados)
        df.to_csv(lote['salida'], index=False, sep=';', encoding='utf-8-sig')
        print(f"   ✅ Generado: {os.path.basename(lote['salida'])} ({len(df)} registros)")
    
    guardar_cache()

if __name__ == "__main__":
    print("--- GENERADOR DE CATÁLOGOS INTELIGENTES V12.3 ---")
    for lote in LOTES_A_PROCESAR:
        procesar_lote(lote)
    print("\n✨ PROCESO COMPLETADO.")