import os
import re
import shutil
import pandas as pd
from bs4 import BeautifulSoup
import unicodedata

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\scrap"
ARCHIVO_HTML = "CATALOGONOVIEMBREV012025NF.html"
CARPETA_IMAGENES_ORIGEN = "images_nf" 

# Salidas
CARPETA_SALIDA = os.path.join(BASE_DIR, "ACTIVOS_CLIENTE_NF_LOCAL")
ARCHIVO_CSV = os.path.join(BASE_DIR, "Inventario_Cliente_NF_Local.csv")

ruta_html = os.path.join(BASE_DIR, ARCHIVO_HTML)
ruta_imgs_origen = os.path.join(BASE_DIR, CARPETA_IMAGENES_ORIGEN)

if os.path.exists(CARPETA_SALIDA): shutil.rmtree(CARPETA_SALIDA)
os.makedirs(CARPETA_SALIDA, exist_ok=True)

# ================= UTILIDADES =================
def limpiar_texto(text):
    if not text: return ""
    return " ".join(text.split()).strip()

def slugify(text):
    text = str(text).lower()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')[:100]

# ================= MOTOR DE EXTRACCIÓN (MODO TABLA) =================
print(f"--- EXTRACCIÓN TABULAR: {ARCHIVO_HTML} ---")

if not os.path.exists(ruta_html):
    print("❌ HTML no encontrado.")
    exit()

with open(ruta_html, "r", encoding="utf-8", errors="ignore") as f:
    soup = BeautifulSoup(f, "html.parser")

filas = soup.find_all('tr')
print(f"🔍 Analizando {len(filas)} filas de tabla...")

datos = []
count = 0

for tr in filas:
    celdas = tr.find_all('td')
    
    # Buscamos filas que tengan imagen y texto
    # Estructura típica detectada: [Codigo] [Descripcion] [Imagen] [Precio]
    # O variaciones. Vamos a buscar dónde está la imagen.
    
    idx_img = -1
    for i, td in enumerate(celdas):
        if td.find('img'):
            idx_img = i
            break
    
    if idx_img != -1:
        # Tenemos una imagen en esta fila. Busquemos datos en las otras celdas.
        img_tag = celdas[idx_img].find('img')
        src = img_tag.get('src')
        filename = os.path.basename(src)
        
        # ESTRATEGIA: Concatenar todo el texto de la fila EXCEPTO la celda de la imagen
        texto_fila = []
        codigo_candidato = ""
        
        for i, td in enumerate(celdas):
            if i == idx_img: continue # Saltar celda de imagen
            txt = limpiar_texto(td.get_text())
            if txt:
                texto_fila.append(txt)
                # Si es la primera celda y parece código, guardarlo
                if i == 0 and len(txt) < 10 and any(c.isdigit() for c in txt):
                    codigo_candidato = txt

        descripcion_completa = " ".join(texto_fila)
        
        # LIMPIEZA Y GUARDADO
        if len(descripcion_completa) > 5:
            # Crear nombre limpio
            slug_desc = slugify(descripcion_completa)
            nuevo_nombre = f"{slug_desc}.jpg"
            if codigo_candidato:
                nuevo_nombre = f"{slug_desc}-{slugify(codigo_candidato)}.jpg"
            
            path_origen = os.path.join(ruta_imgs_origen, filename)
            path_destino = os.path.join(CARPETA_SALIDA, nuevo_nombre)
            
            if os.path.exists(path_origen):
                try:
                    shutil.copy2(path_origen, path_destino)
                    
                    datos.append({
                        "Codigo": codigo_candidato,
                        "Descripcion": descripcion_completa,
                        "Imagen_Original": filename,
                        "Imagen_Final": nuevo_nombre,
                        "Fuente": "HTML_TABLA"
                    })
                    count += 1
                except: pass

# GUARDAR RESULTADOS
if datos:
    df = pd.DataFrame(datos)
    df.to_csv(ARCHIVO_CSV, index=False, encoding='utf-8-sig')
    print("\n" + "="*50)
    print(f"✅ ÉXITO ROTUNDO")
    print(f"   Activos Recuperados: {len(df)}")
    print(f"   CSV: {ARCHIVO_CSV}")
    print(f"   Carpeta: {CARPETA_SALIDA}")
    print("="*50)
else:
    print("\n❌ No se extrajeron datos. La estructura no es una tabla estándar.")