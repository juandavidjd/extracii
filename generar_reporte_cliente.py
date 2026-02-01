import pandas as pd
import os

# --- CONFIGURACIÓN ---
FILE_ORIGINAL = 'LISTADO KAIQI NOV-DIC 2025.csv'
FILE_FINAL = 'Inventario_KAIQI_Shopify_Ready.csv'
OUTPUT_REPORT = 'Reporte_Depuracion_Cliente.csv'

print("--- GENERANDO REPORTE DE DEPURACIÓN PARA CLIENTE ---")

reporte_rows = []

# 1. ANALIZAR DUPLICADOS EN EL LISTADO ORIGINAL
# (Para mostrarle al cliente qué códigos están repetidos en su Excel)
try:
    print(f"1. Buscando duplicados en {FILE_ORIGINAL}...")
    # Leemos con latin-1 y sep=;
    df_orig = pd.read_csv(FILE_ORIGINAL, sep=';', header=None, encoding='latin-1', dtype=str)
    
    # Asumimos columnas por posición según tu archivo
    # Col 1: CODIGO, Col 2: DESCRIPCION, Col 4: PRECIO
    df_orig = df_orig.iloc[:, [1, 2, 4]]
    df_orig.columns = ['SKU', 'Descripcion', 'Precio']
    
    # Limpieza básica
    df_orig['SKU'] = df_orig['SKU'].astype(str).str.strip()
    df_orig = df_orig[~df_orig['SKU'].str.lower().isin(['nan', '', 'codigo', 'codigo new'])]
    
    # Encontrar duplicados
    dupes = df_orig[df_orig.duplicated(subset=['SKU'], keep=False)]
    
    for index, row in dupes.iterrows():
        reporte_rows.append({
            'SKU': row['SKU'],
            'Descripcion': row['Descripcion'],
            'Precio_Actual': row['Precio'],
            'Problema': 'CÓDIGO DUPLICADO (Conflicto)',
            'Accion_Requerida': 'Decidir cuál conservar o renombrar'
        })
        
    print(f"   -> Encontrados {len(dupes)} registros duplicados.")

except Exception as e:
    print(f"   ❌ Error leyendo original: {e}")


# 2. ANALIZAR PRECIOS EN 0 EN EL INVENTARIO FINAL
# (Productos huérfanos de Shopify o sin precio en lista)
try:
    print(f"2. Buscando precios en 0 en {FILE_FINAL}...")
    df_final = pd.read_csv(FILE_FINAL)
    
    # Filtramos precio 0
    zeros = df_final[df_final['Precio'] == 0]
    
    for index, row in zeros.iterrows():
        # Evitamos repetir si ya salió como duplicado (aunque es raro)
        reporte_rows.append({
            'SKU': row['SKU'],
            'Descripcion': row['Descripcion'],
            'Precio_Actual': 0,
            'Problema': 'PRECIO EN CERO',
            'Accion_Requerida': 'Asignar precio o eliminar producto'
        })
        
    print(f"   -> Encontrados {len(zeros)} productos con precio 0.")

except Exception as e:
    print(f"   ❌ Error leyendo final: {e}")

# 3. GENERAR ARCHIVO
if reporte_rows:
    df_reporte = pd.DataFrame(reporte_rows)
    
    # Ordenar para que los duplicados salgan juntos
    df_reporte = df_reporte.sort_values(by=['Problema', 'SKU'])
    
    # Guardar
    df_reporte.to_csv(OUTPUT_REPORT, index=False, sep=';', encoding='utf-8-sig')
    
    print("\n" + "="*50)
    print(f"✅ REPORTE GENERADO: {OUTPUT_REPORT}")
    print("="*50)
    print("Muestra del reporte:")
    print(df_reporte.head(10).to_string(index=False))
else:
    print("\n✅ ¡Felicidades! No se encontraron errores (ni duplicados ni precios en 0).")