import pandas as pd
import os
import re
import shutil
import random
from thefuzz import fuzz
from PIL import Image

# --- CONFIGURACIÓN ---
PROJECT_DIR = r'C:\KAIQI_PROYECTO_FINAL'
FILE_INVENTARIO = os.path.join(PROJECT_DIR, 'Inventario_FINAL_CON_TAXONOMIA.csv')
FILE_CATALOGO_IA = os.path.join(PROJECT_DIR, 'catalogo_kaiqi_imagenes.csv')
DIR_IMAGENES_ORIGEN = os.path.join(PROJECT_DIR, 'FOTOS_COMPETENCIA')
OUTPUT_SHOPIFY = os.path.join(PROJECT_DIR, 'Shopify_Import_Definitivo_V14.csv')
OUTPUT_DIR_IMAGENES = os.path.join(PROJECT_DIR, 'IMAGENES_PARA_SHOPIFY')

# Limpieza inicial
if os.path.exists(OUTPUT_DIR_IMAGENES):
    shutil.rmtree(OUTPUT_DIR_IMAGENES)
os.makedirs(OUTPUT_DIR_IMAGENES)

print("--- SCRIPT V14: ENSAMBLE INTELIGENTE POR CONTEXTO ---")

# --- 1. CARGAR DATOS ---
try:
    print("1. Cargando bases de datos...")
    df_inv = pd.read_csv(FILE_INVENTARIO, sep=';', encoding='utf-8-sig', dtype=str)
    df_ia = pd.read_csv(FILE_CATALOGO_IA, sep=';', encoding='utf-8-sig', dtype=str)
    
    # Normalizar columnas clave para evitar errores de cruce
    df_inv['Sistema Principal'] = df_inv['Sistema Principal'].fillna('VARIOS').str.upper()
    df_ia['Sistema'] = df_ia['Sistema'].fillna('VARIOS').str.upper()
    
    print(f"   -> Inventario: {len(df_inv)} productos.")
    print(f"   -> Banco de Imágenes IA: {len(df_ia)} fotos.")

except Exception as e:
    print(f"❌ Error fatal: {e}")
    exit()

# --- 2. FUNCIONES ---
def limpiar(text):
    if pd.isna(text): return ""
    text = str(text).lower()
    text = text.replace('ñ', 'n').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
    return re.sub(r'[^a-z0-9\s]', '', text).strip()

def get_score(row_inv, row_ia):
    # Puntuación basada en coincidencia de palabras clave
    texto_inv = limpiar(f"{row_inv['Componente']} {row_inv['Descripcion']}")
    texto_ia = limpiar(f"{row_ia['Nombre_Comercial_Catalogo']} {row_ia['Compatibilidad_Probable_Texto']}")
    
    # 1. Coincidencia del Componente (Es lo mas importante)
    comp_inv = limpiar(row_inv['Componente'])
    comp_ia = limpiar(row_ia['Componente_Taxonomia']) # O 'Identificacion_Repuesto'
    
    base_score = fuzz.token_set_ratio(comp_inv, comp_ia)
    
    # 2. Bonus por Marca/Modelo
    bonus = 0
    if base_score > 80: # Solo si el componente parece ser el mismo
        match_score = fuzz.token_set_ratio(texto_inv, texto_ia)
        bonus = match_score / 2 # Le damos peso al detalle
        
    return base_score + bonus

# --- 3. AGRUPAR IMÁGENES POR SISTEMA (Para búsqueda rápida) ---
print("2. Indexando imágenes por Sistema...")
imagenes_por_sistema = {}
for idx, row in df_ia.iterrows():
    sistema = row['Sistema'] # Ej: MOTOR, ELECTRICO
    # Mapeo manual de sistemas si difieren
    if 'MOTOR' in sistema: sistema = 'MOTOR'
    elif 'FREN' in sistema or 'CHASIS' in sistema: sistema = 'CHASIS Y FRENOS'
    elif 'ELEC' in sistema or 'LUZ' in sistema: sistema = 'SISTEMA ELECTRICO'
    elif 'TRANS' in sistema: sistema = 'TRANSMISION'
    else: sistema = 'ACCESORIOS Y OTROS'
    
    if sistema not in imagenes_por_sistema:
        imagenes_por_sistema[sistema] = []
    imagenes_por_sistema[sistema].append(row)

