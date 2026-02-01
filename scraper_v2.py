import pandas as pd
from duckduckgo_search import DDGS
import requests
import os
import time
import random
import re

# --- CONFIGURACIÓN ---
INPUT_FILE = 'Inventario_KAIQI_Shopify_Ready.csv'
OUTPUT_DIR = 'imagenes_descargadas'
STOP_WORDS = ['CAJA', 'X10', 'X 10', 'JUEGO', 'KIT', 'PAR', 'UNIDAD', 'ORIGINAL', 'TIPO', 'OEM', 'KAIQI']

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

print("--- INICIANDO BÚSQUEDA (MODO LENTO ANTI-BLOQUEO) ---")

# 1. Cargar archivo y filtrar
try:
    df = pd.read_csv(INPUT_FILE)
    col_img = 'Imagen' if 'Imagen' in df.columns else 'Product image URL'
    mask_missing = (df[col_img].isna()) | (df[col_img] == '') | (df[col_img] == 'Sin Imagen') | (df[col_img].str.contains('Sin Imagen', case=False, na=False))
    missing_df = df[mask_missing].copy()
    print(f"Total a buscar: {len(missing_df)}")
except Exception as e:
    print(f"Error leyendo archivo: {e}")
    exit()

def limpiar_query(texto):
    texto = str(texto).upper()
    for word in STOP_WORDS:
        texto = texto.replace(word, '')
    texto = re.sub(r'\s+', ' ', texto).strip()
    return f"{texto} repuesto moto"

# 2. Scraping con pausas
ddgs = DDGS()
descargadas = 0
errores = 0

print("\nComenzando... Paciencia, iremos lento para evitar bloqueos.")

for index, row in missing_df.iterrows():
    sku = str(row['SKU']).strip()
    descripcion = str(row['Descripcion'])
    query = limpiar_query(descripcion)
    
    # Verificar si ya existe para no repetir
    if os.path.exists(os.path.join(OUTPUT_DIR, f"{sku}.jpg")) or os.path.exists(os.path.join(OUTPUT_DIR, f"{sku}.png")):
        print(f"⏭️ {sku} ya existe. Saltando.")
        continue

    print(f"[{descargadas+errores+1}/{len(missing_df)}] Buscando: {sku}...")
    
    try:
        # Pausa aleatoria entre 5 y 12 segundos
        sleep_time = random.uniform(5, 12)
        time.sleep(sleep_time)
        
        results = list(ddgs.images(query, max_results=1))
        
        if results:
            image_url = results[0]['image']
            # Headers para parecer un navegador real
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            
            response = requests.get(image_url, headers=headers, timeout=15)
            if response.status_code == 200:
                ext = 'jpg'
                if 'png' in image_url.lower(): ext = 'png'
                
                filepath = os.path.join(OUTPUT_DIR, f"{sku}.{ext}")
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                print(f"   ✅ OK ({ext})")
                descargadas += 1
            else:
                print("   ❌ Error descarga")
                errores += 1
        else:
            print("   ⚠️ Sin resultados")
            errores += 1
            
    except Exception as e:
        print(f"   ❌ Error búsqueda: {e}")
        errores += 1
        # Si hay error de Ratelimit, esperar 45 segundos extra
        if "403" in str(e) or "Ratelimit" in str(e):
            print("   ⏳ Detectado bloqueo. Esperando 45 segundos...")
            time.sleep(45)

print(f"\nProceso terminado. Descargadas: {descargadas}")