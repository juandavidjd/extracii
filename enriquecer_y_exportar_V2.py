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

if not os.path.exists(OUTPUT_FOTOS_DIR):
    os.makedirs(OUTPUT_FOTOS_DIR)

print("--- SCRIPT 3 (V2 - Lógica Inteligente) ---")

# --- LISTAS DE PALABRAS CLAVE PARA CLASIFICACIÓN ---
MOTO_KEYWORDS = ['PULSAR', 'BWS', 'AGILITY', 'SCOOTER', 'NKD', 'FZ', 'LIBERO', 'BOXER', 'GS', 'GN', 'JET', 'EVO', 'TTR']
MOTOCARGUERO_KEYWORDS = ['CARGUERO', '3W', 'AYCO', 'VAISAND', 'MOTOCARRO', 'TORITO']

# --- 1. Cargar Bases de Datos ---
try:
    print("1. Cargando inventario KAIQI (Inventario_Limpio_CORREGIDO.csv)...")
    df_kaiqi = pd.read_csv(KAIQI_INVENTARIO, sep=';', dtype=str) # Importante: leer con ;
    
    print("2. Cargando base de datos de competencia...")
    df_competencia = pd.read_csv(COMPETENCIA_DB, dtype=str)
    
    choices = df_competencia['Nombre_Externo'].dropna().tolist()
    image_map = pd.Series(df_competencia.Imagen_Externa.values, index=df_competencia.Nombre_Externo).to_dict()

except Exception as e:
    print(f"❌ Error fatal cargando archivos: {e}")
    exit()

print(f"3. Iniciando 'Fuzzy Matching' (comparando {len(df_kaiqi)} productos KAIQI)...")

df_kaiqi['Nivel_Confianza'] = 0
df_kaiqi['Imagen_Fuente_Rica'] = ""
df_kaiqi['Descripcion_Rica'] = ""

matches_encontrados = 0

for index, row in df_kaiqi.iterrows():
    # --- LÓGICA DE BÚSQUEDA V2 ---
    # Usamos la descripción original KAIQI (que es más específica)
    query = str(row['Descripcion'])
    
    # Comparamos contra las 904 opciones de la competencia
    best_match = process.extractOne(query, choices, scorer=fuzz.token_set_ratio, score_cutoff=85)
    
    if best_match:
        nombre_competencia, score = best_match[0], best_match[1]
        
        # --- ENRIQUECIMIENTO ---
        # Aplicamos .title() para formato "Tipo Título"
        df_kaiqi.at[index, 'Descripcion_Rica'] = nombre_competencia.title()
        df_kaiqi.at[index, 'Imagen_Fuente_Rica'] = image_map[nombre_competencia]
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

# --- LÓGICA DE CLASIFICACIÓN V2 ---
def get_tipo_vehiculo(desc):
    desc_upper = str(desc).upper()
    # 1. Buscar palabras de MOTO
    if any(keyword in desc_upper for keyword in MOTO_KEYWORDS):
        return "MOTO"
    # 2. Buscar palabras de MOTOCARGUERO
    if any(keyword in desc_upper for keyword in MOTOCARGUERO_KEYWORDS):
        return "MOTOCARGUERO"
    # 3. Default
    return "MOTO" # Asumir moto si no es carguero

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

total_imagenes_copiadas = 0

for index, row in df_kaiqi.iterrows():
    sku = str(row['SKU'])
    
    # --- LÓGICA DE TÍTULO V2 ---
    # Prioridad 1: Título enriquecido
    if row['Nivel_Confianza'] >= 85:
        desc_final = str(row['Descripcion_Rica']) # Ya está en .title()
    else:
        # Prioridad 2: Título original, pero limpiado y en .title()
        desc_final = str(row['Descripcion']).title()
    
    # --- LÓGICA DE NOMBRE DE ARCHIVO SEO V2 ---
    seo_text = desc_final.lower()
    seo_text = re.sub(r'[^a-z0-9\s-]', '', seo_text)
    handle = re.sub(r'[\s]+', '-', seo_text).strip('-')
    seo_filename = f"{handle}_{sku}.jpg" # Forzamos todo a JPG
    
    imagen_final_para_csv = ""
    
    # --- LÓGICA DE COPIA DE IMÁGENES V2 ---
    fuente_path = None
    if row['Nivel_Confianza'] >= 85:
        # 1. Foto "Rica" (Competencia)
        fuente_path = os.path.join(COMPETENCIA_FOTOS_DIR, str(row['Imagen_Fuente_Rica']))
    else:
        # 2. Foto "Fea" (KAIQI original o Google)
        img_actual = str(row['Imagen_Actual'])
        if img_actual != 'Sin Imagen' and img_actual != 'nan':
            # Buscamos en la carpeta FOTOS_COMPETENCIA (donde consolidamos todo)
            fuente_path = os.path.join(COMPETENCIA_FOTOS_DIR, img_actual)
            
    if fuente_path and os.path.exists(fuente_path):
        destino_path = os.path.join(OUTPUT_FOTOS_DIR, seo_filename)
        try:
            with Image.open(fuente_path) as img:
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(destino_path, "JPEG", quality=90)
            
            imagen_final_para_csv = seo_filename
            total_imagenes_copiadas += 1
        except Exception:
            pass # Saltar imagen corrupta
            
    # --- Llenar Taxonomía ---
    categoria_kaiqi = str(row['Categoria']).title()
    sistema_principal = get_sistema(categoria_kaiqi)
    # El componente es el nombre de la categoría (ej: "Bomba Aceite")
    componente = categoria_kaiqi 
    tipo_vehiculo = get_tipo_vehiculo(desc_final) # Usamos la nueva lógica
    
    # Agregar fila al CSV de Shopify
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
        "Variant Price": float(row['Precio']),
        "Variant Grams": 500,
        "Variant Inventory Tracker": "shopify",
        "Variant Inventory Qty": 10,
        "Variant Inventory Policy": "continue" if float(row['Precio']) > 0 else "deny",
        "Image Src": imagen_final_para_csv,
        "Image Position": 1,
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
print(f"✅ ¡PROYECTO FINALIZADO (V2)!")
print(f"   -> {OUTPUT_SHOPIFY_CSV} (Listo para subir a Shopify)")
print(f"   -> {OUTPUT_FOTOS_DIR} ({total_imagenes_copiadas} imágenes únicas listas)")
print("="*50)