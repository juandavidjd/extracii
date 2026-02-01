import os
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
import unicodedata
import re
import json

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\scrap"
BASE_URL = "https://importadoradfg.com"
# NOTA: Verifica si la tienda está en /tienda/, /productos/ o /catalogo/
# Si no carga, cambia esta URL por la correcta del navegador.
START_URL = "https://importadoradfg.com/tienda/" 

# Salidas
CARPETA_SALIDA = os.path.join(BASE_DIR, "ACTIVOS_DFG_WEB")
ARCHIVO_CSV = os.path.join(BASE_DIR, "Inventario_DFG_Profundo.csv")

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

def get_soup(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return BeautifulSoup(r.text, 'html.parser')
    except Exception as e:
        print(f"   ❌ Error conexión: {e}")
    return None

# ================= EXTRACTOR PROFUNDO =================
def extraer_data_producto(url_producto):
    """Entra a la ficha técnica y saca todo lo que pueda."""
    data = {
        "SKU": "",
        "Descripcion": "",
        "Categoria": "",
        "Imagen_Full": ""
    }
    
    soup = get_soup(url_producto)
    if not soup: return data
    
    try:
        # 1. SKU (La joya de la corona)
        # Intento A: Clase estándar
        sku_tag = soup.find(class_='sku')
        if sku_tag: data["SKU"] = limpiar_texto(sku_tag.get_text())
        
        # Intento B: Tabla de información adicional
        if not data["SKU"]:
            # Buscar filas que digan "Código" o "Referencia"
            for row in soup.find_all('tr'):
                th = row.find('th')
                td = row.find('td')
                if th and td:
                    header = th.get_text().lower()
                    if 'código' in header or 'sku' in header or 'referencia' in header:
                        data["SKU"] = limpiar_texto(td.get_text())
                        break
        
        # Intento C: Metadatos JSON-LD (Común en e-commerce modernos)
        if not data["SKU"]:
            scripts = soup.find_all('script', type='application/ld+json')
            for s in scripts:
                try:
                    js = json.loads(s.string)
                    if '@graph' in js:
                        for item in js['@graph']:
                            if item.get('@type') == 'Product':
                                data["SKU"] = item.get('sku', '')
                                break
                    elif js.get('@type') == 'Product':
                        data["SKU"] = js.get('sku', '')
                except: pass

        # 2. Descripción Larga (Para el fitment rico)
        desc_div = soup.find('div', id='tab-description') or \
                   soup.find(class_='woocommerce-product-details__short-description')
        if desc_div:
            data["Descripcion"] = limpiar_texto(desc_div.get_text())

        # 3. Categoría (Breadcrumbs)
        nav = soup.find('nav', class_='woocommerce-breadcrumb')
        if nav:
            data["Categoria"] = limpiar_texto(nav.get_text(" > "))

        # 4. Imagen Full (Zoom)
        # A veces la del listado es pequeña, aquí buscamos la original
        img_wrap = soup.find(class_='woocommerce-product-gallery__image')
        if img_wrap:
            a_tag = img_wrap.find('a')
            if a_tag: data["Imagen_Full"] = a_tag.get('href')
            
    except Exception as e:
        print(f"      ⚠️ Error parsing interno: {e}")
        
    return data

# ================= MOTOR PRINCIPAL =================
def minar_dfg_profundo():
    print(f"--- INICIANDO SCRAPING PROFUNDO: IMPORTADORA DFG ---")
    print(f"    Objetivo: {START_URL}")
    
    productos_totales = []
    page = 1
    
    while True:
        # Construir URL de paginación (Ajustar según sea necesario: /page/2/ o ?paged=2)
        url_actual = START_URL if page == 1 else f"{START_URL}page/{page}/"
        print(f"\n📄 Explorando Listado Página {page}...")
        
        soup = get_soup(url_actual)
        if not soup: 
            print("   🏁 Error de acceso o fin de paginación.")
            break
        
        # Buscar lista de productos
        items = soup.select('li.product')
        if not items: items = soup.select('div.product-item')
        
        if not items:
            print("   🏁 No se encontraron más productos.")
            break
            
        print(f"   -> Detectados {len(items)} productos. Iniciando inmersión...")
        
        nuevos = 0
        for item in items:
            try:
                # Datos superficiales
                title_tag = item.find(class_='woocommerce-loop-product__title')
                if not title_tag: title_tag = item.find('h2')
                
                if not title_tag: continue
                titulo = limpiar_texto(title_tag.get_text())
                
                link_tag = item.find('a', href=True)
                prod_url = link_tag['href'] if link_tag else ""
                
                # Imagen preliminar (por si falla la profunda)
                img_tag = item.find('img')
                img_src = img_tag.get('src') if img_tag else ""

                if prod_url:
                    print(f"      > Analizando: {titulo[:40]}...", end="\r")
                    
                    # --- INMERSIÓN ---
                    # time.sleep(0.5) # Pausa ética recomendada
                    data_profunda = extraer_data_producto(prod_url)
                    
                    sku = data_profunda["SKU"]
                    # Si encontramos una imagen mejor adentro, la usamos
                    if data_profunda["Imagen_Full"]:
                        img_src = data_profunda["Imagen_Full"]
                    
                    # Procesar
                    nombre_base = slugify(titulo)
                    ext = ".jpg"
                    nuevo_nombre = f"{nombre_base}{ext}"
                    if sku: nuevo_nombre = f"{nombre_base}-{slugify(sku)}{ext}"
                    
                    # Descargar
                    exito = descargar_imagen(img_src, nuevo_nombre)
                    
                    if exito:
                        productos_totales.append({
                            "Nombre_Producto": titulo,
                            "SKU": sku,
                            "Categoria": data_profunda["Categoria"],
                            "Descripcion_Larga": data_profunda["Descripcion"],
                            "Imagen_SEO": nuevo_nombre,
                            "Imagen_URL_Origen": img_src,
                            "URL_Producto": prod_url,
                            "Fuente": "DFG_PROFUNDO"
                        })
                        nuevos += 1
                        print(f"      ✅ {titulo[:30]}... [SKU: {sku}]")
                    
            except Exception as e:
                continue
        
        if nuevos == 0:
            print("   ⚠️ Página sin productos nuevos válidos.")
            break
            
        page += 1

    # Guardar
    if productos_totales:
        df = pd.DataFrame(productos_totales)
        df.to_csv(ARCHIVO_CSV, index=False, encoding='utf-8-sig')
        print("\n" + "="*50)
        print(f"✅ MISIÓN DFG COMPLETADA")
        print(f"   Total Activos: {len(df)}")
        print(f"   CSV Maestro: {ARCHIVO_CSV}")
        print(f"   Imágenes: {CARPETA_SALIDA}")
        print("="*50)
    else:
        print("\n❌ No se extrajeron datos.")

if __name__ == "__main__":
    minar_dfg_profundo()