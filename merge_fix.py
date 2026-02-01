import pandas as pd
import re
import os

# --- CONFIGURACIÓN DE ARCHIVOS ---
FILE_PRECIOS = 'LISTADO KAIQI NOV-DIC 2025.csv'
FILE_SHOPIFY = 'catalogo_shopify_completo.csv'
OUTPUT_FILE = 'Inventario_KAIQI_Maestro_Final.csv'

print("--- INICIANDO FUSIÓN KAIQI (Modo Posicional Blindado) ---")

# --- 1. LECTURA LISTADO DE PRECIOS ---
print(f"1. Leyendo: {FILE_PRECIOS}...")
try:
    # Leemos SIN encabezado (header=None) para usar índices numéricos fijos (0, 1, 2...)
    # Esto evita que el "nan" de la primera columna rompa todo.
    df_listado = pd.read_csv(FILE_PRECIOS, sep=';', header=None, encoding='latin-1', dtype=str)
    print(f"   -> Archivo leído. Filas totales: {len(df_listado)}")
    # Mostramos la primera fila para confirmar qué estamos leyendo
    print(f"   -> Primera fila cruda: {df_listado.iloc[0].tolist()}")
except Exception as e:
    print(f"ERROR LEYENDO CSV: {e}")
    exit()

items_list = []
print("   - Extrayendo datos por posición (Col 1=SKU, Col 2=Desc, Col 3=Cat, Col 4=Precio)...")

# Iteramos
for index, row in df_listado.iterrows():
    # Usamos .iloc para ir a la posición segura (ignorando nombres)
    # Basado en tu archivo: Col 0 es basura (nan), Col 1 es CODIGO, etc.
    try:
        sku_raw = str(row.iloc[1]).strip()   # Columna B
        desc_raw = str(row.iloc[2]).strip()  # Columna C
        cat_raw = str(row.iloc[3]).strip()   # Columna D
        price_raw = str(row.iloc[4]).strip() # Columna E
    except IndexError:
        continue # Si la fila es muy corta, la saltamos

    # FILTROS DE BASURA
    # Si el SKU es "nan", "CODIGO", o está vacío, saltamos
    if sku_raw.lower() in ['nan', '', 'codigo', 'codigo new'] or desc_raw.lower() == 'nan':
        continue

    # LIMPIEZA PRECIO
    clean_price = re.sub(r'[^\d]', '', price_raw)
    try:
        final_price = int(clean_price)
    except:
        final_price = 0

    # LIMPIEZA CATEGORÍA
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

# CREACIÓN DATAFRAME MAESTRO
if len(items_list) == 0:
    print("\nERROR ROJO: No se detectaron productos. Verifica los índices de columnas.")
    print("¿Tu archivo tiene la columna CODIGO en la columna B (índice 1)?")
    exit()

df_master = pd.DataFrame(items_list)
df_master = df_master.drop_duplicates(subset=['SKU_Join'], keep='first')
print(f"   -> ¡Éxito! Items válidos extraídos: {len(df_master)}")


# --- 2. LECTURA SHOPIFY ---
print(f"2. Leyendo Shopify: {FILE_SHOPIFY}...")
try:
    df_shopify = pd.read_csv(FILE_SHOPIFY, encoding='latin-1', on_bad_lines='skip')
except:
    df_shopify = pd.read_csv(FILE_SHOPIFY, encoding='utf-8', on_bad_lines='skip')

def clean_sku_shop(val):
    if pd.isna(val): return ""
    s = str(val).strip()
    s = s.replace("Código:", "").strip()
    if s.endswith(".0"): s = s[:-2]
    return s

# Detectar columna SKU en Shopify dinámicamente
col_sku_shop = next((c for c in df_shopify.columns if 'SKU' in str(c).upper()), df_shopify.columns[0])
df_shopify['SKU_Join'] = df_shopify[col_sku_shop].apply(clean_sku_shop)
df_shopify = df_shopify[df_shopify['SKU_Join'] != ""]

# Detectar imagen
col_img = next((c for c in df_shopify.columns if 'Image' in str(c) or 'Src' in str(c)), None)
if col_img:
    df_shopify['Image Src'] = df_shopify[col_img].fillna("Sin Imagen")
else:
    df_shopify['Image Src'] = "Sin Imagen"

# Detectar título
col_title = next((c for c in df_shopify.columns if 'Title' in str(c)), None)
if col_title:
    df_shopify['Title'] = df_shopify[col_title]
else:
    df_shopify['Title'] = ""

# Detectar categoría web
col_cat_web = next((c for c in df_shopify.columns if 'Category' in str(c) or 'Categoría' in str(c)), None)
if col_cat_web:
    df_shopify['Category'] = df_shopify[col_cat_web]
else:
    df_shopify['Category'] = ""

df_shopify_clean = df_shopify[['SKU_Join', 'Title', 'Category', 'Image Src']]


# --- 3. FUSIÓN ---
print("3. Fusionando...")
# Aseguramos que ambas columnas clave sean string
df_master['SKU_Join'] = df_master['SKU_Join'].astype(str)
df_shopify_clean['SKU_Join'] = df_shopify_clean['SKU_Join'].astype(str)

df_merged = pd.merge(df_master, df_shopify_clean, on='SKU_Join', how='outer')


# --- 4. CONSOLIDACIÓN ---
print("4. Consolidando...")
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

# GUARDAR
print(f"5. Guardando: {OUTPUT_FILE}")
df_final.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')

print("\n" + "="*40)
print(f"¡FUSIÓN COMPLETADA! Total items: {len(df_final)}")
print("="*40)
print(df_final['Origen_Dato'].value_counts().to_string())