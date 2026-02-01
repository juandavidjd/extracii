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
    print("⚠️ ADVERTENCIA: No se detectó API Key.")

# Cache separada para análisis rico (no sobreescribir la anterior rápida)
CACHE_FILE = os.path.join(BASE_DIR, "vision_duna_rich_cache.json")

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
    """Carga la verdad absoluta (Nombre y SKU) del CSV."""
    refs = {}
    ruta_real = encontrar_ruta(nombre_csv)
    
    if ruta_real:
        print(f"   ✅ Referencia maestra cargada: {os.path.basename(ruta_real)}")
        try:
            try: df = pd.read_csv(ruta_real, sep=';', encoding='utf-8-sig', on_bad_lines='skip')
            except: df = pd.read_csv(ruta_real, sep=',', encoding='utf-8-sig', on_bad_lines='skip')
            
            df.columns = [c.strip() for c in df.columns]
            
            if col_archivo in df.columns:
                for _, row in df.iterrows():
                    f = str(row[col_archivo]).strip().lower()
                    nom = str(row[col_nombre]).strip() if col_nombre in df.columns else ""
                    sku = str(row[col_sku]).strip() if col_sku in df.columns else ""
                    
                    # Construir nombre final fijo
                    nombre_final = nom
                    if sku and sku not in nom and sku != "nan":
                        nombre_final = f"{nom} {sku}"
                    
                    refs[f] = {
                        "nombre_real": nombre_final,
                        "sku_real": sku if sku != "nan" else ""
                    }
        except Exception as e:
            print(f"   ⚠️ Error CSV: {e}")
    return refs

def analizar_imagen_full_rich(ruta_img, nombre_ref_fijo):
    """
    Usa IA para enriquecer la descripción SIN cambiar el nombre.
    Genera: Características, Función, Compatibilidad, Sistema.
    """
    if not client: return {}
    
    file_hash = f"{os.path.basename(ruta_img)}_{os.path.getsize(ruta_img)}_FULL_RICH"
    if file_hash in CACHE: return CACHE[file_hash]

    try:
        with open(ruta_img, "rb") as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')

        prompt = f"""
        Actúa como un Mecánico Experto de Motos.
        Tienes este producto: "{nombre_ref_fijo}".
        
        Tu tarea es DESCRIBIRLO visual y técnicamente (NO cambies el nombre).
        
        Responde un JSON con estos campos exactos:
        {{
            "Es_Moto_o_Motocarguero": true,
            "Tipo_Contenido": "repuesto_moto" (o herramienta, accesorio),
            "Componente_Taxonomia": "La pieza principal (ej: Amortiguador)",
            "Sistema": "El sistema mecánico (ej: Suspensión)",
            "SubSistema": "Subsistema (ej: Trasera)",
            "Caracteristicas_Observadas": "Descripción visual detallada: material (aluminio/acero/plástico), color, forma, acabados visibles.",
            "Compatibilidad_Probable_Texto": "Lista de motos sugeridas según la forma de la pieza.",
            "Funcion": "Explicación técnica breve de qué hace esta pieza en la moto.",
            "Tags_Sugeridos": "Palabras clave para búsqueda (separadas por coma)"
        }}
        """

        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres un experto catalogador de autopartes. JSON output only."},
                {"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}
            ],
            max_tokens=450,
            response_format={"type": "json_object"}
        )
        
        data = json.loads(resp.choices[0].message.content)
        CACHE[file_hash] = data
        return data

    except: 
        # Fallback básico
        return {
            "Sistema": "General", 
            "Caracteristicas_Observadas": "No analizado",
            "Funcion": "Repuesto para motocicleta"
        }

# ================= CONFIGURACIÓN DUNA =================

LOTE_DUNA = {
    "nombre": "DUNA",
    "carpeta": "FOTOS_COMPETENCIA_DUNA",
    "referencia": "Base_Datos_Duna.csv", 
    "salida": os.path.join(BASE_DIR, "catalogo_kaiqi_imagenes_DUNA.csv"),
    "col_archivo": "Imagen_SEO", 
    "col_nombre": "Nombre_Producto",
    "col_sku": "Referencia_Real"
}

# ================= MOTOR =================

def procesar_duna_rich():
    print(f"\n🚀 Enriqueciendo DUNA (Modo FULL RICH)...")
    
    ruta_carpeta = encontrar_ruta(LOTE_DUNA['carpeta'])
    if not ruta_carpeta:
        print("❌ Carpeta de fotos no encontrada.")
        return

    refs = cargar_referencias_completas(LOTE_DUNA['referencia'], LOTE_DUNA['col_archivo'], LOTE_DUNA['col_nombre'], LOTE_DUNA['col_sku'])
    if not refs: return

    imagenes = [f for f in os.listdir(ruta_carpeta) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    print(f"   🔍 Imágenes a procesar: {len(imagenes)}")

    resultados = []
    
    def worker(img_file):
        ruta_completa = os.path.join(ruta_carpeta, img_file)
        
        # 1. DATOS FIJOS (Del CSV)
        datos_maestros = refs.get(img_file.lower())
        
        if datos_maestros:
            nombre_final = datos_maestros['nombre_real']
            sku_real = datos_maestros['sku_real']
        else:
            # Fallback
            nombre_final = os.path.splitext(img_file)[0].replace("-", " ").title()
            sku_real = ""

        # 2. DATOS RICOS (De la IA)
        # Le pasamos el nombre fijo para que la IA sepa de qué hablar
        ia = analizar_imagen_full_rich(ruta_completa, nombre_final)
        
        # 3. FUSIÓN
        return {
            "Filename_Original": img_file,
            "Es_Moto_o_Motocarguero": ia.get("Es_Moto_o_Motocarguero", True),
            "Tipo_Contenido": ia.get("Tipo_Contenido", "repuesto_moto"),
            "Confianza_Global": 0.99, 
            "Identificacion_Repuesto": nombre_final, # ¡PROTEGIDO!
            "Componente_Taxonomia": ia.get("Componente_Taxonomia", "Repuesto"),
            "Sistema": ia.get("Sistema", "General"),
            "SubSistema": ia.get("SubSistema", ""),
            
            # Aquí está la riqueza que faltaba:
            "Caracteristicas_Observadas": ia.get("Caracteristicas_Observadas", ""),
            "Compatibilidad_Probable_Texto": ia.get("Compatibilidad_Probable_Texto", ""),
            "Compatibilidad_Probable_JSON": "[]",
            "Funcion": ia.get("Funcion", ""),
            
            "Nombre_Comercial_Catalogo": nombre_final, # ¡PROTEGIDO!
            "Tags_Sugeridos": f"{sku_real},{ia.get('Tags_Sugeridos','')}",
            "Notas_Sobre_Textos_Grabados": sku_real, # Ponemos el SKU aquí también por si acaso
            "Necesita_Modelo_Grande": False
        }

    # Ejecución (Un poco más lenta para dar tiempo a la IA de pensar)
    with ThreadPoolExecutor(max_workers=6) as executor:
        for i, res in enumerate(executor.map(worker, imagenes)):
            resultados.append(res)
            if i % 10 == 0: print(f"   ... {i}/{len(imagenes)} enriquecidos", end="\r")

    if resultados:
        df = pd.DataFrame(resultados)
        
        # Columnas Bara (Orden estricto)
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
        print(f"\n   ✅ Catálogo DUNA Enriquecido: {os.path.basename(LOTE_DUNA['salida'])}")
    
    guardar_cache()

if __name__ == "__main__":
    procesar_duna_rich()