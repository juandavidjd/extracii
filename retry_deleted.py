import pandas as pd
import requests
import os
import time
import re
from PIL import Image

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

INPUT_FILE = 'Inventario_KAIQI_Shopify_Ready.csv'
OUTPUT_DIR = 'imagenes_descargadas'
STOP_WORDS = ['CAJA', 'X10', 'X 10', 'JUEGO', 'KIT', 'PAR', 'UNIDAD', 'ORIGINAL', 'TIPO', 'OEM', 'KAIQI', 'REPUESTO', 'DALU', 'SMG', 'HLK', 'TWOM', 'KAY', 'CHO', 'KET', 'MN', 'MV', 'EOM', 'CTO', 'COMPL']

print("--- INICIANDO REINTENTO INTELIGENTE (BUSCANDO FOTO #2 y #3) ---")

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# 1. Identificar qué falta (Lo que borraste)
df = pd.read_csv(INPUT_FILE)
# Consideramos productos que DEBERÍAN tener imagen (existentes) y los nuevos sin imagen
# Filtramos SKU vacíos
df = df[df['SKU'].notna()]

faltantes = []
presentes = 0

for index, row in df.iterrows():
    sku = str(row['SKU']).strip()
    # Check si existe archivo con cualquier extensión
    existe = False
    for f in os.listdir(OUTPUT_DIR):
        if f.startswith(f"{sku}."):
            existe = True
            break
    
    if existe:
        presentes += 1
    else:
        # Si no existe, lo agregamos a la lista de "Reintentar"
        faltantes.append(row)

print(f"Imágenes actuales en carpeta: {presentes}")
print(f"Imágenes eliminadas/faltantes a reintentar: {len(faltantes)}")

if len(faltantes) == 0:
    print("¡Todo completo! No hay nada que reintentar.")
    exit()

def limpiar_query(row):
    desc = str(row['Descripcion']).upper()
    cat = str(row['Categoria']).upper().replace('REPUESTOS VARIOS', '')
    for word in STOP_WORDS: desc = desc.replace(word, '')
    desc = re.sub(r'[^A-Z0-9\s]', ' ', desc)
    return re.sub(r'\s+', ' ', f"{cat} {desc} MOTO").strip()

# 2. Bucle de Reintento
cred_index = 0
descargadas = 0

for row in faltantes:
    sku = str(row['SKU']).strip()
    query = limpiar_query(row)
    print(f"Reintentando: {sku} -> Buscando alternativa...")

    intentos = 0
    while intentos < len(CREDENCIALES):
        current_creds = CREDENCIALES[cred_index]
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            # PEDIMOS 3 RESULTADOS AHORA
            params = {'q': query, 'cx': current_creds['cx'], 'key': current_creds['key'], 'searchType': 'image', 'num': 3}
            
            res = requests.get(url, params=params)
            data = res.json()

            if 'items' in data:
                # ESTRATEGIA: Intentar bajar la foto #2, si falla, la #3, si no la #1
                items = data['items']
                exito = False
                
                # Preferencia: Indice 1 (Foto 2), luego Indice 0 (Foto 1), luego Indice 2
                # ¿Por qué? Porque la 1 la borraste (era mala). La 2 suele ser mejor.
                orden_preferencia = [1, 0, 2] 
                
                for i in orden_preferencia:
                    if i < len(items):
                        img_url = items[i]['link']
                        try:
                            content = requests.get(img_url, timeout=8).content
                            # Validar con Pillow que sea imagen real y no HTML
                            filename = f"{sku}.jpg"
                            filepath = os.path.join(OUTPUT_DIR, filename)
                            with open(filepath, 'wb') as f: f.write(content)
                            
                            # Validación técnica
                            with Image.open(filepath) as img:
                                if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                                img.save(filepath, "JPEG")
                            
                            print(f"   ✅ Rescatada (Opción #{i+1})")
                            exito = True
                            descargadas += 1
                            break
                        except:
                            continue # Si falla la descarga, prueba la siguiente opción del loop
                
                if exito: break # Salir de rotación de claves
                else: 
                    print("   ❌ Ninguna de las 3 opciones sirvió.")
                    break

            elif 'error' in data:
                if "quota" in data['error']['message'].lower():
                    print(f"   ⚠️ Cuota agotada Cuenta {cred_index+1}. Cambiando...")
                    cred_index += 1
                    if cred_index >= len(CREDENCIALES): exit()
                    intentos += 1
                    continue
                else:
                    break
            else:
                break # No results

        except Exception as e:
            break # Error conexión

    time.sleep(0.2)

print(f"\nPROCESO TERMINADO: {descargadas} imágenes recuperadas con alternativas.")