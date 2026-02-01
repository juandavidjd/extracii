import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
import re

# --- CONFIGURACIÓN ---
BASE_URL = "https://www.industriasjapan.com/productos?p="
TOTAL_PAGINAS = 35  # Ponemos un poco más de 31 por si acaso
OUTPUT_DIR = "imagenes_japan"
OUTPUT_CSV = "Base_Datos_Japan.csv"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

print(f"--- INICIANDO SCRAPING MASIVO DE INDUSTRIAS JAPAN (1 a {TOTAL_PAGINAS}) ---")

productos_japan = []
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

for pagina in range(1, TOTAL_PAGINAS + 1):
    url = f"{BASE_URL}{pagina}"
    print(f"📄 Procesando Página {pagina}/{TOTAL_PAGINAS}...")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"   ❌ Error cargando página (Código {response.status_code})")
            continue

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Buscamos los contenedores de productos (Clases típicas, ajustamos búsqueda amplia)
        # Industrias Japan suele usar estructuras tipo 'product-item' o similar.
        # Buscamos todas las imágenes que estén dentro de enlaces
        
        items = soup.find_all('div', class_=re.compile('product-item'))
        
        # Si no encuentra por clase, buscamos genéricamente imágenes grandes
        if not items:
            items = soup.find_all('img')

        encontrados_pag = 0
        
        for item in items:
            # Lógica de extracción: Depende de si es un DIV contenedor o una IMG directa
            img_url = ""
            nombre = ""
            
            if item.name == 'div':
                img_tag = item.find('img')
                if img_tag:
                    img_url = img_tag.get('src')
                    nombre = img_tag.get('alt') or item.get_text(strip=True)
            elif item.name == 'img':
                img_url = item.get('src')
                nombre = item.get('alt')

            # Limpieza y validación
            if img_url and nombre and len(nombre) > 3:
                # Filtramos logos o iconos
                if "logo" in img_url.lower() or "icon" in img_url.lower():
                    continue
                
                # Nombre de archivo limpio
                nombre_limpio = re.sub(r'[^A-Z0-9]', '_', nombre.upper())
                nombre_limpio = re.sub(r'_+', '_', nombre_limpio)[:50] # Max 50 caracteres
                
                filename = f"{nombre_limpio}.jpg"
                filepath = os.path.join(OUTPUT_DIR, filename)
                
                # Guardar en CSV (Memoria)
                productos_japan.append({
                    'Nombre_Externo': nombre.upper(),
                    'Imagen_Externa': filename,
                    'URL_Origen': url
                })
                
                # Descargar imagen si no existe
                if not os.path.exists(filepath):
                    try:
                        # A veces las URL son relativas
                        if not img_url.startswith('http'):
                            img_url = "https://www.industriasjapan.com" + img_url
                            
                        img_data = requests.get(img_url, headers=headers, timeout=5).content
                        with open(filepath, 'wb') as f:
                            f.write(img_data)
                        encontrados_pag += 1
                    except:
                        pass # Si falla una imagen, seguimos
        
        print(f"   ✅ {encontrados_pag} productos nuevos extraídos.")
        
        # Si la página no trajo nada, probablemente llegamos al final
        if encontrados_pag == 0 and len(items) == 0:
            print("   🛑 Página vacía. Fin del catálogo.")
            break

    except Exception as e:
        print(f"   ❌ Error crítico en página: {e}")

    time.sleep(1) # Pausa respetuosa

# Guardar Base de Datos Externa
df = pd.DataFrame(productos_japan)
# Eliminar duplicados
df = df.drop_duplicates(subset=['Nombre_Externo'])
df.to_csv(OUTPUT_CSV, index=False)

print("\n" + "="*40)
print(f"PROCESO FINALIZADO")
print(f"Total productos recolectados: {len(df)}")
print(f"Imágenes guardadas en: {OUTPUT_DIR}")
print(f"Base de datos creada: {OUTPUT_CSV}")
print("="*40)
print("AHORA EJECUTA 'local_matcher.py' PARA CRUZAR ESTOS DATOS CON TU INVENTARIO.")