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

try:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except:
    client = None

CACHE_FILE = os.path.join(BASE_DIR, "vision_rich_analysis_cache.json")
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

# ================= UTILIDADES =================

def encontrar_ruta(nombre):
    rutas = [os.path.join(BASE_DIR, nombre), os.path.join(SCRAP_DIR, nombre)]
    for r in rutas:
        if os.path.exists(r): return r
    return None

def cargar_referencias_completas(nombre_csv, col_archivo, col_nombre, col_sku):
    """Carga Nombre y SKU para no perder el código real."""
    refs = {}
    ruta_real = encontrar_ruta(nombre_csv)
    
    if ruta_real:
        print(f"   ✅ Referencia maestra: {os.path.basename(ruta_real)}")
        try:
            try: 
                df = pd.read_csv(ruta_real, sep=';', encoding='utf-8-sig', on_bad_lines='skip')
            except: 
                df = pd.read_csv(ruta_real, sep=',', encoding='utf-8-sig', on_bad_lines='skip')
            
            df.columns = [c.strip() for c in df.columns]
            
            # Validar columnas
            # Flexibilidad con el nombre de la columna de imagen
            col_img_real = col_archivo
            if col_archivo not in df.columns:
                # Buscar alternativa común
                alternativas = ['Imagen_SEO', 'Imagen_Final', 'Filename']
                for alt in alternativas:
                    if alt in df.columns:
                        col_img_real = alt
                        break

            if col_img_real in df.columns:
                for _, row in df.iterrows():
                    f = str(row[col_img_real]).strip().lower()
                    
                    # Construir nombre rico oficial
                    nom = str(row[col_nombre]).strip() if col_nombre in df.columns else ""
                    sku = str(row[col_sku]).strip() if col_sku in df.columns else ""
                    
                    # Si el SKU es valido, lo forzamos en el nombre si no está
                    nombre_final = nom
                    if sku and sku not in nom and sku != "nan":
                        nombre_final = f"{nom} {sku}"
                    
                    refs[f] = {
                        "nombre_real": nombre_final,
                        "sku_real": sku if sku != "nan" else ""
                    }
                print(f"      -> {len(refs)} productos maestros cargados.")
            else:
                print(f"   ⚠️ Columna de imagen '{col_archivo}' no encontrada en CSV.")
                print(f"      Columnas disponibles: {list(df.columns)}")
        except Exception as e:
            print(f"   ⚠️ Error CSV: {e}")
    else:
        print(f"   ❌ No encuentro el archivo: {nombre_csv}")
        
    return refs

def analizar_imagen_solo_clasificacion(ruta_img, nombre_ref):
    """Usa IA SOLO para clasificar (Sistema/Subsistema), NO para renombrar."""
    if not client: 
        return {"Sistema": "General", "Tipo_Contenido": "repuesto_moto", "Componente_Taxonomia": "Repuesto"}
    
    file_hash = f"{os.path.basename(ruta_img)}_{os.path.getsize(ruta_img)}_CLASS_ONLY"
    if file_hash in CACHE: return CACHE[file_hash]

    try:
        with open(ruta_img, "rb") as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')

        prompt = f"""
        Analiza este repuesto: "{nombre_ref}".
        NO cambies el nombre. Solo clasifícalo.
        Responde JSON:
        {{
            "Es_Moto_o_Motocarguero": true,
            "Tipo_Contenido": "repuesto_moto",
            "Componente_Taxonomia": "Ej: Bombillo",
            "Sistema": "Ej: Eléctrico",
            "SubSistema": "Ej: Iluminación",
            "Tags_Sugeridos": "tag1, tag2"
        }}
        """

        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres experto en taxonomía de repuestos. Responde JSON."},
                {"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}
            ],
            max_tokens=200,
            response_format={"type": "json_object"}
        )
        
        data = json.loads(resp.choices[0].message.content)
        CACHE[file_hash] = data
        return data

    except: 
        return {"Sistema": "General", "Tipo_Contenido": "repuesto_moto"}

# ================= CONFIGURACIÓN DUNA =================

LOTE_DUNA = {
    "nombre": "DUNA",
    "carpeta": "FOTOS_COMPETENCIA_DUNA",
    "referencia": "Base_Datos_Duna.csv", 
    "salida": os.path.join(BASE_DIR, "catalogo_kaiqi_imagenes_DUNA.csv"),
    
    # Columnas Clave
    "col_archivo": "Imagen_SEO", 
    "col_nombre": "Nombre_Producto",
    "col_sku": "Referencia_Real"
}