# --- 4. PROCESAMIENTO ---
print("3. Ejecutando 'El Francotirador' (Matching)...")
resultados = []
matches_count = 0
usadas_tracker = {} # Para intentar no repetir fotos seguidas

for idx, prod in df_inv.iterrows():
    sku = str(prod['SKU'])
    sistema_prod = prod['Sistema Principal']
    
    # Determinar dónde buscar
    grupo_busqueda = []
    if sistema_prod in imagenes_por_sistema:
        grupo_busqueda = imagenes_por_sistema[sistema_prod]
    else:
        # Si no encuentra el sistema exacto, busca en todo (fallback)
        for k in imagenes_por_sistema:
            grupo_busqueda.extend(imagenes_por_sistema[k])
            
    # Buscar mejor match en el grupo
    mejor_match = None
    mejor_score = 0
    
    for img_candidate in grupo_busqueda:
        score = get_score(prod, img_candidate)
        if score > mejor_score:
            mejor_score = score
            mejor_match = img_candidate
    
    # Decisión
    img_final = ""
    desc_final = prod['Descripcion'] # Por defecto la original
    
    if mejor_score > 85: # Umbral de aceptación
        matches_count += 1
        img_name_orig = mejor_match['Filename_Original']
        
        # Enriquecer descripción
        desc_final = f"{prod['Componente'].title()} {prod['Descripcion']} ({mejor_match['Nombre_Comercial_Catalogo']})"
        desc_final = desc_final.replace("  ", " ").strip()

        # Copiar imagen
        src_path = os.path.join(DIR_IMAGENES_ORIGEN, img_name_orig)
        if os.path.exists(src_path):
            ext = os.path.splitext(img_name_orig)[1]
            # NOMBRE ÚNICO: Para que Shopify no detecte duplicados por nombre, usamos el SKU
            new_name = f"{limpiar(prod['Descripcion']).replace(' ','-')}_{sku}{ext}"
            dst_path = os.path.join(OUTPUT_DIR_IMAGENES, new_name)
            shutil.copy2(src_path, dst_path)
            img_final = new_name

    # Fila Shopify
    row_shopify = {
        "Handle": cleaning_handle(prod['Descripcion']),
        "Title": desc_final.title(),
        "Body (HTML)": f"<p>{desc_final}</p>",
        "Vendor": "KAIQI",
        "Type": prod['Componente'],
        "Tags": f"{prod['Sistema Principal']},{prod['Tipo Vehiculo']}",
        "Published": "TRUE",
        "Variant SKU": sku,
        "Variant Price": prod['Precio'],
        "Variant Inventory Qty": 10,
        "Image Src": img_final,
        "Image Position": 1 if img_final else "",
        "Image Alt Text": desc_final
    }
    resultados.append(row_shopify)

# Helper para handle
def cleaning_handle(s):
    return re.sub(r'[^a-z0-9-]', '', str(s).lower().replace(' ', '-'))

# --- 5. EXPORTAR ---
df_out = pd.DataFrame(resultados)
# Corrección de handles (función lambda falló arriba por scope, la aplicamos acá)
df_out['Handle'] = df_out['Title'].apply(lambda x: re.sub(r'[^a-z0-9-]', '', str(x).lower().replace(' ', '-')).strip('-'))

df_out.to_csv(OUTPUT_SHOPIFY, index=False, sep=';', encoding='utf-8-sig')

print("\n" + "="*50)
print(f"✅ REPORTE DE MISIÓN V14")
print(f"   -> Inventario Total: {len(df_inv)}")
print(f"   -> Matches Encontrados: {matches_count} (Debería ser mucho más que 89)")
print(f"   -> Archivo Final: {OUTPUT_SHOPIFY}")
print(f"   -> Carpeta Imágenes: {OUTPUT_DIR_IMAGENES}")
print("="*50)