import os
import re
import shutil
import unicodedata
import hashlib
import pandas as pd
from difflib import SequenceMatcher

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\scrap"

# Entrada: Tu archivo maestro de nombres limpios
ARCHIVO_DICCIONARIO = os.path.join(BASE_DIR, "Inventario_DFG_Web_Canva.csv")

# Salida
CARPETA_SALIDA_GLOBAL = os.path.join(BASE_DIR, "ACTIVOS_DFG_CONSOLIDADOS_V2")
ARCHIVO_MAESTRO_SALIDA = os.path.join(BASE_DIR, "Inventario_Maestro_DFG_Imagenes_v2.csv")

if os.path.exists(CARPETA_SALIDA_GLOBAL): shutil.rmtree(CARPETA_SALIDA_GLOBAL)
os.makedirs(CARPETA_SALIDA_GLOBAL, exist_ok=True)

# ================= UTILIDADES =================
def slugify(text):
    if not text: return "sin-nombre"
    text = str(text).lower()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')[:100]

def limpiar_basura_canva(text):
    if not text: return ""
    t = text.replace('\\n', ' ').replace('\\"', '"')
    # Filtro Anti-Basura (SVG paths, coordenadas, CSS)
    if re.match(r'^[M0-9\sLHVZ\-,]+$', t, re.IGNORECASE): return "" # Detecta paths SVG
    if len(t) < 3: return ""
    return " ".join(t.split()).strip()

def cargar_diccionario():
    """Carga el CSV maestro en memoria para búsquedas rápidas."""
    print(f"📚 Cargando Diccionario: {ARCHIVO_DICCIONARIO}")
    if not os.path.exists(ARCHIVO_DICCIONARIO):
        print("   ❌ No se encontró el archivo diccionario.")
        return {}, []
    
    try:
        df = pd.read_csv(ARCHIVO_DICCIONARIO, dtype=str)
        # Mapa Código -> Nombre
        mapa_codigos = {}
        # Lista de Nombres para búsqueda fuzzy
        lista_nombres = []
        
        for _, row in df.iterrows():
            cod = str(row.get('Codigo', '')).strip()
            nom = str(row.get('Nombre', '')).strip()
            
            if cod and len(cod) > 3:
                mapa_codigos[cod] = nom
            if nom and len(nom) > 4:
                lista_nombres.append(nom)
                
        print(f"   -> {len(mapa_codigos)} códigos y {len(lista_nombres)} nombres cargados.")
        return mapa_codigos, lista_nombres
    except Exception as e:
        print(f"   ⚠️ Error cargando diccionario: {e}")
        return {}, []

