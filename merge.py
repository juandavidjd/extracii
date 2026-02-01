import pandas as pd
import re
import os

# --- CONFIGURACIÓN DE ARCHIVOS ---
FILE_PRECIOS = 'LISTADO KAIQI NOV-DIC 2025.csv'
FILE_SHOPIFY = 'catalogo_shopify_completo.csv'
OUTPUT_FILE = 'Inventario_KAIQI_Maestro_Final.csv'

print("--- INICIANDO FUSIÓN KAIQI (Modo Robusto v3) ---")

# --- FUNCIÓN DE LECTURA INTELIGENTE ---
def leer_csv_robusto(filepath, nombre_archivo):
    print(f"Leyendo {nombre_archivo}...")
    separadores = [';', ','] # Probamos primero punto y coma (común en tu PC)
    codificaciones = ['latin-1', 'utf-8', 'cp1252']
    
    for sep in separadores:
        for enc in codificaciones:
            try:
                # on_bad_lines='warn' nos avisa si hay líneas rotas pero no detiene el script
                df = pd.read_csv(filepath, sep=sep, encoding=enc, on_bad_lines='warn', dtype=str)
                
                # Verificación: Si leyó solo 1 columna, probablemente el separador está mal
                if df.shape[1] > 1:
                    print(f"   -> Éxito leyendo con separador '{sep}' y codificación '{enc}'")
                    return df
            except Exception:
                continue
    
    print(f"ERROR CRÍTICO: No se pudo leer {nombre_archivo} automáticamente.")
    print("Por favor, abre el CSV en Excel y guárdalo como 'CSV (delimitado por comas)' o 'CSV UTF-8'.")
    exit()

# 1. PROCESAR EL LISTADO DE PRECIOS
df_listado = leer_csv_robusto(FILE_PRECIOS, "Listado de Precios")

# Normalizar columnas (quitamos espacios)
df_listado.columns = df_listado.columns.str.strip()
# Intentamos detectar las columnas dinámicamente
col_sku = next((c for c in df_listado.columns if 'CODIGO' in c.upper()), df_listado.columns[1])
col_desc = next((c for c in df_listado.columns if 'DESCRIPCION' in c.upper()), df_listado.columns[2])
col_cat = next((c for c in df_listado.columns if 'CATEGORIA' in c.upper()), df_listado.columns[3])
col_price = next((c for c in df_listado.columns if 'PRECIO' in c.upper()), df_listado.columns[4])

items_list = []
print("   - Procesando filas del listado...")

for index, row in df_listado.iterrows():
    sku = str(row[col_sku]).strip()
    desc = str(row[col_desc]).strip()
    cat = str(row[col_cat]).strip()
    price_raw = str(row[col_price]).strip()
    
    if sku.lower() in ['nan', '', 'codigo'] or desc.lower() == 'nan':
        continue

    clean_price = re.sub(r'[^\d]', '', price_raw) 
    try:
        final_price = int(clean_price)
    except:
        final_price = 0

    if cat.lower() == 'nan' or cat == '':
        cat = "Repuestos Varios"
    else:
        cat = cat.title()

    items_list.append({
        'SKU_Join': sku,
        'Descripcion_List': desc,
        'Precio_List': final_price,
        'Categoria_List': cat
    })

df_master = pd.DataFrame(items_list)
df_master = df_master.drop_duplicates(subset=['SKU_Join'], keep='first')
print(f"   - Items válidos en Lista 2025: {len(df_master)}")


# 2. PROCESAR SHOPIFY
df_shopify = leer_csv_robusto(FILE_SHOPIFY, "Catálogo Shopify")

def clean_sku_shop(val):
    if pd.isna(val): return ""
    s = str(val).strip()
    s = s.replace("Código:", "").strip()
    if s.endswith(".0"): s = s[:-2]
    return s

# Buscamos la columna SKU y otras
col_sku_shop = next((c for c in df_shopify.columns if 'SKU' in c.upper()), 'SKU')
col_img_shop = next((c for c in df_shopify.columns if 'Image' in c or 'Src' in c), 'Image Src')
col_cat_shop = next((c for c in df_shopify.columns if 'Category' in c or 'Categoría' in c), 'Category')
col_title_shop = next((c for c in df_shopify.columns if 'Title' in c or 'Titulo' in c), 'Title')

df_shopify['SKU_Join'] = df_shopify[col_sku_shop].apply(clean_sku_shop)
df_shopify = df_shopify[df_shopify['SKU_Join'] != ""]
df_shopify['Image Src'] = df_shopify[col_img_shop].fillna("Sin Imagen")

# Nos aseguramos de tener las columnas necesarias
for col in ['Title', 'Category']:
    if col not in df_shopify.columns:
        # Intentamos mapear si tienen nombres distintos
        if col == 'Title' and col_title_shop in df_shopify.columns:
            df_shopify['Title'] = df_shopify[col_title_shop]
        elif col == 'Category' and col_cat_shop in df_shopify.columns:
            df_shopify['Category'] = df_shopify[col_cat_shop]
        else:
            df_shopify[col] = ""

df_shopify_clean = df_shopify[['SKU_Join', 'Title', 'Category', 'Image Src']]


# 3. FUSIÓN
print("3. Fusionando bases de datos...")
df_merged = pd.merge(df_master, df_shopify_clean, on='SKU_Join', how='outer')


# 4. CONSOLIDACIÓN FINAL
print("4. Generando maestro final...")

df_merged['SKU'] = df_merged['SKU_Join']
df_merged['Descripcion'] = df_merged['Descripcion_List'].fillna(df_merged['Title'])
df_merged['Precio'] = df_merged['Precio_List'].fillna(0).astype(int)
df_merged['Categoria'] = df_merged['Categoria_List'].fillna(df_merged['Category']).fillna("Repuestos Varios").str.title()
df_merged['Imagen'] = df_merged['Image Src'].fillna("Sin Imagen")

def determine_origin(row):
    in_list = pd.notna(row['Descripcion_List'])
    in_shop = pd.notna(row['Title'])
    if in_list and in_shop: return "Existente (Actualizado)"
    if in_list: return "Nuevo (Solo en Lista)"
    if in_shop: return "Huérfano (Solo en Shopify)"
    return "Error"

df_merged['Origen_Dato'] = df_merged.apply(determine_origin, axis=1)

df_final = df_merged[['SKU', 'Descripcion', 'Precio', 'Categoria', 'Imagen', 'Origen_Dato']]
df_final = df_final.drop_duplicates(subset=['SKU'], keep='first')
df_final = df_final.sort_values(by=['Categoria', 'Descripcion'])

# 5. GUARDAR
print(f"5. Guardando: {OUTPUT_FILE}")
df_final.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig', sep=',') # Guardamos con coma estándar

print("\n" + "="*40)
print(f"¡ÉXITO TOTAL! Archivo generado: {OUTPUT_FILE}")
print(f"Total items: {len(df_final)}")
print("="*40)
print("Resumen por origen:")
print(df_final['Origen_Dato'].value_counts().to_string())