import pandas as pd
import requests
import os
import time
import re

# --- TUS CREDENCIALES (8 CUENTAS) ---
CREDENCIALES = [
    {"key": "AIzaSyACy6NrSC3YDsqgCfnP7pKweWFnFTycJhI", "cx": "7468cbc866be74c62"},
    {"key": "AIzaSyCIt14hUVPuloz6KEAGifdE8Vyyn2Mf0cE", "cx": "152e6e925018c41ca"},
    {"key": "AIzaSyDz_r2WBMjmqZpqYHLRQoZsALs0tBsIDn8", "cx": "f4c070cde3bf24546"},
    {"key": "AIzaSyDNby0O73cWpAcERV2XnY92LM2_5Swv1ww", "cx": "c21bbbe50fa7e4cbc"},
    {"key": "AIzaSyBkqhMQ-6f0Xj8wHvb46sXD1BmbJslrRp4", "cx": "a3f481653a3a34a89"},
    {"key": "AIzaSyCqRxWNMXRpOmUVhpNGXHTmQZYvgcL0Unk", "cx": "d775153f2e9c74e51"},
    {"key": "AIzaSyBIUS2iB1u88MqN4mXxSqdLlP83Kf9s8Rc", "cx": "c6ab83d6950f34110"},
    {"key": "AIzaSyBlGX62Etxc4-rBoO_JWllDq4-CK_FUKz0", "cx": "f59aebe1a50da4ef7"}
]

# --- CONFIGURACIÓN ---
INPUT_FILE = 'Inventario_KAIQI_Shopify_Ready.csv'
OUTPUT_DIR = 'imagenes_descargadas'

# Palabras a eliminar (Códigos internos, cantidades, marcas propias)
STOP_WORDS = [
    'CAJA', 'X10', 'X 10', 'JUEGO', 'KIT', 'PAR', 'UNIDAD', 'ORIGINAL', 'TIPO', 'OEM', 'KAIQI', 
    'REPUESTO', 'DALU', 'SMG', 'HLK', 'TWOM', 'KAY', 'CHO', 'KET', 'MN', 'MV', 'EOM', 'CTO', 'COMPL',
    'X 3', 'X 6', 'PCS'
]

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

print("--- INICIANDO BÚSQUEDA INTELIGENTE (CATEGORÍA + DESCRIPCIÓN) ---")

try:
    df = pd.read_csv(INPUT_FILE)
    col_img = 'Imagen' if 'Imagen' in df.columns else 'Product image URL'
    mask_missing = (df[col_img].isna()) | (df[col_img] == '') | (df[col_img] == 'Sin Imagen')
    missing_df = df[mask_missing].copy()
    print(f"Objetivo: {len(missing_df)} imágenes.")
except Exception as e:
    print(f"Error leyendo archivo: {e}")
    exit()

# --- FUNCIÓN DE BÚSQUEDA MEJORADA ---
def construir_query(row):
    desc = str(row['Descripcion']).upper()
    cat = str(row['Categoria']).upper() # Usamos la categoría como ancla

    # 1. Limpiar Descripción
    for word in STOP_WORDS:
        desc = desc.replace(word, '')
    
    # 2. Limpiar caracteres raros (/, -, *) dejando espacios
    desc = re.sub(r'[^A-Z0-9\s]', ' ', desc)
    
    # 3. Limpiar Categoría (quitar plurales o palabras genéricas si fuera necesario, 
    # pero por ahora la categoría es lo más valioso)
    cat = cat.replace('REPUESTOS VARIOS', '') # Si es "Varios", no ayuda mucho, mejor quitarlo

    # 4. Construir Query: CATEGORIA + DESC LIMPIA + "MOTO"
    # Ejemplo: "ARBOL LEVAS" + "125 SCOOTER" + "MOTO"
    final_text = f"{cat} {desc} MOTO"
    
    # 5. Quitar espacios dobles
    return re.sub(r'\s+', ' ', final_text).strip()

# Variables
cred_index = 0
descargadas = 0
errores = 0
saltadas = 0

print(f"\nUsando Credencial #{cred_index + 1}...")

for index, row in missing_df.iterrows():
    sku = str(row['SKU']).strip()
    
    # Saltar si existe
    existe = False
    for archivo in os.listdir(OUTPUT_DIR):
        if archivo.startswith(f"{sku}."):
            existe = True
            break
    if existe:
        saltadas += 1
        continue

    # USAR NUEVA LÓGICA
    query = construir_query(row)
    print(f"[{descargadas+1}] Buscando: {sku} -> '{query}'")

    intentos = 0
    while intentos < len(CREDENCIALES):
        current_creds = CREDENCIALES[cred_index]
        
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'q': query, 'cx': current_creds['cx'], 'key': current_creds['key'],
                'searchType': 'image', 'num': 1
            }
            
            res = requests.get(url, params=params)
            data = res.json()

            if 'items' in data:
                img_url = data['items'][0]['link']
                try:
                    img_data = requests.get(img_url, timeout=10).content
                    # Detectar extensión
                    ext = 'jpg'
                    if '.png' in img_url.lower(): ext = 'png'
                    elif '.webp' in img_url.lower(): ext = 'webp'
                    
                    with open(os.path.join(OUTPUT_DIR, f"{sku}.{ext}"), 'wb') as f:
                        f.write(img_data)
                    
                    print(f"   ✅ OK")
                    descargadas += 1
                    break
                except:
                    print("   ❌ Link roto.")
                    errores += 1
                    break 
            elif 'error' in data:
                msg = data['error']['message']
                if "quota" in msg.lower() or "bill" in msg.lower():
                    print(f"   ⚠️ CUOTA AGOTADA Cuenta {cred_index+1}...")
                    cred_index += 1
                    if cred_index >= len(CREDENCIALES):
                        print("\n🛑 ¡TODAS LAS CUENTAS AGOTADAS!")
                        exit()
                    print(f"   🔄 Cambio a Cuenta {cred_index+1}")
                    intentos += 1
                    continue 
                else:
                    print(f"   ⚠️ Error API: {msg}")
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
    
    time.sleep(0.2)

print("\n" + "="*40)
print(f"FINALIZADO: {descargadas} nuevas imágenes.")
print("="*40)