import os
import re

INPUT_FILE = 'Inventario_Limpio_CORREGIDO.csv' # El archivo que subiste
OUTPUT_FILE = 'Inventario_Limpio_CORREGIDO.csv' # Vamos a sobrescribir y reparar

print(f"--- SCRIPT 1.7: REPARACIÓN DE SKUs (V5 - Semicolon Fix) ---")

try:
    print(f"Leyendo {INPUT_FILE} como texto (modo reparación)...")
    # Usamos latin-1 por si acaso, aunque guardaremos en utf-8
    with open(INPUT_FILE, 'r', encoding='latin-1', errors='ignore') as f:
        lines = f.readlines()
    
    if not lines:
        print("❌ Error: El archivo está vacío.")
        exit()

except Exception as e:
    print(f"❌ Error al leer: {e}")
    exit()

new_lines = []
# Guardamos el encabezado (la primera línea)
header = lines[0]
new_lines.append(header)
skus_generados = 0

print("Analizando líneas y corrigiendo SKUs...")

# Iteramos por el resto de las líneas (saltando el encabezado)
for line in lines[1:]:
    line_stripped = line.strip()
    if not line_stripped:
        continue # Saltar líneas vacías

    # --- LA CORRECCIÓN CLAVE ---
    # 1. Buscamos líneas que empiezan con ; (SKU vacío)
    if line_stripped.startswith(';'):
        
        # 2. Separamos por ;
        parts = line_stripped.split(';')
        
        # parts[0] es '', parts[1] es 'Motor de Carguero...'
        desc = parts[1].upper().strip() 
        
        # Generar SKU
        match = re.search(r'(\d{3})', desc)
        if match:
            numero = match.group(1)
            new_sku = f"MOTOR-CTO-{numero}"
            print(f"   🔧 Corrigiendo: '{desc}' -> NUEVO SKU: {new_sku}")
            
            # 3. Reemplazar la parte vacía (índice 0)
            parts[0] = new_sku
            skus_generados += 1
        else:
            # Fallback por si no encuentra el número
            new_sku_gen = f"SKU-GENERADO-{hash(desc)}"
            print(f"   ⚠️ Corrigiendo: '{desc}' -> NUEVO SKU: {new_sku_gen}")
            parts[0] = new_sku_gen
            skus_generados += 1
            
        # 4. Volver a unir con ; y agregar el salto de línea
        new_line = ";".join(parts) + "\n"
        new_lines.append(new_line)
    else:
        # La línea está bien (ya tiene SKU), la agregamos tal cual
        new_lines.append(line)

# Escribir el archivo corregido
try:
    # Guardamos en UTF-8-SIG (bueno para Excel)
    with open(OUTPUT_FILE, 'w', encoding='utf-8-sig') as f:
        f.writelines(new_lines)
except Exception as e:
    print(f"❌ Error al guardar: {e}")
    exit()

print(f"\n✅ {OUTPUT_FILE} ha sido REPARADO.")
print(f"   -> Se generaron {skus_generados} SKUs nuevos.")
print("--- SCRIPT 1.7 TERMINADO ---")

print("\nPASO SIGUIENTE: Ejecuta 'python consolidar_fuentes.py'")