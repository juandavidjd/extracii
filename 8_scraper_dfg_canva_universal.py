import os
import re
import shutil
import unicodedata
import hashlib

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\scrap"

# CAMBIA ESTO PARA CADA ARCHIVO NUEVO QUE DESCARGUES:
NOMBRE_BASE = "CARBURADORES"  # Ejemplo: "AMORTIGUADORES", "CILINDROS"

ARCHIVO_HTML = f"{NOMBRE_BASE}.html"
CARPETA_ORIGEN = f"{NOMBRE_BASE}_files"
CARPETA_DESTINO = f"ACTIVOS_DFG_{NOMBRE_BASE}_FINAL"

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

def limpiar_basura_canva(text):
    # Elimina ruido típico del JSON de Canva
    if not text: return ""
    t = text.replace('\\n', ' ').replace('\\"', '"')
    return " ".join(t.split()).strip()

def sha1_short(path):
    try:
        h = hashlib.sha1()
        with open(path, "rb") as f: h.update(f.read())
        return h.hexdigest()[:6]
    except: return "0000"

# ================= MOTOR UNIVERSAL =================
def procesar_canva_universal():
    print(f"--- PROCESANDO: {ARCHIVO_HTML} ---")
    
    if not os.path.exists(ruta_html):
        print(f"❌ No encuentro el archivo {ARCHIVO_HTML}")
        return

    if not os.path.exists(ruta_imgs_origen):
        print(f"❌ No encuentro la carpeta {CARPETA_ORIGEN}")
        return

    # 1. Leer el HTML completo como texto plano
    with open(ruta_html, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # 2. Listar imágenes físicas
    imagenes_fisicas = [f for f in os.listdir(ruta_imgs_origen) if f.lower().endswith(('.jpg', '.png', '.jpeg', '.webp'))]
    print(f"🔍 Imágenes detectadas en carpeta: {len(imagenes_fisicas)}")
    
    count_ok = 0
    count_huerfanas = 0
    
    for foto in imagenes_fisicas:
        nombre_final = ""
        codigo_encontrado = ""
        nombre_encontrado = ""
        
        # 3. Buscar la ubicación de la foto en el código
        # Canva a veces usa el nombre exacto o un hash, buscamos el exacto primero.
        pos = content.find(foto)
        
        if pos != -1:
            # 4. Extraer contexto (Radio de búsqueda: 2000 caracteres antes y después)
            # El texto suele estar ANTES en el JSON de Canva, pero miramos ambos lados.
            contexto = content[max(0, pos-2000):min(len(content), pos+2000)]
            contexto_limpio = limpiar_basura_canva(contexto)
            
            # A. BUSCAR CÓDIGO (COD. XXXX o REF. XXXX)
            # Regex: Busca "COD" seguido de caracteres, ignorando mayúsculas
            match_cod = re.search(r'(?:COD|REF)[\s\.:]+([A-Z0-9\-]{4,10})', contexto_limpio, re.IGNORECASE)
            if match_cod:
                codigo_encontrado = match_cod.group(1)
            
            # B. BUSCAR NOMBRE (Texto en Mayúsculas cercano)
            # Buscamos palabras en mayúscula sostenida que no sean comandos de Canva
            # Excluimos: WIDTH, HEIGHT, RGB, CANVA, HTTP, JPG, PNG
            palabras_clave = re.findall(r'\b(?!(?:WIDTH|HEIGHT|RGB|CANVA|HTTP|JPG|PNG|DIV|SPAN))[A-Z0-9\-\s]{5,50}\b', contexto_limpio)
            
            # Filtramos candidatos válidos
            candidatos = [p.strip() for p in palabras_clave if len(p.strip()) > 4 and not p.strip().isdigit()]
            
            if candidatos:
                # Heurística: El nombre del producto suele ser el texto más largo en mayúsculas cerca de la foto
                # O el que está más cerca del código si lo encontramos.
                nombre_encontrado = max(candidatos, key=len)
        
        # 5. Definir Nombre Final
        if nombre_encontrado:
            if codigo_encontrado:
                base = f"{slugify(nombre_encontrado)}-{slugify(codigo_encontrado)}"
                tipo = "FULL_MATCH"
            else:
                base = slugify(nombre_encontrado)
                tipo = "SOLO_NOMBRE"
        else:
            # Si falló todo, NO BORRAMOS. Guardamos para revisión manual.
            # Usamos un hash corto para que el nombre sea único pero corto.
            base = f"revisar-{slugify(foto)}-{sha1_short(os.path.join(ruta_imgs_origen, foto))}"
            tipo = "HUERFANA"
            count_huerfanas += 1

        # 6. Copiar y Renombrar
        ext = os.path.splitext(foto)[1]
        nuevo_archivo = f"{base}{ext}"
        
        origen = os.path.join(ruta_imgs_origen, foto)
        destino = os.path.join(ruta_imgs_destino, nuevo_archivo)
        
        # Evitar colisiones (si dos productos se llaman igual)
        c = 1
        while os.path.exists(destino):
            nuevo_archivo = f"{base}-{c}{ext}"
            destino = os.path.join(ruta_imgs_destino, nuevo_archivo)
            c += 1
            
        try:
            shutil.copy2(origen, destino)
            if tipo != "HUERFANA":
                print(f"   ✅ [{tipo}] {nuevo_archivo}")
                count_ok += 1
            # else:
            #     print(f"   ⚠️ [HUERFANA] {nuevo_archivo}")
        except: pass

    print("\n" + "="*50)
    print(f"✅ PROCESO TERMINADO: {NOMBRE_BASE}")
    print(f"   Identificadas con texto: {count_ok}")
    print(f"   Sin texto (Rescatadas): {count_huerfanas}")
    print(f"   Total Imágenes: {count_ok + count_huerfanas}")
    print(f"   Carpeta Salida: {CARPETA_DESTINO}")
    print("="*50)

if __name__ == "__main__":
    procesar_canva_universal()