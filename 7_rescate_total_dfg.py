import os
import re
import shutil
import unicodedata
import json

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\scrap"
ARCHIVO_MENU = "PRODUCTOS.html"          # El que tiene la lista de nombres
ARCHIVO_PAGINA = "CARBURADORES.html"     # El que tiene las fotos
CARPETA_FOTOS = "CARBURADORES_files"     # Donde están las fotos hash
CARPETA_FINAL = "ACTIVOS_DFG_CARBURADORES_RESCATADOS"

# Rutas
ruta_menu = os.path.join(BASE_DIR, ARCHIVO_MENU)
ruta_pagina = os.path.join(BASE_DIR, ARCHIVO_PAGINA)
ruta_fotos = os.path.join(BASE_DIR, CARPETA_FOTOS)
ruta_final = os.path.join(BASE_DIR, CARPETA_FINAL)

if os.path.exists(ruta_final): shutil.rmtree(ruta_final)
os.makedirs(ruta_final, exist_ok=True)

# ================= UTILIDADES =================
def slugify(text):
    if not text: return "sin-nombre"
    text = str(text).lower()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')[:100]

def limpiar_texto(text):
    if not text: return ""
    text = text.replace('\\n', ' ').replace('\\"', '"')
    return " ".join(text.split()).strip()

# ================= 1. CREAR DICCIONARIO MAESTRO =================
def crear_diccionario():
    print(f"1. Extrayendo Diccionario Maestro de {ARCHIVO_MENU}...")
    if not os.path.exists(ruta_menu):
        print("❌ No encuentro PRODUCTOS.html")
        return []
    
    with open(ruta_menu, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        
    # Extraer JSON de Canva
    match = re.search(r"window\['bootstrap'\]\s*=\s*JSON\.parse\('((?:[^'\\]|\\.)*)'\);", content)
    diccionario = []
    
    if match:
        json_str = match.group(1)
        # Buscamos pares cercanos de CODIGO y NOMBRE en el JSON crudo
        # Estrategia: Buscar "COD." y tomar el texto anterior como nombre
        
        # Partimos el JSON por comillas para tener una lista de strings
        tokens = re.findall(r'"A":"([^"]+)"', json_str)
        
        for i, token in enumerate(tokens):
            if "COD." in token or "REF." in token:
                codigo = re.sub(r'(COD\.|REF\.|\\)', '', token).strip()
                
                # Buscar nombre hacia atrás (ventana 5)
                nombre = "Desconocido"
                for j in range(1, 6):
                    if i - j < 0: break
                    cand = limpiar_texto(tokens[i-j])
                    if len(cand) > 4 and "COD" not in cand and "HTTP" not in cand:
                        nombre = cand
                        break
                
                if codigo and len(codigo) > 3:
                    diccionario.append({'cod': codigo, 'nom': nombre})
    
    print(f"   -> {len(diccionario)} referencias cargadas en memoria.")
    return diccionario

# ================= 2. CRUZAR CON PÁGINA DE FOTOS =================
def procesar_fotos(diccionario):
    print(f"2. Analizando {ARCHIVO_PAGINA} para rescatar fotos...")
    
    if not os.path.exists(ruta_pagina):
        print("❌ No encuentro CARBURADORES.html")
        return

    with open(ruta_pagina, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        
    if not os.path.exists(ruta_fotos):
        print(f"❌ No existe la carpeta {CARPETA_FOTOS}")
        return

    fotos_fisicas = [f for f in os.listdir(ruta_fotos) if f.lower().endswith(('.jpg','.png'))]
    print(f"   -> {len(fotos_fisicas)} fotos encriptadas encontradas.")
    
    recuperadas = 0
    
    # BARRIDO INTELIGENTE
    for foto in fotos_fisicas:
        # Buscar dónde aparece el nombre del archivo (hash) en el HTML
        # Canva suele ponerlo en src="..." o en JSON escapado
        nombre_regex = re.escape(foto)
        match = re.search(nombre_regex, content)
        
        match_encontrado = None
        
        if match:
            # Extraer contexto (2000 chars alrededor)
            pos = match.start()
            contexto = content[max(0, pos-2000):min(len(content), pos+2000)]
            
            # Limpiar contexto para búsqueda
            contexto_limpio = re.sub(r'<[^>]+>', ' ', contexto)
            
            # A. BUSCAR CÓDIGO DEL DICCIONARIO EN EL CONTEXTO
            for item in diccionario:
                # Buscamos si el código (ej: 014002) aparece cerca de la foto
                if item['cod'] in contexto_limpio:
                    match_encontrado = item
                    break
            
            # B. SI FALLA, BUSCAR PATRÓN DE CÓDIGO SUELTO "COD. XXXX"
            if not match_encontrado:
                match_cod_suelto = re.search(r'(?:COD|REF)[:\.\s]+([A-Z0-9\-]{4,10})', contexto_limpio)
                if match_cod_suelto:
                    cod_suelto = match_cod_suelto.group(1)
                    # Buscar si ese código está en nuestro diccionario para traer el nombre
                    for item in diccionario:
                        if item['cod'] == cod_suelto:
                            match_encontrado = item
                            break
                    # Si no está en diccionario, al menos tenemos el código
                    if not match_encontrado:
                        match_encontrado = {'cod': cod_suelto, 'nom': 'Carburador_DFG'}

        # PROCESAR
        if match_encontrado:
            slug_nom = slugify(match_encontrado['nom'])
            slug_cod = slugify(match_encontrado['cod'])
            ext = os.path.splitext(foto)[1]
            
            nuevo_nombre = f"{slug_nom}-{slug_cod}{ext}"
            
            src = os.path.join(ruta_fotos, foto)
            dst = os.path.join(ruta_final, nuevo_nombre)
            
            # Evitar colisión
            c = 1
            while os.path.exists(dst):
                nuevo_nombre = f"{slug_nom}-{slug_cod}-{c}{ext}"
                dst = os.path.join(ruta_final, nuevo_nombre)
                c += 1
                
            try:
                shutil.copy2(src, dst)
                recuperadas += 1
                print(f"   ✅ [MATCH] {match_encontrado['cod']} -> {nuevo_nombre}")
            except: pass
        else:
            # GUARDAR HUÉRFANAS (Importante no perderlas)
            # Si no encontramos texto, guardamos la foto con un prefijo "revisar"
            # Puede que sea un icono o fondo, pero mejor tenerla que perderla.
            pass # O descomenta abajo para guardar todo
            # nuevo_nombre = f"revisar-{foto}"
            # shutil.copy2(os.path.join(ruta_fotos, foto), os.path.join(ruta_final, nuevo_nombre))

    print("\n" + "="*50)
    print(f"✅ RESCATE TOTAL FINALIZADO")
    print(f"   Imágenes Identificadas: {recuperadas} / {len(fotos_fisicas)}")
    print(f"   Carpeta: {CARPETA_FINAL}")
    print("="*50)

if __name__ == "__main__":
    dic = crear_diccionario()
    if dic:
        procesar_fotos(dic)