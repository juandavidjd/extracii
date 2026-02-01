import os
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
import unicodedata
import re

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\scrap"
BASE_URL = "https://armvalle.com"
TARGET_URL = "https://armvalle.com/?page_id=394"  # URL Específica

# Salidas
CARPETA_SALIDA = os.path.join(BASE_DIR, "ACTIVOS_CLIENTE_NF_CATALOGO")
ARCHIVO_CSV = os.path.join(BASE_DIR, "Inventario_Cliente_NF_Catalogo_Page.csv")

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
            if url.startswith('//'): url = "https:" + url
            elif url.startswith('/'): url = BASE_URL + url
            else: url = f"{BASE_URL}/{url}"
            
        path = os.path.join(CARPETA_SALIDA, nombre_archivo)
        if os.path.exists(path): return True 

        r = requests.get(url, headers=HEADERS, stream=True, timeout=15)
        if r.status_code == 200:
            with open(path, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
            return True
    except Exception as e:
        print(f"   ⚠️ Error imagen: {e}")
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

def minar_pagina_especial():
    print(f"--- INICIANDO SCRAPING ESPECIAL: {TARGET_URL} ---")
    productos_encontrados = []
    
    soup = get_soup(TARGET_URL)
    if not soup: 
        print("   ❌ No se pudo acceder a la página.")
        return

    # 1. INTENTO A: Búsqueda Estándar WooCommerce
    items = soup.select('li.product')
    if not items: items = soup.select('div.product')
    
    # 2. INTENTO B: Búsqueda Genérica (Si es una landing de Elementor)
    # Buscamos columnas que tengan imagen + título h2/h3/h4
    if not items:
        print("   ℹ️ No se detectó estructura estándar de tienda. Activando modo 'Landing Page'...")
        # Buscamos contenedores genéricos que tengan imagen
        posibles_items = soup.find_all(['div', 'article'], class_=re.compile(r'column|item|elementor-widget-image-box'))
        items = [i for i in posibles_items if i.find('img') and i.find(re.compile('h[1-6]'))]

    print(f"   -> Detectados {len(items)} elementos potenciales.")
    
    for item in items:
        try:
            # Extracción Título
            title_tag = item.find(re.compile('h[1-6]'), class_=re.compile(r'title|name'))
            if not title_tag: 
                title_tag = item.find(re.compile('h[1-6]')) # Fallback agresivo
            
            if not title_tag: continue
            titulo = limpiar_texto(title_tag.get_text())
            
            # Extracción Imagen
            img_tag = item.find('img')
            img_src = ""
            if img_tag:
                img_src = img_tag.get('data-src') or img_tag.get('src')
                if img_src and '?' in img_src: img_src = img_src.split('?')[0] # Limpiar params

            # Extracción Enlace (URL Producto)
            link_tag = item.find('a', href=True)
            prod_url = link_tag['href'] if link_tag else ""

            # Extracción SKU (Si existe visible)
            sku = ""
            # Buscar texto que parezca SKU cercano
            texto_item = item.get_text(" ", strip=True)
            match_sku = re.search(r'(COD|REF|SKU)[:\.\s]*([A-Z0-9-]{4,10})', texto_item, re.IGNORECASE)
            if match_sku:
                sku = match_sku.group(2)

            if titulo and img_src and len(titulo) > 3:
                # Renombrado SEO
                nombre_base = slugify(titulo)
                ext = ".jpg"
                nuevo_nombre = f"{nombre_base}{ext}"
                if sku: nuevo_nombre = f"{nombre_base}-{slugify(sku)}{ext}"
                
                # Descargar
                exito = descargar_imagen(img_src, nuevo_nombre)
                
                if exito:
                    productos_encontrados.append({
                        "Nombre_Producto": titulo,
                        "SKU_Detectado": sku,
                        "Imagen_SEO": nuevo_nombre,
                        "Imagen_URL_Origen": img_src,
                        "URL_Producto": prod_url,
                        "Fuente": "ARMVALLE_CATALOGO_PAGE"
                    })
                    print(f"   + {titulo[:40]}...")

        except Exception as e:
            continue

    # Guardar
    if productos_encontrados:
        df = pd.DataFrame(productos_encontrados)
        df.to_csv(ARCHIVO_CSV, index=False, encoding='utf-8-sig')
        print("\n" + "="*50)
        print(f"✅ EXTRACCIÓN ESPECIAL FINALIZADA")
        print(f"   Total Activos: {len(df)}")
        print(f"   CSV: {ARCHIVO_CSV}")
        print(f"   Imágenes: {CARPETA_SALIDA}")
        print("="*50)
    else:
        print("\n❌ No se encontraron productos. La estructura puede ser muy diferente.")

if __name__ == "__main__":
    minar_pagina_especial()