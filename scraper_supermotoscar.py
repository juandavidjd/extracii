import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
import re

# --- CONFIGURACIÓN ---
URL_SUPERMOTOSCAR = "https://supermotoscar.com/ayco-bajaj-vaisand-repuestos-motocarros.html"
OUTPUT_DIR = "imagenes_supermotoscar" # Nueva carpeta para estas fotos
OUTPUT_CSV = "Base_Datos_Supermotoscar.csv" # Nueva base de datos

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

print(f"--- INICIANDO SCRAPING DE SUPERMOTOSCAR ---")

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
    
    # Esta es la clase que usa Supermotoscar para cada producto
    items = soup.find_all('div', class_='product-container')
    
    if not items:
        print("   🛑 No se encontraron productos. La estructura de la web pudo cambiar.")
        exit()

    print(f"✅ Página cargada. Analizando {len(items)} productos encontrados...")
    encontrados_pag = 0
    
    for item in items:
        try:
            # Encontrar el nombre del producto
            name_tag = item.find('div', class_='product-name')
            nombre = name_tag.get_text(strip=True) if name_tag else "SIN NOMBRE"
            
            # Encontrar la imagen
            img_tag = item.find('img')
            img_url = img_tag.get('src') if img_tag else None

            if img_url and nombre != "SIN NOMBRE":
                
                # Nombre de archivo (usamos el nombre del producto)
                filename = re.sub(r'[\\/*?:"<>|]', '', nombre) + ".jpg"
                filepath = os.path.join(OUTPUT_DIR, filename)
                
                # Guardar en CSV
                productos_scar.append({
                    'Nombre_Externo': nombre.upper(),
                    'Imagen_Externa': filename, # El nombre del archivo local
                    'URL_Origen': img_url # URL de la imagen
                })
                
                # Descargar imagen si no la tenemos
                if not os.path.exists(filepath):
                    # Asegurarse que la URL es absoluta
                    if not img_url.startswith('http'):
                        img_url = "https://supermotoscar.com" + img_url
                        
                    img_data = requests.get(img_url, headers=headers, timeout=5).content
                    with open(filepath, 'wb') as f:
                        f.write(img_data)
                    encontrados_pag += 1
        except Exception as e:
            print(f"   Error en un item: {e}")
            continue # Si un item falla, saltar al siguiente
    
    print(f"   ✅ {encontrados_pag} imágenes nuevas descargadas.")

except Exception as e:
    print(f"   ❌ Error crítico en el scraping: {e}")

# Guardar Base de Datos Externa
df = pd.DataFrame(productos_scar)
df = df.drop_duplicates(subset=['Nombre_Externo'])
df.to_csv(OUTPUT_CSV, index=False)

print("\n" + "="*40)
print(f"PROCESO FINALIZADO")
print(f"Total productos recolectados: {len(df)}")
print(f"Imágenes guardadas en: {OUTPUT_DIR}")
print(f"Base de datos creada: {OUTPUT_CSV}")
print("="*40)