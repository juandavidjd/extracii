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

# LISTA MAESTRA DE CATEGORÍAS (Extraída de tu HTML)
URLS_SEMILLA = [
    "https://dunasas.com/productos/categorias/iluminacion-bombillos-incandescentes/12",
    "https://dunasas.com/productos/categorias/iluminacion-led-bombillos/211",
    "https://dunasas.com/productos/categorias/iluminacion-led-accesorios/215",
    "https://dunasas.com/productos/categorias/partes-electricas-y-electronicas/19",
    "https://dunasas.com/productos/categorias/rodamientos/98",
    "https://dunasas.com/productos/categorias/guayas/302",
    "https://dunasas.com/productos/categorias/maniguetas-y-porta-maniguetas/309",
    "https://dunasas.com/productos/categorias/accesorios-y-partes/314",
    "https://dunasas.com/productos/categorias/clutch/323",
    "https://dunasas.com/productos/categorias/frenos/327",
    "https://dunasas.com/productos/categorias/iluminacion-incandescente-accesorios/336",
    "https://dunasas.com/productos/categorias/relacion/339",
    "https://dunasas.com/productos/categorias/aceleracion-y-velocimetro/95",
    "https://dunasas.com/productos/categorias/motor/6"
]

# Salidas
CARPETA_SALIDA = os.path.join(BASE_DIR, "ACTIVOS_CLIENTE_DUNA_TOTAL")
ARCHIVO_CSV = os.path.join(BASE_DIR, "Inventario_Cliente_Duna_Total.csv")

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

def extraer_id_de_url(url):
    match = re.search(r'/(\d+)$', url)
    return match.group(1) if match else ""

def get_soup(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return BeautifulSoup(r.text, 'html.parser')
    except Exception as e:
        print(f"   ❌ Error conexión: {e}")
    return None

# ================= MOTOR DE MINERÍA MASIVA =================
def minar_duna_total():
    print(f"--- INICIANDO BARRIDO TOTAL DUNA (14 CATEGORÍAS) ---")
    
    productos_encontrados = []
    urls_visitadas = set()
    cola_urls = URLS_SEMILLA.copy() # Empezamos con las categorías
    
    count_categorias = 0
    count_productos = 0
    
    while cola_urls:
        url_actual = cola_urls.pop(0)
        
        if url_actual in urls_visitadas: continue
        urls_visitadas.add(url_actual)
        
        print(f"\n📄 Escaneando: {url_actual.split('/')[-2]}") # Mostrar solo nombre categoria
        
        soup = get_soup(url_actual)
        if not soup: continue
        
        # 1. Buscar Elementos (Pueden ser Subcategorías o Productos)
        # Duna usa la misma clase 'ctn-item' para ambos
        items = soup.select('div.ctn-item')
        
        for item in items:
            try:
                # Extraer datos básicos
                link_tag = item.find('a', href=True)
                url_destino = link_tag['href'] if link_tag else ""
                if url_destino and not url_destino.startswith('http'):
                    url_destino = BASE_URL + url_destino
                
                title_tag = item.find('h3', class_='title-item')
                titulo = limpiar_texto(title_tag.get_text()) if title_tag else ""
                
                img_tag = item.find('img')
                img_src = img_tag.get('src') if img_tag else ""

                # CLASIFICACIÓN: ¿Es Categoría o Producto?
                # En Duna, las categorías suelen tener "/categorias/" en la URL.
                # Los productos suelen tener "/productos/nombre/ID".
                
                if "/categorias/" in url_destino:
                    # ES SUBCATEGORÍA -> Añadir a la cola
                    if url_destino not in urls_visitadas and url_destino not in cola_urls:
                        cola_urls.append(url_destino)
                        count_categorias += 1
                        # print(f"   📂 Subcategoría detectada: {titulo}")
                
                elif "/productos/" in url_destino:
                    # ES PRODUCTO -> Procesar
                    sku_id = extraer_id_de_url(url_destino)
                    if not sku_id: sku_id = f"UNK-{len(productos_encontrados)}"
                    
                    # Nombre SEO
                    nombre_base = slugify(titulo)
                    ext = ".jpg"
                    nuevo_nombre = f"{nombre_base}-{sku_id}{ext}"
                    
                    # Descargar imagen (quitando thumb si es posible, o bajando lo que hay)
                    # Duna usa phpThumb, a veces quitar parametros rompe. Bajamos tal cual.
                    if "phpThumb" in img_src and not img_src.startswith("http"):
                         img_src = BASE_URL + "/" + img_src.lstrip("/")
                    
                    exito = descargar_imagen(img_src, nuevo_nombre)
                    
                    if exito:
                        productos_encontrados.append({
                            "Nombre_Producto": titulo,
                            "SKU_Duna": sku_id,
                            "Categoria_Padre": url_actual.split('/')[-2],
                            "Imagen_SEO": nuevo_nombre,
                            "Imagen_URL_Origen": img_src,
                            "URL_Producto": url_destino,
                            "Fuente": "DUNA_BARRIDO_TOTAL"
                        })
                        print(f"   + {titulo[:30]}...")
                        count_productos += 1
                        
            except: continue
            
        # time.sleep(0.5) # Cortesía con el servidor

    # Guardar CSV
    if productos_encontrados:
        df = pd.DataFrame(productos_encontrados)
        # Eliminar duplicados por ID
        df = df.drop_duplicates(subset=['SKU_Duna'])
        df.to_csv(ARCHIVO_CSV, index=False, encoding='utf-8-sig')
        
        print("\n" + "="*50)
        print(f"✅ MISIÓN DUNA COMPLETADA")
        print(f"   Subcategorías exploradas: {count_categorias}")
        print(f"   Productos extraídos: {len(df)}")
        print(f"   CSV Maestro: {ARCHIVO_CSV}")
        print(f"   Carpeta: {CARPETA_SALIDA}")
        print("="*50)
    else:
        print("\n❌ No se extrajeron datos.")

if __name__ == "__main__":
    minar_duna_total()