# ================= MOTOR =================

def procesar_duna_fix():
    print(f"\n🚀 Procesando DUNA (SKU PROTEGIDO)...")
    
    ruta_carpeta = encontrar_ruta(LOTE_DUNA['carpeta'])
    if not ruta_carpeta:
        print("❌ Carpeta de fotos no encontrada.")
        return

    # Cargar referencias completas (CORREGIDO)
    refs = cargar_referencias_completas(LOTE_DUNA['referencia'], LOTE_DUNA['col_archivo'], LOTE_DUNA['col_nombre'], LOTE_DUNA['col_sku'])
    
    if not refs:
        print("⚠️ No se pudieron cargar referencias. Abortando para no dañar datos.")
        return

    imagenes = [f for f in os.listdir(ruta_carpeta) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    print(f"   🔍 Imágenes físicas: {len(imagenes)}")

    resultados = []
    
    def worker(img_file):
        ruta_completa = os.path.join(ruta_carpeta, img_file)
        
        # 1. Obtener Datos Reales (Sin IA)
        datos_maestros = refs.get(img_file.lower())
        
        nombre_final = ""
        sku_real = ""
        
        if datos_maestros:
            nombre_final = datos_maestros['nombre_real']
            sku_real = datos_maestros['sku_real']
        else:
            # Fallback: Si la imagen no está en el CSV, usamos el nombre del archivo limpio
            nombre_final = os.path.splitext(img_file)[0].replace("-", " ").title()

        # 2. Usar IA SOLO para clasificar
        ia = analizar_imagen_solo_clasificacion(ruta_completa, nombre_final)
        
        # 3. Construir Fila
        return {
            "Filename_Original": img_file,
            "Es_Moto_o_Motocarguero": ia.get("Es_Moto_o_Motocarguero", True),
            "Tipo_Contenido": ia.get("Tipo_Contenido", "repuesto_moto"),
            "Confianza_Global": 1.0, 
            "Identificacion_Repuesto": nombre_final, # Nombre + SKU
            "Componente_Taxonomia": ia.get("Componente_Taxonomia", "Repuesto"),
            "Sistema": ia.get("Sistema", "General"),
            "SubSistema": ia.get("SubSistema", ""),
            "Caracteristicas_Observadas": f"Referencia: {sku_real}" if sku_real else "",
            "Compatibilidad_Probable_Texto": "",
            "Compatibilidad_Probable_JSON": "[]",
            "Funcion": "",
            "Nombre_Comercial_Catalogo": nombre_final, # ESTO ES LO QUE VALE
            "Tags_Sugeridos": f"{sku_real},{ia.get('Tags_Sugeridos','')}",
            "Notas_Sobre_Textos_Grabados": sku_real,
            "Necesita_Modelo_Grande": False
        }

    with ThreadPoolExecutor(max_workers=10) as executor:
        for i, res in enumerate(executor.map(worker, imagenes)):
            resultados.append(res)
            if i % 50 == 0: print(f"   ... {i}/{len(imagenes)}", end="\r")

    if resultados:
        df = pd.DataFrame(resultados)
        
        # Columnas Bara
        cols_bara = [
            "Filename_Original", "Es_Moto_o_Motocarguero", "Tipo_Contenido", "Confianza_Global",
            "Identificacion_Repuesto", "Componente_Taxonomia", "Sistema", "SubSistema",
            "Caracteristicas_Observadas", "Compatibilidad_Probable_Texto", "Compatibilidad_Probable_JSON",
            "Funcion", "Nombre_Comercial_Catalogo", "Tags_Sugeridos", "Notas_Sobre_Textos_Grabados",
            "Necesita_Modelo_Grande"
        ]
        for c in cols_bara:
            if c not in df.columns: df[c] = ""
            
        df = df[cols_bara]
        df.to_csv(LOTE_DUNA['salida'], index=False, sep=';', encoding='utf-8-sig')
        print(f"\n   ✅ Archivo DUNA Correcto: {os.path.basename(LOTE_DUNA['salida'])}")
    
    guardar_cache()

if __name__ == "__main__":
    procesar_duna_fix()