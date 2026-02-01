import pandas as pd
import os
import re
import shutil
from thefuzz import fuzz
from thefuzz import process
from PIL import Image

# --- CONFIGURACIÓN ---
PROJECT_DIR = r'C:\KAIQI_PROYECTO_FINAL'
KAIQI_INVENTARIO = os.path.join(PROJECT_DIR, 'Inventario_Limpio_CORREGIDO.csv')
COMPETENCIA_DB = os.path.join(PROJECT_DIR, 'Base_Datos_Competencia_Maestra.csv')
COMPETENCIA_FOTOS_DIR = os.path.join(PROJECT_DIR, 'FOTOS_COMPETENCIA')

# --- SALIDAS ---
OUTPUT_SHOPIFY_CSV = os.path.join(PROJECT_DIR, 'Shopify_Import_FINAL.csv')
OUTPUT_FOTOS_DIR = os.path.join(PROJECT_DIR, 'IMAGENES_PARA_SHOPIFY')
OUTPUT_INVENTARIO_ENRIQUECIDO = os.path.join(PROJECT_DIR, 'Inventario_ENRIQUECIDO.csv')

# --- LISTAS DE PALABRAS CLAVE PARA LÓGICA ---
# Palabras para LIMPIEZA (ignorar en la búsqueda)
STOP_WORDS = [
    'CAJA', 'X10', 'JUEGO', 'KIT', 'PAR', 'UNIDAD', 'ORIGINAL', 'TIPO', 'OEM', 'KAIQI', 
    'REPUESTO', 'DALU', 'SMG', 'HLK', 'TWOM', 'KAY', 'CHO', 'KET', 'MN', 'MV', 'EOM', 'CTO', 
    'COMPL', 'REF', 'GENERICO', 'PARA', 'CON', 'DE'
]
# Palabras para TIPO DE VEHÍCULO
MOTO_KEYWORDS = ['PULSAR', 'BWS', 'AGILITY', 'SCOOTER', 'NKD', 'FZ', 'LIBERO', 'BOXER', 'GS', 'GN', 'JET', 'EVO', 'TTR', 'AKT', 'YAMAHA', 'HONDA', 'SUZUKI', 'KYMCO']
MOTOCARGUERO_KEYWORDS = ['CARGUERO', '3W', 'AYCO', 'VAISAND', 'MOTOCARRO', 'TORITO', 'BAJAJ']
# Palabras para CORRECCIÓN DE MAYÚSCULAS
CAPITALIZE_WORDS = ['AKT', 'AYCO', 'KYMCO', 'BWS', 'NKD', 'SLR', 'TTR', 'CGR', 'CG', 'CDI', 'LED', 'OEM', 'KAIQI']

# --- Crear carpeta de salida (si borraste la anterior) ---
if not os.path.exists(OUTPUT_FOTOS_DIR):
    os.makedirs(OUTPUT_FOTOS_DIR)

print("--- SCRIPT 3 (V3 - Lógica de Esencia y Cosmética) ---")

# --- 1. Funciones de Limpieza y Formato ---

def clean_text_for_matching(text):
    text = str(text).upper()
    for word in STOP_WORDS:
        text = text.replace(word, '')
    text = re.sub(r'[^A-Z0-9\s]', ' ', text) # Quitar puntuación
    return re.sub(r'\s+', ' ', text).strip() # Quitar espacios extra

def format_title(text):
    text = str(text).title() # Ej: "Arbol De Levas Akt 125"
    # Ahora, forzamos las mayúsculas de marcas
    for word in CAPITALIZE_WORDS:
        # Usamos regex para reemplazar la palabra exacta (ignorando may/min)
        text = re.sub(r'\b' + re.escape(word.title()) + r'\b', word, text, flags=re.IGNORECASE)
    return text

def get_tipo_vehiculo(desc):
    desc_upper = str(desc).upper()
    # Prioridad 1: Si dice MOTOCARGUERO
    if any(keyword in desc_upper for keyword in MOTOCARGUERO_KEYWORDS):
        return "MOTOCARGUERO"
    # Prioridad 2: Si dice MOTO
    if any(keyword in desc_upper for keyword in MOTO_KEYWORDS):
        return "MOTO"
    return "MOTOCARGUERO" # Default para KAIQI

