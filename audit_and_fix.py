import pandas as pd
import re
import os

# --- CONFIGURACIÓN ---
FILE_PRECIOS = 'LISTADO KAIQI NOV-DIC 2025.csv'
FILE_FIXED = 'LISTADO_KAIQI_CORREGIDO.csv'

print("--- AUDITORÍA Y CORRECCIÓN DE DUPLICADOS ---")

# 1. Cargar archivo original
try:
    df = pd.read_csv(FILE_PRECIOS, sep=';', header=None, encoding='latin-1', dtype=str)
except:
    df = pd.read_csv(FILE_PRECIOS, sep=';', header=None, encoding='utf-8', dtype=str)

# Normalizar columnas (Indices fijos: 1=SKU, 2=Desc, 4=Price)
# Creamos un dataframe limpio para trabajar
data = []
for index, row in df.iterrows():
    try:
        sku = str(row.iloc[1]).strip()
        desc = str(row.iloc[2]).strip()
        cat = str(row.iloc[3]).strip()
        price = str(row.iloc[4]).strip()
    except:
        continue

    # Filtros de basura
    if sku.lower() in ['nan', '', 'codigo', 'codigo new'] or desc.lower() == 'nan':
        continue
        
    data.append({'SKU': sku, 'Desc': desc, 'Cat': cat, 'Price': price})

df_clean = pd.DataFrame(data)

# 2. Detectar Duplicados
dupes = df_clean[df_clean.duplicated(subset=['SKU'], keep=False)].sort_values('SKU')

print(f"⚠️ Se encontraron {len(dupes)} registros en conflicto (SKUs repetidos).")
print("Generando sufijos únicos (-A, -B) para salvarlos todos...\n")

# 3. Corregir Duplicados (Logic de Sufijos)
# Usamos un diccionario para contar ocurrencias
sku_counts = {}
new_rows = []

for index, row in df_clean.iterrows():
    sku = row['SKU']
    
    # Si el SKU existe en la lista de duplicados
    if sku in dupes['SKU'].values:
        if sku not in sku_counts:
            sku_counts[sku] = 1
            new_sku = f"{sku}-A" # El primero será -A
        else:
            sku_counts[sku] += 1
            # Generamos letra B, C, D...
            suffix = chr(65 + sku_counts[sku] - 1) # 65 es 'A'
            new_sku = f"{sku}-{suffix}"
        
        print(f"   🔧 Corregido: {sku} -> {new_sku} ({row['Desc'][:30]}...)")
        row['SKU'] = new_sku
    
    new_rows.append(row)

df_fixed = pd.DataFrame(new_rows)

# 4. Guardar archivo corregido con formato original (para que funcione con el merge anterior)
# Reconstruimos el formato: CODIGO NEW; CODIGO; DESCRIPCION; CATEGORIA; PRECIO
df_export = pd.DataFrame()
df_export['0'] = "" # Columna vacía inicial
df_export['1'] = df_fixed['SKU']
df_export['2'] = df_fixed['Desc']
df_export['3'] = df_fixed['Cat']
df_export['4'] = df_fixed['Price']

df_export.to_csv(FILE_FIXED, sep=';', index=False, header=False, encoding='latin-1')

print("\n" + "="*40)
print(f"✅ ARCHIVO CORREGIDO GENERADO: {FILE_FIXED}")
print("="*40)
print("Ahora debes actualizar tu script 'merge_final.py' para usar este nuevo archivo.")