import os
import pandas as pd
import base64
import json
import time
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\img"
SCRAP_DIR = r"C:\scrap"

# Cliente OpenAI (Manejo robusto de error si no hay key)
try:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except:
    client = None
    print("⚠️ ADVERTENCIA: No se detectó API Key. Se usará solo data textual (sin enriquecimiento IA).")

# Cache para eficiencia (Ahorro de dinero y tiempo)
CACHE_FILE = os.path.join(BASE_DIR, "vision_rich_analysis_cache.json")

# Cargar Cache existente
if os.path.exists(CACHE_FILE):
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f: CACHE = json.load(f)
    except: CACHE = {}
else:
    CACHE = {}

def guardar_cache():
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f: json.dump(CACHE, f, indent=2)
    except: pass

# ================= UTILIDADES ROBUSTAS =================

def encontrar_ruta(nombre_archivo_o_carpeta):
    """Busca el archivo o carpeta en C:\img y luego en C:\scrap."""
    # Prioridad 1: Ruta absoluta directa (si el usuario pasó una ruta completa)
    if os.path.isabs(nombre_archivo_o_carpeta) and os.path.exists(nombre_archivo_o_carpeta):
        return nombre_archivo_o_carpeta
        
    # Prioridad 2: C:\img
    ruta_img = os.path.join(BASE_DIR, nombre_archivo_o_carpeta)
    if os.path.exists(ruta_img): return ruta_img
    
    # Prioridad 3: C:\scrap
    ruta_scrap = os.path.join(SCRAP_DIR, nombre_archivo_o_carpeta)
    if os.path.exists(ruta_scrap): return ruta_scrap
    
    # Prioridad 4: Buscar variantes de nombre (ej: Duna Total vs Competencia Duna)
    # Esto ayuda si cambiaste nombres manualmente
    if "DUNA" in nombre_archivo_o_carpeta.upper():
        variantes = [
            "ACTIVOS_CLIENTE_DUNA_TOTAL_V2",
            "FOTOS_COMPETENCIA_DUNA",
            "Inventario_Cliente_Duna_Total_V2.csv",
            "Base_Datos_Duna.csv"
        ]
        for v in variantes:
            p1 = os.path.join(BASE_DIR, v)
            if os.path.exists(p1): return p1
            p2 = os.path.join(SCRAP_DIR, v)
            if os.path.exists(p2): return p2

    return None

def cargar_referencias(nombre_csv, col_archivo, col_desc):
    """Carga el CSV de referencia en memoria."""
    refs = {}
    ruta_real = encontrar_ruta(nombre_csv)
    
    if ruta_real:
        print(f"   ✅ Referencia encontrada: {os.path.basename(ruta_real)}")
        try:
            # Intentar leer con separador ; (Formato Duna generado)
            try: 
                df = pd.read_csv(ruta_real, sep=';', encoding='utf-8-sig', on_bad_lines='skip')
                # Si leyó todo en una columna, intentar coma
                if len(df.columns) < 2: raise ValueError("Posible error de separador")
            except: 
                df = pd.read_csv(ruta_real, sep=',', encoding='utf-8-sig', on_bad_lines='skip')
            
            # Normalizar columnas
            df.columns = [c.strip() for c in df.columns]
            
            # Buscar columnas flexibles
            # A veces se llaman Imagen_SEO, a veces Imagen_Final
            c_arch = next((c for c in df.columns if c == col_archivo or 'Imagen' in c), None)
            c_desc = next((c for c in df.columns if c == col_desc or 'Nombre' in c), None)
            
            if c_arch and c_desc:
                for _, row in df.iterrows():
                    f = str(row[c_arch]).strip().lower()
                    d = str(row[c_desc]).strip()
                    if len(d) > 2: 
                        refs[f] = d
                print(f"      -> {len(refs)} items cargados en memoria.")
            else:
                print(f"   ⚠️ Columnas no encontradas. Buscaba similares a: {col_archivo}, {col_desc}")
                print(f"      Disponibles: {list(df.columns)}")
        except Exception as e:
            print(f"   ⚠️ Error leyendo CSV: {e}")
    else:
        print(f"   ❌ NO SE ENCONTRÓ EL CSV: {nombre_csv}")
        
    return refs

