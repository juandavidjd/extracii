import os
import requests
import pandas as pd
from bs4 import BeautifulSoup
import unicodedata
import re

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\scrap"
BASE_URL = "https://armvalle.com"
TARGET_URL = "https://armvalle.com/?page_id=394"

CARPETA_SALIDA = os.path.join(BASE_DIR, "ACTIVOS_CLIENTE_NF_GALERIA")
ARCHIVO_CSV = os.path.join(BASE_DIR, "Inventario_Cliente_NF_Galeria.csv")

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
    # Quitar extensiones de archivo si aparecen en el texto
    text = text.replace('.jpg', '').replace('.png', '').replace('.jpeg', '')
    return " ".join(text.split()).strip()

def descargar_imagen(url, nombre_archivo):
    try:
        if not url: return False
        if not url.startswith('http'):
            url = BASE_URL + url if url.startswith('/') else f"{BASE_URL}/{url}"
            
        path = os.path.join(CARPETA_SALIDA, nombre_archivo)
        if os.path.exists(path): return True

        r = requests.get(url, headers=HEADERS, stream=True, timeout=15)
        if r.status_code == 200:
            with open(path, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
            return True
    except: return False

# ================= MOTOR DE MINERÍA =================
def minar_galeria():
    print(f"--- ATAQUE QUIRÚRGICO A GALERÍA: {TARGET_URL} ---")
    
    try:
        r = requests.get(TARGET_URL, headers=HEADERS, timeout=20)
    except Exception as e:
        print(f"Error fatal de conexión: {e}")
        return

    soup = BeautifulSoup(r.text, 'html.parser')
    productos_encontrados = []
    
    # ESTRATEGIA 1: Buscar items de Galería (figure.gallery-item)
    items_galeria = soup.select('figure.gallery-item')
    print(f"-> Encontrados {len(items_galeria)} items en galería.")
    
    # ESTRATEGIA 2: Buscar Widgets de Imagen Elementor (sueltos)
    items_elementor = soup.select('.elementor-widget-image')
    print(f"-> Encontrados {len(items_elementor)} widgets de imagen.")
    
    todos_items = items_galeria + items_elementor
    
    for item in todos_items:
        try:
            img_tag = item.find('img')
            if not img_tag: continue
            
            src = img_tag.get('data-src') or img_tag.get('src')
            if not src: continue
            
            # BUSQUEDA DE TEXTO (INTELIGENCIA DE CONTEXTO)
            texto_encontrado = ""
            
            # 1. Buscar Caption explícito (figcaption)
            caption_tag = item.find('figcaption')
            if caption_tag:
                texto_encontrado = caption_tag.get_text(strip=True)
            
            # 2. Si no hay caption, buscar atributo ALT o TITLE de la imagen
            if not texto_encontrado:
                alt = img_tag.get('alt', '')
                title = img_tag.get('title', '')
                # Usamos el que sea más largo y no parezca nombre de archivo
                if len(alt) > 5 and "whatsapp" not in alt.lower():
                    texto_encontrado = alt
                elif len(title) > 5 and "whatsapp" not in title.lower():
                    texto_encontrado = title
            
            # 3. Si sigue vacío, buscar texto cercano (para widgets elementor)
            if not texto_encontrado:
                # Buscar un div hermano con clase de texto
                padre = item.find_parent()
                if padre:
                    texto_cercano = padre.get_text(" ", strip=True)
                    # Limpieza básica para ver si es útil
                    if len(texto_cercano) > 5 and len(texto_cercano) < 200:
                        texto_encontrado = texto_cercano

            # LIMPIEZA FINAL
            nombre_producto = limpiar_texto(texto_encontrado)
            
            # DESCARTAR BASURA
            # Si el nombre sigue pareciendo un archivo "WhatsApp Image...", lo ignoramos o lo marcamos
            es_basura = False
            if "whatsapp" in nombre_producto.lower() or len(nombre_producto) < 3:
                nombre_producto = "Producto_Sin_Nombre_Detectado"
                es_basura = True
            
            if src and not es_basura:
                # Renombrar para SEO
                nombre_base = slugify(nombre_producto)
                ext = ".jpg"
                nuevo_nombre = f"{nombre_base}{ext}"
                
                if descargar_imagen(src, nuevo_nombre):
                    print(f"   + [OK] {nombre_producto[:40]}...")
                    
                    productos_encontrados.append({
                        "Descripcion": nombre_producto,
                        "Nombre_Archivo_Nuevo": nuevo_nombre,
                        "Nombre_Original": os.path.basename(src),
                        "Fuente": "ARMVALLE_GALERIA"
                    })
            elif es_basura:
                # Opcional: Descargar igual para revisión manual? 
                # Por ahora solo avisamos.
                # print(f"   - [SKIP] Sin descripción válida: {os.path.basename(src)}")
                pass

        except Exception as e:
            continue

    # GUARDAR
    if productos_encontrados:
        df = pd.DataFrame(productos_encontrados)
        df.to_csv(ARCHIVO_CSV, index=False, encoding='utf-8-sig')
        print("\n" + "="*50)
        print(f"✅ EXTRACCIÓN DE GALERÍA FINALIZADA")
        print(f"   Activos recuperados: {len(df)}")
        print(f"   CSV: {ARCHIVO_CSV}")
        print(f"   Carpeta: {CARPETA_SALIDA}")
        print("="*50)
    else:
        print("\n⚠️ No se pudo extraer información útil. Es posible que la galería solo contenga fotos sin texto asociado.")

if __name__ == "__main__":
    minar_galeria()