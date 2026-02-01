import os
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
import unicodedata

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\scrap"
ARCHIVOS_HTML = [
    "Tienda _ Kaiqi Parts - Partes y Accesorios para Motocargueros y Motos en Villavicencio1.html",
    "Tienda _ Kaiqi Parts - Partes y Accesorios para Motocargueros y Motos en Villavicencio2.html",
    "Tienda _ Kaiqi Parts - Partes y Accesorios para Motocargueros y Motos en Villavicencio3.html",
    "Tienda _ Kaiqi Parts - Partes y Accesorios para Motocargueros y Motos en Villavicencio4.html",
    "Tienda _ Kaiqi Parts - Partes y Accesorios para Motocargueros y Motos en Villavicencio5.html",
    "Tienda _ Kaiqi Parts - Partes y Accesorios para Motocargueros y Motos en Villavicencio6.html",
    "Tienda _ Kaiqi Parts - Partes y Accesorios para Motocargueros y Motos en Villavicencio7.html"
]

CARPETA_SALIDA = os.path.join(BASE_DIR, "ACTIVOS_KAIQI_WEB_OFICIAL_LOCAL")
ARCHIVO_CSV = os.path.join(BASE_DIR, "Inventario_Kaiqi_Web_Oficial_Local.csv")

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
        # Limpiar URL (a veces viene con ../)
        if not url.startswith('http'):
            # Si es relativa local, no podemos bajarla a menos que tengamos la carpeta _files
            # Asumiremos que el HTML tiene URLs absolutas o que podemos reconstruirlas
            if url.startswith('//'):
                url = "https:" + url
            elif url.startswith('/'):
                url = "https://kaiqiparts.com" + url
            else:
                # Intento de adivinanza si es relativa
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
def procesar_htmls_locales():
    print(f"--- MINERÍA LOCAL DE HTMLs KAIQI ---")
    productos_totales = []
    
    for archivo in ARCHIVOS_HTML:
        ruta_completa = os.path.join(BASE_DIR, archivo)
        if not os.path.exists(ruta_completa):
            print(f"⚠️ Archivo no encontrado: {archivo}")
            continue
            
        print(f"\n📄 Procesando: {archivo}")
        
        with open(ruta_completa, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f, "html.parser")
            
        # Selectores
        items = soup.select('li.product')
        if not items: items = soup.select('div.product')
        
        print(f"   -> {len(items)} items detectados.")
        
        for item in items:
            try:
                # Título
                title_tag = item.find(class_='woocommerce-loop-product__title')
                if not title_tag: continue
                titulo = limpiar_texto(title_tag.get_text())
                
                # Imagen
                img_tag = item.find('img')
                img_src = ""
                if img_tag:
                    # En HTML guardado, a veces el src apunta a una carpeta local "_files"
                    # Si es así, no podemos descargarla de internet, pero podemos copiarla si existe la carpeta.
                    # Pero KAIQI usa Lazy Load, así que buscamos el data-original o similar.
                    
                    img_src = img_tag.get('data-large_image') or \
                              img_tag.get('data-src') or \
                              img_tag.get('src')
                              
                    # Si es una URL web, la bajamos. Si es local (file:///), intentamos copiar si tuviéramos la carpeta.
                    # Asumiré que queremos bajar la versión web de alta calidad si el HTML tiene el link.
                
                # SKU
                sku = ""
                sku_tag = item.find(class_='sku')
                if sku_tag: sku = limpiar_texto(sku_tag.get_text())
                
                # Enlace
                link_tag = item.find('a', href=True)
                prod_url = link_tag['href'] if link_tag else ""
                
                if not sku:
                    match_cod = re.search(r'(COD|REF)[:\.\s]*([A-Z0-9-]{4,10})', titulo, re.IGNORECASE)
                    if match_cod: sku = match_cod.group(2)

                if titulo and img_src:
                    # Nombre SEO
                    nombre_base = slugify(titulo)
                    ext = ".jpg"
                    # Limpiar query strings de la imagen
                    if '?' in img_src: img_src_clean = img_src.split('?')[0]
                    else: img_src_clean = img_src
                    
                    if img_src_clean.lower().endswith('.png'): ext = ".png"
                    
                    nuevo_nombre = f"{nombre_base}{ext}"
                    if sku: nuevo_nombre = f"{nombre_base}-{slugify(sku)}{ext}"
                    
                    # Intentar descargar solo si es URL web
                    exito = False
                    if "http" in img_src:
                        exito = descargar_imagen(img_src, nuevo_nombre)
                    
                    productos_totales.append({
                        "Nombre_Producto": titulo,
                        "SKU": sku,
                        "Imagen_SEO": nuevo_nombre if exito else "",
                        "Imagen_URL_Original": img_src,
                        "Fuente": "KAIQI_HTML_LOCAL"
                    })
                    # print(f"   + {titulo[:30]}...")

            except Exception as e:
                continue

    # Guardar
    if productos_totales:
        df = pd.DataFrame(productos_totales).drop_duplicates(subset=['Nombre_Producto'])
        df.to_csv(ARCHIVO_CSV, index=False, encoding='utf-8-sig')
        print("\n" + "="*50)
        print(f"✅ PROCESO LOCAL FINALIZADO")
        print(f"   Total Productos Únicos: {len(df)}")
        print(f"   CSV Maestro: {ARCHIVO_CSV}")
        print(f"   Imágenes Descargadas: {CARPETA_SALIDA}")
        print("="*50)
    else:
        print("\n❌ No se extrajeron datos.")

if __name__ == "__main__":
    procesar_htmls_locales()