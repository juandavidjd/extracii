import os
import shutil
import pandas as pd
import base64
import json
import re
import unicodedata  # <--- ¡Faltaba esto!
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\img"
SCRAP_DIR = r"C:\scrap"

# Carpetas a Limpiar (Origen -> Destino Base)
LOTES_LIMPIEZA = [
    {
        "nombre": "DFG",
        "origen": os.path.join(BASE_DIR, "FOTOS_COMPETENCIA_DFG"),
        "referencia_csv": "Inventario_Maestro_DFG_Completo.csv",
        "destino_base": os.path.join(BASE_DIR, "LIMPIEZA_DFG")
    },
    {
        "nombre": "ARMOTOS",
        "origen": os.path.join(BASE_DIR, "FOTOS_COMPETENCIA_ARMOTOS"),
        "referencia_csv": "Inventario_Cliente_NF_Web.csv",
        "destino_base": os.path.join(BASE_DIR, "LIMPIEZA_ARMOTOS")
    },
    {
        "nombre": "ARMOTOSS",
        "origen": os.path.join(BASE_DIR, "FOTOS_COMPETENCIA_ARMOTOSS"),
        "referencia_csv": "Inventario_Cliente_NF_GOLDEN.csv",
        "destino_base": os.path.join(BASE_DIR, "LIMPIEZA_ARMOTOSS")
    }
]

# Categorías de Clasificación
CATEGORIAS = ["REPUESTOS", "HERRAMIENTAS", "LUJOS_ACCESORIOS", "EMBELLECIMIENTO", "OTROS_NO_MOTO"]

# Cliente OpenAI
try:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except:
    client = None
    print("❌ SIN API KEY: El script solo usará nombres de archivo, no visión.")

# Cache
CACHE_FILE = os.path.join(BASE_DIR, "vision_classification_cache.json")
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
def encontrar_archivo(nombre):
    p1 = os.path.join(BASE_DIR, nombre)
    if os.path.exists(p1): return p1
    p2 = os.path.join(SCRAP_DIR, nombre)
    if os.path.exists(p2): return p2
    return None

def cargar_referencias(csv_name):
    path = encontrar_archivo(csv_name)
    refs = {}
    if path:
        try:
            # Intento de lectura flexible
            try: df = pd.read_csv(path, encoding='utf-8', on_bad_lines='skip')
            except: df = pd.read_csv(path, encoding='latin-1', sep=None, engine='python')
            
            # Buscar columna de nombre
            cols = [c.lower() for c in df.columns]
            col_name = next((c for c in df.columns if 'nombre' in c.lower() or 'desc' in c.lower()), None)
            col_file = next((c for c in df.columns if 'imagen' in c.lower() or 'file' in c.lower()), None)
            
            if col_name and col_file:
                for _, row in df.iterrows():
                    f = str(row[col_file]).strip().lower()
                    n = str(row[col_name]).strip()
                    refs[f] = n
        except: pass
    return refs

def clasificar_con_ia(ruta_img, nombre_ref):
    if not client: return "REPUESTOS", nombre_ref
    
    file_hash = f"{os.path.basename(ruta_img)}_{os.path.getsize(ruta_img)}"
    if file_hash in CACHE:
        return CACHE[file_hash]["categoria"], CACHE[file_hash]["nombre"]

    try:
        with open(ruta_img, "rb") as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
            
        prompt = f"""
        Analiza esta imagen. Nombre sugerido: "{nombre_ref}".
        Clasifícala en UNA de estas categorías: {CATEGORIAS}.
        Si es repuesto de moto, dame su nombre técnico corregido.
        Si NO es de moto (ej: ropa, sticker suelto, logo), marca como OTROS_NO_MOTO.
        Responde SOLO JSON: {{"categoria": "...", "nombre_tecnico": "..."}}
        """
        
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]}
            ],
            max_tokens=100,
            response_format={"type": "json_object"}
        )
        
        data = json.loads(resp.choices[0].message.content)
        cat = data.get("categoria", "REPUESTOS")
        nom = data.get("nombre_tecnico", nombre_ref)
        
        if cat not in CATEGORIAS: cat = "REPUESTOS"
        
        CACHE[file_hash] = {"categoria": cat, "nombre": nom}
        return cat, nom

    except Exception as e:
        return "REPUESTOS", nombre_ref

def slugify(text):
    if not isinstance(text, str): return "sin-nombre"
    text = str(text).lower()
    # Normalización Unicode para quitar tildes
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

# ================= MOTOR PRINCIPAL =================
def procesar_limpieza(lote):
    print(f"\n🧹 Limpiando Lote: {lote['nombre']}...")
    
    origen = lote['origen']
    if not os.path.exists(origen):
        print(f"   ❌ Carpeta origen no existe: {origen}")
        return

    # Crear carpetas destino
    base_dest = lote['destino_base']
    for cat in CATEGORIAS:
        os.makedirs(os.path.join(base_dest, cat), exist_ok=True)

    # Cargar referencias
    refs = cargar_referencias(lote['referencia_csv'])
    imagenes = [f for f in os.listdir(origen) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    print(f"   🔍 Analizando {len(imagenes)} imágenes...")
    
    def worker(img_file):
        ruta_src = os.path.join(origen, img_file)
        nombre_ref = refs.get(img_file.lower(), os.path.splitext(img_file)[0])
        
        # Clasificar
        categoria, nombre_final = clasificar_con_ia(ruta_src, nombre_ref)
        
        # Mover y Renombrar
        nuevo_nombre = f"{slugify(nombre_final)}.jpg"
        ruta_dest = os.path.join(base_dest, categoria, nuevo_nombre)
        
        # Evitar colisión
        c = 1
        while os.path.exists(ruta_dest):
            ruta_dest = os.path.join(base_dest, categoria, f"{slugify(nombre_final)}-{c}.jpg")
            c += 1
            
        try:
            shutil.copy2(ruta_src, ruta_dest)
        except Exception as e:
            print(f"Error copiando {img_file}: {e}")
        return 1

    with ThreadPoolExecutor(max_workers=10) as executor:
        list(executor.map(worker, imagenes))
        
    guardar_cache()
    print(f"   ✅ Limpieza terminada. Revisa: {base_dest}")

if __name__ == "__main__":
    print("--- LIMPIADOR Y CLASIFICADOR DE IMÁGENES (V13.1 Fixed) ---")
    for lote in LOTES_LIMPIEZA:
        procesar_limpieza(lote)