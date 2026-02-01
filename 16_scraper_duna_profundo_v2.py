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

# LISTA DE CATEGORÍAS (La misma que antes)
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
CARPETA_SALIDA = os.path.join(BASE_DIR, "ACTIVOS_CLIENTE_DUNA_TOTAL_V2")
ARCHIVO_CSV = os.path.join(BASE_DIR, "Inventario_Cliente_Duna_Total_V2.csv")

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

def get_soup(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return BeautifulSoup(r.text, 'html.parser')
    except Exception as e:
        print(f"   ❌ Error conexión: {e}")
    return None

# ================= MOTOR DE MINERÍA PROFUNDA =================
def extraer_ref_profunda(url_producto):
    """Entra al producto y busca REF: XXXX"""
    ref_encontrada = ""
    soup = get_soup(url_producto)
    if not soup: return ""
    
    # Buscar en todo el texto visible
    texto_completo = soup.get_text(" ", strip=True)
    
    # Regex para buscar REF: o REFERENCIA: seguido de código
    match = re.search(r'(?:REF|REFERENCIA)[:\.\s]+([A-Z0-9\.-]+)', texto_completo, re.IGNORECASE)
    if match:
        ref_encontrada = match.group(1)
        
    # Limpiar la referencia (quitar puntos finales)
    return ref_encontrada.strip('.')

def minar_duna_profundo_v2():
    print(f"--- INICIANDO MINERÍA PROFUNDA DUNA V2 (BUSCANDO REF) ---")
    
    productos_encontrados = []
    urls_visitadas = set()
    refs_vistas = set() # Para evitar duplicados reales
    cola_urls = URLS_SEMILLA.copy()
    
    while cola_urls:
        url_actual = cola_urls.pop(0)
        if url_actual in urls_visitadas: continue
        urls_visitadas.add(url_actual)
        
        print(f"\n📄 Escaneando Categoría: {url_actual.split('/')[-2]}")
        soup = get_soup(url_actual)
        if not soup: continue
        
        items = soup.select('div.ctn-item')
        
        for item in items:
            try:
                # Link
                link_tag = item.find('a', href=True)
                url_destino = link_tag['href'] if link_tag else ""
                if url_destino and not url_destino.startswith('http'):
                    url_destino = BASE_URL + url_destino
                
                # Título Base
                title_tag = item.find('h3', class_='title-item')
                titulo_base = limpiar_texto(title_tag.get_text()) if title_tag else ""
                
                # Imagen Base
                img_tag = item.find('img')
                img_src = img_tag.get('src') if img_tag else ""
                
                # CLASIFICACIÓN
                if "/categorias/" in url_destino:
                    if url_destino not in urls_visitadas and url_destino not in cola_urls:
                        cola_urls.append(url_destino)
                
                elif "/productos/" in url_destino and titulo_base:
                    # ES PRODUCTO -> PROFUNDIZAR
                    # print(f"   > Analizando: {titulo_base[:30]}...", end="\r")
                    
                    # Entrar para sacar la REF
                    ref_real = extraer_ref_profunda(url_destino)
                    
                    # Si no encuentra REF, usa el ID de la URL como fallback
                    if not ref_real:
                        match_id = re.search(r'/(\d+)$', url_destino)
                        ref_real = match_id.group(1) if match_id else "UNK"
                    
                    # Chequear duplicados por REF
                    if ref_real in refs_vistas:
                        continue
                    refs_vistas.add(ref_real)

                    # Nombre Final Único
                    nombre_completo = f"{titulo_base} {ref_real}"
                    
                    # Imagen
                    # Intentar limpiar phpThumb para obtener full size
                    if "phpThumb" in img_src and not img_src.startswith("http"):
                         img_src = BASE_URL + "/" + img_src.lstrip("/")
                    
                    # Nombre Archivo SEO
                    nombre_archivo = f"{slugify(nombre_completo)}.jpg"
                    
                    exito = descargar_imagen(img_src, nombre_archivo)
                    
                    if exito:
                        productos_encontrados.append({
                            "Nombre_Producto": titulo_base,
                            "Referencia_Real": ref_real,
                            "Nombre_Completo": nombre_completo,
                            "Imagen_SEO": nombre_archivo,
                            "URL_Producto": url_destino,
                            "Fuente": "DUNA_PROFUNDO_V2"
                        })
                        print(f"   + {titulo_base} [REF: {ref_real}]")
                        
            except: continue

    # Guardar
    if productos_encontrados:
        df = pd.DataFrame(productos_encontrados)
        df.to_csv(ARCHIVO_CSV, index=False, encoding='utf-8-sig')
        print("\n" + "="*50)
        print(f"✅ PROCESO DUNA V2 COMPLETADO")
        print(f"   Productos Únicos: {len(df)}")
        print(f"   CSV: {ARCHIVO_CSV}")
        print(f"   Carpeta: {CARPETA_SALIDA}")
        print("="*50)
    else:
        print("\n❌ No se extrajeron datos.")

if __name__ == "__main__":
    minar_duna_profundo_v2()