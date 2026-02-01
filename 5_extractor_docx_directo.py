import os
import zipfile
import xml.etree.ElementTree as ET
import shutil
import re
import unicodedata

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\scrap"
ARCHIVO_DOCX = "CATALOGO NOVIEMBRE V01-2025 NF.docx"

# Salidas
CARPETA_SALIDA = os.path.join(BASE_DIR, "ACTIVOS_CLIENTE_NF_DOCX_FULL")
ARCHIVO_CSV = os.path.join(BASE_DIR, "Inventario_Cliente_NF_Docx.csv")

ruta_docx = os.path.join(BASE_DIR, ARCHIVO_DOCX)

if os.path.exists(CARPETA_SALIDA): shutil.rmtree(CARPETA_SALIDA)
os.makedirs(CARPETA_SALIDA, exist_ok=True)

# Espacios de nombres XML de Word (necesarios para encontrar las etiquetas)
NS = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
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
    return " ".join(text.split()).strip()

# ================= MOTOR DE EXTRACCIÓN =================
def procesar_docx():
    print(f"--- DECONSTRUYENDO DOCX: {ARCHIVO_DOCX} ---")
    
    if not os.path.exists(ruta_docx):
        print("❌ Archivo DOCX no encontrado.")
        return

    datos_extraidos = []
    
    # 1. Abrir el DOCX como ZIP
    with zipfile.ZipFile(ruta_docx, 'r') as z:
        # A. Leer el mapa de relaciones (rId -> Archivo de imagen)
        xml_rels = z.read('word/_rels/document.xml.rels')
        tree_rels = ET.fromstring(xml_rels)
        
        mapa_imagenes = {} # rId: media/image1.jpeg
        for rel in tree_rels.findall('{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
            if 'image' in rel.get('Type'):
                mapa_imagenes[rel.get('Id')] = rel.get('Target')
        
        print(f"📋 Mapa de relaciones creado: {len(mapa_imagenes)} imágenes vinculadas.")

        # B. Leer el contenido del documento
        xml_doc = z.read('word/document.xml')
        tree_doc = ET.fromstring(xml_doc)
        
        # C. Recorrer el documento buscando Párrafos (P)
        # Estrategia: Guardar el último texto visto para asignarlo a la siguiente imagen
        ultimo_texto_valido = ""
        count = 0
        
        # Iteramos sobre todos los párrafos <w:p>
        for p in tree_doc.iter(f"{{{NS['w']}}}p"):
            # 1. Extraer texto del párrafo
            textos = [node.text for node in p.iter(f"{{{NS['w']}}}t") if node.text]
            texto_parrafo = limpiar_texto(" ".join(textos))
            
            # Si el párrafo tiene texto sustancial, lo guardamos como "buffer"
            if len(texto_parrafo) > 5 and not texto_parrafo.isdigit():
                ultimo_texto_valido = texto_parrafo
            
            # 2. Buscar imágenes dentro del párrafo <w:drawing> o <w:pict>
            # Las imágenes se referencian por el 'r:embed' (el rId)
            for blip in p.iter(f"{{{NS['a']}}}blip"):
                rId = blip.get(f"{{{NS['r']}}}embed")
                
                if rId in mapa_imagenes:
                    ruta_interna = mapa_imagenes[rId] # ej: media/image1.jpeg
                    # La ruta interna suele ser relativa "media/...", en el zip es "word/media/..."
                    ruta_zip = f"word/{ruta_interna}"
                    
                    nombre_original = os.path.basename(ruta_interna)
                    
                    # ASOCIACIÓN: Usamos el último texto visto como nombre
                    if ultimo_texto_valido:
                        slug_nombre = slugify(ultimo_texto_valido)
                        ext = os.path.splitext(nombre_original)[1]
                        if not ext: ext = ".jpg" # Fallback
                        
                        nuevo_nombre = f"{slug_nombre}{ext}"
                        
                        # Extraer del ZIP y guardar en disco
                        source = z.open(ruta_zip)
                        target_path = os.path.join(CARPETA_SALIDA, nuevo_nombre)
                        
                        # Evitar sobreescritura simple
                        if os.path.exists(target_path):
                            nuevo_nombre = f"{slug_nombre}-{count}{ext}"
                            target_path = os.path.join(CARPETA_SALIDA, nuevo_nombre)

                        with open(target_path, "wb") as f:
                            shutil.copyfileobj(source, f)
                        
                        datos_extraidos.append({
                            "Descripcion": ultimo_texto_valido,
                            "Imagen_Original": nombre_original,
                            "Imagen_Final": nuevo_nombre,
                            "Fuente": "DOCX_DIRECTO"
                        })
                        
                        count += 1
                        # print(f"   + {nuevo_nombre}")

    # Guardar CSV
    if datos_extraidos:
        import pandas as pd
        df = pd.DataFrame(datos_extraidos)
        df.to_csv(ARCHIVO_CSV, index=False, encoding='utf-8-sig')
        
        print("\n" + "="*50)
        print(f"✅ EXTRACCIÓN DE ALTA FIDELIDAD COMPLETADA")
        print(f"   Activos Originales: {count}")
        print(f"   CSV: {ARCHIVO_CSV}")
        print(f"   Carpeta: {CARPETA_SALIDA}")
        print("="*50)
    else:
        print("⚠️ No se encontraron asociaciones imagen-texto.")

if __name__ == "__main__":
    procesar_docx()