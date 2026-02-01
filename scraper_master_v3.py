import pandas as pd
import requests
import os
import time
import re

# --- TUS CREDENCIALES (5 NUEVAS + 3 ANTERIORES) ---
# El script las usará en orden. Si una se agota, pasa a la siguiente.
CREDENCIALES = [
    # --- 5 NUEVAS ---
    {"key": "AIzaSyACy6NrSC3YDsqgCfnP7pKweWFnFTycJhI", "cx": "7468cbc866be74c62"},
    {"key": "AIzaSyCIt14hUVPuloz6KEAGifdE8Vyyn2Mf0cE", "cx": "152e6e925018c41ca"},
    {"key": "AIzaSyDz_r2WBMjmqZpqYHLRQoZsALs0tBsIDn8", "cx": "f4c070cde3bf24546"},
    {"key": "AIzaSyDNby0O73cWpAcERV2XnY92LM2_5Swv1ww", "cx": "c21bbbe50fa7e4cbc"},
    {"key": "AIzaSyBkqhMQ-6f0Xj8wHvb46sXD1BmbJslrRp4", "cx": "a3f481653a3a34a89"},
    
    # --- 3 ANTERIORES (Por si acaso mañana o si les queda saldo) ---
    {"key": "AIzaSyCqRxWNMXRpOmUVhpNGXHTmQZYvgcL0Unk", "cx": "d775153f2e9c74e51"},
    {"key": "AIzaSyBIUS2iB1u88MqN4mXxSqdLlP83Kf9s8Rc", "cx": "c6ab83d6950f34110"},
    {"key": "AIzaSyBlGX62Etxc4-rBoO_JWllDq4-CK_FUKz0", "cx": "f59aebe1a50da4ef7"}
]

# --- CONFIGURACIÓN ---
INPUT_FILE = 'Inventario_KAIQI_Shopify_Ready.csv'
OUTPUT_DIR = 'imagenes_descargadas'

# Palabras basura a eliminar para que la búsqueda sea "humana" y efectiva
STOP_WORDS = [
    'CAJA', 'X10', 'X 10', 'JUEGO', 'KIT', 'PAR', 'UNIDAD', 'ORIGINAL', 'TIPO', 'OEM', 'KAIQI', 
    'REPUESTO', 'DALU', 'SMG', 'HLK', 'TWOM', 'KAY', 'CHO', 'KET', 'MN', 'MV', 'EOM', 'CTO', 'COMPL'
]

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

print("--- INICIANDO BÚSQUEDA MAESTRA (MODO ASPIRADORA - 8 CUENTAS) ---")

# 1. Cargar Datos
try:
    df = pd.read_csv(INPUT_FILE)
    col_img = 'Imagen' if 'Imagen' in df.columns else 'Product image URL'
    # Filtramos los que no tienen imagen (vacíos, NaN o "Sin Imagen")
    mask_missing = (df[col_img].isna()) | (df[col_img] == '') | (df[col_img] == 'Sin Imagen')
    missing_df = df[mask_missing].copy()
    print(f"Total productos: {len(df)}")
    print(f"Faltantes por buscar: {len(missing_df)}")
except Exception as e:
    print(f"Error leyendo archivo: {e}")
    exit()

def limpiar_query(texto):
    # 1. Convertir a mayúsculas
    texto = str(texto).upper()
    # 2. Eliminar palabras técnicas del SKU que confunden a Google
    for word in STOP_WORDS:
        texto = texto.replace(word, '')
    # 3. Quitar caracteres raros pero dejar números (para cilindradas 125, 200, etc)
    texto = re.sub(r'[^A-Z0-9\s]', ' ', texto) 
    # 4. Quitar espacios dobles
    texto = re.sub(r'\s+', ' ', texto).strip()
    # 5. Agregar contexto clave
    return f"{texto} repuesto moto colombia"

# Variables de control
cred_index = 0
descargadas = 0
errores = 0
saltadas = 0

print(f"\nUsando Credencial #{cred_index + 1}...")

for index, row in missing_df.iterrows():
    sku = str(row['SKU']).strip()
    desc = str(row['Descripcion'])
    
    # --- SALTAR SI YA EXISTE (Cualquier extensión) ---
    # Buscamos si existe algun archivo que empiece con el SKU en la carpeta de descarga
    existe = False
    for archivo in os.listdir(OUTPUT_DIR):
        if archivo.startswith(f"{sku}."):
            existe = True
            break
    
    if existe:
        saltadas += 1
        # No imprimimos "saltando" para que corra más rápido visualmente
        continue

    query = limpiar_query(desc)
    print(f"[{descargadas+1}] Buscando: {sku} -> '{query}'...")

    # Bucle de intentos (Rotación de claves)
    intentos = 0
    while intentos < len(CREDENCIALES):
        current_creds = CREDENCIALES[cred_index]
        
        try:
            # --- CONFIGURACIÓN MODO ASPIRADORA ---
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'q': query, 
                'cx': current_creds['cx'], 
                'key': current_creds['key'],
                'searchType': 'image', 
                'num': 1
                # SIN FILTROS DE TAMAÑO NI FORMATO NI TIPO DE ARCHIVO
            }
            
            res = requests.get(url, params=params)
            data = res.json()

            # SI HAY ÉXITO
            if 'items' in data:
                img_url = data['items'][0]['link']
                try:
                    # Descargar contenido
                    img_data = requests.get(img_url, timeout=10).content
                    
                    # Detectar extensión real por URL
                    ext = 'jpg' # Default
                    if '.png' in img_url.lower(): ext = 'png'
                    elif '.webp' in img_url.lower(): ext = 'webp'
                    elif '.jpeg' in img_url.lower(): ext = 'jpg'
                    elif '.gif' in img_url.lower(): ext = 'gif'

                    filename = f"{sku}.{ext}"
                    with open(os.path.join(OUTPUT_DIR, filename), 'wb') as f:
                        f.write(img_data)
                    
                    print(f"   ✅ OK ({ext})")
                    descargadas += 1
                    break # Éxito, salimos del bucle de intentos
                except:
                    print("   ❌ Error descargando archivo (Link roto).")
                    errores += 1
                    break 
            
            # SI HAY ERROR EN LA API (CUOTA)
            elif 'error' in data:
                msg = data['error']['message']
                if "quota" in msg.lower() or "bill" in msg.lower():
                    print(f"   ⚠️ CUOTA AGOTADA en Cuenta {cred_index+1}. Cambiando...")
                    # Cambiar a la siguiente cuenta
                    cred_index += 1
                    if cred_index >= len(CREDENCIALES):
                        print("\n🛑 ¡TODAS LAS 8 CUENTAS AGOTADAS! Intenta mañana.")
                        exit()
                    print(f"   🔄 Ahora usando Cuenta {cred_index+1}")
                    intentos += 1
                    continue # Reintentar el MISMO producto con la nueva clave
                else:
                    print(f"   ⚠️ No encontrada / Error API: {msg}")
                    errores += 1
                    break
            else:
                print("   ⚠️ No encontrada (Ni en modo aspiradora)")
                errores += 1
                break

        except Exception as e:
            print(f"   ❌ Error conexión: {e}")
            errores += 1
            break
    
    # Pausa mínima para velocidad
    time.sleep(0.2)

print("\n" + "="*40)
print(f"INFORME FINAL:")
print(f"⏭️  Saltadas (Ya existían): {saltadas}")
print(f"✅ Nuevas descargadas: {descargadas}")
print(f"⚠️ No encontradas: {errores}")
print("="*40)