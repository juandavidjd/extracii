import os
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
import unicodedata
import re

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\scrap"
BASE_URL = "https://yokomar.com"
START_URL = "https://yokomar.com/catalogo/"

# Salidas
CARPETA_SALIDA = os.path.join(BASE_DIR, "ACTIVOS_CLIENTE_YOKOMAR_WEB")
ARCHIVO_CSV = os.path.join(BASE_DIR, "Inventario_Cliente_Yokomar_Web.csv")

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

def obtener_mejor_imagen(img_tag):
    """Extrae la URL de mayor calidad disponible."""
    if not img_tag: return None
    
    # 1. Intentar srcset (contiene varias resoluciones)
    srcset = img_tag.get('srcset')
    if srcset:
        # Tomar la última URL (usualmente la más grande)
        urls = [u.split()[0] for u in srcset.split(',')]
        if urls: return urls[-1]
        
    # 2. Intentar data-src (lazy load)
    if img_tag.get('data-src'): return img_tag.get('data-src')
    if img_tag.get('data-large_image'): return img_tag.get('data-large_image')
    
    # 3. Fallback a src
    return img_tag.get('src')

# ================= MOTOR DE SCRAPING =================
def get_soup(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return BeautifulSoup(r.text, 'html.parser')
    except Exception as e:
        print(f"   ❌ Error conexión: {e}")
    return None

def minar_yokomar():
    print(f"--- INICIANDO SCRAPING: YOKOMAR (JetWooBuilder Mode) ---")
    productos_encontrados = []
    page = 1
    
    while True:
        # Manejo de paginación específico de Yokomar (probablemente /page/X/)
        url_actual = START_URL if page == 1 else f"{START_URL}page/{page}/"
        print(f"\n📄 Escaneando Página {page} ({url_actual})...")
        
        soup = get_soup(url_actual)
        if not soup: 
            print("   🏁 Fin (No se pudo acceder o no existe más contenido).")
            break
        
        # SELECTOR CORREGIDO: Clases específicas de JetWooBuilder encontradas en tu HTML
        items = soup.find_all('div', class_='jet-woo-products__item')
        
        if not items:
            print("   🏁 No se encontraron productos en esta página. Terminando.")
            break
            
        print(f"   -> Encontrados {len(items)} productos potenciales.")
        nuevos_en_pagina = 0
        
        for item in items:
            try:
                # A. Título
                title_tag = item.find(class_='jet-woo-product-title')
                if not title_tag: continue
                titulo = limpiar_texto(title_tag.get_text())
                
                # B. SKU (Clave para tu negocio)
                sku = ""
                sku_tag = item.find(class_='jet-woo-product-sku')
                if sku_tag:
                    sku = limpiar_texto(sku_tag.get_text())
                
                # C. Imagen
                img_wrap = item.find(class_='jet-woo-product-thumbnail')
                img_tag = img_wrap.find('img') if img_wrap else None
                img_src = obtener_mejor_imagen(img_tag)
                
                # D. URL Producto
                link_tag = item.find('a', href=True)
                prod_url = link_tag['href'] if link_tag else ""

                if titulo and img_src:
                    # Crear nombre de archivo SEO: nombre-sku.jpg
                    nombre_base = slugify(titulo)
                    ext = ".jpg"
                    
                    nuevo_nombre = f"{nombre_base}{ext}"
                    if sku: 
                        nuevo_nombre = f"{nombre_base}-{slugify(sku)}{ext}"
                    
                    # Descargar
                    exito_img = descargar_imagen(img_src, nuevo_nombre)
                    
                    productos_encontrados.append({
                        "Nombre_Producto": titulo,
                        "SKU": sku,
                        "Imagen_SEO": nuevo_nombre if exito_img else "",
                        "Imagen_URL_Origen": img_src,
                        "URL_Producto": prod_url,
                        "Fuente": "YOKOMAR_WEB_V2"
                    })
                    
                    sku_str = f" [SKU: {sku}]" if sku else ""
                    print(f"   + {titulo[:40]}...{sku_str}")
                    nuevos_en_pagina += 1
                    
            except Exception as e:
                continue

        if nuevos_en_pagina == 0:
            print("   ⚠️ Página escaneada pero sin productos nuevos.")
            break
            
        page += 1
        time.sleep(1) # Cortesía

    # Guardar CSV Final
    if productos_encontrados:
        df = pd.DataFrame(productos_encontrados)
        df.to_csv(ARCHIVO_CSV, index=False, encoding='utf-8-sig')
        print("\n" + "="*50)
        print(f"✅ SCRAPING YOKOMAR FINALIZADO")
        print(f"   Total Productos: {len(df)}")
        print(f"   CSV Maestro: {ARCHIVO_CSV}")
        print(f"   Imágenes: {CARPETA_SALIDA}")
        print("="*50)
    else:
        print("\n❌ No se extrajeron datos.")

if __name__ == "__main__":
    minar_yokomar()