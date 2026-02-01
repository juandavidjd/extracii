import pandas as pd
import requests
import os
import time
import re

# --- TUS 3 CUENTAS CONFIGURADAS ---
CREDENCIALES = [
    {"key": "AIzaSyCqRxWNMXRpOmUVhpNGXHTmQZYvgcL0Unk", "cx": "d775153f2e9c74e51"}, # Cuenta 1
    {"key": "AIzaSyBIUS2iB1u88MqN4mXxSqdLlP83Kf9s8Rc", "cx": "c6ab83d6950f34110"}, # Cuenta 2
    {"key": "AIzaSyBlGX62Etxc4-rBoO_JWllDq4-CK_FUKz0", "cx": "f59aebe1a50da4ef7"}  # Cuenta 3
]

# --- CONFIGURACIÓN ---
INPUT_FILE = 'Inventario_KAIQI_Shopify_Ready.csv'
OUTPUT_DIR = 'imagenes_descargadas'
STOP_WORDS = ['CAJA', 'X10', 'X 10', 'JUEGO', 'KIT', 'PAR', 'UNIDAD', 'ORIGINAL', 'TIPO', 'OEM', 'KAIQI', 'REPUESTO']

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

print("--- INICIANDO BÚSQUEDA MAESTRA (ROTACIÓN DE 3 CUENTAS) ---")

# 1. Cargar Datos
try:
    df = pd.read_csv(INPUT_FILE)
    col_img = 'Imagen' if 'Imagen' in df.columns else 'Product image URL'
    mask_missing = (df[col_img].isna()) | (df[col_img] == '') | (df[col_img] == 'Sin Imagen')
    missing_df = df[mask_missing].copy()
    print(f"Total productos: {len(df)}")
    print(f"Faltantes por buscar: {len(missing_df)}")
except Exception as e:
    print(f"Error leyendo archivo: {e}")
    exit()

def limpiar_query(texto):
    texto = str(texto).upper()
    for word in STOP_WORDS:
        texto = texto.replace(word, '')
    texto = re.sub(r'[^A-Z0-9\s]', '', texto) 
    texto = re.sub(r'\s+', ' ', texto).strip()
    return f"{texto} repuesto moto"

# Variables de control
cred_index = 0  # Empezamos con la credencial 0 (la primera)
descargadas = 0
errores = 0
saltadas = 0

print(f"\nUsando Credencial #{cred_index + 1}...")

for index, row in missing_df.iterrows():
    sku = str(row['SKU']).strip()
    desc = str(row['Descripcion'])
    
    # --- SALTAR SI YA EXISTE ---
    if os.path.exists(os.path.join(OUTPUT_DIR, f"{sku}.jpg")) or os.path.exists(os.path.join(OUTPUT_DIR, f"{sku}.png")):
        saltadas += 1
        continue

    query = limpiar_query(desc)
    print(f"[{descargadas+1}] Buscando: {sku} -> '{query}'...")

    # Bucle de intentos (para rotar clave si falla)
    intentos = 0
    while intentos < len(CREDENCIALES):
        current_creds = CREDENCIALES[cred_index]
        
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'q': query, 
                'cx': current_creds['cx'], 
                'key': current_creds['key'],
                'searchType': 'image', 
                'num': 1, 
                'imgSize': 'large', 
                'fileType': 'jpg'
            }
            
            res = requests.get(url, params=params)
            data = res.json()

            # SI HAY ÉXITO
            if 'items' in data:
                img_url = data['items'][0]['link']
                try:
                    img_data = requests.get(img_url, timeout=10).content
                    with open(os.path.join(OUTPUT_DIR, f"{sku}.jpg"), 'wb') as f:
                        f.write(img_data)
                    print(f"   ✅ OK (Cuenta {cred_index+1})")
                    descargadas += 1
                    break # Salimos del while, vamos al siguiente producto
                except:
                    print("   ❌ Error descargando archivo.")
                    errores += 1
                    break 
            
            # SI HAY ERROR EN LA API
            elif 'error' in data:
                msg = data['error']['message']
                if "quota" in msg.lower() or "bill" in msg.lower():
                    print(f"   ⚠️ CUOTA AGOTADA en Cuenta {cred_index+1}. Cambiando...")
                    # Cambiar a la siguiente cuenta
                    cred_index += 1
                    if cred_index >= len(CREDENCIALES):
                        print("\n🛑 ¡TODAS LAS CUENTAS AGOTADAS! Intenta mañana.")
                        exit()
                    print(f"   🔄 Ahora usando Cuenta {cred_index+1}")
                    intentos += 1
                    continue # Reintentar el MISMO producto con la nueva clave
                else:
                    print(f"   ⚠️ No encontrada / Error API: {msg}")
                    errores += 1
                    break
            else:
                print("   ⚠️ No encontrada")
                errores += 1
                break

        except Exception as e:
            print(f"   ❌ Error conexión: {e}")
            errores += 1
            break
    
    time.sleep(0.5)

print("\n" + "="*40)
print(f"INFORME FINAL:")
print(f"⏭️  Saltadas (Ya existían): {saltadas}")
print(f"✅ Nuevas descargadas: {descargadas}")
print(f"⚠️ No encontradas: {errores}")
print("="*40)