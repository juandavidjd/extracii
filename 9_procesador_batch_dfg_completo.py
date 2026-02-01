import os
import re
import shutil
import unicodedata
import hashlib
import pandas as pd

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\scrap"

# Salida Maestra (Todo caerá aquí)
CARPETA_SALIDA_GLOBAL = os.path.join(BASE_DIR, "ACTIVOS_DFG_CONSOLIDADOS")
ARCHIVO_MAESTRO_CSV = os.path.join(BASE_DIR, "Inventario_Maestro_DFG_Completo.csv")

if not os.path.exists(CARPETA_SALIDA_GLOBAL):
    os.makedirs(CARPETA_SALIDA_GLOBAL)

# ================= UTILIDADES =================
def slugify(text):
    if not text: return "sin-nombre"
    text = str(text).lower()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')[:100]

def limpiar_basura_canva(text):
    if not text: return ""
    # Limpia caracteres de escape del JSON de Canva
    t = text.replace('\\n', ' ').replace('\\"', '"')
    return " ".join(t.split()).strip()

def sha1_short(path):
    try:
        h = hashlib.sha1()
        with open(path, "rb") as f: h.update(f.read())
        return h.hexdigest()[:6]
    except: return "0000"

# ================= MOTOR DE PROCESAMIENTO ÚNICO =================
def procesar_catalogo(archivo_html, carpeta_origen):
    print(f"\n>>> Procesando Categoría: {archivo_html}...")
    
    nombre_categoria = os.path.splitext(archivo_html)[0]
    ruta_html = os.path.join(BASE_DIR, archivo_html)
    ruta_imgs_origen = os.path.join(BASE_DIR, carpeta_origen)
    
    # Leer HTML
    try:
        with open(ruta_html, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except:
        print(f"   ❌ Error leyendo archivo HTML: {archivo_html}")
        return []

    # Listar imágenes (jpg, png, jpeg, webp)
    try:
        imagenes_fisicas = [f for f in os.listdir(ruta_imgs_origen) if f.lower().endswith(('.jpg', '.png', '.jpeg', '.webp'))]
    except FileNotFoundError:
        print(f"   ⚠️ No se encontró la carpeta de imágenes: {carpeta_origen}")
        return []

    print(f"   🔍 {len(imagenes_fisicas)} imágenes encontradas.")
    
    datos_extraidos = []
    count_cat = 0
    
    for foto in imagenes_fisicas:
        nombre_final = ""
        codigo_encontrado = ""
        nombre_encontrado = ""
        
        # Buscar la foto en el código fuente del HTML
        pos = content.find(foto)
        
        if pos != -1:
            # Extraer contexto (2000 chars alrededor)
            contexto = content[max(0, pos-2000):min(len(content), pos+2000)]
            contexto_limpio = limpiar_basura_canva(contexto)
            
            # A. Buscar CÓDIGO (COD. XXXX o REF. XXXX)
            match_cod = re.search(r'(?:COD|REF)[\s\.:]+([A-Z0-9\-]{4,10})', contexto_limpio, re.IGNORECASE)
            if match_cod:
                codigo_encontrado = match_cod.group(1)
            
            # B. Buscar NOMBRE (Mayúsculas, excluyendo palabras técnicas)
            palabras_clave = re.findall(r'\b(?!(?:WIDTH|HEIGHT|RGB|CANVA|HTTP|JPG|PNG|DIV|SPAN|STYLE))[A-Z0-9\-\s\.\/]{4,50}\b', contexto_limpio)
            
            # Filtros de calidad
            candidatos = [
                p.strip() for p in palabras_clave 
                if len(p.strip()) > 4 
                and not p.strip().isdigit()
                and "CANVA" not in p
            ]
            
            if candidatos:
                # Heurística: Tomar el candidato más largo (suele ser la descripción completa)
                nombre_encontrado = max(candidatos, key=len)
        
        # Definir nombres finales
        if nombre_encontrado:
            slug_nom = slugify(nombre_encontrado)
            if codigo_encontrado:
                slug_cod = slugify(codigo_encontrado)
                base_name = f"{slug_nom}-{slug_cod}"
            else:
                base_name = slug_nom
        else:
            # Fallback: Si no hay texto, usamos el nombre de la categoría + hash para no perder la foto
            base_name = f"revisar-{slugify(nombre_categoria)}-{sha1_short(os.path.join(ruta_imgs_origen, foto))}"
            nombre_encontrado = f"{nombre_categoria} (Sin Identificar)"

        # Copiar y Registrar
        ext = os.path.splitext(foto)[1]
        nuevo_archivo = f"{base_name}{ext}"
        
        origen = os.path.join(ruta_imgs_origen, foto)
        destino = os.path.join(CARPETA_SALIDA_GLOBAL, nuevo_archivo)
        
        # Evitar colisiones globales
        c = 1
        while os.path.exists(destino):
            nuevo_archivo = f"{base_name}-{c}{ext}"
            destino = os.path.join(CARPETA_SALIDA_GLOBAL, nuevo_archivo)
            c += 1
            
        try:
            shutil.copy2(origen, destino)
            count_cat += 1
            
            datos_extraidos.append({
                "Categoria_Origen": nombre_categoria,
                "Codigo": codigo_encontrado,
                "Nombre_Producto": nombre_encontrado,
                "Imagen_Original": foto,
                "Imagen_Final": nuevo_archivo,
                "Fuente": "DFG_BATCH_CANVA"
            })
        except: pass
    
    print(f"   ✅ Procesadas: {count_cat}/{len(imagenes_fisicas)}")
    return datos_extraidos

# ================= MOTOR PRINCIPAL =================
def main_batch():
    print(f"--- INICIANDO PROCESAMIENTO MASIVO DFG ({len(os.listdir(BASE_DIR))} archivos) ---")
    
    # 1. Detectar parejas HTML + Carpeta
    archivos = os.listdir(BASE_DIR)
    parejas = []
    
    for f in archivos:
        if f.endswith(".html"):
            nombre_base = os.path.splitext(f)[0]
            # Detectar variantes de nombre de carpeta (_files o _archivos)
            carpeta_files = f"{nombre_base}_files"
            carpeta_archivos = f"{nombre_base}_archivos"
            
            if os.path.exists(os.path.join(BASE_DIR, carpeta_files)):
                parejas.append({"html": f, "folder": carpeta_files})
            elif os.path.exists(os.path.join(BASE_DIR, carpeta_archivos)):
                parejas.append({"html": f, "folder": carpeta_archivos})
    
    print(f"📚 Catálogos válidos detectados: {len(parejas)}")
    
    todos_los_datos = []
    
    # 2. Procesar cada pareja
    for p in parejas:
        datos = procesar_catalogo(p["html"], p["folder"])
        todos_los_datos.extend(datos)

    # 3. Guardar CSV Maestro
    if todos_los_datos:
        df = pd.DataFrame(todos_los_datos)
        # Ordenar columnas
        cols = ["Codigo", "Nombre_Producto", "Imagen_Final", "Categoria_Origen", "Imagen_Original"]
        # Asegurar que existan las columnas en el DF
        cols_existentes = [c for c in cols if c in df.columns]
        df = df[cols_existentes]
        
        df.to_csv(ARCHIVO_MAESTRO_CSV, index=False, encoding='utf-8-sig')
        
        print("\n" + "="*50)
        print(f"✅ MISIÓN CUMPLIDA")
        print(f"   Total Activos Recuperados: {len(df)}")
        print(f"   CSV Maestro: {ARCHIVO_MAESTRO_CSV}")
        print(f"   Carpeta Unificada: {CARPETA_SALIDA_GLOBAL}")
        print("="*50)
    else:
        print("\n❌ No se encontraron datos procesables.")

if __name__ == "__main__":
    main_batch()