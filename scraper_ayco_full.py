import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
import re

# --- CONFIGURACIÓN ---
# Lista de las categorías principales que minaremos
CATEGORIAS_A_MINAR = [
    "https://ayco.com.co/categoria-producto/motor/",
    "https://ayco.com.co/categoria-producto/caja-velocidades/",
    "https://ayco.com.co/categoria-producto/transmision/",
    "https://ayco.com.co/categoria-producto/electrico/",
    "https://ayco.com.co/categoria-producto/chasis/",
    "https://ayco.com.co/categoria-producto/accesorios/"
]

MAX_PAGINAS_POR_CAT = 15 # Límite de seguridad
OUTPUT_DIR = "imagenes_ayco"
OUTPUT_CSV = "Base_Datos_AYCO.csv"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

print(f"--- INICIANDO SCRAPING MASIVO DE AYCO (Multi-Categoría) ---")

productos_ayco = []
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# 1. Loop por cada CATEGORÍA
for categoria_url in CATEGORIAS_A_MINAR:
    print(f"\n--- 📂 Iniciando Categoría: {categoria_url.split('/')[-2]} ---")
    
    # 2. Loop por cada PÁGINA dentro de esa categoría
    for pagina in range(1, MAX_PAGINAS_POR_CAT + 1):
        
        # La página 1 tiene URL base, las siguientes usan /page/N/
        if pagina == 1:
            url = categoria_url
        else:
            url = f"{categoria_url}page/{pagina}/"
            
        print(f"  📄 Procesando Página {pagina}...")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            # Si da 404, significa que esta categoría no tiene tantas páginas
            if response.status_code != 200:
                print(f"     🛑 Fin de la categoría (Error {response.status_code}).")
                break 

            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Usamos la misma estructura de Vaisand/WooCommerce
            items = soup.find_all('li', class_='product')
            
            if not items:
                print("     🛑 No se encontraron productos. Fin de la categoría.")
                break

            encontrados_pag = 0
            
            for item in items:
                try:
                    name_tag = item.find('h2', class_='woocommerce-LoopProduct-title')
                    nombre = name_tag.get_text(strip=True) if name_tag else "SIN NOMBRE"
                    
                    img_tag = item.find('img', class_='woo-entry-image-main')
                    img_url = img_tag.get('src') if img_tag else None

                    if img_url and nombre != "SIN NOMBRE":
                        
                        filename = re.sub(r'[\\/*?:"<>|]', '', nombre) + ".jpg"
                        filepath = os.path.join(OUTPUT_DIR, filename)
                        
                        productos_ayco.append({
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
            
            print(f"     ✅ {encontrados_pag} imágenes nuevas extraídas.")

        except Exception as e:
            print(f"   ❌ Error crítico en página: {e}")

        time.sleep(0.5) # Pausa respetuosa

# Guardar Base de Datos Externa
df = pd.DataFrame(productos_ayco)
df = df.drop_duplicates(subset=['Nombre_Externo'])
df.to_csv(OUTPUT_CSV, index=False)

print("\n" + "="*40)
print(f"PROCESO FINALIZADO")
print(f"Total productos recolectados: {len(df)}")
print(f"Imágenes guardadas en: {OUTPUT_DIR}")
print(f"Base de datos creada: {OUTPUT_CSV}")
print("="*40)