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
CARPETA_SALIDA = os.path.join(BASE_DIR, "ACTIVOS_KAIQI_PROFUNDO")
ARCHIVO_CSV = os.path.join(BASE_DIR, "Inventario_Kaiqi_Profundo_SKU.csv")

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

def get_soup(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return BeautifulSoup(r.text, 'html.parser')
    except Exception as e:
        print(f"   ❌ Error conexión: {e}")
    return None

def obtener_sku_profundo(url_producto):
    """Entra a la página individual para sacar el SKU."""
    if not url_producto: return ""
    
    try:
        # Pausa pequeña para no tumbar el servidor
        time.sleep(0.5) 
        soup = get_soup(url_producto)
        if not soup: return ""
        
        # 1. Buscar clase SKU estándar
        sku_tag = soup.find(class_='sku')
        if sku_tag:
            return limpiar_texto(sku_tag.get_text())
            
        # 2. Buscar en metadatos JSON (común en WooCommerce)
        # A veces está en <script type="application/ld+json">
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            if '"sku":' in script.text:
                match = re.search(r'"sku":\s*"([^"]+)"', script.text)
                if match: return match.group(1)
                
        # 3. Buscar en tabla de información adicional
        tabla = soup.find('table', class_='woocommerce-product-attributes')
        if tabla:
            fila_sku = tabla.find('td', class_='woocommerce-product-attributes-item__value')
            if fila_sku: return limpiar_texto(fila_sku.get_text())
            
    except Exception as e:
        print(f"   ⚠️ Error extrayendo SKU profundo: {e}")
        
    return ""

# ================= MOTOR DE SCRAPING PROFUNDO =================
def minar_kaiqi_profundo():
    print(f"--- INICIANDO SCRAPING PROFUNDO (MODO LENTO PERO SEGURO) ---")
    productos_totales = []
    hashes_vistos = set()
    
    # Rango de páginas (ajustable)
    for page in range(1, 8):
        if page == 1:
            url_actual = START_URL
        else:
            url_actual = f"{START_URL}?product-page={page}" # Formato correcto detectado
            
        print(f"\n📄 Escaneando Listado Página {page} ({url_actual})...")
        
        soup = get_soup(url_actual)
        if not soup: continue
        
        items = soup.select('li.product')
        if not items: items = soup.select('div.product')
        
        if not items:
            print("   🏁 No se encontraron más productos.")
            break
            
        # Detector de bucle simple
        primer_titulo = items[0].get_text(strip=True)[:50]
        if primer_titulo in hashes_vistos:
            print("   ⚠️ ALERTA: Página repetida. Fin del catálogo.")
            break
        hashes_vistos.add(primer_titulo)
        
        print(f"   -> {len(items)} productos en lista. Entrando a extraer SKUs...")
        
        for item in items:
            try:
                # Título y Link
                title_tag = item.find(class_='woocommerce-loop-product__title')
                if not title_tag: continue
                titulo = limpiar_texto(title_tag.get_text())
                
                link_tag = item.find('a', href=True)
                prod_url = link_tag['href'] if link_tag else ""
                
                # Imagen (Desde el listado está bien, suele ser la misma)
                img_tag = item.find('img')
                img_src = ""
                if img_tag:
                    img_src = img_tag.get('data-large_image') or img_tag.get('src')
                    if img_src and '?' in img_src: img_src = img_src.split('?')[0]

                # --- MAGIA: EXTRACCIÓN PROFUNDA ---
                sku = "PENDIENTE"
                if prod_url:
                    print(f"      > Entrando a: {titulo[:30]}...", end="\r")
                    sku = obtener_sku_profundo(prod_url)
                    print(f"      ✅ SKU: {sku if sku else 'NO ENCONTRADO'} | {titulo[:30]}...")
                
                if titulo and img_src:
                    nombre_base = slugify(titulo)
                    ext = ".jpg"
                    nuevo_nombre = f"{nombre_base}{ext}"
                    if sku and sku != "PENDIENTE": 
                        nuevo_nombre = f"{nombre_base}-{slugify(sku)}{ext}"
                    
                    # Descargar Imagen
                    exito_img = descargar_imagen(img_src, nuevo_nombre)
                    
                    productos_totales.append({
                        "Nombre_Producto": titulo,
                        "SKU": sku,
                        "URL_Producto": prod_url,
                        "Imagen_SEO": nuevo_nombre,
                        "Imagen_URL_Origen": img_src,
                        "Fuente": "KAIQI_PROFUNDO"
                    })
                    
            except Exception as e:
                print(f"   Error en item: {e}")
                continue
        
        # Guardado parcial por seguridad (si se corta la luz, no pierdes todo)
        pd.DataFrame(productos_totales).to_csv(ARCHIVO_CSV, index=False, encoding='utf-8-sig')

    print("\n" + "="*50)
    print(f"✅ PROCESO PROFUNDO COMPLETADO")
    print(f"   Total Productos: {len(productos_totales)}")
    print(f"   CSV Maestro: {ARCHIVO_CSV}")
    print("="*50)

if __name__ == "__main__":
    minar_kaiqi_profundo()