import os
import pandas as pd
import base64
import json
import time
import random
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\img"
ARCHIVO_CSV = os.path.join(BASE_DIR, "catalogo_kaiqi_imagenes_DUNA_RICH.csv")
CARPETA_IMAGENES = os.path.join(BASE_DIR, "FOTOS_COMPETENCIA_DUNA")
ARCHIVO_CACHE = os.path.join(BASE_DIR, "vision_hyper_rich_cache.json")

# Cliente OpenAI
try:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except:
    print("❌ ERROR: No hay API Key configurada.")
    exit()

# Cargar Cache
if os.path.exists(ARCHIVO_CACHE):
    try:
        with open(ARCHIVO_CACHE, "r", encoding="utf-8") as f: CACHE = json.load(f)
    except: CACHE = {}
else:
    CACHE = {}

def guardar_cache():
    try:
        with open(ARCHIVO_CACHE, "w", encoding="utf-8") as f: json.dump(CACHE, f, indent=2)
    except: pass

# ================= MOTOR DE IA ROBUSTO =================

def analizar_con_retry(ruta_img, nombre_ref):
    """Intenta analizar con reintentos inteligentes."""
    if not client: return None
    
    file_hash = f"{os.path.basename(ruta_img)}_{os.path.getsize(ruta_img)}_HYPER"
    if file_hash in CACHE: return CACHE[file_hash]

    max_retries = 3
    for intento in range(max_retries):
        try:
            with open(ruta_img, "rb") as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')

            prompt = f"""
            Actúa como un Ingeniero Mecánico experto. Analiza: "{nombre_ref}".
            Describe visualmente el repuesto.
            Responde JSON:
            {{
                "Es_Moto_o_Motocarguero": true,
                "Tipo_Contenido": "repuesto_moto",
                "Componente_Taxonomia": "Ej: Carburador",
                "Sistema": "Ej: Motor",
                "SubSistema": "Ej: Admisión",
                "Caracteristicas_Observadas": "Material, color, forma, detalles.",
                "Compatibilidad_Probable_Texto": "Motos sugeridas",
                "Funcion": "Uso técnico",
                "Tags_Sugeridos": "tag1, tag2"
            }}
            """

            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Experto en autopartes. JSON only."},
                    {"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}
                ],
                max_tokens=450,
                response_format={"type": "json_object"}
            )
            
            data = json.loads(resp.choices[0].message.content)
            CACHE[file_hash] = data
            return data

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate limit" in error_msg.lower():
                wait_time = (intento + 1) * 5  # Espera 5s, 10s, 15s...
                print(f"   ⏳ Rate Limit (429). Esperando {wait_time}s para reintentar {os.path.basename(ruta_img)}...")
                time.sleep(wait_time)
            else:
                print(f"   ❌ Error en {os.path.basename(ruta_img)}: {e}")
                return None # Error no recuperable (ej: imagen corrupta)
    
    return None # Falló después de reintentos

# ================= LÓGICA DE REPARACIÓN =================

def reparar_catalogo():
    print(f"--- REPARANDO CATÁLOGO DUNA: {os.path.basename(ARCHIVO_CSV)} ---")
    
    if not os.path.exists(ARCHIVO_CSV):
        print("❌ No encuentro el CSV a reparar.")
        return

    # Leer CSV con separador correcto
    try:
        df = pd.read_csv(ARCHIVO_CSV, sep=';', encoding='utf-8-sig')
    except:
        df = pd.read_csv(ARCHIVO_CSV, sep=';', encoding='latin-1')

    # Identificar filas fallidas
    # Criterio: Sistema == "General" O Caracteristicas == "Descripción técnica pendiente."
    mask_fallo = (df['Sistema'] == 'General') | (df['Caracteristicas_Observadas'].str.contains('pendiente', na=False))
    indices_fallidos = df[mask_fallo].index.tolist()
    
    print(f"📦 Total Registros: {len(df)}")
    print(f"⚠️ Registros Pendientes/Fallidos: {len(indices_fallidos)}")
    
    if len(indices_fallidos) == 0:
        print("✅ ¡El catálogo ya está completo! No hay nada que reparar.")
        return

    print("🚀 Iniciando reparación inteligente...")
    
    # Procesar solo los fallidos
    reparados = 0
    
    # Usamos un solo hilo o muy pocos para evitar rate limit
    for idx in indices_fallidos:
        row = df.loc[idx]
        img_file = row['Filename_Original']
        ruta_img = os.path.join(CARPETA_IMAGENES, img_file)
        
        # Buscar en scrap si no está en img
        if not os.path.exists(ruta_img):
             ruta_scrap = os.path.join(r"C:\scrap\FOTOS_COMPETENCIA_DUNA", img_file)
             if os.path.exists(ruta_scrap): ruta_img = ruta_scrap
        
        if os.path.exists(ruta_img):
            print(f"   > Reparando [{reparados+1}/{len(indices_fallidos)}]: {img_file}...", end="\r")
            
            ia_data = analizar_con_retry(ruta_img, row['Identificacion_Repuesto'])
            
            if ia_data:
                # Actualizar DataFrame en memoria
                df.at[idx, 'Es_Moto_o_Motocarguero'] = ia_data.get('Es_Moto_o_Motocarguero', True)
                df.at[idx, 'Tipo_Contenido'] = ia_data.get('Tipo_Contenido', 'repuesto_moto')
                df.at[idx, 'Componente_Taxonomia'] = ia_data.get('Componente_Taxonomia', 'Repuesto')
                df.at[idx, 'Sistema'] = ia_data.get('Sistema', 'General')
                df.at[idx, 'SubSistema'] = ia_data.get('SubSistema', '')
                df.at[idx, 'Caracteristicas_Observadas'] = ia_data.get('Caracteristicas_Observadas', '')
                df.at[idx, 'Funcion'] = ia_data.get('Funcion', '')
                df.at[idx, 'Tags_Sugeridos'] = ia_data.get('Tags_Sugeridos', '')
                
                reparados += 1
                
                # Guardado incremental cada 10 registros para no perder progreso
                if reparados % 10 == 0:
                    df.to_csv(ARCHIVO_CSV, index=False, sep=';', encoding='utf-8-sig')
                    guardar_cache()
            else:
                print(f"\n   ⚠️ No se pudo reparar {img_file} (IA falló o imagen corrupta).")
        else:
            print(f"\n   ❌ Imagen física no encontrada: {img_file}")

    # Guardado final
    df.to_csv(ARCHIVO_CSV, index=False, sep=';', encoding='utf-8-sig')
    guardar_cache()
    
    print("\n" + "="*50)
    print(f"✅ REPARACIÓN FINALIZADA")
    print(f"   Registros Reparados: {reparados}")
    print(f"   Archivo Actualizado: {ARCHIVO_CSV}")
    print("="*50)

if __name__ == "__main__":
    reparar_catalogo()