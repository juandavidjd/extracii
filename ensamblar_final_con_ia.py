import pandas as pd
import os
import re
import shutil
from thefuzz import fuzz
from thefuzz import process

# --- CONFIGURACIÓN ---
PROJECT_DIR = r'C:\KAIQI_PROYECTO_FINAL'

# 1. Archivos de Entrada
FILE_INVENTARIO = os.path.join(PROJECT_DIR, 'Inventario_FINAL_CON_TAXONOMIA.csv')
FILE_CATALOGO_IA = os.path.join(PROJECT_DIR, 'catalogo_kaiqi_imagenes.csv')
DIR_IMAGENES_ORIGEN = os.path.join(PROJECT_DIR, 'FOTOS_COMPETENCIA')

# 2. Salidas
OUTPUT_SHOPIFY = os.path.join(PROJECT_DIR, 'Shopify_Import_Definitivo_V13.csv')
OUTPUT_DIR_IMAGENES = os.path.join(PROJECT_DIR, 'IMAGENES_PARA_SHOPIFY')

# Crear carpeta de salida limpia
if os.path.exists(OUTPUT_DIR_IMAGENES):
    shutil.rmtree(OUTPUT_DIR_IMAGENES)
os.makedirs(OUTPUT_DIR_IMAGENES)

print("--- SCRIPT V13: ENSAMBLE FINAL CON INTELIGENCIA ARTIFICIAL ---")

# --- 1. CARGAR DATOS ---
try:
    print("1. Cargando bases de datos...")
    df_inv = pd.read_csv(FILE_INVENTARIO, sep=';', encoding='utf-8-sig', dtype=str)
    df_ia = pd.read_csv(FILE_CATALOGO_IA, sep=';', encoding='utf-8-sig', dtype=str)
    
    print(f"   -> Inventario KAIQI: {len(df_inv)} productos.")
    print(f"   -> Catálogo IA: {len(df_ia)} imágenes analizadas.")
    
    # Preparar datos de IA para búsqueda rápida
    # Creamos una lista de textos de búsqueda combinando Nombre y Compatibilidad
    df_ia['Texto_Busqueda'] = df_ia['Nombre_Comercial_Catalogo'].fillna('') + " " + df_ia['Compatibilidad_Probable_Texto'].fillna('')
    opciones_ia = df_ia['Texto_Busqueda'].tolist()
    
    # Mapa para recuperar datos de IA rápidamente usando el índice
    mapa_ia = df_ia.to_dict('index')
    
except Exception as e:
    print(f"❌ Error fatal cargando archivos: {e}")
    exit()

# --- 2. FUNCIONES DE LIMPIEZA ---
def limpiar_texto_seo(text):
    if pd.isna(text): return ""
    text = str(text).lower()
    text = text.replace('ñ', 'n').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'\s+', '-', text).strip('-')
    return text

def format_titulo(text):
    if pd.isna(text): return ""
    text = str(text).replace('Ã±', 'ñ').replace('Ã³', 'ó') # Fix encoding rápido
    # Capitalizar marcas conocidas
    for marca in ['AKT', 'AYCO', 'KYMCO', 'BWS', 'NKD', 'SLR', 'TTR', 'CGR', 'CG', 'CDI', 'LED', 'OEM', 'KAIQI', 'BAJAJ', 'YAMAHA', 'HONDA', 'SUZUKI']:
        pattern = re.compile(re.escape(marca), re.IGNORECASE)
        text = pattern.sub(marca, text)
    return text

# --- 3. PROCESAMIENTO Y MATCHING ---
print("2. Iniciando fusión inteligente (Matching)...")

resultados_shopify = []
matches_encontrados = 0

