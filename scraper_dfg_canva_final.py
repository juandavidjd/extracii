import os
import re
import pandas as pd
import shutil
import unicodedata

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\scrap"
ARCHIVO_HTML = "PRODUCTOS.html"
CARPETA_ORIGEN = "PRODUCTOS_files" # Carpeta local de imágenes
CARPETA_SALIDA = "ACTIVOS_DFG_WEB_CANVA"
ARCHIVO_CSV = "Inventario_DFG_Web_Canva.csv"

ruta_html = os.path.join(BASE_DIR, ARCHIVO_HTML)
ruta_imgs_origen = os.path.join(BASE_DIR, CARPETA_ORIGEN)
ruta_imgs_destino = os.path.join(BASE_DIR, CARPETA_SALIDA)

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
    # Limpiar basura de JSON
    text = text.replace('\\n', ' ').replace('\\', '')
    return " ".join(text.split()).strip()

# ================= MOTOR DE EXTRACCIÓN =================
def procesar_canva_dfg():
    print(f"--- EXTRACCIÓN CANVA DFG: {ARCHIVO_HTML} ---")
    
    if not os.path.exists(ruta_html):
        print("❌ HTML no encontrado.")
        return

    with open(ruta_html, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # 1. Extraer JSON crudo
    match = re.search(r"window\['bootstrap'\]\s*=\s*JSON\.parse\('((?:[^'\\]|\\.)*)'\);", content)
    
    datos_extraidos = []
    
    if match:
        json_str = match.group(1)
        # Extraer todos los textos "A":"VALOR"
        textos = re.findall(r'"A":"([^"]+)"', json_str)
        print(f"🔍 Analizando {len(textos)} fragmentos de texto...")
        
        count = 0
        
        for i, text in enumerate(textos):
            # Buscar patrones de CÓDIGO
            if "COD." in text or "REF." in text:
                codigo_raw = limpiar_texto(text)
                # Extraer solo el número/código
                codigo = re.sub(r'(COD\.|REF\.|\\)', '', codigo_raw).strip()
                
                # Buscar NOMBRE hacia atrás (ventana de 10 items)
                nombre_encontrado = ""
                for j in range(1, 11):
                    if i - j < 0: break
                    cand = limpiar_texto(textos[i-j])
                    
                    # Filtros de calidad para el nombre
                    if len(cand) > 4 and \
                       not cand.startswith("M64") and \
                       "COD." not in cand and \
                       "TAG" not in cand and \
                       "HTTP" not in cand:
                        nombre_encontrado = cand
                        break
                
                if nombre_encontrado:
                    # Guardar registro
                    slug_nom = slugify(nombre_encontrado)
                    slug_cod = slugify(codigo)
                    nombre_archivo = f"{slug_nom}-{slug_cod}.jpg"
                    
                    # Intentar asociar imagen (Difícil en JSON plano, usaremos placeholder por ahora)
                    # O si tienes suerte y el nombre de la imagen está cerca en el HTML, podríamos buscarlo.
                    # Por ahora, guardamos la DATA que es lo más valioso.
                    
                    datos_extraidos.append({
                        "Codigo": codigo,
                        "Nombre": nombre_encontrado,
                        "Nombre_Archivo_Sugerido": nombre_archivo,
                        "Fuente": "DFG_CANVA_JSON"
                    })
                    count += 1
                    # print(f"   + {nombre_encontrado} [{codigo}]")

    # Guardar CSV
    if datos_extraidos:
        df = pd.DataFrame(datos_extraidos)
        df = df.drop_duplicates(subset=['Codigo'])
        df.to_csv(ARCHIVO_CSV, index=False, encoding='utf-8-sig')
        print("\n" + "="*50)
        print(f"✅ MINERÍA DFG COMPLETADA")
        print(f"   Productos Identificados: {len(df)}")
        print(f"   CSV Maestro: {ARCHIVO_CSV}")
        print("="*50)
        print("NOTA: Las imágenes están en la carpeta '_files'.") 
        print("      Usa el CSV para cruzar códigos y renombrarlas manualmente si es necesario.")
    else:
        print("❌ No se encontraron productos.")

if __name__ == "__main__":
    procesar_canva_dfg()