import os
import re
import pandas as pd
from bs4 import BeautifulSoup
import unicodedata
import shutil
import requests

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\scrap"
ARCHIVO_HTML = "WWW.IMPORTADORA DFG.html"
BASE_URL = "https://importadoradfg.com"

# Salidas
CARPETA_SALIDA = os.path.join(BASE_DIR, "ACTIVOS_CLIENTE_DFG_LOCAL")
ARCHIVO_CSV = os.path.join(BASE_DIR, "Inventario_Cliente_DFG_Local.csv")

ruta_html = os.path.join(BASE_DIR, ARCHIVO_HTML)

if not os.path.exists(CARPETA_SALIDA):
    os.makedirs(CARPETA_SALIDA)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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
        
        # Reconstruir URL absoluta si es relativa
        if not url.startswith('http'):
            if url.startswith('//'):
                url = "https:" + url
            elif url.startswith('/'):
                url = BASE_URL + url
            else:
                # Si es una ruta local (file:///), no podemos descargarla a menos que tengas la carpeta _files
                return False
            
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

# ================= MOTOR DE MINERÍA LOCAL =================
def procesar_dfg_local():
    print(f"--- MINERÍA LOCAL DFG: {ARCHIVO_HTML} ---")
    
    if not os.path.exists(ruta_html):
        print("❌ Archivo HTML no encontrado.")
        return

    with open(ruta_html, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f, "html.parser")

    # Selectores DFG (WooCommerce estándar o Divi)
    # Intentamos varios patrones comunes
    items = soup.select('li.product')
    if not items: items = soup.select('div.product-item')
    if not items: items = soup.select('.product') # Genérico
    
    # Filtrar contenedores padres para evitar duplicados
    # (A veces .product está dentro de otro .product-wrapper)
    items_reales = [i for i in items if i.find('h2') or i.find('h3')]
    
    print(f"   -> {len(items_reales)} productos detectados en el HTML.")
    
    productos_encontrados = []
    count_ok = 0
    
    for item in items_reales:
        try:
            # Título
            title_tag = item.find(class_='woocommerce-loop-product__title')
            if not title_tag: 
                title_tag = item.find(re.compile('h[1-6]'), class_=re.compile('title'))
            
            if not title_tag: continue
            titulo = limpiar_texto(title_tag.get_text())
            
            # Link
            link_tag = item.find('a', href=True)
            prod_url = link_tag['href'] if link_tag else ""
            
            # Imagen
            img_tag = item.find('img')
            img_src = ""
            if img_tag:
                # Buscar la URL de alta calidad en data attributes
                img_src = img_tag.get('data-large_image') or \
                          img_tag.get('data-src') or \
                          img_tag.get('src')
                          
                if img_src and '?' in img_src: 
                    img_src = img_src.split('?')[0]

            # SKU (Si está visible)
            sku = ""
            # Intento: Buscar texto "SKU: 123"
            texto_item = item.get_text(" ", strip=True)
            match_sku = re.search(r'(SKU|REF)[:\.\s]*([A-Z0-9-]{4,12})', texto_item, re.IGNORECASE)
            if match_sku: sku = match_sku.group(2)

            if titulo and img_src:
                # Nombre SEO
                nombre_base = slugify(titulo)
                ext = ".jpg"
                if ".png" in img_src.lower(): ext = ".png"
                
                nuevo_nombre = f"{nombre_base}{ext}"
                if sku: nuevo_nombre = f"{nombre_base}-{slugify(sku)}{ext}"
                
                # Descargar (Si es URL web)
                exito = False
                if "http" in img_src:
                    exito = descargar_imagen(img_src, nuevo_nombre)
                
                # Guardar en lista
                # Si no descargó (porque es local), igual guardamos el registro para referencia
                productos_encontrados.append({
                    "Nombre_Producto": titulo,
                    "SKU": sku,
                    "Imagen_SEO": nuevo_nombre if exito else "",
                    "Imagen_URL_Origen": img_src,
                    "URL_Producto": prod_url,
                    "Fuente": "DFG_HTML_LOCAL"
                })
                
                if exito:
                    print(f"   + [OK] {titulo[:30]}...")
                    count_ok += 1
                
        except Exception as e:
            continue

    # Guardar CSV
    if productos_encontrados:
        df = pd.DataFrame(productos_encontrados)
        # Eliminar duplicados
        df = df.drop_duplicates(subset=['Nombre_Producto'])
        df.to_csv(ARCHIVO_CSV, index=False, encoding='utf-8-sig')
        
        print("\n" + "="*50)
        print(f"✅ MINERÍA LOCAL DFG FINALIZADA")
        print(f"   Total Productos Únicos: {len(df)}")
        print(f"   Imágenes Descargadas: {count_ok}")
        print(f"   CSV Maestro: {ARCHIVO_CSV}")
        print(f"   Carpeta: {CARPETA_SALIDA}")
        print("="*50)
    else:
        print("\n❌ No se encontraron productos legibles en el HTML.")

if __name__ == "__main__":
    procesar_dfg_local()