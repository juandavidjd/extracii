import os
import re
import shutil
import unicodedata

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\scrap"
ARCHIVO_HTML = "CARBURADORES.html"
CARPETA_ORIGEN = "CARBURADORES_files" 
CARPETA_DESTINO = "ACTIVOS_DFG_CARBURADORES_FULL"

ruta_html = os.path.join(BASE_DIR, ARCHIVO_HTML)
ruta_imgs_origen = os.path.join(BASE_DIR, CARPETA_ORIGEN)
ruta_imgs_destino = os.path.join(BASE_DIR, CARPETA_DESTINO)

if os.path.exists(ruta_imgs_destino): shutil.rmtree(ruta_imgs_destino)
os.makedirs(ruta_imgs_destino, exist_ok=True)

# ================= UTILIDADES =================
def slugify(text):
    if not text: return "sin-nombre"
    text = str(text).lower()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')[:100]

# ================= MOTOR DE EXTRACCIÓN =================
def procesar_canva_profundo():
    print(f"--- EXTRACCIÓN CANVA PROFUNDA: {ARCHIVO_HTML} ---")
    
    if not os.path.exists(ruta_html):
        print("❌ HTML no encontrado.")
        return

    with open(ruta_html, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    archivos_encontrados = []
    
    # Buscar todas las referencias a imágenes en la carpeta _files
    # Patrón flexible para encontrar el nombre del archivo
    # Puede estar en src="..." o en JSON escapado \"src\":\"...\"
    
    # Primero listamos los archivos reales en la carpeta para saber qué buscar
    if not os.path.exists(ruta_imgs_origen):
        print(f"❌ Carpeta de imágenes no encontrada: {CARPETA_ORIGEN}")
        return

    imagenes_fisicas = [f for f in os.listdir(ruta_imgs_origen) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    print(f"🔍 Imágenes físicas detectadas: {len(imagenes_fisicas)}")
    
    for imagen_archivo in imagenes_fisicas:
        # Buscamos dónde aparece este nombre de archivo en el HTML
        # Escapamos puntos para regex
        nombre_regex = re.escape(imagen_archivo)
        
        # Buscamos todas las ocurrencias en el texto
        # Ampliamos el contexto a 3000 caracteres antes y después (Canva mete mucha basura de estilos)
        iterador = re.finditer(nombre_regex, content)
        
        texto_mejor_match = ""
        
        for match in iterador:
            pos = match.start()
            # Extraer un bloque grande alrededor
            bloque = content[max(0, pos-3000):min(len(content), pos+3000)]
            
            # Limpiar HTML y JSON chars del bloque
            texto_limpio = re.sub(r'<[^>]+>', ' ', bloque) # Quitar tags
            texto_limpio = texto_limpio.replace('\\n', ' ').replace('\\"', '"').replace('"', ' ')
            
            # Buscar patrones de texto que parezcan nombres de producto
            # Mayúsculas, longitud > 5, palabras clave como CARBURADOR
            # Regex: Palabras en mayuscula o numeros, longitud min 5, que contengan CARBURADOR o similar
            
            posibles_nombres = re.findall(r'\b(?:CARBURADOR|KIT|CILINDRO)[A-Z0-9\-\s\/\.]{5,50}\b', texto_limpio, re.IGNORECASE)
            
            if posibles_nombres:
                # Tomar el más cercano al centro del bloque (donde estaba la imagen)
                # Por simplicidad, tomamos el más largo encontrado en el contexto
                texto_mejor_match = max(posibles_nombres, key=len)
                break # Ya encontramos uno bueno
        
        if texto_mejor_match:
            # Renombrar
            nombre_nuevo = slugify(texto_mejor_match)
            ext = os.path.splitext(imagen_archivo)[1]
            nombre_final = f"{nombre_nuevo}{ext}"
            
            # Copiar
            origen = os.path.join(ruta_imgs_origen, imagen_archivo)
            destino = os.path.join(ruta_imgs_destino, nombre_final)
            
            # Evitar colisiones
            count = 1
            while os.path.exists(destino):
                nombre_final = f"{nombre_nuevo}-{count}{ext}"
                destino = os.path.join(ruta_imgs_destino, nombre_final)
                count += 1
            
            try:
                shutil.copy2(origen, destino)
                print(f"   + {nombre_final}")
                archivos_encontrados.append(nombre_final)
            except: pass
            
    print("\n" + "="*50)
    print(f"✅ EXTRACCIÓN COMPLETADA")
    print(f"   Recuperados: {len(archivos_encontrados)} / {len(imagenes_fisicas)}")
    print(f"   Carpeta: {CARPETA_DESTINO}")
    print("="*50)

if __name__ == "__main__":
    procesar_canva_profundo()