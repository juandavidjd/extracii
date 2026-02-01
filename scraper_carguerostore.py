import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
import re

# --- CONFIGURACIÓN ---
BASE_URL = "https://www.carguerostore.com/productos/page/" # URL base para paginación
TOTAL_PAGINAS = 25  # Tienen 23, ponemos 25 por si acaso
OUTPUT_DIR = "imagenes_carguerostore"
OUTPUT_CSV = "Base_Datos_CargueroStore.csv"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

print(f"--- INICIANDO SCRAPING MASIVO DE CARGUEROSTORE (1 a {TOTAL_PAGINAS}) ---")

productos_store = []
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

for pagina in range(1, TOTAL_PAGINAS + 1):
    # La página 1 es la URL raíz de la tienda
    if pagina == 1:
        url = "https://www.carguerostore.com/productos/"
    else:
        url = f"{BASE_URL}{pagina}/"
        
    print(f"📄 Procesando Página {pagina}/{TOTAL_PAGINAS}...")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"   🛑 Error {response.status_code}. Asumiendo fin del catálogo.")
            break 

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Estructura de WooCommerce
        items = soup.find_all('li', class_='product')
        
        if not items:
            print("   🛑 No se encontraron productos. Fin del catálogo.")
            break

        encontrados_pag = 0
        
        for item in items:
            try:
                # Encontrar el nombre
                name_tag = item.find('h2', class_='woocommerce-loop-product__title')
                nombre = name_tag.get_text(strip=True) if name_tag else "SIN NOMBRE"
                
                # Encontrar la imagen
                img_tag = item.find('img')
                # Usamos 'data-src' o 'src' (a veces usan lazy loading)
                img_url = img_tag.get('data-src') or img_tag.get('src') if img_tag else None

                if img_url and nombre != "SIN NOMBRE":
                    
                    filename = re.sub(r'[\\/*?:"<>|]', '', nombre) + ".jpg"
                    filepath = os.path.join(OUTPUT_DIR, filename)
                    
                    productos_store.append({
                        'Nombre_Externo': nombre.upper(),
                        'Imagen_Externa': filename,
                        'URL_Origen': img_url
                    })
                    
                    if not os.path.exists(filepath):
                        img_data = requests.get(img_url, headers=headers, timeout=5).content
                        with open(filepath, 'wb') as f:
                            f.write(img_data)
                        encontrados_pag += 1
            except Exception:
                continue 
        
        print(f"   ✅ {encontrados_pag} imágenes nuevas extraídas.")

    except Exception as e:
        print(f"   ❌ Error crítico en página: {e}")

    time.sleep(1) # Pausa respetuosa

# Guardar Base de Datos Externa
df = pd.DataFrame(productos_store)
df = df.drop_duplicates(subset=['Nombre_Externo'])
df.to_csv(OUTPUT_CSV, index=False)

print("\n" + "="*40)
print(f"PROCESO FINALIZADO")
print(f"Total productos recolectados: {len(df)}")
print(f"Imágenes guardadas en: {OUTPUT_DIR}")
print(f"Base de datos creada: {OUTPUT_CSV}")
print("="*40)