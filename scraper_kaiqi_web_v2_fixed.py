import os
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
import unicodedata
import re

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\scrap"
BASE_URL = "https://kaiqiparts.com"
# URL Base limpia
START_URL = "https://kaiqiparts.com/tienda/"

CARPETA_SALIDA = os.path.join(BASE_DIR, "ACTIVOS_KAIQI_WEB_OFICIAL")
ARCHIVO_CSV = os.path.join(BASE_DIR, "Inventario_Kaiqi_Web_Oficial.csv")

if not os.path.exists(CARPETA_SALIDA):
    os.makedirs(CARPETA_SALIDA)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
}

# ================= UTILIDADES =================
def slugify(text):
    if not text: return "sin-nombre"
    text = str(text).lower()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')[:100]

def limpiar_texto(text):
    if not text: return ""
    return " ".join(text.split()).strip()

def descargar_imagen(url, nombre_archivo):
    try:
        if not url: return False
        if not url.startswith('http'):
            url = BASE_URL + url if url.startswith('/') else f"{BASE_URL}/{url}"
            
        path = os.path.join(CARPETA_SALIDA, nombre_archivo)
        if os.path.exists(path): return True 

        r = requests.get(url, headers=HEADERS, stream=True, timeout=15)
        if r.status_code == 200:
            with open(path, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
            return True
    except: pass
    return False

# ================= MOTOR DE SCRAPING =================
def get_soup(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return BeautifulSoup(r.text, 'html.parser')
    except Exception as e:
        print(f"   ❌ Error conexión: {e}")
    return None

def minar_kaiqi():
    print(f"--- INICIANDO SCRAPING CORREGIDO: KAIQI PARTS ---")
    productos_totales = []
    page = 1
    
    # Memoria para detectar bucles
    hashes_pagina_anterior = set()
    
    while True:
        # ESTRATEGIA DE PAGINACIÓN: Probamos query param ?paged= que suele ser más robusto
        if page == 1:
            url_actual = START_URL
        else:
            url_actual = f"{START_URL}page/{page}/" 
            
        print(f"\n📄 Escaneando Página {page} ({url_actual})...")
        
        soup = get_soup(url_actual)
        if not soup: break
        
        items = soup.select('li.product')
        if not items: items = soup.select('div.product')
        
        if not items:
            print("   🏁 Fin del catálogo (no items).")
            break
            
        # --- DETECTOR DE BUCLE ---
        hashes_pagina_actual = set()
        nuevos_en_pagina = 0
        
        for item in items:
            try:
                title_tag = item.find(class_='woocommerce-loop-product__title')
                if not title_tag: continue
                titulo = limpiar_texto(title_tag.get_text())
                
                # Generar huella digital del producto
                producto_hash = hashlib.md5(titulo.encode('utf-8')).hexdigest()
                hashes_pagina_actual.add(producto_hash)
                
                # Extracción de datos
                img_tag = item.find('img')
                img_src = ""
                if img_tag:
                    img_src = img_tag.get('data-large_image') or img_tag.get('data-src') or img_tag.get('src')
                    if img_src and '?' in img_src: img_src = img_src.split('?')[0]

                sku = ""
                sku_tag = item.find(class_='sku')
                if sku_tag: sku = limpiar_texto(sku_tag.get_text())
                
                link_tag = item.find('a', href=True)
                prod_url = link_tag['href'] if link_tag else ""
                
                if not sku:
                    match_cod = re.search(r'(COD|REF)[:\.\s]*([A-Z0-9-]{4,10})', titulo, re.IGNORECASE)
                    if match_cod: sku = match_cod.group(2)

                if titulo and img_src:
                    nombre_base = slugify(titulo)
                    ext = ".jpg"
                    nuevo_nombre = f"{nombre_base}{ext}"
                    if sku: nuevo_nombre = f"{nombre_base}-{slugify(sku)}{ext}"
                    
                    exito = descargar_imagen(img_src, nuevo_nombre)
                    
                    if exito:
                        productos_totales.append({
                            "Nombre_Producto": titulo,
                            "SKU": sku,
                            "Imagen_SEO": nuevo_nombre,
                            "Imagen_URL_Origen": img_src,
                            "URL_Producto": prod_url,
                            "Fuente": "KAIQI_WEB_OFICIAL"
                        })
                        print(f"   + {titulo[:40]}...")
                        nuevos_en_pagina += 1
                    
            except Exception as e:
                continue
        
        # CHEQUEO DE SEGURIDAD: ¿Esta página es igual a la anterior?
        if hashes_pagina_actual == hashes_pagina_anterior:
            print("   ⚠️ ALERTA: Bucle detectado. La página es idéntica a la anterior. TERMINANDO.")
            break
            
        hashes_pagina_anterior = hashes_pagina_actual
        
        if nuevos_en_pagina == 0:
            print("   ⚠️ Página sin productos nuevos válidos.")
            break
            
        page += 1
        # time.sleep(1) 

    # Guardar
    if productos_totales:
        # Eliminar duplicados absolutos por si acaso
        df = pd.DataFrame(productos_totales).drop_duplicates(subset=['Nombre_Producto'])
        df.to_csv(ARCHIVO_CSV, index=False, encoding='utf-8-sig')
        print("\n" + "="*50)
        print(f"✅ SCRAPING KAIQI FINALIZADO")
        print(f"   Total Productos Únicos: {len(df)}")
        print(f"   CSV Maestro: {ARCHIVO_CSV}")
        print(f"   Imágenes: {CARPETA_SALIDA}")
        print("="*50)
    else:
        print("\n❌ No se extrajeron datos.")

import hashlib # Import necesario para el detector

if __name__ == "__main__":
    minar_kaiqi()