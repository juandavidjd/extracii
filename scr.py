import os
import glob
import shutil
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import random
from urllib.parse import unquote

# ==========================================
# CONFIGURACIÓN
# ==========================================
BASE_DIR = r"C:\sqk\html_pages"
OUTPUT_CSV = os.path.join(BASE_DIR, "catalogo_shopify_completo.csv")
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def obtener_sku_online(url):
    """
    Realiza scraping a la URL del producto para obtener el SKU real.
    Retorna el SKU limpio o None si falla.
    """
    try:
        # Pequeña pausa para no saturar el servidor
        time.sleep(random.uniform(0.5, 1.5))
        
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # Selector específico solicitado: <span class="sku_wrapper">SKU: <span class="sku">X</span></span>
            sku_wrapper = soup.find('span', class_='sku_wrapper')
            if sku_wrapper:
                sku_span = sku_wrapper.find('span', class_='sku')
                if sku_span:
                    sku = sku_span.get_text(strip=True)
                    print(f"   [OK] SKU encontrado: {sku}")
                    return sku
        
        print(f"   [WARN] SKU no encontrado en {url} (Status: {response.status_code})")
        return None
    except Exception as e:
        print(f"   [ERR] Error conectando a {url}: {str(e)}")
        return None

def procesar_imagenes(ruta_local_imagen, sku, carpeta_files):
    """
    Renombra la imagen física basándose en el SKU.
    Retorna el nuevo nombre de archivo para el CSV.
    """
    if not sku:
        return os.path.basename(ruta_local_imagen)

    nombre_archivo_original = os.path.basename(unquote(ruta_local_imagen))
    # Limpiar ruta relativa si viene del HTML (ej: ./Carpeta_files/img.png)
    if "?" in nombre_archivo_original:
        nombre_archivo_original = nombre_archivo_original.split('?')[0]

    ruta_origen = os.path.join(BASE_DIR, carpeta_files, nombre_archivo_original)
    
    # Intentar localizar la imagen si la ruta exacta falla
    if not os.path.exists(ruta_origen):
        # A veces la ruta en el HTML difiere ligeramente de la estructura de carpetas local
        posible_ruta = os.path.join(os.path.dirname(ruta_origen), nombre_archivo_original)
        if not os.path.exists(posible_ruta):
            print(f"   [WARN] Imagen física no encontrada: {nombre_archivo_original}")
            return nombre_archivo_original # Retornar original si no se encuentra el archivo físico
        ruta_origen = posible_ruta

    _, ext = os.path.splitext(nombre_archivo_original)
    if not ext: ext = ".png" # Default extension

    nuevo_nombre = f"{sku}{ext}"
    ruta_destino = os.path.join(os.path.dirname(ruta_origen), nuevo_nombre)

    # Manejo de colisiones si ya existe un archivo con ese SKU (para variantes)
    contador = 1
    while os.path.exists(ruta_destino):
        # Si el archivo ya existe y es el mismo, no hacemos nada
        if ruta_origen == ruta_destino:
            break
        nuevo_nombre = f"{sku}_{contador}{ext}"
        ruta_destino = os.path.join(os.path.dirname(ruta_origen), nuevo_nombre)
        contador += 1

    try:
        os.rename(ruta_origen, ruta_destino)
        print(f"   [IMG] Renombrado: {nombre_archivo_original} -> {nuevo_nombre}")
        return nuevo_nombre
    except OSError as e:
        print(f"   [ERR] No se pudo renombrar la imagen: {e}")
        return nombre_archivo_original

def main():
    print("=== INICIANDO AUTOMATIZACIÓN DE CATÁLOGO E-COMMERCE ===")
    
    datos_csv = []
    
    # Buscar todos los archivos HTML en el directorio base
    archivos_html = glob.glob(os.path.join(BASE_DIR, "*.html"))
    
    if not archivos_html:
        print(f"[FATAL] No se encontraron archivos HTML en {BASE_DIR}")
        return

    for archivo in archivos_html:
        print(f"\nProcesando archivo: {os.path.basename(archivo)}")
        
        # Determinar nombre de carpeta _files asociada
        # Normalmente: "Nombre.html" -> "Nombre_files"
        nombre_base = os.path.splitext(os.path.basename(archivo))[0]
        carpeta_files = f"{nombre_base}_files"
        
        with open(archivo, 'r', encoding='utf-8', errors='ignore') as f:
            soup = BeautifulSoup(f, 'html.parser')
            
            # Iterar sobre productos (basado en estructura Divi/WooCommerce)
            items = soup.find_all('div', class_='df-product-outer-wrap')
            
            for item in items:
                # 1. Extracción Datos Básicos
                titulo_tag = item.find('h2', class_='df-product-title')
                if not titulo_tag: continue
                
                title = titulo_tag.get_text(strip=True)
                link_tag = titulo_tag.find('a')
                product_url = link_tag['href'] if link_tag else None
                
                cat_tag = item.find('span', class_='df_term_item')
                category = cat_tag.get_text(strip=True) if cat_tag else ""
                
                img_tag = item.find('img')
                img_src_raw = img_tag['src'] if img_tag else ""
                
                if not product_url:
                    print(f"   [SKIP] Producto sin URL: {title}")
                    continue

                print(f"-> Analizando: {title[:40]}...")

                # 2. Scraping Online para SKU
                sku = obtener_sku_online(product_url)
                
                # 3. Renombrado Físico
                final_image_name = procesar_imagenes(img_src_raw, sku, carpeta_files)
                
                # Agregar a la data
                datos_csv.append({
                    'Title': title,
                    'Image Src': final_image_name,
                    'Category': category,
                    'SKU': sku if sku else ""
                })

    # 4. Generación CSV Final
    if datos_csv:
        df = pd.DataFrame(datos_csv)
        
        # Ordenar columnas según requerimiento
        df = df[['Title', 'Image Src', 'Category', 'SKU']]
        
        # Guardar datos principales
        df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
        
        # 5. Documentación Integrada (Append al archivo)
        documentacion = """
# Convenciones
Convención,Descripción
SKU como identificador único,El SKU extraído de la web se usa para nombrar imágenes y enlazar inventario.
Imagen renombrada físicamente → SKU.png,Estandarización para subida masiva a Cloudinary/Shopify.
Categorías extraídas desde <span class='df_term_item'>,Mantiene la taxonomía original del HTML fuente.
Notas de Integración,"Las imágenes han sido renombradas en disco. Subir carpeta completa a CDN antes de importar CSV."
"""
        with open(OUTPUT_CSV, 'a', encoding='utf-8-sig') as f:
            f.write(documentacion)
            
        print(f"\n[ÉXITO] Proceso completado.")
        print(f"        Total productos procesados: {len(df)}")
        print(f"        Archivo generado: {OUTPUT_CSV}")
    else:
        print("\n[WARN] No se extrajeron datos válidos.")

if __name__ == "__main__":
    main()