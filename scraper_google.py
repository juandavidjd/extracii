import pandas as pd
import requests
import os
import time
import re

# --- TUS CREDENCIALES ---
MY_API_KEY = "AIzaSyCqRxWNMXRpOmUVhpNGXHTmQZYvgcL0Unk"
MY_CX = "d775153f2e9c74e51"

# --- CONFIGURACIÓN ---
INPUT_FILE = 'Inventario_KAIQI_Shopify_Ready.csv'
OUTPUT_DIR = 'imagenes_descargadas'
# Palabras a ignorar para limpiar la búsqueda
STOP_WORDS = ['CAJA', 'X10', 'X 10', 'JUEGO', 'KIT', 'PAR', 'UNIDAD', 'ORIGINAL', 'TIPO', 'OEM', 'KAIQI', 'REPUESTO']

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

print("--- INICIANDO BÚSQUEDA DE IMÁGENES (GOOGLE API OFICIAL) ---")

# 1. Cargar y filtrar
try:
    df = pd.read_csv(INPUT_FILE)
    col_img = 'Imagen' if 'Imagen' in df.columns else 'Product image URL'
    
    # Detectar productos sin imagen (vacíos, NaN o "Sin Imagen")
    mask_missing = (df[col_img].isna()) | (df[col_img] == '') | (df[col_img] == 'Sin Imagen')
    missing_df = df[mask_missing].copy()
    
    print(f"Total productos en archivo: {len(df)}")
    print(f"Objetivo a buscar: {len(missing_df)} imágenes.")
except Exception as e:
    print(f"Error leyendo archivo {INPUT_FILE}: {e}")
    exit()

def limpiar_query(texto):
    texto = str(texto).upper()
    for word in STOP_WORDS:
        texto = texto.replace(word, '')
    # Limpiar espacios y agregar contexto
    texto = re.sub(r'\s+', ' ', texto).strip()
    return f"{texto} repuesto moto"

# 2. Bucle de descarga
descargadas = 0
errores = 0
daily_limit = 100 # Límite gratuito diario de Google

print(f"\nATENCIÓN: Tienes {daily_limit} búsquedas gratis hoy.")
print("El script parará automáticamente si llegas al límite o si hay error de cuota.\n")

for index, row in missing_df.iterrows():
    # Verificar límite local (contador simple)
    if descargadas + errores >= daily_limit:
        print("\n🛑 LÍMITE DIARIO ALCANZADO (Contador local). Continúa mañana.")
        break

    sku = str(row['SKU']).strip()
    desc = str(row['Descripcion'])
    
    # Saltar si ya existe el archivo
    if os.path.exists(os.path.join(OUTPUT_DIR, f"{sku}.jpg")) or os.path.exists(os.path.join(OUTPUT_DIR, f"{sku}.png")):
        print(f"⏭️ {sku} ya existe.")
        continue

    query = limpiar_query(desc)
    print(f"[{descargadas+1}] Buscando: {sku} -> '{query}'...")

    try:
        # Petición a Google API
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'q': query,
            'cx': MY_CX,
            'key': MY_API_KEY,
            'searchType': 'image',
            'num': 1,
            'imgSize': 'large', # Intentar buscar imágenes grandes
            'fileType': 'jpg'   # Preferir JPG
        }
        
        res = requests.get(url, params=params)
        data = res.json()

        if 'items' in data:
            img_url = data['items'][0]['link']
            
            # Intentar descargar la imagen
            try:
                img_data = requests.get(img_url, timeout=10).content
                
                filename = f"{sku}.jpg"
                with open(os.path.join(OUTPUT_DIR, filename), 'wb') as f:
                    f.write(img_data)
                
                print(f"   ✅ OK")
                descargadas += 1
            except:
                print("   ❌ Error descargando el archivo de imagen.")
                errores += 1
        else:
            # Manejo de errores de API
            if 'error' in data:
                msg = data['error']['message']
                print(f"   ❌ Error API: {msg}")
                if "quota" in msg.lower() or "bill" in msg.lower():
                    print("\n🛑 SE ACABÓ LA CUOTA DIARIA DE GOOGLE.")
                    break
            else:
                print("   ⚠️ No se encontraron resultados visuales.")
                errores += 1

    except Exception as e:
        print(f"   ❌ Error conexión: {e}")
        errores += 1
    
    # Pequeña pausa de cortesía
    time.sleep(0.5)

print("\n" + "="*40)
print(f"RESUMEN: {descargadas} nuevas imágenes descargadas.")
print(f"Revisa la carpeta: {os.path.abspath(OUTPUT_DIR)}")
print("="*40)