import pandas as pd
import re
import os

# --- CONFIGURACIÓN DE ARCHIVOS ---
FILE_PRECIOS = 'LISTADO KAIQI NOV-DIC 2025.csv'
FILE_SHOPIFY = 'catalogo_shopify_completo.csv'
OUTPUT_FILE = 'Inventario_KAIQI_Maestro_Final.csv'

print("--- INICIANDO FUSIÓN KAIQI (Corrección Separadores) ---")

# ---------------------------------------------------------
# 1. PROCESAR LISTADO DE PRECIOS (Separador ';')
# ---------------------------------------------------------
print(f"1. Leyendo Listado: {FILE_PRECIOS}...")
try:
    # Leemos sin encabezado para usar posiciones fijas
    df_listado = pd.read_csv(FILE_PRECIOS, sep=';', header=None, encoding='latin-1', dtype=str)
except Exception as e:
    print(f"ERROR LEYENDO LISTADO: {e}")
    exit()

items_list = []
print("   - Extrayendo datos del listado...")

for index, row in df_listado.iterrows():
    try:
        # Posiciones fijas: 1=SKU, 2=Desc, 3=Cat, 4=Precio
        sku_raw = str(row.iloc[1]).strip()
        desc_raw = str(row.iloc[2]).strip()
        cat_raw = str(row.iloc[3]).strip()
        price_raw = str(row.iloc[4]).strip()
    except IndexError:
        continue

    if sku_raw.lower() in ['nan', '', 'codigo', 'codigo new'] or desc_raw.lower() == 'nan':
        continue

    # Limpieza Precio
    clean_price = re.sub(r'[^\d]', '', price_raw)
    try:
        final_price = int(clean_price)
    except:
        final_price = 0

    # Limpieza Categoría
    if cat_raw.lower() in ['nan', '']:
        final_cat = "Repuestos Varios"
    else:
        final_cat = cat_raw.title()

    items_list.append({
        'SKU_Join': sku_raw,
        'Descripcion_List': desc_raw,
        'Precio_List': final_price,
        'Categoria_List': final_cat
    })

df_master = pd.DataFrame(items_list)
df_master = df_master.drop_duplicates(subset=['SKU_Join'], keep='first')
print(f"   -> Items válidos en Lista: {len(df_master)}")


# ---------------------------------------------------------
# 2. PROCESAR SHOPIFY (AHORA CON SEPARADOR ';')
# ---------------------------------------------------------
print(f"2. Leyendo Shopify: {FILE_SHOPIFY}...")
try:
    # AQUÍ ESTÁ EL ARREGLO: sep=';'
    df_shopify = pd.read_csv(FILE_SHOPIFY, sep=';', encoding='latin-1', dtype=str)
except:
    try:
        df_shopify = pd.read_csv(FILE_SHOPIFY, sep=';', encoding='utf-8', dtype=str)
    except Exception as e:
        print(f"ERROR CRÍTICO LEYENDO SHOPIFY: {e}")
        exit()

# Normalizar nombres de columnas (quitar espacios)
df_shopify.columns = df_shopify.columns.str.strip()

# Buscar columnas dinámicamente
col_sku = next((c for c in df_shopify.columns if 'SKU' in c.upper()), None)
col_title = next((c for c in df_shopify.columns if 'Title' in c or 'Titulo' in c), None)
col_cat = next((c for c in df_shopify.columns if 'Category' in c or 'Categoría' in c), None)
col_img = next((c for c in df_shopify.columns if 'Image' in c or 'Src' in c), None)

if not col_sku:
    print("ERROR: No se encontró columna SKU en el archivo de Shopify.")
    print("Columnas detectadas:", df_shopify.columns.tolist())
    exit()

# Limpieza SKU Shopify
def clean_sku_shop(val):
    if pd.isna(val): return ""
    s = str(val).strip()
    s = s.replace("Código:", "").strip()
    if s.endswith(".0"): s = s[:-2]
    return s

df_shopify['SKU_Join'] = df_shopify[col_sku].apply(clean_sku_shop)
df_shopify = df_shopify[df_shopify['SKU_Join'] != ""]

# Preparar columnas
df_shopify['Title'] = df_shopify[col_title] if col_title else ""
df_shopify['Category'] = df_shopify[col_cat] if col_cat else ""
df_shopify['Image Src'] = df_shopify[col_img] if col_img else "Sin Imagen"

df_shopify_clean = df_shopify[['SKU_Join', 'Title', 'Category', 'Image Src']]
print(f"   -> Items válidos en Shopify: {len(df_shopify_clean)}")


# ---------------------------------------------------------
# 3. FUSIÓN Y CONSOLIDACIÓN
# ---------------------------------------------------------
print("3. Fusionando y Consolidando...")

# Asegurar tipos string para el cruce
df_master['SKU_Join'] = df_master['SKU_Join'].astype(str)
df_shopify_clean['SKU_Join'] = df_shopify_clean['SKU_Join'].astype(str)

df_merged = pd.merge(df_master, df_shopify_clean, on='SKU_Join', how='outer')

df_merged['SKU'] = df_merged['SKU_Join']
df_merged['Descripcion'] = df_merged['Descripcion_List'].fillna(df_merged['Title'])
df_merged['Precio'] = df_merged['Precio_List'].fillna(0).astype(int)
df_merged['Categoria'] = df_merged['Categoria_List'].fillna(df_merged['Category']).fillna("Repuestos Varios").str.title()
df_merged['Imagen'] = df_merged['Image Src'].fillna("Sin Imagen")

def get_origin(row):
    in_list = pd.notna(row['Descripcion_List'])
    in_shop = pd.notna(row['Title'])
    if in_list and in_shop: return "Existente (Actualizado)"
    if in_list: return "Nuevo (Solo en Lista)"
    if in_shop: return "Huérfano (Solo en Shopify)"
    return "Error"

df_merged['Origen_Dato'] = df_merged.apply(get_origin, axis=1)

final_cols = ['SKU', 'Descripcion', 'Precio', 'Categoria', 'Imagen', 'Origen_Dato']
df_final = df_merged[final_cols].drop_duplicates(subset=['SKU']).sort_values(['Categoria', 'Descripcion'])

# ---------------------------------------------------------
# 4. GUARDAR
# ---------------------------------------------------------
print(f"4. Guardando: {OUTPUT_FILE}")
# Guardamos con comas (sep=',') para que sea estándar mundial
df_final.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig', sep=',')

print("\n" + "="*40)
print(f"¡LISTO! Total items: {len(df_final)}")
print("="*40)
print(df_final['Origen_Dato'].value_counts().to_string())