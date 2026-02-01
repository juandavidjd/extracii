import pandas as pd
from duckduckgo_search import DDGS
import requests
import os
import time
import re

# --- CONFIGURACIÓN ---
INPUT_FILE = 'Inventario_KAIQI_Shopify_Ready.csv'
OUTPUT_DIR = 'imagenes_descargadas'
# Palabras a eliminar para mejorar la búsqueda (hacerla más genérica)
STOP_WORDS = ['CAJA', 'X10', 'X 10', 'JUEGO', 'KIT', 'PAR', 'UNIDAD', 'ORIGINAL', 'TIPO', 'OEM', 'KAIQI']

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

print("--- INICIANDO BÚSQUEDA AUTOMÁTICA DE IMÁGENES ---")

# 1. Cargar archivo
try:
    df = pd.read_csv(INPUT_FILE)
    # Filtrar solo los que NO tienen imagen o dicen "Sin Imagen"
    # Normalizamos columnas por si acaso
    col_img = 'Imagen' if 'Imagen' in df.columns else 'Product image URL'
    
    # Identificar faltantes: vacíos, NaN, o 'Sin Imagen'
    mask_missing = (df[col_img].isna()) | (df[col_img] == '') | (df[col_img] == 'Sin Imagen') | (df[col_img].str.contains('Sin Imagen', case=False, na=False))
    missing_df = df[mask_missing].copy()
    
    print(f"Total productos en inventario: {len(df)}")
    print(f"Productos sin imagen a buscar: {len(missing_df)}")
    
except Exception as e:
    print(f"Error leyendo archivo: {e}")
    exit()

# Función para limpiar la búsqueda
def limpiar_query(texto):
    texto = str(texto).upper()
    for word in STOP_WORDS:
        texto = texto.replace(word, '')
    # Quitar caracteres raros y espacios extra
    texto = re.sub(r'\s+', ' ', texto).strip()
    # Truco: Agregar "Repuesto Moto" para contexto
    return f"{texto} repuesto moto"

# 2. Proceso de Scraping
ddgs = DDGS()
descargadas = 0
errores = 0

print("\nComenzando descargas... (Esto tomará un tiempo, presiona Ctrl+C para detener)")

for index, row in missing_df.iterrows():
    sku = str(row['SKU']).strip()
    descripcion_original = str(row['Descripcion'])
    query = limpiar_query(descripcion_original)
    
    print(f"[{descargadas+errores+1}/{len(missing_df)}] Buscando: {sku} - {query[:40]}...")
    
    try:
        # Buscamos 1 resultado de imagen
        results = list(ddgs.images(query, max_results=1))
        
        if results:
            image_url = results[0]['image']
            
            # Descargar
            response = requests.get(image_url, timeout=10)
            if response.status_code == 200:
                # Definir extensión (jpg o png)
                ext = 'jpg'
                if 'png' in image_url.lower(): ext = 'png'
                
                filename = f"{sku}.{ext}"
                filepath = os.path.join(OUTPUT_DIR, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                print(f"   ✅ Descargada: {filename}")
                descargadas += 1
            else:
                print("   ❌ Error descargando URL")
                errores += 1
        else:
            print("   ⚠️ No se encontraron imágenes")
            errores += 1
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        errores += 1
    
    # Pausa pequeña para no ser bloqueados
    time.sleep(1.5)

print("\n" + "="*40)
print(f"PROCESO TERMINADO")
print(f"Imágenes descargadas: {descargadas}")
print(f"Fallos/No encontradas: {errores}")
print(f"Revisa la carpeta: {os.path.abspath(OUTPUT_DIR)}")
print("="*40)
print("IMPORTANTE: Revisa las fotos manualmente. Si alguna no corresponde, bórrala.")