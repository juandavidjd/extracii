import os
import re
import shutil
import pandas as pd
import unicodedata

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\scrap"
ARCHIVO_CANVA_HTML = "CARBURADORES.html"  # Cambia esto por el archivo que bajes (ej. AMORTIGUADORES.html)
CARPETA_ORIGEN = "CARBURADORES_files"     # La carpeta que acompaña al HTML
CARPETA_DESTINO = "ACTIVOS_DFG_CONSOLIDADOS"

ARCHIVO_MAESTRO_DFG = "Inventario_DFG_Web_Canva.csv" # La lista de 358 que acabamos de sacar

# Rutas
ruta_html = os.path.join(BASE_DIR, ARCHIVO_CANVA_HTML)
ruta_imgs_origen = os.path.join(BASE_DIR, CARPETA_ORIGEN)
ruta_imgs_destino = os.path.join(BASE_DIR, CARPETA_DESTINO)
ruta_maestro = os.path.join(BASE_DIR, ARCHIVO_MAESTRO_DFG)

if not os.path.exists(ruta_imgs_destino):
    os.makedirs(ruta_imgs_destino)

# ================= UTILIDADES =================
def slugify(text):
    if not text: return "sin-nombre"
    text = str(text).lower()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')[:100]

def cargar_diccionario_dfg():
    """Carga los 358 productos conocidos para buscarlos en el HTML."""
    if not os.path.exists(ruta_maestro):
        print("⚠️ No se encontró el CSV maestro de DFG.")
        return []
    
    try:
        df = pd.read_csv(ruta_maestro)
        # Crear lista de tuplas (Codigo, Nombre)
        # Limpiamos para asegurar coincidencia
        lista = []
        for _, row in df.iterrows():
            cod = str(row['Codigo']).strip()
            nom = str(row['Nombre']).strip()
            lista.append({'cod': cod, 'nom': nom})
        return lista
    except:
        return []

# ================= MOTOR DE CRUCE =================
def procesar_canva_inteligente():
    print(f"--- CRUZANDO DATA CON HTML: {ARCHIVO_CANVA_HTML} ---")
    
    # 1. Cargar Conocimiento (Los 358 productos)
    diccionario = cargar_diccionario_dfg()
    print(f"📚 Diccionario cargado: {len(diccionario)} referencias conocidas.")

    if not os.path.exists(ruta_html):
        print("❌ HTML no encontrado.")
        return

    # 2. Leer HTML Sucio
    with open(ruta_html, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    if not os.path.exists(ruta_imgs_origen):
        print(f"❌ Carpeta de imágenes no encontrada: {CARPETA_ORIGEN}")
        return

    imagenes_fisicas = [f for f in os.listdir(ruta_imgs_origen) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    print(f"🔍 Imágenes en carpeta local: {len(imagenes_fisicas)}")
    
    recuperadas = 0
    
    # 3. El Gran Barrido
    for imagen_archivo in imagenes_fisicas:
        # Buscar dónde está esta imagen en el HTML
        nombre_regex = re.escape(imagen_archivo)
        match = re.search(nombre_regex, content)
        
        producto_identificado = None
        
        if match:
            # Extraer contexto (1000 caracteres alrededor de la imagen)
            pos = match.start()
            contexto = content[max(0, pos-1000):min(len(content), pos+1000)]
            
            # Buscar si ALGUN código o nombre del diccionario aparece en este contexto
            # Priorizamos búsqueda por CÓDIGO (es más exacto)
            
            for item in diccionario:
                # Buscamos el código exacto
                if item['cod'] in contexto:
                    producto_identificado = item
                    break
            
            # Si no encontró por código, intentar por Nombre (si es largo y único)
            if not producto_identificado:
                for item in diccionario:
                    if len(item['nom']) > 10 and item['nom'] in contexto:
                        producto_identificado = item
                        break
        
        # 4. Resultado
        if producto_identificado:
            # Tenemos Match!
            nombre_rico = producto_identificado['nom']
            codigo = producto_identificado['cod']
            
            slug_nom = slugify(nombre_rico)
            slug_cod = slugify(codigo)
            ext = os.path.splitext(imagen_archivo)[1]
            
            nuevo_nombre = f"{slug_nom}-{slug_cod}{ext}"
            
            # Copiar y Renombrar
            origen = os.path.join(ruta_imgs_origen, imagen_archivo)
            destino = os.path.join(ruta_imgs_destino, nuevo_nombre)
            
            # Evitar duplicados
            if not os.path.exists(destino):
                try:
                    shutil.copy2(origen, destino)
                    print(f"   ✅ [MATCH] {codigo} -> {nuevo_nombre}")
                    recuperadas += 1
                except: pass
        else:
            # Opcional: Guardar las no identificadas en una carpeta "REVISAR"
            # print(f"   Build warning: No se identificó texto para {imagen_archivo}")
            pass

    print("\n" + "="*50)
    print(f"✅ PROCESO INTELIGENTE FINALIZADO")
    print(f"   Imágenes Rescatadas: {recuperadas} / {len(imagenes_fisicas)}")
    print(f"   Carpeta Final: {CARPETA_DESTINO}")
    print("="*50)
    print("💡 Consejo: Repite este proceso con cada página que descargues (Amortiguadores, etc.)")
    print("   Solo cambia el nombre del ARCHIVO_HTML y la CARPETA_ORIGEN en el script.")

if __name__ == "__main__":
    procesar_canva_inteligente()