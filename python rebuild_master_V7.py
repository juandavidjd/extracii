import pandas as pd
import os
import re

# --- CONFIGURACIÓN ---
FILE_LISTADO_ORIGINAL = 'LISTADO KAIQI NOV-DIC 2025.csv'
FILE_SHOPIFY = 'catalogo_shopify_completo.csv' 
OUTPUT_INVENTARIO = 'Inventario_Limpio_CORREGIDO.csv'

print("--- SCRIPT DE RECONSTRUCCIÓN MAESTRA (V7 - Reparación Total) ---")

# --- 1. CARGAR Y REPARAR LISTADO ORIGINAL ---
try:
    print(f"1. Cargando y reparando {FILE_LISTADO_ORIGINAL}...")
    df_orig = pd.read_csv(FILE_LISTADO_ORIGINAL, sep=';', header=None, encoding='latin-1', dtype=str)
    
    productos_kaiqi = []
    
    # Iteramos "a ciegas" para encontrar los datos correctos
    for index, row in df_orig.iterrows():
        try:
            sku = str(row.iloc[1]).strip()
            desc = str(row.iloc[2]).strip()
            col3 = str(row.iloc[3]).strip() # Posible Categoria o Precio
            col4 = str(row.iloc[4]).strip() # Posible Precio o Categoria
        except:
            continue # Saltar filas rotas

        # Ignorar encabezados o basura
        if sku.lower() in ['nan', '', 'codigo', 'codigo new'] or desc.lower() == 'nan':
            continue

        # Lógica de reparación: Detectar dónde está el precio
        precio_limpio = re.sub(r'[^\d]', '', col4) # Limpiar columna 4
        if precio_limpio.isdigit() and len(precio_limpio) > 2:
            # Caso Normal: Precio está en Col 4, Categoría en Col 3
            precio = int(precio_limpio)
            cat = col3
        else:
            # Caso Roto (como fila 1271): Precio está en Col 3, Categoría en Col 4
            precio_limpio = re.sub(r'[^\d]', '', col3)
            if precio_limpio.isdigit() and len(precio_limpio) > 2:
                precio = int(precio_limpio)
                cat = col4
            else:
                # No se pudo encontrar precio
                precio = 0
                cat = col3 # Asumir que 3 es categoría
        
        productos_kaiqi.append({
            'SKU_Join': sku,
            'Descripcion_List': desc,
            'Categoria_List': cat,
            'Precio_List': precio
        })

    df_orig_clean = pd.DataFrame(productos_kaiqi)
    
    # Lógica de corrección de duplicados (-A, -B)
    print("   -> Buscando y corrigiendo duplicados...")
    dupes_mask = df_orig_clean.duplicated(subset=['SKU_Join'], keep=False)
    dupes_skus = df_orig_clean[dupes_mask]['SKU_Join'].unique()
    
    sku_counts = {}
    
    def fix_duplicates(row):
        sku = row['SKU_Join']
        if sku in dupes_skus:
            if sku not in sku_counts: sku_counts[sku] = 0
            sku_counts[sku] += 1
            suffix = chr(64 + sku_counts[sku]) # A, B, C...
            return f"{sku}-{suffix}"
        return sku

    df_orig_clean['SKU_Join'] = df_orig_clean.apply(fix_duplicates, axis=1)
    print(f"   -> Listado KAIQI reparado y listo con {len(df_orig_clean)} productos.")
    
except Exception as e:
    print(f"   ❌ Error fatal leyendo {FILE_LISTADO_ORIGINAL}: {e}")
    exit()

# --- 2. CARGAR Y LIMPIAR SHOPIFY (HUÉRFANOS) ---
try:
    print(f"2. Cargando {FILE_SHOPIFY}...")
    try:
        df_shopify = pd.read_csv(FILE_SHOPIFY, sep=',', encoding='latin-1')
    except pd.errors.ParserError:
        df_shopify = pd.read_csv(FILE_SHOPIFY, sep=';', encoding='latin-1')

    def clean_sku_shop(val):
        if pd.isna(val): return ""
        s = str(val).strip()
        s = s.replace("Código:", "").strip()
        if s.endswith(".0"): s = s[:-2]
        return s

    df_shopify['SKU_Join'] = df_shopify['SKU'].apply(clean_sku_shop)
    df_shopify_clean = df_shopify[['SKU_Join', 'Title', 'Category', 'Image Src']].copy()

except Exception as e:
    print(f"   ❌ Error fatal leyendo {FILE_SHOPIFY}: {e}")
    exit()

# --- 3. FUSIÓN TOTAL (OUTER JOIN) ---
print("3. Fusionando bases de datos...")
df_merged = pd.merge(
    df_orig_clean[['SKU_Join', 'Descripcion_List', 'Categoria_List', 'Precio_List']],
    df_shopify_clean,
    on='SKU_Join',
    how='outer'
)

# --- 4. CONSOLIDACIÓN FINAL (CORRECCIÓN V7) ---
print("4. Consolidando datos y reparando SKUs vacíos...")

# PASO A: Consolidar Descripción PRIMERO
df_merged['Descripcion'] = df_merged['Descripcion_List'].fillna(df_merged['Title'])

# PASO B: Generar SKUs FALTANTES (Ahora sí funciona)
def generate_sku(row):
    sku = row['SKU_Join']
    desc = row['Descripcion'] # Usamos la descripción ya consolidada
    
    if pd.isna(sku) or str(sku).strip() == '':
        desc_upper = str(desc).upper()
        match = re.search(r'(\d{3})', desc_upper)
        if match:
            new_sku = f"MOTOR-CTO-{match.group(1)}"
            print(f"   🔧 Corrigiendo: '{desc_upper.strip()}' -> NUEVO SKU: {new_sku}")
            return new_sku
        return f"SKU-GENERADO-{hash(desc)}"
    return sku

df_merged['SKU'] = df_merged.apply(generate_sku, axis=1)

# PASO C: Llenar el resto de columnas
df_merged['Precio'] = df_merged['Precio_List'].fillna(0) # Huérfanos quedan con 0
df_merged['Categoria'] = df_merged['Categoria_List'].fillna(df_merged['Category']).fillna("Repuestos Varios")
df_merged['Imagen_Actual'] = df_merged['Image Src'].fillna("Sin Imagen")

# Crear nuevas columnas
df_merged['Sistema Principal'] = ""
df_merged['Subsistema'] = ""
df_merged['Componente'] = ""
df_merged['Tipo Vehiculo'] = "" 

# Definir columnas finales
columnas_finales = [
    'SKU', 'Descripcion', 'Precio', 'Categoria', 'Imagen_Actual',
    'Sistema Principal', 'Subsistema', 'Componente', 'Tipo Vehiculo'
]
df_final = df_merged[columnas_finales]
# Limpieza final de espacios
df_final['Descripcion'] = df_final['Descripcion'].str.replace(r'\s+', ' ', regex=True).str.strip()
df_final['Categoria'] = df_final['Categoria'].str.replace(r'\s+', ' ', regex=True).str.strip()

# --- 5. GUARDAR ---
# Guardamos con punto y coma (;) para que Excel lo abra bien
df_final.to_csv(OUTPUT_INVENTARIO, index=False, sep=';', encoding='utf-8-sig')

print("\n" + "="*50)
print(f"✅ ¡ÉXITO! INVENTARIO MAESTRO RECONSTRUIDO:")
print(f"   -> {OUTPUT_INVENTARIO}")
print(f"   -> Total Productos: {len(df_final)}")
print("="*50)