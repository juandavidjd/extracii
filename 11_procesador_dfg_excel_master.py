import os
import re
import shutil
import unicodedata
import hashlib
import pandas as pd

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\scrap"
# Ruta al Excel Maestro de DFG (Asegúrate que esté aquí o cambia la ruta)
ARCHIVO_EXCEL_MAESTRO = os.path.join(r"C:\img", "DFGMOTOS.xlsx") 

# Salida
CARPETA_SALIDA_GLOBAL = os.path.join(BASE_DIR, "ACTIVOS_DFG_FINAL_EXCEL")
ARCHIVO_REPORTE = os.path.join(BASE_DIR, "Reporte_DFG_Excel_Match.csv")

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
    if re.match(r'^[M0-9\sLHVZ\-,]+$', t, re.IGNORECASE): return "" 
    return " ".join(t.split()).strip()

def limpiar_codigo_para_match(codigo):
    # Quita puntos, espacios y ceros a la izquierda para mejorar el cruce
    # Ej: "010919" -> "10919", "D-123" -> "D123"
    c = str(codigo).upper().replace('.', '').replace('-', '').replace(' ', '').strip()
    return c

# ================= 1. CARGAR CEREBRO (EXCEL) =================
def cargar_excel_maestro():
    print(f"📚 Cargando Maestro: {ARCHIVO_EXCEL_MAESTRO}")
    if not os.path.exists(ARCHIVO_EXCEL_MAESTRO):
        print(f"   ❌ No encuentro el archivo {ARCHIVO_EXCEL_MAESTRO}")
        # Intento buscar en C:\scrap por si acaso
        alt_path = os.path.join(BASE_DIR, "DFGMOTOS.xlsx")
        if os.path.exists(alt_path):
            print(f"   ✅ Encontrado en {alt_path}")
            return cargar_df(alt_path)
        return {}
    
    return cargar_df(ARCHIVO_EXCEL_MAESTRO)

def cargar_df(path):
    try:
        # Intentar leer Excel
        df = pd.read_excel(path)
        # Normalizar columnas
        df.columns = [c.strip().upper() for c in df.columns]
        
        mapa = {}
        count = 0
        
        # Buscar columnas clave
        col_cod = next((c for c in df.columns if 'CODIGO' in c), None)
        col_desc = next((c for c in df.columns if 'DESCRIPCION' in c), None)
        
        if col_cod and col_desc:
            for _, row in df.iterrows():
                cod_orig = str(row[col_cod]).strip()
                desc = str(row[col_desc]).strip()
                
                # Guardar varias versiones del código para asegurar match
                # 1. Código exacto
                mapa[cod_orig] = desc
                # 2. Código limpio (sin guiones/puntos)
                mapa[limpiar_codigo_para_match(cod_orig)] = desc
                
                count += 1
        
        print(f"   -> {count} referencias cargadas del Excel.")
        return mapa
    except Exception as e:
        print(f"   ❌ Error leyendo Excel: {e}")
        return {}

