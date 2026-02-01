import os
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
import unicodedata
import time

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\scrap"
BASE_URL = "https://dunasas.com"
# URLs semilla (puedes agregar más categorías aquí)
START_URLS = [
    "https://dunasas.com/productos/categorias/ah11-bombillos-direccionalstop/204",
    "https://dunasas.com/productos/categorias/iluminacion-bombillos-incandescentes/12"
]

# Salidas
CARPETA_SALIDA = os.path.join(BASE_DIR, "ACTIVOS_CLIENTE_DUNA_WEB")
ARCHIVO_CSV = os.path.join(BASE_DIR, "Inventario_Cliente_Duna_Web.csv")

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
            if url.startswith('/'): url = BASE_URL + url
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

def reconstruir_url_imagen(src_thumb):
    """
    Intenta obtener la imagen full desde el thumbnail.
    Ej: src=".../phpThumb_generated_thumbnailpng(4)" -> Buscar enlace padre o patrón.
    """
    # En Duna, a veces el enlace <a> que envuelve la imagen lleva al producto,
    # y dentro del producto está la imagen grande.
    # O la imagen tiene un data-src.
    return src_thumb

# ================= MOTOR DE SCRAPING =================
def get_soup(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return BeautifulSoup(r.text, 'html.parser')
    except Exception as e:
        print(f"   ❌ Error conexión: {e}")
    return None

def minar_duna():
    print(f"--- INICIANDO SCRAPING: DUNA SAS ---")
    productos_encontrados = []
    
    # Cola de URLs para visitar (empezamos con las categorías)
    urls_a_visitar = START_URLS.copy()
    urls_visitadas = set()
    
    while urls_a_visitar:
        url_actual = urls_a_visitar.pop(0)
        if url_actual in urls_visitadas: continue
        urls_visitadas.add(url_actual)
        
        print(f"\n📄 Escaneando: {url_actual}")
        soup = get_soup(url_actual)
        if not soup: continue
        
        # 1. Buscar Productos en la lista
        # Estructura detectada: div.ctn-item > div.item
        items = soup.select('div.ctn-item')
        
        print(f"   -> {len(items)} elementos encontrados.")
        
        for item in items:
            try:
                # Título
                title_tag = item.find('h3', class_='title-item')
                if not title_tag: continue
                titulo = limpiar_texto(title_tag.get_text())
                
                # Enlace al detalle
                link_tag = item.find('a', href=True)
                prod_url = link_tag['href'] if link_tag else ""
                if prod_url and not prod_url.startswith('http'):
                    prod_url = BASE_URL + prod_url
                
                # Imagen (Miniatura)
                img_tag = item.find('img')
                img_src = img_tag.get('src') if img_tag else ""
                
                # Si es una categoría (no un producto final), la añadimos a la cola
                # Duna mezcla productos y subcategorías.
                # Pista: Si el enlace tiene "categorias", es categoría. Si no, es producto?
                # Vamos a asumir que todo lo que tiene precio o código es producto.
                # Si entramos al detalle, podemos sacar la foto grande.
                
                if titulo and prod_url:
                    # ESTRATEGIA DE PROFUNDIZACIÓN
                    # Entramos al producto para sacar la foto HD y el Código
                    # print(f"      > Entrando a {titulo[:30]}...", end="\r")
                    
                    # (Opcional: Si quieres velocidad, usa la miniatura. Si quieres calidad, descomenta abajo)
                    # soup_prod = get_soup(prod_url)
                    # if soup_prod:
                    #     # Buscar imagen grande
                    #     img_full = soup_prod.find('img', class_='img-responsive') # Ajustar selector
                    #     if img_full: img_src = img_full.get('src')
                    
                    # Nombre SEO
                    nombre_base = slugify(titulo)
                    nuevo_nombre = f"{nombre_base}.jpg"
                    
                    # Descargar
                    # Nota: Si la URL es relativa phpThumb, hay que arreglarla
                    if img_src and not img_src.startswith('http'):
                        img_src = BASE_URL + '/' + img_src.lstrip('/')
                        
                    exito = descargar_imagen(img_src, nuevo_nombre)
                    
                    if exito:
                        productos_encontrados.append({
                            "Nombre_Producto": titulo,
                            "SKU": "", # Duna suele tener SKU adentro, habría que entrar
                            "Imagen_SEO": nuevo_nombre,
                            "Imagen_URL_Origen": img_src,
                            "URL_Producto": prod_url,
                            "Fuente": "DUNA_WEB"
                        })
                        print(f"   + {titulo[:40]}...")
                        
                    # Si detectamos que es una subcategoría (enlace contiene 'categorias')
                    if 'categorias' in prod_url and prod_url not in urls_visitadas:
                        urls_a_visitar.append(prod_url)
                        
            except Exception as e:
                continue

    # Guardar
    if productos_encontrados:
        df = pd.DataFrame(productos_encontrados)
        df.to_csv(ARCHIVO_CSV, index=False, encoding='utf-8-sig')
        print("\n" + "="*50)
        print(f"✅ SCRAPING DUNA FINALIZADO")
        print(f"   Total Activos: {len(df)}")
        print(f"   CSV: {ARCHIVO_CSV}")
        print(f"   Imágenes: {CARPETA_SALIDA}")
        print("="*50)
    else:
        print("\n❌ No se extrajeron datos.")

if __name__ == "__main__":
    minar_duna()