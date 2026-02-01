import os
import re
import json
import shutil
import unicodedata

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\scrap"
ARCHIVO_HTML = "CARBURADORES.html"
CARPETA_ORIGEN = "CARBURADORES_files" # La carpeta que crea el navegador
CARPETA_DESTINO = "ACTIVOS_DFG_CARBURADORES_LIMPIOS"

# Rutas
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

def limpiar_texto(text):
    if not text: return ""
    # Limpiar códigos de Canva o basura
    text = re.sub(r'\\n', ' ', text)
    return " ".join(text.split()).strip()

# ================= MOTOR DE EXTRACCIÓN CANVA =================
def procesar_canva_local():
    print(f"--- EXTRACCIÓN CANVA LOCAL: {ARCHIVO_HTML} ---")
    
    if not os.path.exists(ruta_html):
        print("❌ HTML no encontrado.")
        return

    with open(ruta_html, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # 1. Encontrar el JSON de Canva que tiene los textos y las referencias a imágenes
    # Canva guarda el contenido en window['bootstrap'] = JSON.parse('...')
    # Pero en el HTML guardado localmente, las imágenes están en <img> tags con src local.
    
    # ESTRATEGIA HÍBRIDA:
    # Vamos a usar Regex para encontrar la pareja: Texto cercano + Tag IMG
    # En exportaciones de Canva, el texto suele estar en un <div> antes o después de la imagen.
    
    # Buscamos bloques de imagen
    # Patrón: src="./CARBURADORES_files/NOMBRE.png"
    # Y tratamos de encontrar texto alrededor.
    
    # NOTA: Canva genera HTML muy sucio con clases aleatorias. 
    # La mejor apuesta local es listar los archivos de la carpeta _files y tratar de cruzarlos 
    # con el texto que aparece en el HTML cerca de la referencia a ese archivo.

    archivos_encontrados = []
    
    # Buscar todas las ocurrencias de imágenes en el HTML
    # Ejemplo: src="./CARBURADORES_files/xyz.jpg"
    matches = re.finditer(r'src=["\']\./' + re.escape(CARPETA_ORIGEN) + r'/([^"\']+)["\']', content)
    
    print("🔍 Buscando referencias y contexto...")
    
    for m in matches:
        filename_sucio = m.group(1)
        pos_inicio = m.start()
        
        # Mirar 1000 caracteres antes y después para encontrar texto
        contexto_antes = content[max(0, pos_inicio-1000):pos_inicio]
        contexto_despues = content[m.end():min(len(content), m.end()+1000)]
        
        # Limpiar etiquetas HTML del contexto para ver solo texto
        texto_cercano = re.sub(r'<[^>]+>', ' ', contexto_antes + " " + contexto_despues)
        
        # Buscar palabras clave que parezcan repuestos (Mayúsculas, > 3 letras)
        # Ejemplo: "CARBURADOR BOXER CT 100"
        palabras_clave = re.findall(r'\b[A-Z0-9\-\s]{5,50}\b', texto_cercano)
        
        # Filtrar palabras irrelevantes de Canva
        palabras_validas = [p.strip() for p in palabras_clave if "CANVA" not in p and "WIDTH" not in p and len(p.strip()) > 5]
        
        nombre_detectado = "desconocido"
        if palabras_validas:
            # Tomar la palabra válida más cercana (la última del 'antes' o primera del 'después')
            # Simplificación: Tomamos la más larga encontrada en el bloque
            nombre_detectado = max(palabras_validas, key=len)

        # Procesar archivo
        if nombre_detectado != "desconocido":
            nombre_nuevo = slugify(nombre_detectado)
            ext = os.path.splitext(filename_sucio)[1]
            nombre_final = f"{nombre_nuevo}{ext}"
            
            origen_path = os.path.join(ruta_imgs_origen, filename_sucio)
            destino_path = os.path.join(ruta_imgs_destino, nombre_final)
            
            # Verificar si existe el archivo físico
            if os.path.exists(origen_path):
                try:
                    # Evitar duplicados de nombre
                    if os.path.exists(destino_path):
                        nombre_final = f"{nombre_nuevo}-{sha1_file(origen_path)[:5]}{ext}"
                        destino_path = os.path.join(ruta_imgs_destino, nombre_final)
                        
                    shutil.copy2(origen_path, destino_path)
                    archivos_encontrados.append((filename_sucio, nombre_final))
                    print(f"   + {nombre_final}")
                except: pass

    print("\n" + "="*50)
    print(f"✅ EXTRACCIÓN CANVA FINALIZADA")
    print(f"   Imágenes recuperadas: {len(archivos_encontrados)}")
    print(f"   Carpeta: {CARPETA_DESTINO}")
    print("="*50)

def sha1_file(path):
    h = hashlib.sha1()
    with open(path, "rb") as f: h.update(f.read())
    return h.hexdigest()

if __name__ == "__main__":
    procesar_canva_local()