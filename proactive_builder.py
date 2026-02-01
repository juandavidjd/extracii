import pandas as pd
import os
import re

# --- CONFIGURACIÓN ---
FILE_LISTADO_ORIGINAL = 'LISTADO KAIQI NOV-DIC 2025.csv'
FILE_SHOPIFY = 'catalogo_shopify_completo.csv' 
OUTPUT_INVENTARIO = 'Inventario_Limpio_Para_Enriquecer.csv'

print("--- SCRIPT PROACTIVO: CONSTRUYENDO INVENTARIO (V2 Encoding Fix) ---")
print("Este script unifica, corrige duplicados y retiene precios 0.")

# --- 1. CARGAR Y CORREGIR LISTADO ORIGINAL (CON DUPLICADOS) ---
try:
    print(f"1. Cargando {FILE_LISTADO_ORIGINAL}...")
    # Forzamos encoding latin-1
    df_orig = pd.read_csv(FILE_LISTADO_ORIGINAL, sep=';', header=None, encoding='latin-1', dtype=str)
    
    df_orig_clean = df_orig.iloc[:, [1, 2, 3, 4]]
    df_orig_clean.columns = ['SKU_Join', 'Descripcion_List', 'Categoria_List', 'Precio_Raw']
    
    df_orig_clean['SKU_Join'] = df_orig_clean['SKU_Join'].astype(str).str.strip()
    df_orig_clean = df_orig_clean[~df_orig_clean['SKU_Join'].str.lower().isin(['nan', '', 'codigo', 'codigo new'])]
    
    # Lógica de corrección de duplicados (-A, -B)
    print("   -> Buscando y corrigiendo duplicados...")
    dupes_mask = df_orig_clean.duplicated(subset=['SKU_Join'], keep=False)
    dupes_skus = df_orig_clean[dupes_mask]['SKU_Join'].unique()
    
    sku_counts = {}
    
    def fix_duplicates(row):
        sku = row['SKU_Join']
        if sku in dupes_skus:
            if sku not in sku_counts:
                sku_counts[sku] = 1
                new_sku = f"{sku}-A"
            else:
                sku_counts[sku] += 1
                suffix = chr(64 + sku_counts[sku]) # 65='A', 66='B', etc.
                new_sku = f"{sku}-{suffix}"
            
            print(f"   🔧 Corregido: {sku} -> {new_sku}")
            return new_sku
        return sku

    df_orig_clean['SKU_Join'] = df_orig_clean.apply(fix_duplicates, axis=1)
    
    # Limpiar Precio
    df_orig_clean['Precio_List'] = df_orig_clean['Precio_Raw'].str.replace(r'[^\d]', '', regex=True)
    df_orig_clean['Precio_List'] = pd.to_numeric(df_orig_clean['Precio_List'], errors='coerce').fillna(0).astype(int)

    print(f"   -> Listado KAIQI corregido y listo con {len(df_orig_clean)} productos.")
    
except Exception as e:
    print(f"   ❌ Error fatal leyendo {FILE_LISTADO_ORIGINAL}: {e}")
    exit()

# --- 2. CARGAR Y LIMPIAR SHOPIFY (HUÉRFANOS) ---
try:
    print(f"2. Cargando {FILE_SHOPIFY}...")
    
    # --- AQUÍ LA CORRECCIÓN V2 ---
    # Probamos ambos separadores PERO forzando latin-1 en ambos
    try:
        df_shopify = pd.read_csv(FILE_SHOPIFY, sep=',', encoding='latin-1')
    except pd.errors.ParserError:
        df_shopify = pd.read_csv(FILE_SHOPIFY, sep=';', encoding='latin-1')
    # -----------------------------

    # Limpieza de SKU de Shopify
    def clean_sku_shop(val):
        if pd.isna(val): return ""
        s = str(val).strip()
        s = s.replace("Código:", "").strip()
        if s.endswith(".0"): s = s[:-2]
        return s

    df_shopify['SKU_Join'] = df_shopify['SKU'].apply(clean_sku_shop)
    df_shopify_clean = df_shopify[['SKU_Join', 'Title', 'Category', 'Image Src']].copy()
    print(f"   -> Catálogo Shopify cargado con {len(df_shopify_clean)} productos.")

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

# --- 4. CONSOLIDACIÓN FINAL ---
print("4. Consolidando datos y creando nuevas columnas...")

df_merged['SKU'] = df_merged['SKU_Join']
df_merged['Descripcion'] = df_merged['Descripcion_List'].fillna(df_merged['Title'])
df_merged['Precio'] = df_merged['Precio_List'].fillna(0) # Los huérfanos quedan con precio 0
df_merged['Categoria'] = df_merged['Categoria_List'].fillna(df_merged['Category']).fillna("Repuestos Varios")
df_merged['Imagen_Actual'] = df_merged['Image Src'].fillna("Sin Imagen")

# Crear nuevas columnas de Taxonomía (listas para llenar)
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
df_final['Descripcion'] = df_final['Descripcion'].str.replace(r'\s+', ' ', regex=True).str.strip()

# --- 5. GUARDAR ---
df_final.to_csv(OUTPUT_INVENTARIO, index=False)

print("\n" + "="*50)
print(f"✅ ¡ÉXITO! INVENTARIO MAESTRO CREADO:")
print(f"   -> {OUTPUT_INVENTARIO}")
print(f"   -> Total Productos (Limpios + Duplicados Corregidos + Precio 0): {len(df_final)}")
print("="*50)