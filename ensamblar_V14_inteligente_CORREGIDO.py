import pandas as pd
import os
import re
import shutil
from thefuzz import fuzz
from thefuzz import process

# --- CONFIGURACIÓN ---
PROJECT_DIR = r'C:\KAIQI_PROYECTO_FINAL'
FILE_INVENTARIO = os.path.join(PROJECT_DIR, 'Inventario_FINAL_CON_TAXONOMIA.csv')
FILE_CATALOGO_IA = os.path.join(PROJECT_DIR, 'catalogo_kaiqi_imagenes.csv')
DIR_IMAGENES_ORIGEN = os.path.join(PROJECT_DIR, 'FOTOS_COMPETENCIA')
OUTPUT_SHOPIFY = os.path.join(PROJECT_DIR, 'Shopify_Import_Definitivo_V14.csv')
OUTPUT_DIR_IMAGENES = os.path.join(PROJECT_DIR, 'IMAGENES_PARA_SHOPIFY')

# Limpieza inicial de carpeta de salida
if os.path.exists(OUTPUT_DIR_IMAGENES):
    shutil.rmtree(OUTPUT_DIR_IMAGENES)
os.makedirs(OUTPUT_DIR_IMAGENES)

print("--- SCRIPT V14 (CORREGIDO): ENSAMBLE INTELIGENTE POR CONTEXTO ---")

# --- 1. FUNCIONES DE LIMPIEZA Y UTILIDAD ---
def limpiar(text):
    if pd.isna(text): return ""
    text = str(text).lower()
    # Mapeo de caracteres latinos
    text = text.replace('ñ', 'n').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
    return re.sub(r'[^a-z0-9\s]', '', text).strip()

def cleaning_handle(s):
    # Crea una URL amigable (handle) para Shopify y nombres de archivo
    if pd.isna(s): return "producto-sin-nombre"
    s = str(s).lower()
    s = s.replace('ñ', 'n').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
    s = re.sub(r'[^a-z0-9-]', '', s.replace(' ', '-'))
    return re.sub(r'-+', '-', s).strip('-')

def get_score(row_inv, row_ia):
    # Puntuación basada en coincidencia de palabras clave
    # Usamos .fillna('') para evitar errores si hay celdas vacías
    comp_inv_raw = str(row_inv['Componente']) if pd.notna(row_inv['Componente']) else ""
    desc_inv_raw = str(row_inv['Descripcion']) if pd.notna(row_inv['Descripcion']) else ""
    
    nombre_ia_raw = str(row_ia['Nombre_Comercial_Catalogo']) if pd.notna(row_ia['Nombre_Comercial_Catalogo']) else ""
    compat_ia_raw = str(row_ia['Compatibilidad_Probable_Texto']) if pd.notna(row_ia['Compatibilidad_Probable_Texto']) else ""
    comp_ia_raw = str(row_ia['Componente_Taxonomia']) if pd.notna(row_ia['Componente_Taxonomia']) else ""

    # Texto completo para comparar
    texto_inv = limpiar(f"{comp_inv_raw} {desc_inv_raw}")
    texto_ia = limpiar(f"{nombre_ia_raw} {compat_ia_raw}")
    
    # 1. Coincidencia del Componente (Es lo mas importante)
    # Si el componente no coincide, penalizamos fuertemente
    comp_inv = limpiar(comp_inv_raw)
    comp_ia = limpiar(comp_ia_raw)
    
    if not comp_inv or not comp_ia:
        return 0

    base_score = fuzz.token_set_ratio(comp_inv, comp_ia)
    
    # 2. Bonus por Marca/Modelo (Solo si el componente parece ser el mismo)
    bonus = 0
    if base_score > 75: # Bajamos un poco el umbral para ser más flexibles con sinonimos
        # Comparamos la descripción completa
        match_score = fuzz.token_set_ratio(texto_inv, texto_ia)
        bonus = match_score / 2 # Le damos peso al detalle
        
    return base_score + bonus

# --- 2. CARGAR DATOS ---
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
    print(f"❌ Error fatal cargando archivos: {e}")
    exit()

# --- 3. AGRUPAR IMÁGENES POR SISTEMA (Para búsqueda rápida) ---
print("2. Indexando imágenes por Sistema...")
imagenes_por_sistema = {}
for idx, row in df_ia.iterrows():
    sistema = str(row['Sistema'])
    # Mapeo manual de sistemas para asegurar coincidencia
    if 'MOTOR' in sistema: sistema_norm = 'MOTOR'
    elif 'FREN' in sistema or 'CHASIS' in sistema: sistema_norm = 'CHASIS Y FRENOS'
    elif 'ELEC' in sistema or 'LUZ' in sistema: sistema_norm = 'SISTEMA ELECTRICO'
    elif 'TRANS' in sistema: sistema_norm = 'TRANSMISION'
    else: sistema_norm = 'ACCESORIOS Y OTROS'
    
    if sistema_norm not in imagenes_por_sistema:
        imagenes_por_sistema[sistema_norm] = []
    imagenes_por_sistema[sistema_norm].append(row)