# ================= MOTOR DE PROCESAMIENTO =================
def procesar_catalogo(archivo_html, carpeta_origen, mapa_codigos, lista_nombres):
    print(f"\n>>> Procesando: {archivo_html}...")
    
    categoria = os.path.splitext(archivo_html)[0]
    ruta_html = os.path.join(BASE_DIR, archivo_html)
    ruta_imgs = os.path.join(BASE_DIR, carpeta_origen)
    
    with open(ruta_html, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    imagenes = [f for f in os.listdir(ruta_imgs) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    print(f"   🔍 {len(imagenes)} imágenes.")
    
    datos = []
    
    for foto in imagenes:
        # Buscar ubicación en el HTML
        pos = content.find(foto)
        
        nombre_final = ""
        codigo_match = ""
        estrategia = "NINGUNA"
        
        if pos != -1:
            # Contexto amplio
            contexto = content[max(0, pos-2500):min(len(content), pos+2500)]
            contexto_limpio = limpiar_basura_canva(contexto)
            
            # 1. BUSCAR CÓDIGOS DEL DICCIONARIO EN EL CONTEXTO
            # Esto es lo más preciso: Si el código "01064001" está cerca, usamos el nombre del diccionario.
            for cod, nom in mapa_codigos.items():
                if cod in contexto_limpio:
                    codigo_match = cod
                    nombre_final = nom
                    estrategia = "MATCH_CODIGO_MAESTRO"
                    break
            
            # 2. SI FALLA, BUSCAR CÓDIGO GENÉRICO (COD. XXXX)
            if not nombre_final:
                match_cod = re.search(r'(?:COD|REF)[\s\.:]+([A-Z0-9\-]{4,12})', contexto_limpio, re.IGNORECASE)
                if match_cod:
                    cod_temp = match_cod.group(1)
                    # Verificar si este código está en el diccionario
                    if cod_temp in mapa_codigos:
                        codigo_match = cod_temp
                        nombre_final = mapa_codigos[cod_temp]
                        estrategia = "MATCH_CODIGO_DETECTADO"
                    else:
                        # Si no está en el diccionario, lo usamos igual pero sin nombre oficial
                        codigo_match = cod_temp
                        estrategia = "CODIGO_NUEVO"

            # 3. BUSCAR NOMBRE GENÉRICO (SI AÚN NO TENEMOS NOMBRE)
            if not nombre_final:
                # Regex mejorado: Excluye SVG paths y basura
                palabras = re.findall(r'\b(?!(?:WIDTH|HEIGHT|RGB|CANVA|HTTP|JPG|PNG|DIV|SPAN|M[0-9]))[A-Z0-9\-\s]{5,50}\b', contexto_limpio)
                validos = [p.strip() for p in palabras if len(p.strip()) > 4 and not re.search(r'[0-9]+-[0-9]+', p) and not p.startswith("M ")]
                
                if validos:
                    nombre_final = max(validos, key=len) # El más largo suele ser la descripción
                    if estrategia == "NINGUNA": estrategia = "NOMBRE_DETECTADO"

        # CONSTRUIR NOMBRE FINAL
        if nombre_final or codigo_match:
            if not nombre_final: nombre_final = f"{categoria}_{codigo_match}"
            
            s_nom = slugify(nombre_final)
            s_cod = slugify(codigo_match) if codigo_match else ""
            
            base = f"{s_nom}-{s_cod}" if s_cod else s_nom
        else:
            # Fallback limpio: Categoria + Hash corto
            h = hashlib.sha1(foto.encode()).hexdigest()[:6]
            base = f"{slugify(categoria)}-revisar-{h}"
            estrategia = "HUERFANA"

        # COPIAR
        ext = os.path.splitext(foto)[1]
        nuevo_archivo = f"{base}{ext}"
        destino = os.path.join(CARPETA_SALIDA_GLOBAL, nuevo_archivo)
        
        # Evitar colisiones
        c = 1
        while os.path.exists(destino):
            nuevo_archivo = f"{base}-{c}{ext}"
            destino = os.path.join(CARPETA_SALIDA_GLOBAL, nuevo_archivo)
            c += 1
            
        try:
            shutil.copy2(os.path.join(ruta_imgs, foto), destino)
            if estrategia != "HUERFANA":
                print(f"   ✅ {estrategia}: {nuevo_archivo}")
            
            datos.append({
                "Codigo": codigo_match,
                "Nombre_Producto": nombre_final,
                "Imagen_Final": nuevo_archivo,
                "Categoria": categoria,
                "Estrategia": estrategia
            })
        except: pass

    return datos

# ================= EJECUCIÓN BATCH =================
def main():
    print("--- MOTOR V10: PROCESAMIENTO INTELIGENTE DFG ---")
    
    mapa_codigos, _ = cargar_diccionario()
    
    archivos = os.listdir(BASE_DIR)
    todos_datos = []
    
    for f in archivos:
        if f.endswith(".html") and f != "PRODUCTOS.html": # Ignorar el menú
            base = os.path.splitext(f)[0]
            # Buscar carpeta _files o _archivos
            if os.path.exists(os.path.join(BASE_DIR, f"{base}_files")):
                datos = procesar_catalogo(f, f"{base}_files", mapa_codigos, [])
                todos_datos.extend(datos)
    
    # Guardar CSV
    if todos_datos:
        df = pd.DataFrame(todos_datos)
        df.to_csv(ARCHIVO_MAESTRO_SALIDA, index=False, encoding='utf-8-sig')
        print("\n" + "="*50)
        print(f"✅ PROCESO COMPLETADO")
        print(f"   Total Imágenes: {len(df)}")
        print(f"   CSV: {ARCHIVO_MAESTRO_SALIDA}")
        print(f"   Carpeta: {CARPETA_SALIDA_GLOBAL}")
        print("="*50)

if __name__ == "__main__":
    main()