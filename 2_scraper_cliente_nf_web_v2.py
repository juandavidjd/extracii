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
START_URL = "https://armvalle.com/?post_type=product"

# Salidas
CARPETA_SALIDA = os.path.join(BASE_DIR, "ACTIVOS_CLIENTE_NF_WEB")
ARCHIVO_CSV = os.path.join(BASE_DIR, "Inventario_Cliente_NF_Web.csv")

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
        # Corregir URL relativa
        if not url.startswith('http'):
            if url.startswith('//'):
                url = "https:" + url
            elif url.startswith('/'):
                url = BASE_URL + url
            else:
                url = f"{BASE_URL}/{url}"
            
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

def minar_armvalle():
    print(f"--- INICIANDO SCRAPING: ARMVALLE ({START_URL}) ---")
    productos_encontrados = []
    
    # Detectar paginación
    # En WordPress suele ser /page/2/ o ?paged=2
    page = 1
    
    while True:
        url_actual = f"{START_URL}&paged={page}" if page > 1 else START_URL
        print(f"\n📄 Escaneando Página {page}...")
        
        soup = get_soup(url_actual)
        if not soup: 
            print("   🏁 Fin (Error o fin de páginas).")
            break
        
        # Selector basado en tu archivo Shop - CarKIT.html (Clases estándar de Elementor/WooCommerce)
        # Buscamos los 'li' o 'div' que tengan la clase 'product'
        items = soup.select('li.product')
        if not items:
            items = soup.select('div.product') # Fallback
            
        if not items:
            print("   🏁 No se encontraron más productos. Terminando.")
            break
            
        print(f"   -> Encontrados {len(items)} productos.")
        nuevos_en_pagina = 0
        
        for item in items:
            try:
                # A. Título
                title_tag = item.find('h2', class_='woocommerce-loop-product__title')
                if not title_tag: continue
                titulo = limpiar_texto(title_tag.get_text())
                
                # B. Enlace (para profundización futura)
                link_tag = item.find('a', class_='woocommerce-LoopProduct-link')
                prod_url = link_tag['href'] if link_tag else ""
                
                # C. Imagen
                img_tag = item.find('img')
                img_src = ""
                if img_tag:
                    # Prioridad: data-src > src
                    img_src = img_tag.get('data-src') or img_tag.get('src')
                    # Limpiar query params (?resize=...) para obtener full size
                    if img_src and '?' in img_src:
                        img_src = img_src.split('?')[0]

                # D. SKU (A veces oculto en lista, a veces visible)
                # En tu HTML no se ve explícito en la lista, intentaremos extraerlo del título si tiene formato COD: XXX
                sku = ""
                # Intento 1: Buscar en clases CSS (post-1234)
                classes = item.get('class', [])
                post_id = next((c for c in classes if c.startswith('post-')), None)
                if post_id: sku = post_id # ID interno como fallback de SKU
                
                # Intento 2: Regex en título
                match_sku = re.search(r'\b([A-Z0-9-]{5,10})\b', titulo)
                if match_sku and match_sku.group(1).isupper():
                    # Un heurístico simple
                    pass 

                # E. Precio (Opcional, útil para validación)
                price_tag = item.find('span', class_='price')
                precio = limpiar_texto(price_tag.get_text()) if price_tag else "0"

                if titulo and img_src:
                    # Crear nombre de archivo SEO
                    nombre_base = slugify(titulo)
                    ext = ".jpg"
                    # Usamos el titulo como ID único visual
                    nuevo_nombre = f"{nombre_base}{ext}"
                    
                    # Descargar
                    exito = descargar_imagen(img_src, nuevo_nombre)
                    
                    if exito:
                        productos_encontrados.append({
                            "Nombre_Producto": titulo,
                            "SKU_Detectado": sku,
                            "Precio": precio,
                            "Imagen_SEO": nuevo_nombre,
                            "Imagen_URL_Origen": img_src,
                            "URL_Producto": prod_url,
                            "Fuente": "ARMVALLE_WEB"
                        })
                        nuevos_en_pagina += 1
                        print(f"   + {titulo[:40]}...")
                    
            except Exception as e:
                continue
        
        if nuevos_en_pagina == 0:
            print("   ⚠️ Página escaneada pero sin productos nuevos válidos.")
            break
            
        page += 1
        time.sleep(1)

    # Guardar CSV
    if productos_encontrados:
        df = pd.DataFrame(productos_encontrados)
        df.to_csv(ARCHIVO_CSV, index=False, encoding='utf-8-sig')
        print("\n" + "="*50)
        print(f"✅ SCRAPING ARMVALLE FINALIZADO")
        print(f"   Total Productos: {len(df)}")
        print(f"   CSV Maestro: {ARCHIVO_CSV}")
        print(f"   Imágenes: {CARPETA_SALIDA}")
        print("="*50)
    else:
        print("\n❌ No se extrajeron datos.")

if __name__ == "__main__":
    minar_armvalle()