def get_sistema(cat_text):
    cat_text = str(cat_text).upper()
    if any(word in cat_text for word in ['MOTOR', 'CULATA', 'CILINDRO', 'PISTON', 'BOMBA', 'CARBURADOR', 'CIGUEÑAL', 'BIELA', 'EMPAQUE', 'CLUTCH', 'ARBOL', 'BALANCIN']):
        return 'MOTOR'
    if any(word in cat_text for word in ['FRENO', 'RIN', 'TREN', 'CHASIS', 'AMORTIGUADOR', 'DIRECCION', 'GUARDABARRO', 'MANUBRIO']):
        return 'CHASIS Y FRENOS'
    if any(word in cat_text for word in ['ELECTRICO', 'CDI', 'BOBINA', 'ARRANQUE', 'REGULADOR', 'BENDIX', 'COMANDO', 'LUCES', 'PITO', 'SWICH']):
        return 'SISTEMA ELECTRICO'
    if any(word in cat_text for word in ['CAJA', 'TRANSMISION', 'CADENILLA', 'PIÑON']):
        return 'TRANSMISION'
    return 'ACCESORIOS Y OTROS'

# --- 2. Cargar Bases de Datos ---
try:
    print("1. Cargando inventario KAIQI (Inventario_Limpio_CORREGIDO.csv)...")
    df_kaiqi = pd.read_csv(KAIQI_INVENTARIO, sep=';', dtype=str)
    
    print("2. Cargando base de datos de competencia...")
    df_competencia = pd.read_csv(COMPETENCIA_DB, dtype=str)
    
    # --- Pre-procesamiento de "Esencias" ---
    print("   -> Pre-procesando esencias de KAIQI...")
    df_kaiqi['query_clean'] = df_kaiqi.apply(lambda row: clean_text_for_matching(f"{row['Categoria']} {row['Descripcion']}"), axis=1)
    
    print("   -> Pre-procesando esencias de Competencia (904 productos)...")
    df_competencia['query_clean'] = df_competencia['Nombre_Externo'].apply(clean_text_for_matching)
    
    # Creamos el mapa de elección
    choices = df_competencia['query_clean'].dropna().tolist()
    # Mapa: 'ESENCIA' -> ('Descripcion Rica Original', 'Foto Original')
    choice_map = {}
    for i, row in df_competencia.iterrows():
        choice_map[row['query_clean']] = (row['Nombre_Externo'], row['Imagen_Externa'])

except Exception as e:
    print(f"❌ Error fatal cargando archivos: {e}")
    exit()

print(f"3. Iniciando 'Fuzzy Matching' (Comparando Esencias)...")

df_kaiqi['Nivel_Confianza'] = 0
df_kaiqi['Imagen_Fuente_Rica'] = ""
df_kaiqi['Descripcion_Rica'] = ""

matches_encontrados = 0

for index, row in df_kaiqi.iterrows():
    query = row['query_clean']
    best_match = process.extractOne(query, choices, scorer=fuzz.token_set_ratio, score_cutoff=85)
    
    if best_match:
        nombre_esencia_match, score = best_match[0], best_match[1]
        
        # Recuperamos los datos ricos usando el mapa
        desc_rica, img_rica = choice_map[nombre_esencia_match]
        
        # --- ENRIQUECIMIENTO ---
        df_kaiqi.at[index, 'Descripcion_Rica'] = desc_rica
        df_kaiqi.at[index, 'Imagen_Fuente_Rica'] = img_rica
        df_kaiqi.at[index, 'Nivel_Confianza'] = score
        
        matches_encontrados += 1

print(f"\n--- TOTAL MATCHES DE ALTA CONFIANZA: {matches_encontrados} ---")
print("4. Guardando inventario enriquecido (temporal)...")
df_kaiqi.to_csv(OUTPUT_INVENTARIO_ENRIQUECIDO, index=False, sep=';')

# --- 5. PREPARAR ARCHIVOS DE SHOPIFY ---
print("5. Generando archivo de importación Shopify y renombrando imágenes...")

