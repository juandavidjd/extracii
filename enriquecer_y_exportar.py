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

print("--- SCRIPT 3: ENRIQUECIMIENTO Y ENSAMBLAJE FINAL ---")

# --- 1. Cargar Bases de Datos ---
try:
    print("1. Cargando inventario KAIQI (Inventario_Limpio_CORREGIDO.csv)...")
    df_kaiqi = pd.read_csv(KAIQI_INVENTARIO, sep=';', dtype=str) # Leer con punto y coma
    
    print("2. Cargando base de datos de competencia (Base_Datos_Competencia_Maestra.csv)...")
    df_competencia = pd.read_csv(COMPETENCIA_DB, dtype=str)
    
    # Preparamos la lista de "opciones" para el fuzzy matching
    choices = df_competencia['Nombre_Externo'].dropna().tolist()
    
    # Creamos un 'mapa' para encontrar la imagen por nombre
    image_map = pd.Series(df_competencia.Imagen_Externa.values, index=df_competencia.Nombre_Externo).to_dict()

except Exception as e:
    print(f"❌ Error fatal cargando archivos: {e}")
    exit()

print(f"3. Iniciando 'Fuzzy Matching' (comparando {len(df_kaiqi)} vs {len(choices)} productos)...")

# Nuevas columnas para el enriquecimiento
df_kaiqi['Nivel_Confianza'] = 0
df_kaiqi['Imagen_Fuente_Rica'] = ""
df_kaiqi['Descripcion_Rica'] = ""

matches_encontrados = 0

for index, row in df_kaiqi.iterrows():
    # Creamos un string de búsqueda inteligente (Categoría + Descripción)
    query = f"{row['Categoria']} {row['Descripcion']}"
    
    # Usamos token_set_ratio: es el mejor para descripciones desordenadas
    best_match = process.extractOne(query, choices, scorer=fuzz.token_set_ratio, score_cutoff=85)
    
    if best_match:
        # ¡Encontramos un gemelo!
        nombre_competencia, score = best_match[0], best_match[1]
        
        # --- ENRIQUECIMIENTO ---
        df_kaiqi.at[index, 'Descripcion_Rica'] = nombre_competencia
        df_kaiqi.at[index, 'Imagen_Fuente_Rica'] = image_map[nombre_competencia]
        df_kaiqi.at[index, 'Nivel_Confianza'] = score
        
        matches_encontrados += 1

print(f"\n--- TOTAL MATCHES DE ALTA CONFIANZA: {matches_encontrados} ---")
print("4. Guardando inventario enriquecido (temporal)...")
df_kaiqi.to_csv(OUTPUT_INVENTARIO_ENRIQUECIDO, index=False, sep=';')

# --- 5. PREPARAR ARCHIVOS DE SHOPIFY ---
print("5. Generando archivo de importación Shopify y renombrando imágenes...")

# Columnas finales de Shopify
shopify_cols = [
    "Handle", "Title", "Body (HTML)", "Vendor", "Product category", "Type", "Tags",
    "Published", "Status", "Variant SKU", "Variant Price", "Variant Grams", 
    "Variant Inventory Tracker", "Variant Inventory Qty", "Variant Inventory Policy", 
    "Image Src", "Image Position", "Image Alt Text",
    "KAIQI / Sistema Principal", "KAIQI / Subsistema", "KAIQI / Componente", "KAIQI / Tipo Vehiculo"
]
df_shopify = pd.DataFrame(columns=shopify_cols)

# Función para crear el 'Handle' (URL) y el nombre SEO
def crear_seo_names(row):
    sku = str(row['SKU'])
    # USAMOS LA DESCRIPCIÓN RICA SI LA TENEMOS, SI NO, LA ORIGINAL
    desc = str(row['Descripcion_Rica']) if row['Nivel_Confianza'] >= 85 else str(row['Descripcion'])
    
    # Limpiar descripción para URL/Nombre de archivo
    seo_text = desc.lower()
    seo_text = re.sub(r'[^a-z0-9\s-]', '', seo_text)
    handle = re.sub(r'[\s]+', '-', seo_text).strip('-')
    
    # Nombre final: arbol-de-levas_SKU123.jpg
    seo_filename = f"{handle}_{sku}.jpg" # Forzamos todo a JPG
    return handle, desc, seo_filename

# Lógica de Taxonomía
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
    handle, desc_final, seo_filename = crear_seo_names(row)
    imagen_final_para_csv = ""
    
    # --- Lógica de Copia de Imágenes ---
    fuente_path = None
    if row['Nivel_Confianza'] >= 85:
        # 1. Prioridad: La foto "Rica" que robamos de la competencia
        fuente_path = os.path.join(COMPETENCIA_FOTOS_DIR, str(row['Imagen_Fuente_Rica']))
    
    # Si encontramos una fuente, la copiamos y la convertimos a JPG
    if fuente_path and os.path.exists(fuente_path):
        destino_path = os.path.join(OUTPUT_FOTOS_DIR, seo_filename)
        try:
            # Usamos Pillow para abrir, convertir a RGB (quitar transparencias) y guardar como JPG
            with Image.open(fuente_path) as img:
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(destino_path, "JPEG", quality=90)
            
            imagen_final_para_csv = seo_filename # Solo asignamos si la copia fue exitosa
            total_imagenes_copiadas += 1
        except Exception as e:
            # Si la imagen de la competencia estaba corrupta, no la usamos
            print(f"   ⚠️ Error convirtiendo {fuente_path} (se saltará): {e}")
            
    # --- Llenar Taxonomía ---
    categoria_kaiqi = str(row['Categoria'])
    sistema_principal = get_sistema(categoria_kaiqi)
    componente = categoria_kaiqi # La categoría KAIQI es el componente más específico
    tipo_vehiculo = "MOTOCARGUERO" # Valor por defecto
    
    # Agregar fila al CSV de Shopify
    nueva_fila = {
        "Handle": handle,
        "Title": desc_final,
        "Body (HTML)": desc_final,
        "Vendor": "KAIQI",
        "Product category": "", 
        "Type": categoria_kaiqi, # El tipo de producto (ej: "Bomba Aceite")
        "Tags": f"{sistema_principal}, {componente}",
        "Published": "TRUE",
        "Status": "active",
        "Variant SKU": row['SKU'],
        "Variant Price": row['Precio'],
        "Variant Grams": 500,
        "Variant Inventory Tracker": "shopify",
        "Variant Inventory Qty": 10,
        "Variant Inventory Policy": "continue" if float(row['Precio']) > 0 else "deny",
        "Image Src": imagen_final_para_csv, # El nombre del archivo SEO
        "Image Position": 1,
        "Image Alt Text": desc_final,
        "KAIQI / Sistema Principal": sistema_principal,
        "KAIQI / Subsistema": "", # Dejado en blanco
        "KAIQI / Componente": componente,
        "KAIQI / Tipo Vehiculo": tipo_vehiculo
    }
    df_shopify = pd.concat([df_shopify, pd.DataFrame([nueva_fila])], ignore_index=True)

# Guardar el CSV final
df_shopify.to_csv(OUTPUT_SHOPIFY_CSV, index=False, sep=';', encoding='utf-8-sig')

print("\n" + "="*50)
print(f"✅ ¡PROYECTO FINALIZADO!")
print(f"   -> {OUTPUT_SHOPIFY_CSV} (Listo para subir a Shopify)")
print(f"   -> {OUTPUT_FOTOS_DIR} ({total_imagenes_copiadas} imágenes listas para subir)")
print("="*50)