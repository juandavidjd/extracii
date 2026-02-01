import pandas as pd
import os
import re

INPUT_FILE = 'Inventario_Limpio_Para_Enriquecer.csv'

print(f"--- SCRIPT 1.5: CORRECCIÓN DE SKUs (V3 - Python Engine) ---")

try:
    print(f"Intentando leer {INPUT_FILE} con el motor flexible...")
    
    # --- AQUÍ LA CORRECCIÓN V3 ---
    # Usamos engine='python' para que maneje las comas
    # mal formateadas dentro de las descripciones.
    df = pd.read_csv(INPUT_FILE, sep=',', engine='python')
    # --------------------------

    print(f"   -> ¡Éxito! Archivo leído correctamente.")

except Exception as e:
    print(f"❌ Error: No se pudo leer el archivo '{INPUT_FILE}'. {e}")
    exit()

# Función para generar SKUs basados en la descripción
def generate_sku(row):
    # Revisamos si el SKU está vacío (es NaN o un string vacío)
    if pd.isna(row['SKU']) or str(row['SKU']).strip() == '':
        desc = str(row['Descripcion']).upper()
        
        # Usamos regex para extraer el número (200, 250, etc.)
        match = re.search(r'(\d{3})', desc)
        if match:
            numero = match.group(1)
            new_sku = f"MOTOR-CTO-{numero}"
            print(f"   🔧 Corrigiendo: '{desc}' -> NUEVO SKU: {new_sku}")
            return new_sku
        
        # Si no encuentra número, le pone un SKU genérico
        return "SKU-REQUERIDO"
    
    # Si ya tiene SKU, lo deja quieto
    return row['SKU']

print("1. Asignando SKUs a productos huérfanos...")
df['SKU'] = df.apply(generate_sku, axis=1)

# Sobrescribimos el archivo con los SKUs corregidos
# Guardamos con coma (,) para mantener consistencia
df.to_csv(INPUT_FILE, index=False, sep=',')

print(f"\n✅ {INPUT_FILE} ha sido actualizado con los nuevos SKUs.")
print("--- SCRIPT 1.5 TERMINADO ---")