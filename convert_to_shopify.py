import pandas as pd
import re
import os

# --- CONFIGURACIÓN ---
INPUT_FILE = 'Inventario_KAIQI_Shopify_Ready.csv'
OUTPUT_FILE = 'Shopify_Import_KAIQI.csv'

print("--- INICIANDO CONVERSIÓN A FORMATO SHOPIFY ---")

# 1. CARGAR DATOS
try:
    df = pd.read_csv(INPUT_FILE)
    print(f"1. Leyendo {INPUT_FILE}...")
except FileNotFoundError:
    print(f"Error: No se encuentra {INPUT_FILE}. Asegúrate de haber ejecutado el paso anterior.")
    exit()

# 2. CREAR ESTRUCTURA SHOPIFY
# Lista de columnas exactas solicitadas
shopify_cols = [
    "Title", "URL handle", "Description", "Vendor", "Product category", "Type", "Tags",
    "Published on online store", "Status", "SKU", "Barcode", "Option1 name", "Option1 value",
    "Option2 name", "Option2 value", "Option3 name", "Option3 value", "Price", "Compare-at price",
    "Cost per item", "Charge tax", "Tax code", "Unit price total measure", "Unit price total measure unit",
    "Unit price base measure", "Unit price base measure unit", "Inventory tracker", "Inventory quantity",
    "Continue selling when out of stock", "Weight value (grams)", "Weight unit for display", "Requires shipping",
    "Fulfillment service", "Product image URL", "Image position", "Image alt text", "Variant image URL",
    "Gift card", "SEO title", "SEO description", "Google Shopping / Google product category",
    "Google Shopping / Gender", "Google Shopping / Age group", "Google Shopping / MPN",
    "Google Shopping / AdWords Grouping", "Google Shopping / AdWords labels", "Google Shopping / Condition",
    "Google Shopping / Custom product", "Google Shopping / Custom label 0", "Google Shopping / Custom label 1",
    "Google Shopping / Custom label 2", "Google Shopping / Custom label 3", "Google Shopping / Custom label 4"
]

# Crear DataFrame vacío con esas columnas
df_shopify = pd.DataFrame(columns=shopify_cols)

# 3. MAPEO Y TRANSFORMACIÓN
print("2. Transformando datos y generando Handles...")

# Función para generar Handle (slug único)
def generate_handle(row):
    # Handle = Titulo + SKU (para asegurar unicidad y evitar conflictos)
    text = f"{str(row['Descripcion'])} {str(row['SKU'])}"
    # Limpieza: minúsculas, reemplazar espacios por guiones, quitar caracteres raros
    slug = text.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s]+', '-', slug)
    return slug

# Mapeo directo
df_shopify['Title'] = df['Descripcion']
df_shopify['URL handle'] = df.apply(generate_handle, axis=1)
df_shopify['Description'] = df['Descripcion'] # Descripción corta (body html)
df_shopify['Vendor'] = "KAIQI"
df_shopify['Type'] = df['Categoria']
df_shopify['Tags'] = df['Categoria'] + ", " + df['Origen_Dato']
df_shopify['Published on online store'] = "TRUE"
df_shopify['Status'] = "active"
df_shopify['SKU'] = df['SKU']
df_shopify['Option1 name'] = "Title"
df_shopify['Option1 value'] = "Default Title"
df_shopify['Price'] = df['Precio']
df_shopify['Charge tax'] = "TRUE"
df_shopify['Inventory tracker'] = "shopify"
df_shopify['Inventory quantity'] = 10 # Stock inicial por defecto (puedes cambiarlo)
df_shopify['Continue selling when out of stock'] = "continue"
df_shopify['Weight value (grams)'] = 500 # Peso estimado por defecto
df_shopify['Weight unit for display'] = "g"
df_shopify['Requires shipping'] = "TRUE"
df_shopify['Fulfillment service'] = "manual"
df_shopify['Product image URL'] = df['Imagen_URL']
df_shopify['Image position'] = df['Imagen_URL'].apply(lambda x: 1 if pd.notna(x) and x != "" else "")
df_shopify['Image alt text'] = df['Descripcion']
df_shopify['Gift card'] = "FALSE"
df_shopify['SEO title'] = df['Descripcion']
df_shopify['SEO description'] = df['Descripcion']
df_shopify['Google Shopping / Condition'] = "new"

# 4. EXPORTAR
print(f"3. Guardando archivo final: {OUTPUT_FILE}...")
# Usamos separador ';' como solicitaste en los encabezados
df_shopify.to_csv(OUTPUT_FILE, sep=';', index=False, encoding='utf-8-sig')

print("\n" + "="*50)
print(f"✅ ARCHIVO GENERADO: {OUTPUT_FILE}")
print("="*50)
print("Resumen de las primeras filas:")
print(df_shopify[['Title', 'SKU', 'Price', 'Product image URL']].head().to_string())