import pandas as pd
import os
import re

# --- CONFIGURACIÓN ---
FILE_INVENTARIO_MAESTRO = 'Inventario_KAIQI_Shopify_Ready.csv'
FILE_LISTADO_ORIGINAL = 'LISTADO KAIQI NOV-DIC 2025.csv'

OUTPUT_REPORTE_CLIENTE = 'Reporte_Cliente_ACCION_REQUERIDA.csv'
OUTPUT_INVENTARIO_LIMPIO = 'Inventario_Limpio_Para_Enriquecer.csv'

print("--- SCRIPT 1: DEPURACIÓN DE INVENTARIO KAIQI (V3 Robusto) ---")

lista_problemas = []
skus_problematicos = set()

# --- 1. BUSCAR DUPLICADOS (CONFLICTOS) EN EL LISTADO ORIGINAL ---
# (Esto ya sabemos que funciona bien)
try:
    print(f"1. Analizando {FILE_LISTADO_ORIGINAL} en busca de duplicados...")
    df_orig = pd.read_csv(FILE_LISTADO_ORIGINAL, sep=';', header=None, encoding='latin-1', dtype=str)
    
    df_orig = df_orig.iloc[:, [1, 2, 3, 4]]
    df_orig.columns = ['SKU', 'Descripcion', 'Categoria', 'Precio']
    
    df_orig['SKU'] = df_orig['SKU'].astype(str).str.strip()
    df_orig = df_orig[~df_orig['SKU'].str.lower().isin(['nan', '', 'codigo', 'codigo new'])]
    
    dupes = df_orig[df_orig.duplicated(subset=['SKU'], keep=False)].sort_values('SKU')
    
    for index, row in dupes.iterrows():
        lista_problemas.append({
            'SKU': row['SKU'],
            'Descripcion_Original': row['Descripcion'],
            'Precio_Original': row['Precio'],
            'Categoria_Original': row['Categoria'],
            'PROBLEMA': 'SKU DUPLICADO (Conflicto en Origen)'
        })
        skus_problematicos.add(row['SKU'])
        
    print(f"   -> Encontrados {len(dupes)} registros con SKU duplicado.")

except Exception as e:
    print(f"   ❌ Error leyendo {FILE_LISTADO_ORIGINAL}: {e}")

# --- 2. BUSCAR PRECIO 0 (HUÉRFANOS) EN EL MAESTRO (CON LÓGICA V3) ---
try:
    print(f"2. Analizando {FILE_INVENTARIO_MAESTRO} en busca de precios 0...")
    
    # --- AQUÍ LA CORRECCIÓN V3 ---
    try:
        # Intento 1: Leer con coma (,)
        df_maestro = pd.read_csv(FILE_INVENTARIO_MAESTRO, sep=',')
    except pd.errors.ParserError:
        # Intento 2: Si falla, leer con punto y coma (;)
        print("   -> Falló con comas. Reintentando con punto y coma...")
        df_maestro = pd.read_csv(FILE_INVENTARIO_MAESTRO, sep=';')
    print("   -> Archivo maestro leído correctamente.")
    # -------------------------
    
    zeros = df_maestro[df_maestro['Precio'] == 0]
    
    for index, row in zeros.iterrows():
        lista_problemas.append({
            'SKU': row['SKU'],
            'Descripcion_Original': row['Descripcion'],
            'Precio_Original': 0,
            'Categoria_Original': row['Categoria'],
            'PROBLEMA': 'PRECIO CERO (Huérfano de Shopify)'
        })
        skus_problematicos.add(row['SKU'])
        
    print(f"   -> Encontrados {len(zeros)} productos con precio 0.")

    # --- 3. GENERAR EL INVENTARIO LIMPIO ---
    print(f"3. Generando inventario limpio (excluyendo {len(skus_problematicos)} SKUs problemáticos)...")
    
    df_limpio = df_maestro[~df_maestro['SKU'].isin(skus_problematicos)].copy()
    
    df_limpio.to_csv(OUTPUT_INVENTARIO_LIMPIO, index=False)
    print(f"   -> Guardado: {OUTPUT_INVENTARIO_LIMPIO} ({len(df_limpio)} productos listos para enriquecer)")


except Exception as e:
    print(f"   ❌ Error leyendo {FILE_INVENTARIO_MAESTRO}: {e}")

# --- 4. GENERAR REPORTE PARA EL CLIENTE ---
if lista_problemas:
    df_reporte = pd.DataFrame(lista_problemas)
    df_reporte = df_reporte.sort_values(by=['PROBLEMA', 'SKU'])
    
    columnas_reporte = ['PROBLEMA', 'SKU', 'Descripcion_Original', 'Precio_Original', 'Categoria_Original']
    df_reporte = df_reporte[columnas_reporte]
    
    df_reporte.to_csv(OUTPUT_REPORTE_CLIENTE, index=False, sep=';', encoding='utf-8-sig')
    
    print("\n" + "="*50)
    print(f"✅ REPORTE PARA CLIENTE GENERADO: {OUTPUT_REPORTE_CLIENTE}")
    print("="*50)
    print("Muestra del reporte de problemas (Ahora completo):")
    print(df_reporte.head(10).to_string(index=False))
else:
    print("\n✅ No se encontraron problemas.")