shopify_cols = [
    "Handle", "Title", "Body (HTML)", "Vendor", "Product category", "Type", "Tags",
    "Published", "Status", "Variant SKU", "Variant Price", "Variant Grams", 
    "Variant Inventory Tracker", "Variant Inventory Qty", "Variant Inventory Policy", 
    "Image Src", "Image Position", "Image Alt Text",
    "KAIQI / Sistema Principal", "KAIQI / Subsistema", "KAIQI / Componente", "KAIQI / Tipo Vehiculo"
]
df_shopify = pd.DataFrame(columns=shopify_cols)

total_imagenes_copiadas = 0

for index, row in df_kaiqi.iterrows():
    sku = str(row['SKU'])
    
    # --- LÓGICA DE TÍTULO V3 ---
    if row['Nivel_Confianza'] >= 85:
        desc_final = format_title(row['Descripcion_Rica']) # Formato "Rico"
    else:
        desc_final = format_title(row['Descripcion']) # Formato "Original"
    
    # --- LÓGICA DE NOMBRE DE ARCHIVO SEO V3 ---
    seo_text = desc_final.lower()
    seo_text = re.sub(r'[^a-z0-9\s-]', '', seo_text)
    handle = re.sub(r'[\s]+', '-', seo_text).strip('-')
    seo_filename = f"{handle}_{sku}.jpg" 
    
    imagen_final_para_csv = ""
    
    # --- LÓGICA DE COPIA DE IMÁGENES V3 ---
    fuente_path = None
    if row['Nivel_Confianza'] >= 85:
        # 1. Foto "Rica" (Competencia)
        fuente_path = os.path.join(COMPETENCIA_FOTOS_DIR, str(row['Imagen_Fuente_Rica']))
    else:
        # 2. Foto "Fea" (KAIQI original o Google)
        img_actual = str(row['Imagen_Actual'])
        if img_actual != 'Sin Imagen' and pd.notna(img_actual):
            fuente_path = os.path.join(COMPETENCIA_FOTOS_DIR, img_actual)
            
    if fuente_path and os.path.exists(fuente_path):
        destino_path = os.path.join(OUTPUT_FOTOS_DIR, seo_filename)
        try:
            with Image.open(fuente_path) as img:
                if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                img.save(destino_path, "JPEG", quality=90)
            
            imagen_final_para_csv = seo_filename
            total_imagenes_copiadas += 1
        except Exception:
            pass
            
    # --- Llenar Taxonomía ---
    categoria_kaiqi = format_title(row['Categoria'])
    sistema_principal = get_sistema(categoria_kaiqi)
    componente = categoria_kaiqi 
    tipo_vehiculo = get_tipo_vehiculo(desc_final)
    
    nueva_fila = {
        "Handle": handle,
        "Title": desc_final,
        "Body (HTML)": desc_final,
        "Vendor": "KAIQI",
        "Product category": "", 
        "Type": categoria_kaiqi,
        "Tags": f"{sistema_principal}, {componente}, {tipo_vehiculo}",
        "Published": "TRUE",
        "Status": "active",
        "Variant SKU": row['SKU'],
        "Variant Price": float(pd.to_numeric(row['Precio'], errors='coerce').fillna(0)),
        "Variant Grams": 500,
        "Variant Inventory Tracker": "shopify",
        "Variant Inventory Qty": 10,
        "Variant Inventory Policy": "continue" if float(pd.to_numeric(row['Precio'], errors='coerce').fillna(0)) > 0 else "deny",
        "Image Src": imagen_final_para_csv,
        "Image Position": 1 if imagen_final_para_csv else "",
        "Image Alt Text": desc_final,
        "KAIQI / Sistema Principal": sistema_principal,
        "KAIQI / Subsistema": "",
        "KAIQI / Componente": componente,
        "KAIQI / Tipo Vehiculo": tipo_vehiculo
    }
    df_shopify = pd.concat([df_shopify, pd.DataFrame([nueva_fila])], ignore_index=True)

# Guardar el CSV final
df_shopify.to_csv(OUTPUT_SHOPIFY_CSV, index=False, sep=';', encoding='utf-8-sig')

print("\n" + "="*50)
print(f"✅ ¡PROYECTO FINALIZADO (V3)!")
print(f"   -> {OUTPUT_SHOPIFY_CSV} (Listo para subir a Shopify)")
print(f"   -> {OUTPUT_FOTOS_DIR} ({total_imagenes_copiadas} imágenes únicas listas)")
print("="*50)