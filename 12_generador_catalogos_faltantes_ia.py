import os
import pandas as pd
import base64
import json
import re
import time
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\img"

# Mapeo: Carpeta Física -> CSV de Referencia (Data Minada) -> Archivo Salida
LOTES_A_PROCESAR = [
    {
        "nombre": "DFG",
        "carpeta": os.path.join(BASE_DIR, "FOTOS_COMPETENCIA_DFG"),
        "referencia": os.path.join(BASE_DIR, "Inventario_Maestro_DFG_Completo.csv"),
        "salida": os.path.join(BASE_DIR, "catalogo_kaiqi_imagenes_DFG.csv"),
        "col_archivo": "Imagen_Final", "col_desc": "Nombre_Producto"
    },
    {
        "nombre": "ARMOTOS",
        "carpeta": os.path.join(BASE_DIR, "FOTOS_COMPETENCIA_ARMOTOS"),
        "referencia": os.path.join(BASE_DIR, "Inventario_Cliente_NF_Web.csv"),
        "salida": os.path.join(BASE_DIR, "catalogo_kaiqi_imagenes_ARMOTOS.csv"),
        "col_archivo": "Imagen_SEO", "col_desc": "Nombre_Producto"
    },
    {
        "nombre": "ARMOTOSS",
        "carpeta": os.path.join(BASE_DIR, "FOTOS_COMPETENCIA_ARMOTOSS"),
        "referencia": os.path.join(BASE_DIR, "Inventario_Cliente_NF_GOLDEN.csv"), # Usamos el limpio GOLDEN
        "salida": os.path.join(BASE_DIR, "catalogo_kaiqi_imagenes_ARMOTOSS.csv"),
        "col_archivo": "Imagen_Final", "col_desc": "Descripcion"
    }
]

# Cliente OpenAI
try:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except:
    print("❌ Error: No se encontró API KEY de OpenAI.")
    client = None

# Cache para no gastar doble
CACHE_FILE = os.path.join(BASE_DIR, "vision_analysis_cache.json")
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r", encoding="utf-8") as f: CACHE = json.load(f)
else:
    CACHE = {}

def guardar_cache():
    with open(CACHE_FILE, "w", encoding="utf-8") as f: json.dump(CACHE, f, indent=2)

# ================= UTILIDADES =================
def cargar_referencias(ruta_csv, col_archivo, col_desc):
    """Carga el CSV minado en un diccionario {nombre_archivo: descripcion}."""
    refs = {}
    if os.path.exists(ruta_csv):
        try:
            # Intentar leer con diferentes separadores/encodings
            try: df = pd.read_csv(ruta_csv, encoding='utf-8', on_bad_lines='skip')
            except: df = pd.read_csv(ruta_csv, encoding='latin-1', sep=None, engine='python', on_bad_lines='skip')
            
            # Normalizar columnas
            df.columns = [c.strip() for c in df.columns]
            
            if col_archivo in df.columns and col_desc in df.columns:
                for _, row in df.iterrows():
                    f = str(row[col_archivo]).strip()
                    d = str(row[col_desc]).strip()
                    if len(d) > 3: refs[f.lower()] = d
        except Exception as e:
            print(f"   ⚠️ Error leyendo referencia {os.path.basename(ruta_csv)}: {e}")
    return refs

def analizar_imagen_ia(ruta_img, contexto_nombre=""):
    """Usa GPT-4o Vision para categorizar y extraer datos."""
    if not client: return {}
    
    # Check Cache
    file_hash = f"{os.path.basename(ruta_img)}_{os.path.getsize(ruta_img)}"
    if file_hash in CACHE: return CACHE[file_hash]

    try:
        with open(ruta_img, "rb") as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')

        prompt = f"""
        Analiza esta imagen de un producto automotriz. Tienes este contexto de nombre: "{contexto_nombre}".
        Responde SIEMPRE en formato JSON puro con estas claves:
        - es_moto_o_motocarguero: (bool)
        - tipo_contenido: (string: "repuesto", "herramienta", "accesorio", "lujo", "consumible", "otro")
        - nombre_comercial: (string) El nombre técnico más preciso. Si ves marca visible, inclúyela.
        - sistema: (string) Motor, Frenos, Chasis, Electrico, Transmision, etc.
        - caracteristicas: (string) Descripción visual breve.
        - textos_grabados: (string) Si ves códigos o marcas en el metal/empaque.
        """

        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres un experto en autopartes. Responde solo JSON."},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]}
            ],
            max_tokens=300,
            response_format={"type": "json_object"}
        )
        
        data = json.loads(resp.choices[0].message.content)
        CACHE[file_hash] = data
        return data

    except Exception as e:
        print(f"   [ERR Vision]: {e}")
        return {}

