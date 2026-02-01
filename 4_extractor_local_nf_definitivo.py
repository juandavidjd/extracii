import os
import re
import shutil
import pandas as pd
from bs4 import BeautifulSoup
import unicodedata

# ================= CONFIGURACIÓN LOCAL =================
BASE_DIR = r"C:\scrap"
ARCHIVO_HTML = "CATALOGONOVIEMBREV012025NF.html"
CARPETA_IMAGENES_ORIGEN = "images_nf" # Carpeta creada por la conversión PDF->HTML

# Salidas
CARPETA_SALIDA = "ACTIVOS_CLIENTE_NF_LOCAL"
ARCHIVO_CSV = "Inventario_Cliente_NF_Local.csv"

ruta_html = os.path.join(BASE_DIR, ARCHIVO_HTML)
ruta_imgs_origen = os.path.join(BASE_DIR, CARPETA_IMAGENES_ORIGEN)
ruta_imgs_destino = os.path.join(BASE_DIR, CARPETA_SALIDA)
ruta_csv_salida = os.path.join(BASE_DIR, ARCHIVO_CSV)

if os.path.exists(ruta_imgs_destino): shutil.rmtree(ruta_imgs_destino)
os.makedirs(ruta_imgs_destino, exist_ok=True)

# ================= UTILIDADES =================
def limpiar_texto(text):
    if not text: return ""
    # Eliminar espacios multiples y caracteres invisibles
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def slugify(text):
    text = str(text).lower()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')[:100]

def es_texto_valido(text):
    # Filtra textos que no son productos (encabezados, paginación, basura)
    if len(text) < 5: return False
    if "Página" in text or "Page" in text: return False
    if text.isdigit(): return False # Solo números
    return True

# ================= MOTOR DE EXTRACCIÓN =================
print(f"--- PROCESANDO LOCALMENTE: {ARCHIVO_HTML} ---")

if not os.path.exists(ruta_html):
    print("❌ No encuentro el archivo HTML.")
    exit()

with open(ruta_html, "r", encoding="utf-8", errors="ignore") as f:
    soup = BeautifulSoup(f, "html.parser")

imagenes = soup.find_all('img')
datos_extraidos = []

print(f"🔍 Analizando {len(imagenes)} imágenes y su contexto...")

count_ok = 0

for img in imagenes:
    src = img.get('src')
    if not src: continue
    
    filename_original = os.path.basename(src) # ej: image100.jpg
    
    # INTELIGENCIA DE CONTEXTO (La clave del éxito)
    texto_encontrado = ""
    
    # 1. Buscar en el padre inmediato (p, div, span)
    padre = img.find_parent(['p', 'div', 'span', 'td'])
    
    if padre:
        # Texto en el mismo bloque
        texto_encontrado = padre.get_text(" ", strip=True)
        
        # 2. Si el bloque es solo la imagen, buscar el ANTERIOR (Título suele ir arriba)
        if len(texto_encontrado) < 5:
            prev = padre.find_previous_sibling(['p', 'div', 'h1', 'h2', 'h3', 'h4'])
            if prev:
                texto_encontrado = prev.get_text(" ", strip=True)
                
        # 3. Si sigue vacío, buscar el SIGUIENTE (A veces el título va abajo)
        if len(texto_encontrado) < 5:
            sig = padre.find_next_sibling(['p', 'div', 'h1', 'h2', 'h3', 'h4'])
            if sig:
                texto_encontrado = sig.get_text(" ", strip=True)

    descripcion = limpiar_texto(texto_encontrado)
    
    # VALIDACIÓN Y GUARDADO
    if es_texto_valido(descripcion):
        # Crear nombre limpio
        nuevo_nombre = f"{slugify(descripcion)}.jpg"
        
        # Ruta origen (la carpeta images_nf que ya tienes)
        path_origen = os.path.join(ruta_imgs_origen, filename_original)
        path_destino = os.path.join(ruta_imgs_destino, nuevo_nombre)
        
        # Verificar si existe la imagen física
        if os.path.exists(path_origen):
            try:
                shutil.copy2(path_origen, path_destino)
                
                datos_extraidos.append({
                    "Descripcion": descripcion,
                    "Imagen_Original": filename_original,
                    "Imagen_Final": nuevo_nombre,
                    "Fuente": "HTML_LOCAL_NF"
                })
                count_ok += 1
            except Exception as e:
                print(f"Error copiando {filename_original}: {e}")

# RESULTADOS
if datos_extraidos:
    df = pd.DataFrame(datos_extraidos)
    # Eliminar duplicados (a veces la misma imagen aparece 2 veces)
    df = df.drop_duplicates(subset=['Imagen_Final'])
    df.to_csv(ruta_csv_salida, index=False, sep=',', encoding='utf-8-sig')
    
    print("\n" + "="*50)
    print(f"✅ EXTRACCIÓN LOCAL FINALIZADA")
    print(f"   Activos Recuperados: {len(df)}")
    print(f"   CSV Generado: {ARCHIVO_CSV}")
    print(f"   Carpeta Lista: {CARPETA_SALIDA}")
    print("="*50)
else:
    print("\n⚠️ No pude asociar texto a las imágenes. Revisa si el HTML tiene texto seleccionable.")