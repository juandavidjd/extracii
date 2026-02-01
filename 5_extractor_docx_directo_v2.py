import os
import zipfile
import xml.etree.ElementTree as ET
import shutil
import re
import unicodedata
import csv
import pandas as pd

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\scrap"
ARCHIVO_DOCX = "CATALOGO NOVIEMBRE V01-2025 NF.docx"

# Salidas
CARPETA_SALIDA = os.path.join(BASE_DIR, "ACTIVOS_CLIENTE_NF_DOCX_FULL")
ARCHIVO_CSV = os.path.join(BASE_DIR, "Inventario_Cliente_NF_Docx_Mejorado.csv")

ruta_docx = os.path.join(BASE_DIR, ARCHIVO_DOCX)

if os.path.exists(CARPETA_SALIDA): shutil.rmtree(CARPETA_SALIDA)
os.makedirs(CARPETA_SALIDA, exist_ok=True)

# Espacios de nombres XML de Word
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

def limpiar_texto_seguro(text):
    if not text: return ""
    # Reemplaza saltos de línea y tabulaciones por espacios simples
    text = text.replace('\n', ' ').replace('\r', '').replace('\t', ' ')
    # Elimina espacios múltiples
    return " ".join(text.split()).strip()

# ================= MOTOR DE EXTRACCIÓN =================
def procesar_docx():
    print(f"--- DECONSTRUYENDO DOCX (MODO SEGURO): {ARCHIVO_DOCX} ---")
    
    if not os.path.exists(ruta_docx):
        print("❌ Archivo DOCX no encontrado.")
        return

    datos_extraidos = []
    
    with zipfile.ZipFile(ruta_docx, 'r') as z:
        # A. Mapa de relaciones
        try:
            xml_rels = z.read('word/_rels/document.xml.rels')
            tree_rels = ET.fromstring(xml_rels)
            mapa_imagenes = {} 
            for rel in tree_rels.findall('{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
                if 'image' in rel.get('Type'):
                    mapa_imagenes[rel.get('Id')] = rel.get('Target')
            print(f"📋 Mapa de relaciones creado: {len(mapa_imagenes)} imágenes.")
        except:
            print("❌ Error leyendo relaciones del DOCX.")
            return

        # B. Leer documento
        xml_doc = z.read('word/document.xml')
        tree_doc = ET.fromstring(xml_doc)
        
        ultimo_texto_valido = ""
        count = 0
        
        # C. Iterar párrafos
        for p in tree_doc.iter(f"{{{NS['w']}}}p"):
            # 1. Extraer texto
            textos = [node.text for node in p.iter(f"{{{NS['w']}}}t") if node.text]
            texto_parrafo = limpiar_texto_seguro(" ".join(textos))
            
            if len(texto_parrafo) > 5 and not texto_parrafo.isdigit():
                ultimo_texto_valido = texto_parrafo
            
            # 2. Buscar imágenes
            for blip in p.iter(f"{{{NS['a']}}}blip"):
                rId = blip.get(f"{{{NS['r']}}}embed")
                
                if rId in mapa_imagenes:
                    ruta_interna = mapa_imagenes[rId]
                    ruta_zip = f"word/{ruta_interna}"
                    nombre_original = os.path.basename(ruta_interna)
                    
                    if ultimo_texto_valido:
                        slug_nombre = slugify(ultimo_texto_valido)
                        ext = os.path.splitext(nombre_original)[1]
                        if not ext: ext = ".jpg"
                        
                        nuevo_nombre = f"{slug_nombre}{ext}"
                        target_path = os.path.join(CARPETA_SALIDA, nuevo_nombre)
                        
                        # Evitar colisiones
                        if os.path.exists(target_path):
                            nuevo_nombre = f"{slug_nombre}-{count}{ext}"
                            target_path = os.path.join(CARPETA_SALIDA, nuevo_nombre)

                        # Extraer
                        try:
                            with z.open(ruta_zip) as source, open(target_path, "wb") as f:
                                shutil.copyfileobj(source, f)
                            
                            datos_extraidos.append({
                                "Descripcion": ultimo_texto_valido,
                                "Imagen_Original": nombre_original,
                                "Imagen_Final": nuevo_nombre,
                                "Fuente": "DOCX_V2_SEGURO"
                            })
                            count += 1
                        except: pass

    # Guardar CSV Robusto
    if datos_extraidos:
        df = pd.DataFrame(datos_extraidos)
        
        # Limpieza final de seguridad en la columna descripción
        df['Descripcion'] = df['Descripcion'].apply(limpiar_texto_seguro)
        
        # GUARDADO MAESTRO:
        # sep=';' -> Para que Excel abra las columnas bien.
        # quotechar='"' -> Para proteger los textos que tengan ; o , adentro.
        # quoting=csv.QUOTE_ALL -> Fuerza comillas en TODO para evitar errores.
        df.to_csv(ARCHIVO_CSV, index=False, sep=';', quotechar='"', quoting=csv.QUOTE_ALL, encoding='utf-8-sig')
        
        print("\n" + "="*50)
        print(f"✅ EXTRACCIÓN MEJORADA COMPLETADA")
        print(f"   Activos: {count}")
        print(f"   CSV Seguro: {ARCHIVO_CSV}")
        print("="*50)
    else:
        print("⚠️ No se encontraron datos.")

if __name__ == "__main__":
    procesar_docx()