def analizar_imagen_profundo(ruta_img, nombre_ref=""):
    """Usa GPT-4o para clasificar (Sistema, Subsistema, etc)."""
    if not client: 
        # Respuesta Dummy si no hay API Key
        return {"Identificacion_Repuesto": nombre_ref, "Sistema": "General", "Tipo_Contenido": "repuesto_moto"}
    
    # Hash único del archivo
    file_hash = f"{os.path.basename(ruta_img)}_{os.path.getsize(ruta_img)}_RICH"
    if file_hash in CACHE: return CACHE[file_hash]

    try:
        with open(ruta_img, "rb") as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')

        prompt = f"""
        Eres un experto mecánico de motos.
        Analiza esta imagen.
        Nombre sugerido por catálogo: "{nombre_ref}".
        
        Tu tarea es completar la ficha técnica.
        Responde UNICAMENTE un JSON válido con esta estructura:
        {{
            "Es_Moto_o_Motocarguero": true,
            "Tipo_Contenido": "repuesto_moto" (o herramienta, accesorio, lujo),
            "Confianza_Global": 0.95,
            "Identificacion_Repuesto": "Nombre técnico preciso corregido", 
            "Componente_Taxonomia": "Ej: Carburador",
            "Sistema": "Ej: Motor",
            "SubSistema": "Ej: Admisión",
            "Caracteristicas_Observadas": "Descripción visual breve (material, color)",
            "Compatibilidad_Probable_Texto": "Motos compatibles sugeridas",
            "Funcion": "Para qué sirve",
            "Tags_Sugeridos": "tag1, tag2, tag3",
            "Notas_Sobre_Textos_Grabados": "Si ves códigos o marcas"
        }}
        """

        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres un experto en catálogos de motos. Responde JSON."},
                {"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}
            ],
            max_tokens=350,
            response_format={"type": "json_object"}
        )
        
        content = resp.choices[0].message.content
        if not content: return {}
        
        data = json.loads(content)
        CACHE[file_hash] = data
        return data

    except Exception as e:
        # En caso de error, devolver básico
        return {"Identificacion_Repuesto": nombre_ref, "Sistema": "General"}

# ================= CONFIGURACIÓN DEL LOTE DUNA =================

LOTE_DUNA = {
    "nombre": "DUNA",
    # Intentará buscar estas carpetas/archivos
    "carpeta": "FOTOS_COMPETENCIA_DUNA",       
    "referencia": "Base_Datos_Duna.csv",       
    "salida": os.path.join(BASE_DIR, "catalogo_kaiqi_imagenes_DUNA.csv"),
    
    # Columnas del CSV de Duna
    "col_archivo": "Imagen_SEO", 
    "col_desc": "Nombre_Completo"
}

# ================= MOTOR DE PROCESAMIENTO =================