# ================= MOTOR DE PROCESAMIENTO =================
def procesar_catalogo(archivo_html, carpeta_origen, diccionario_excel):
    print(f"\n>>> Procesando: {archivo_html}...")
    
    ruta_html = os.path.join(BASE_DIR, archivo_html)
    ruta_imgs = os.path.join(BASE_DIR, carpeta_origen)
    
    try:
        with open(ruta_html, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except: return []

    if not os.path.exists(ruta_imgs): return []
    
    imagenes = [f for f in os.listdir(ruta_imgs) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    datos = []
    
    for foto in imagenes:
        pos = content.find(foto)
        
        nombre_final = ""
        codigo_encontrado = ""
        estrategia = "NINGUNA"
        
        if pos != -1:
            # Contexto
            contexto = content[max(0, pos-3000):min(len(content), pos+3000)]
            contexto_limpio = limpiar_basura_canva(contexto)
            
            # 1. BUSCAR CÓDIGO (COD. XXXX o REF. XXXX o solo numeros largos)
            # Regex flexible para capturar códigos DFG
            # Ejemplos DFG: 010919, 370381..., D-123
            matches_cod = re.findall(r'(?:COD|REF)[\s\.:]*([A-Z0-9\-]{4,15})', contexto_limpio, re.IGNORECASE)
            
            # También buscar números de 6+ dígitos aislados (común en DFG)
            matches_num = re.findall(r'(?<!\d)(\d{6,10})(?!\d)', contexto_limpio)
            
            candidatos_codigo = matches_cod + matches_num
            
            # 2. VALIDAR CONTRA EXCEL
            for cand in candidatos_codigo:
                # Probar exacto
                if cand in diccionario_excel:
                    codigo_encontrado = cand
                    nombre_final = diccionario_excel[cand]
                    estrategia = "MATCH_EXCEL_EXACTO"
                    break
                
                # Probar limpio
                cand_limpio = limpiar_codigo_para_match(cand)
                if cand_limpio in diccionario_excel:
                    codigo_encontrado = cand # Usamos el encontrado en HTML para referencia
                    nombre_final = diccionario_excel[cand_limpio]
                    estrategia = "MATCH_EXCEL_LIMPIO"
                    break
            
            # 3. SI FALLA EL EXCEL, BUSCAR TEXTO VISUAL (Plan B)
            if not nombre_final:
                # Buscar palabras mayúsculas cercanas
                palabras = re.findall(r'\b(?!(?:WIDTH|HEIGHT|RGB|CANVA|HTTP|JPG|PNG))[A-Z0-9\-\s]{5,50}\b', contexto_limpio)
                candidatos_texto = [p.strip() for p in palabras if len(p.strip()) > 5 and not p.strip().isdigit()]
                if candidatos_texto:
                    nombre_final = max(candidatos_texto, key=len)
                    estrategia = "SOLO_TEXTO_DETECTADO"
                    # Si encontramos un código huérfano antes, lo usamos
                    if candidatos_codigo:
                        codigo_encontrado = candidatos_codigo[0]

        # CONSTRUIR NOMBRE
        if nombre_final:
            s_nom = slugify(nombre_final)
            s_cod = slugify(codigo_encontrado) if codigo_encontrado else ""
            
            base = f"{s_nom}-{s_cod}" if s_cod else s_nom
            
            # Limpieza final: si el nombre empieza con el hash original, está mal.
            if base.startswith(foto[:10]): 
                base = f"revisar-{base}" # Marca visual de error
        else:
            # Fallback: No perder la foto
            h = hashlib.sha1(foto.encode()).hexdigest()[:6]
            base = f"sin-datos-{slugify(archivo_html)}-{h}"
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
                print(f"   ✅ {nuevo_archivo}")
            
            datos.append({
                "Archivo_HTML": archivo_html,
                "Codigo_Detectado": codigo_encontrado,
                "Nombre_Asignado": nombre_final,
                "Imagen_Final": nuevo_archivo,
                "Estrategia": estrategia
            })
        except: pass

    return datos

# ================= EJECUCIÓN =================
def main():
    print("--- MOTOR V11: PROCESAMIENTO CON MAESTRO EXCEL ---")
    
    diccionario_excel = cargar_excel_maestro()
    if not diccionario_excel:
        print("⚠️ Advertencia: Procesando SIN Excel Maestro (Solo heurística visual).")
    
    archivos = os.listdir(BASE_DIR)
    todos_datos = []
    
    for f in archivos:
        if f.endswith(".html") and f != "PRODUCTOS.html":
            base = os.path.splitext(f)[0]
            if os.path.exists(os.path.join(BASE_DIR, f"{base}_files")):
                datos = procesar_catalogo(f, f"{base}_files", diccionario_excel)
                todos_datos.extend(datos)
    
    if todos_datos:
        df = pd.DataFrame(todos_datos)
        df.to_csv(ARCHIVO_REPORTE, index=False, encoding='utf-8-sig')
        print(f"\n✅ PROCESO COMPLETADO. Reporte: {ARCHIVO_REPORTE}")

if __name__ == "__main__":
    main()