import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
import re

# --- CONFIGURACIÓN ---
URL_SUPERMOTOSCAR = "https://supermotoscar.com/ayco-bajaj-vaisand-repuestos-motocarros.html"
OUTPUT_DIR = "imagenes_supermotoscar"
OUTPUT_CSV = "Base_Datos_Supermotoscar.csv"

# --- LISTA DE POSIBLES ESTRUCTURAS (Adivinador) ---
# Intentaremos encontrar productos usando estas clases comunes
CLASES_CONTENEDOR = [
    'product-container',     # Intento 1 (El que falló)
    'product-item',          # Intento 2 (Muy común)
    'product',               # Intento 3 (Común en WooCommerce)
    'item-product',          # Intento 4
]

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

print(f"--- INICIANDO SCRAPING V2 (Modo Resiliente) ---")

productos_scar = []
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

try:
    response = requests.get(URL_SUPERMOTOSCAR, headers=headers, timeout=20)
    
    if response.status_code != 200:
        print(f"   ❌ Error {response.status_code}. No se pudo cargar la página.")
        exit()

    soup = BeautifulSoup(response.content, 'html.parser')
    
    items = []
    for clase in CLASES_CONTENEDOR:
        print(f"Probando estructura: 'div.{clase}'...")
        items = soup.find_all('div', class_=clase)
        if items:
            print(f"   ✅ ¡Éxito! Estructura encontrada: '{clase}' (Detectados {len(items)} productos)")
            break
        else:
            print(f"   ...falló.")
    
    if not items:
        print("   🛑 AGOTADOS TODOS LOS INTENTOS. No se pudo identificar la estructura de productos.")
        exit()

    encontrados_pag = 0
    
    for item in items:
        try:
            # Encontrar el nombre del producto (buscamos por varias clases comunes)
            name_tag = item.find(['div', 'a', 'h2', 'h3'], class_=re.compile(r'name|title|nombre', re.IGNORECASE))
            if not name_tag: # Si no lo encuentra por clase, busca el texto del contenedor
                nombre = item.get_text(strip=True)
            else:
                nombre = name_tag.get_text(strip=True)

            # Encontrar la imagen
            img_tag = item.find('img')
            img_url = img_tag.get('src') if img_tag else None

            if img_url and nombre and len(nombre) > 3:
                
                # Limpiar nombre de archivo
                filename = re.sub(r'[\\/*?:"<>|]', '', nombre) + ".jpg"
                filepath = os.path.join(OUTPUT_DIR, filename)
                
                # Guardar en CSV
                productos_scar.append({
                    'Nombre_Externo': nombre.upper(),
                    'Imagen_Externa': filename,
                    'URL_Origen': img_url
                })
                
                if not os.path.exists(filepath):
                    if not img_url.startswith('http'):
                        img_url = "https://supermotoscar.com" + img_url
                        
                    img_data = requests.get(img_url, headers=headers, timeout=5).content
                    with open(filepath, 'wb') as f:
                        f.write(img_data)
                    encontrados_pag += 1
        except Exception:
            continue 
    
    print(f"   ✅ {encontrados_pag} imágenes nuevas descargadas.")

except Exception as e:
    print(f"   ❌ Error crítico en el scraping: {e}")

# Guardar Base de Datos Externa
df = pd.DataFrame(productos_scar)
df = df.drop_duplicates(subset=['Nombre_Externo'])
df.to_csv(OUTPUT_CSV, index=False)

print("\n" + "="*40)
print(f"PROCESO V2 FINALIZADO")
print(f"Total productos recolectados: {len(df)}")
print(f"Base de datos creada: {OUTPUT_CSV}")
print("="*40)