# --- 4. PROCESAMIENTO ---
print("3. Ejecutando 'El Francotirador' (Matching)...")
resultados = []
matches_count = 0

for idx, prod in df_inv.iterrows():
    sku = str(prod['SKU'])
    sistema_prod = prod['Sistema Principal']
    
    # Normalizar sistema del producto para buscar en el grupo correcto
    grupo_busqueda = []
    sistema_prod_norm = 'ACCESORIOS Y OTROS'
    if 'MOTOR' in sistema_prod: sistema_prod_norm = 'MOTOR'
    elif 'FREN' in sistema_prod or 'CHASIS' in sistema_prod: sistema_prod_norm = 'CHASIS Y FRENOS'
    elif 'ELEC' in sistema_prod: sistema_prod_norm = 'SISTEMA ELECTRICO'
    elif 'TRANS' in sistema_prod: sistema_prod_norm = 'TRANSMISION'
    
    if sistema_prod_norm in imagenes_por_sistema:
        grupo_busqueda = imagenes_por_sistema[sistema_prod_norm]
    else:
        # Fallback: buscar en todo si no hay coincidencia de sistema
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
    img_final_name_csv = ""
    desc_final = prod['Descripcion'] # Usamos tu descripción reparada
    
    if mejor_score > 85: # Umbral de aceptación
        matches_count += 1
        img_name_orig = mejor_match['Filename_Original']
        
        # Enriquecer descripción HTML con datos de IA
        funcion_ia = str(mejor_match['Funcion']) if pd.notna(mejor_match['Funcion']) else ""
        compat_ia = str(mejor_match['Compatibilidad_Probable_Texto']) if pd.notna(mejor_match['Compatibilidad_Probable_Texto']) else ""
        
        body_html = f"""
        <p><strong>{desc_final}</strong></p>
        <p>{funcion_ia}</p>
        <p><strong>Compatibilidad:</strong> {compat_ia}</p>
        <p><em>Calidad garantizada KAIQI.</em></p>
        """

        # Copiar y Renombrar imagen
        src_path = os.path.join(DIR_IMAGENES_ORIGEN, img_name_orig)
        if os.path.exists(src_path):
            ext = os.path.splitext(img_name_orig)[1]
            # NOMBRE ÚNICO SEO: descripcion-reparada_SKU.jpg
            handle_name = cleaning_handle(desc_final)
            new_name = f"{handle_name}_{sku}{ext}"
            dst_path = os.path.join(OUTPUT_DIR_IMAGENES, new_name)
            try:
                shutil.copy2(src_path, dst_path)
                img_final_name_csv = new_name
            except Exception:
                pass 
    else:
        # Sin match de IA, body básico
        body_html = f"<p><strong>{desc_final}</strong></p><p>Repuesto de alta calidad para motocicletas y motocargueros.</p>"

    # Fila Shopify
    row_shopify = {
        "Handle": cleaning_handle(desc_final),
        "Title": desc_final,
        "Body (HTML)": body_html,
        "Vendor": "KAIQI",
        "Product category": "",
        "Type": str(prod['Componente']),
        "Tags": f"{prod['Sistema Principal']},{prod['Subsistema']},{prod['Componente']},{prod['Tipo Vehiculo']}",
        "Published": "TRUE",
        "Status": "active",
        "Variant SKU": sku,
        "Variant Price": prod['Precio'],
        "Variant Grams": 500,
        "Variant Inventory Tracker": "shopify",
        "Variant Inventory Qty": 10,
        "Variant Inventory Policy": "deny",
        "Image Src": img_final_name_csv,
        "Image Position": 1 if img_final_name_csv else "",
        "Image Alt Text": desc_final,
        # Metafields
        "KAIQI / CODIGO NEW": prod['CODIGO NEW'],
        "KAIQI / Sistema Principal": prod['Sistema Principal'],
        "KAIQI / Subsistema": prod['Subsistema'],
        "KAIQI / Componente": prod['Componente'],
        "KAIQI / Tipo Vehiculo": prod['Tipo Vehiculo']
    }
    resultados.append(row_shopify)

# --- 5. EXPORTAR ---
df_out = pd.DataFrame(resultados)
df_out.to_csv(OUTPUT_SHOPIFY, index=False, sep=';', encoding='utf-8-sig')

print("\n" + "="*50)
print(f"✅ REPORTE DE MISIÓN V14 (FINAL)")
print(f"   -> Inventario Total: {len(df_inv)}")
print(f"   -> Matches Encontrados: {matches_count}")
print(f"   -> Archivo Final: {OUTPUT_SHOPIFY}")
print(f"   -> Carpeta Imágenes: {OUTPUT_DIR_IMAGENES}")
print("="*50)