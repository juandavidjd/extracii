import os
import re

INPUT_FILE = 'Inventario_Limpio_Para_Enriquecer.csv'
OUTPUT_FILE = 'Inventario_Limpio_CORREGIDO.csv' # Guardamos en un NUEVO archivo

print(f"--- SCRIPT 1.5: CORRECCIÓN DE SKUs (V4 - Cirugía Manual) ---")

try:
    print(f"Leyendo {INPUT_FILE} como archivo de texto...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    if not lines:
        print("❌ Error: El archivo está vacío.")
        exit()

except Exception as e:
    print(f"❌ Error: No se pudo leer el archivo '{INPUT_FILE}'. {e}")
    exit()

new_lines = []
skus_generados = 0

# Guardamos el encabezado
header = lines[0]
new_lines.append(header)

print("Analizando líneas y corrigiendo SKUs vacíos...")

# Iteramos por el resto de las líneas
for line in lines[1:]:
    # Si la línea está vacía, la saltamos
    if not line.strip():
        continue

    # --- LÓGICA DE CORRECCIÓN ---
    # Si la línea empieza con una coma (significa SKU vacío)
    if line.startswith(','):
        # Dividimos la línea (ej: ",Motor de Carguero 200,0.0...")
        parts = line.split(',')
        desc = parts[1].upper() # Columna 'Descripcion'
        
        # Generar SKU
        match = re.search(r'(\d{3})', desc)
        if match:
            numero = match.group(1)
            new_sku = f"MOTOR-CTO-{numero}"
            print(f"   🔧 Corrigiendo: '{desc.strip()}' -> NUEVO SKU: {new_sku}")
            
            # Reconstruir la línea con el nuevo SKU
            parts[0] = new_sku # Reemplazar el vacío
            new_line = ",".join(parts)
            new_lines.append(new_line)
            skus_generados += 1
        else:
            # Si no puede generar SKU, la dejamos como estaba
            new_lines.append(line)
    else:
        # Si la línea está bien (ya tiene SKU), simplemente la agregamos
        new_lines.append(line)

# Escribir el archivo NUEVO y CORREGIDO
try:
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
except Exception as e:
    print(f"❌ Error al guardar el archivo: {e}")
    exit()

print(f"\n✅ {OUTPUT_FILE} ha sido creado.")
print(f"   -> Se generaron {skus_generados} SKUs nuevos.")
print("--- SCRIPT 1.5 TERMINADO ---")
print("\nPASO SIGUIENTE: Ejecuta 'python consolidar_fuentes.py'")