for idx, row in df_inv.iterrows():
    sku = str(row['SKU'])
    # Usamos la descripción que ya habías construido/pulido en V11 como base
    desc_base = str(row['Descripcion']) 
    componente = str(row['Componente'])
    
    # Datos por defecto (si no hay match IA)
    titulo_final = format_titulo(desc_base)
    body_html = f"<p><strong>Repuesto:</strong> {componente}</p><p>Calidad garantizada KAIQI.</p>"
    img_filename_final = ""
    
    # --- FUZZY MATCHING ---
    # Buscamos la descripción del inventario en la base de datos de la IA
    query = f"{componente} {desc_base}"
    match = process.extractOne(query, opciones_ia, scorer=fuzz.token_set_ratio)
    
    if match and match[1] >= 80: # Umbral de confianza
        matches_encontrados += 1
        idx_ia = opciones_ia.index(match[0])
        datos_ia = mapa_ia[idx_ia]
        
        # --- ENRIQUECIMIENTO ---
        # 1. Título Híbrido: Usamos tu descripción (que tiene el modelo exacto) pero pulida
        # A veces la IA da un nombre muy genérico "Bobina", tu inventario tiene "Bobina Crypton". Nos quedamos con el tuyo para el título, pero usamos la data IA para el cuerpo.
        titulo_final = format_titulo(desc_base) 
        
        # 2. Descripción Rica (HTML)
        funcion = str(datos_ia.get('Funcion', 'Repuesto de alta calidad.'))
        compatibilidad = str(datos_ia.get('Compatibilidad_Probable_Texto', 'Verificar con muestra.'))
        body_html = f"""
        <p><strong>Producto:</strong> {titulo_final}</p>
        <p><strong>Función:</strong> {funcion}</p>
        <p><strong>Compatibilidad Sugerida:</strong> {compatibilidad}</p>
        <p><em>Nota: Las imágenes son de referencia. Verifique visualmente su repuesto.</em></p>
        """
        
        # 3. Imagen y Renombrado
        img_original_name = datos_ia['Filename_Original']
        ruta_origen = os.path.join(DIR_IMAGENES_ORIGEN, img_original_name)
        
        if os.path.exists(ruta_origen):
            # NOMBRE SEO: titulo-del-producto_SKU.jpg
            ext = os.path.splitext(img_original_name)[1]
            nuevo_nombre = f"{limpiar_texto_seo(titulo_final)}_{sku}{ext}"
            ruta_destino = os.path.join(OUTPUT_DIR_IMAGENES, nuevo_nombre)
            
            try:
                shutil.copy2(ruta_origen, ruta_destino)
                img_filename_final = nuevo_nombre # Este va al CSV
            except Exception:
                pass

    # --- CONSTRUIR FILA SHOPIFY ---
    row_shopify = {
        "Handle": limpiar_texto_seo(titulo_final),
        "Title": titulo_final,
        "Body (HTML)": body_html,
        "Vendor": "KAIQI",
        "Product category": "",
        "Type": format_titulo(row['Componente']),
        "Tags": f"{row['Sistema Principal']},{row['Subsistema']},{row['Componente']},{row['Tipo Vehiculo']}",
        "Published": "TRUE",
        "Status": "active",
        "Variant SKU": sku,
        "Variant Price": row['Precio'],
        "Variant Grams": 500,
        "Variant Inventory Tracker": "shopify",
        "Variant Inventory Qty": 10,
        "Variant Inventory Policy": "deny",
        "Image Src": img_filename_final, # Aquí va el nombre SEO o vacío
        "Image Position": 1 if img_filename_final else "",
        "Image Alt Text": titulo_final,
        # Metafields KAIQI
        "KAIQI_Codigo_New": row['CODIGO NEW'],
        "KAIQI_Sistema": row['Sistema Principal'],
        "KAIQI_Subsistema": row['Subsistema']
    }
    resultados_shopify.append(row_shopify)

# --- 4. EXPORTAR ---
print(f"3. Generando archivo final...")
df_final = pd.DataFrame(resultados_shopify)
df_final.to_csv(OUTPUT_SHOPIFY, index=False, sep=';', encoding='utf-8-sig')

print("\n" + "="*50)
print(f"✅ ¡MISIÓN CUMPLIDA!")
print(f"   -> Total Procesados: {len(df_inv)}")
print(f"   -> Matches con IA (Fotos + Datos): {matches_encontrados}")
print(f"   -> Archivo CSV Final: {OUTPUT_SHOPIFY}")
print(f"   -> Carpeta Imágenes Renombradas: {OUTPUT_DIR_IMAGENES}")
print("="*50)
print("👉 Siguiente paso: Sube las imágenes de la carpeta a Shopify (Contenido > Archivos) y luego importa el CSV.")