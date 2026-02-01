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

# Cache para no gastar dinero doble
CACHE_FILE = os.path.join(BASE_DIR, "vision_analysis_cache.json")

# Cargar Cache existente
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

# ================= UTILIDADES ROBUSTAS =================

def encontrar_archivo(nombre_archivo):
    """Busca el archivo en C:\img o C:\scrap indistintamente."""
    rutas_posibles = [
        os.path.join(BASE_DIR, nombre_archivo),
        os.path.join(SCRAP_DIR, nombre_archivo)
    ]
    
    for ruta in rutas_posibles:
        if os.path.exists(ruta):
            return ruta
    return None

def cargar_referencias(nombre_archivo_csv, col_archivo, col_desc):
    """Carga el CSV de referencia en un diccionario {nombre_imagen: descripcion}."""
    refs = {}
    ruta_real = encontrar_archivo(nombre_archivo_csv)
    
    if ruta_real:
        print(f"   ✅ Referencia encontrada: {os.path.basename(ruta_real)}")
        try:
            # Intentar leer con diferentes codificaciones y separadores
            try: 
                df = pd.read_csv(ruta_real, encoding='utf-8-sig', on_bad_lines='skip', sep=None, engine='python')
            except: 
                df = pd.read_csv(ruta_real, encoding='latin-1', sep=None, engine='python', on_bad_lines='skip')
            
            # Normalizar columnas (quitar espacios)
            df.columns = [c.strip() for c in df.columns]
            
            # Verificar que las columnas existan
            if col_archivo in df.columns and col_desc in df.columns:
                for _, row in df.iterrows():
                    f = str(row[col_archivo]).strip().lower()
                    d = str(row[col_desc]).strip()
                    if len(d) > 2: 
                        refs[f] = d
            else:
                print(f"   ⚠️ Columnas no encontradas en {nombre_archivo_csv}. Buscaba: {col_archivo}, {col_desc}")
                print(f"      Columnas disponibles: {list(df.columns)}")
        except Exception as e:
            print(f"   ⚠️ Error leyendo CSV: {e}")
    else:
        print(f"   ❌ NO SE ENCONTRÓ EL CSV: {nombre_archivo_csv}")
        
    return refs

def analizar_imagen_ia(ruta_img, contexto_nombre=""):
    """Consulta a GPT-4o Vision de forma segura."""
    if not client: return {}
    
    try:
        file_hash = f"{os.path.basename(ruta_img)}_{os.path.getsize(ruta_img)}"
        if file_hash in CACHE: return CACHE[file_hash]

        with open(ruta_img, "rb") as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')

        prompt = f"""
        Analiza esta imagen de un repuesto de moto.
        Contexto previo: "{contexto_nombre}"
        Responde SOLO un JSON válido con este formato:
        {{
            "tipo_contenido": "repuesto" (o "herramienta", "accesorio"),
            "nombre_comercial": "Nombre técnico corregido",
            "sistema": "Motor" (o Frenos, Electrico, Chasis, etc)
        }}
        """

        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres un experto en autopartes. Responde JSON."},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]}
            ],
            max_tokens=150,
            response_format={"type": "json_object"}
        )
        
        contenido = resp.choices[0].message.content
        if not contenido: return {}
            
        data = json.loads(contenido)
        CACHE[file_hash] = data
        return data

    except Exception as e:
        # print(f"   [IA Error]: {e}") # Descomentar para debug
        return {}

# ================= CONFIGURACIÓN DE LOTES =================

LOTES_A_PROCESAR = [
    {
        "nombre": "DFG",
        "carpeta": os.path.join(BASE_DIR, "FOTOS_COMPETENCIA_DFG"),
        # Nombre del archivo generado por el script 11 (Excel Match) o el 9 (Batch)
        "referencia": "Inventario_Maestro_DFG_Completo.csv", 
        "salida": os.path.join(BASE_DIR, "catalogo_kaiqi_imagenes_DFG.csv"),
        # Columnas que generó el script 9/11
        "col_archivo": "Imagen_Final", 
        "col_desc": "Nombre_Producto"
    },
    {
        "nombre": "ARMOTOS",
        "carpeta": os.path.join(BASE_DIR, "FOTOS_COMPETENCIA_ARMOTOS"),
        "referencia": "Inventario_Cliente_NF_Web.csv",
        "salida": os.path.join(BASE_DIR, "catalogo_kaiqi_imagenes_ARMOTOS.csv"),
        "col_archivo": "Imagen_SEO", 
        "col_desc": "Nombre_Producto"
    },
    {
        "nombre": "ARMOTOSS",
        "carpeta": os.path.join(BASE_DIR, "FOTOS_COMPETENCIA_ARMOTOSS"),
        "referencia": "Inventario_Cliente_NF_FINAL_CLEAN.csv", # Usamos el limpio v3
        "salida": os.path.join(BASE_DIR, "catalogo_kaiqi_imagenes_ARMOTOSS.csv"),
        "col_archivo": "Imagen_Final", 
        "col_desc": "Descripcion"
    }
]