# ================= MOTOR DE PROCESAMIENTO =================
def procesar_lote(lote):
    print(f"\n🚀 Iniciando Lote: {lote['nombre']}...")
    
    carpeta = lote['carpeta']
    if not os.path.exists(carpeta):
        print(f"   ❌ Carpeta no encontrada: {carpeta}")
        return

    # 1. Cargar Referencias (La "Verdad" Minada)
    referencias = cargar_referencias(lote['referencia'], lote['col_archivo'], lote['col_desc'])
    print(f"   📚 Referencias cargadas: {len(referencias)}")

    imagenes = [f for f in os.listdir(carpeta) if f.lower().endswith(('.jpg', '.png', '.jpeg', '.webp'))]
    print(f"   🔍 Imágenes a procesar: {len(imagenes)}")

    resultados = []
    
    # Función worker para hilos
    def procesar_una(img_file):
        ruta_completa = os.path.join(carpeta, img_file)
        
        # A. Buscar nombre en referencias (Costo $0)
        nombre_ref = referencias.get(img_file.lower(), "")
        
        # B. Análisis IA (Para clasificar y limpiar)
        # Solo llamamos a IA si NO tenemos referencia O si queremos enriquecer la clasificación
        # Para ahorrar, usaremos IA para categorizar (repuesto vs herramienta) usando el nombre como pista
        # O visión real si se requiere. Asumiremos Visión para "Limpieza Profunda" como pidió el usuario.
        
        data_ia = analizar_imagen_ia(ruta_completa, nombre_ref)
        
        # Consolidar Datos
        nombre_final = data_ia.get("nombre_comercial", nombre_ref)
        if not nombre_final: nombre_final = nombre_ref # Fallback
        if not nombre_final: nombre_final = os.path.splitext(img_file)[0] # Ultimo recurso
        
        return {
            "Filename_Original": img_file,
            "Es_Moto_o_Motocarguero": data_ia.get("es_moto_o_motocarguero", True),
            "Tipo_Contenido": data_ia.get("tipo_contenido", "repuesto"),
            "Confianza_Global": 0.95 if nombre_ref else 0.8,
            "Identificacion_Repuesto": nombre_final,
            "Componente_Taxonomia": nombre_final.split()[0] if nombre_final else "",
            "Sistema": data_ia.get("sistema", ""),
            "SubSistema": "",
            "Caracteristicas_Observadas": data_ia.get("caracteristicas", ""),
            "Compatibilidad_Probable_Texto": "",
            "Funcion": "",
            "Nombre_Comercial_Catalogo": nombre_final, # ESTE ES EL CLAVE PARA EL RENOMBRADOR
            "Tags_Sugeridos": f"{data_ia.get('tipo_contenido','')},{data_ia.get('sistema','')}",
            "Notas_Sobre_Textos_Grabados": data_ia.get("textos_grabados", ""),
            "Necesita_Modelo_Grande": False
        }

    # Ejecución en Paralelo (Rapidez)
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(procesar_una, img) for img in imagenes]
        for i, f in enumerate(futures):
            res = f.result()
            resultados.append(res)
            if i % 10 == 0: print(f"   ... {i}/{len(imagenes)} procesados", end="\r")

    # Guardar CSV Final
    if resultados:
        df = pd.DataFrame(resultados)
        df.to_csv(lote['salida'], index=False, sep=';', encoding='utf-8-sig') # Sep ; como el original Bara
        print(f"   ✅ Generado: {os.path.basename(lote['salida'])}")
    
    guardar_cache()

# ================= MAIN =================
if __name__ == "__main__":
    print("--- GENERADOR DE CATÁLOGOS DE INTELIGENCIA (IA PROFUNDA) ---")
    
    for lote in LOTES_A_PROCESAR:
        procesar_lote(lote)
        
    print("\n✨ TODAS LAS LISTAS GENERADAS. LISTO PARA FASE DE RENOMBRADO.")