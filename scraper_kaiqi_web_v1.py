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
START_URL = "https://kaiqiparts.com/tienda/"

# Salidas
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
    print(f"--- INICIANDO SCRAPING: KAIQI PARTS ({START_URL}) ---")
    productos_encontrados = []
    page = 1
    
    while True:
        # URL de paginación estándar (WooCommerce suele ser /page/2/)
        url_actual = START_URL if page == 1 else f"{START_URL}page/{page}/"
        print(f"\n📄 Escaneando Página {page} ({url_actual})...")
        
        soup = get_soup(url_actual)
        if not soup: 
            print("   🏁 Fin (Error de conexión o fin de páginas).")
            break
        
        # Selectores estándar de WooCommerce
        items = soup.select('li.product')
        if not items: items = soup.select('div.product')
        
        if not items:
            # Verificación extra: ¿Hay mensaje de "no encontrado"?
            if "no products found" in soup.text.lower() or "no se encontraron" in soup.text.lower():
                print("   🏁 Fin del catálogo detectado.")
                break
            
            # Si no hay items pero tampoco mensaje de fin, puede que la estructura sea distinta
            print("   ⚠️ No se detectaron productos. Revisando estructura alternativa...")
            items = soup.find_all(class_=re.compile(r'product-type'))
            if not items:
                print("   🏁 No hay más productos.")
                break
            
        print(f"   -> Encontrados {len(items)} productos.")
        nuevos_en_pagina = 0
        
        for item in items:
            try:
                # A. Título
                title_tag = item.find(class_='woocommerce-loop-product__title')
                if not title_tag: title_tag = item.find(re.compile('h[1-6]'), class_=re.compile('title'))
                
                if not title_tag: continue
                titulo = limpiar_texto(title_tag.get_text())
                
                # B. Imagen
                img_tag = item.find('img')
                img_src = ""
                if img_tag:
                    # Prioridad a imagen grande
                    img_src = img_tag.get('data-large_image') or \
                              img_tag.get('data-src') or \
                              img_tag.get('src')
                    if img_src and '?' in img_src: img_src = img_src.split('?')[0]

                # C. SKU (Si está visible en la grilla)
                sku = ""
                # Intento 1: Buscar clase 'sku'
                sku_tag = item.find(class_='sku')
                if sku_tag: sku = limpiar_texto(sku_tag.get_text())
                
                # Intento 2: Extraer del enlace (a veces el slug es el SKU o nombre-sku)
                link_tag = item.find('a', href=True)
                prod_url = link_tag['href'] if link_tag else ""
                
                # Si no hay SKU visible, intentamos inferirlo del título si tiene formato "COD: 123"
                if not sku:
                    match_cod = re.search(r'(COD|REF)[:\.\s]*([A-Z0-9-]{4,10})', titulo, re.IGNORECASE)
                    if match_cod: sku = match_cod.group(2)

                # D. Categoría (Opcional)
                cat_tag = item.find(class_='product-category')
                categoria = limpiar_texto(cat_tag.get_text()) if cat_tag else ""

                if titulo and img_src:
                    # Nombre SEO
                    nombre_base = slugify(titulo)
                    ext = ".jpg"
                    nuevo_nombre = f"{nombre_base}{ext}"
                    if sku: nuevo_nombre = f"{nombre_base}-{slugify(sku)}{ext}"
                    
                    # Descargar
                    exito = descargar_imagen(img_src, nuevo_nombre)
                    
                    # Solo guardamos si tiene imagen válida (filtro de calidad)
                    # O si queremos el registro aunque no tenga foto, quitamos el 'if exito'
                    if exito or "placeholder" not in img_src:
                        productos_encontrados.append({
                            "Nombre_Producto": titulo,
                            "SKU": sku,
                            "Categoria": categoria,
                            "Imagen_SEO": nuevo_nombre if exito else "",
                            "Imagen_URL_Origen": img_src,
                            "URL_Producto": prod_url,
                            "Fuente": "KAIQI_WEB_OFICIAL"
                        })
                        print(f"   + {titulo[:40]}...")
                        nuevos_en_pagina += 1
                    
            except Exception as e:
                continue
        
        if nuevos_en_pagina == 0:
            print("   ⚠️ Página sin productos nuevos. Terminando por seguridad.")
            break
            
        page += 1
        time.sleep(1) # Pausa para no saturar el servidor

    # Guardar
    if productos_encontrados:
        df = pd.DataFrame(productos_encontrados)
        df.to_csv(ARCHIVO_CSV, index=False, encoding='utf-8-sig')
        print("\n" + "="*50)
        print(f"✅ SCRAPING KAIQI FINALIZADO")
        print(f"   Total Productos: {len(df)}")
        print(f"   CSV Maestro: {ARCHIVO_CSV}")
        print(f"   Imágenes: {CARPETA_SALIDA}")
        print("="*50)
    else:
        print("\n❌ No se extrajeron datos.")

if __name__ == "__main__":
    minar_kaiqi()