# ================= MOTOR PRINCIPAL =================

def procesar_lote(lote):
    print(f"\n🚀 Iniciando Lote: {lote['nombre']}...")
    
    # 1. Verificar Carpeta de Imágenes
    carpeta = lote['carpeta']
    if not os.path.exists(carpeta):
        # Intentar buscar en scrap
        carpeta_alt = os.path.join(SCRAP_DIR, os.path.basename(lote['carpeta']))
        if os.path.exists(carpeta_alt):
            carpeta = carpeta_alt
            print(f"   📍 Carpeta encontrada en: {carpeta}")
        else:
            print(f"   ❌ Carpeta de fotos NO encontrada: {lote['carpeta']}")
            return

    # 2. Cargar Referencias
    referencias = cargar_referencias(lote['referencia'], lote['col_archivo'], lote['col_desc'])
    print(f"   📚 Referencias en memoria: {len(referencias)}")

    # 3. Listar Imágenes
    imagenes = [f for f in os.listdir(carpeta) if f.lower().endswith(('.jpg', '.png', '.jpeg', '.webp'))]
    print(f"   🔍 Imágenes físicas: {len(imagenes)}")

    resultados = []
    
    # Función Worker
    def worker(img_file):
        ruta_completa = os.path.join(carpeta, img_file)
        
        # A. ESTRATEGIA 1: DATA MINADA (Gratis y Exacta)
        nombre_ref = referencias.get(img_file.lower(), "")
        
        # Intento secundario: buscar coincidencia parcial si el nombre de archivo cambió un poco
        if not nombre_ref:
            for k, v in referencias.items():
                if img_file.lower() in k or k in img_file.lower():
                    nombre_ref = v
                    break
        
        # B. ESTRATEGIA 2: INTELIGENCIA ARTIFICIAL (Solo si hace falta)
        data_ia = {}
        if not nombre_ref or client: 
            # Si no hay nombre, preguntamos a la IA qué es.
            # Si hay nombre, le damos el nombre a la IA para que solo clasifique (ahorra alucinaciones).
            data_ia = analizar_imagen_ia(ruta_completa, nombre_ref)
        
        # Consolidar Datos
        nombre_final = data_ia.get("nombre_comercial", "")
        if not nombre_final: nombre_final = nombre_ref
        if not nombre_final: nombre_final = os.path.splitext(img_file)[0] # Fallback final
        
        sistema = data_ia.get("sistema", "General")
        tipo = data_ia.get("tipo_contenido", "repuesto")
        
        return {
            "Filename_Original": img_file,
            "Es_Moto_o_Motocarguero": True,
            "Tipo_Contenido": tipo,
            "Confianza_Global": 0.95 if nombre_ref else 0.7,
            "Identificacion_Repuesto": nombre_final,
            "Componente_Taxonomia": nombre_final.split()[0],
            "Sistema": sistema,
            "SubSistema": "",
            "Caracteristicas_Observadas": "",
            "Compatibilidad_Probable_Texto": "",
            "Funcion": "",
            "Nombre_Comercial_Catalogo": nombre_final, # CLAVE MAESTRA
            "Tags_Sugeridos": f"{tipo},{sistema},KAIQI_ECOSYSTEM",
            "Notas_Sobre_Textos_Grabados": "",
            "Necesita_Modelo_Grande": False
        }

    # Ejecutar en Paralelo
    with ThreadPoolExecutor(max_workers=8) as executor:
        for i, res in enumerate(executor.map(worker, imagenes)):
            resultados.append(res)
            if i % 50 == 0: print(f"   ... {i}/{len(imagenes)}", end="\r")

    # Guardar
    if resultados:
        df = pd.DataFrame(resultados)
        df.to_csv(lote['salida'], index=False, sep=';', encoding='utf-8-sig')
        print(f"   ✅ Generado Exitosamente: {os.path.basename(lote['salida'])}")
    
    guardar_cache()

if __name__ == "__main__":
    print("--- GENERADOR DE CATÁLOGOS INTELIGENTES V12.2 ---")
    for lote in LOTES_A_PROCESAR:
        procesar_lote(lote)
    print("\n✨ PROCESO COMPLETADO.")