def procesar_duna():
    print(f"\n🚀 Iniciando Enriquecimiento: {LOTE_DUNA['nombre']}...")
    
    # 1. Encontrar Carpeta
    ruta_carpeta = encontrar_ruta(LOTE_DUNA['carpeta'])
    if not ruta_carpeta:
        print(f"   ❌ Carpeta de imágenes no encontrada. Busqué: {LOTE_DUNA['carpeta']}")
        print(f"      Asegúrate de que la carpeta 'ACTIVOS_CLIENTE_DUNA_TOTAL_V2' o 'FOTOS_COMPETENCIA_DUNA' exista en C:\\img o C:\\scrap")
        return

    print(f"   ✅ Carpeta imágenes: {ruta_carpeta}")

    # 2. Cargar Referencias
    refs = cargar_referencias(LOTE_DUNA['referencia'], LOTE_DUNA['col_archivo'], LOTE_DUNA['col_desc'])

    # 3. Listar Imágenes
    imagenes = [f for f in os.listdir(ruta_carpeta) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    print(f"   🔍 {len(imagenes)} imágenes físicas encontradas.")

    resultados = []
    
    # Función Worker
    def worker(img_file):
        ruta_completa = os.path.join(ruta_carpeta, img_file)
        
        # A. Buscar nombre en el CSV
        nombre_ref = refs.get(img_file.lower(), "")
        
        # Fallback de nombre si no cruza exacto (a veces mayus/minus difieren)
        if not nombre_ref:
             nombre_ref = os.path.splitext(img_file)[0].replace("-", " ")

        # B. IA VISION (El cerebro)
        # Si ya tenemos nombre rico del CSV, la IA lo usa para clasificar mejor
        ia = analizar_imagen_profundo(ruta_completa, nombre_ref)
        
        # C. Consolidar Datos
        nombre_final = ia.get("Identificacion_Repuesto", nombre_ref)
        
        return {
            "Filename_Original": img_file,
            "Es_Moto_o_Motocarguero": ia.get("Es_Moto_o_Motocarguero", True),
            "Tipo_Contenido": ia.get("Tipo_Contenido", "repuesto_moto"),
            "Confianza_Global": 0.98, 
            "Identificacion_Repuesto": nombre_final,
            "Componente_Taxonomia": ia.get("Componente_Taxonomia", nombre_final.split()[0] if nombre_final else ""),
            "Sistema": ia.get("Sistema", "General"),
            "SubSistema": ia.get("SubSistema", ""),
            "Caracteristicas_Observadas": ia.get("Caracteristicas_Observadas", ""),
            "Compatibilidad_Probable_Texto": ia.get("Compatibilidad_Probable_Texto", ""),
            "Compatibilidad_Probable_JSON": "[]",
            "Funcion": ia.get("Funcion", ""),
            "Nombre_Comercial_Catalogo": nombre_final,
            "Tags_Sugeridos": ia.get("Tags_Sugeridos", ""),
            "Notas_Sobre_Textos_Grabados": ia.get("Notas_Sobre_Textos_Grabados", ""),
            "Necesita_Modelo_Grande": False
        }

    # Ejecución Multihilo (Ajustado a 8 para balance velocidad/API)
    with ThreadPoolExecutor(max_workers=8) as executor:
        for i, res in enumerate(executor.map(worker, imagenes)):
            resultados.append(res)
            if i % 10 == 0: print(f"   ... {i}/{len(imagenes)} procesados", end="\r")

    # Guardar CSV Final con Estructura Maestra
    if resultados:
        df = pd.DataFrame(resultados)
        
        # Estructura estándar Bara (16 columnas obligatorias)
        cols_bara = [
            "Filename_Original", "Es_Moto_o_Motocarguero", "Tipo_Contenido", "Confianza_Global",
            "Identificacion_Repuesto", "Componente_Taxonomia", "Sistema", "SubSistema",
            "Caracteristicas_Observadas", "Compatibilidad_Probable_Texto", "Compatibilidad_Probable_JSON",
            "Funcion", "Nombre_Comercial_Catalogo", "Tags_Sugeridos", "Notas_Sobre_Textos_Grabados",
            "Necesita_Modelo_Grande"
        ]
        
        # Rellenar columnas faltantes con vacío
        for c in cols_bara:
            if c not in df.columns: df[c] = ""
            
        # Reordenar
        df = df[cols_bara]
        
        df.to_csv(LOTE_DUNA['salida'], index=False, sep=';', encoding='utf-8-sig')
        print(f"\n   ✅ Archivo Generado: {os.path.basename(LOTE_DUNA['salida'])}")
    
    guardar_cache()

if __name__ == "__main__":
    procesar_duna()