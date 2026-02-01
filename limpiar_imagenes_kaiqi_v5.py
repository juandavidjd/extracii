import os
import shutil
import threading
import queue
import base64
import json
from openai import OpenAI

# ==========================================
# 🔧 CONFIGURACIÓN
# ==========================================
IMAGE_DIR = r"C:\img\FOTOS_COMPETENCIA"
OUTPUT_DIR = r"C:\img"

# Carpetas de Destino
DIR_MAESTRAS      = os.path.join(OUTPUT_DIR, "IMAGENES_KAIQI_MAESTRAS")
DIR_EDITAR        = os.path.join(OUTPUT_DIR, "IMAGENES_PARA_EDITAR")
DIR_NO_MOTO       = os.path.join(OUTPUT_DIR, "DESCARTADAS_NO_MOTO")
DIR_BAJA_CALIDAD  = os.path.join(OUTPUT_DIR, "DESCARTADAS_BAJA_CALIDAD")
DIR_LOGS          = os.path.join(OUTPUT_DIR, "LOGS")

# Hilos
NUM_WORKERS = 5  # Aumenté un poco para ir más rápido

# Cliente IA (Asegúrate de tener la variable de entorno o pega tu key aquí)
# client = OpenAI(api_key="sk-TU-API-KEY-AQUI") 
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ==========================================
# 🧠 PROMPT DE PRECISIÓN V5
# ==========================================
PROMPT_ANALISIS = """
Actúa como un curador de catálogo de repuestos de moto. Clasifica esta imagen.

REGLAS DE ORO:
1. "MAESTRA": Imagen limpia, producto visible, fondo aceptable (blanco/neutro/o taller limpio). Puede tener números de parte o marcas grabadas en el metal/plástico (ej: "HONDA", "125cm3").
2. "EDITAR": Imagen buena del producto, PERO tiene: Marcas de agua del vendedor, Logos de tiendas superpuestos, Números de teléfono, URLs, o el fondo es muy sucio/confuso.
3. "NO_MOTO": No es un repuesto (es una moto entera, un carro, un diagrama técnico, una persona, o basura).
4. "BAJA_CALIDAD": Borrosa, pixelada, muy oscura, o el producto está cortado.

Responde SOLO este JSON:
{
  "clasificacion": "MAESTRA" | "EDITAR" | "NO_MOTO" | "BAJA_CALIDAD",
  "razon": "Breve explicación",
  "tipo_repuesto": "Nombre del repuesto si lo identificas, sino null"
}
"""

# ==========================================
# 🔧 FUNCIONES
# ==========================================

def setup_dirs():
    for d in [DIR_MAESTRAS, DIR_EDITAR, DIR_NO_MOTO, DIR_BAJA_CALIDAD, DIR_LOGS]:
        os.makedirs(d, exist_ok=True)

def encode_image(img_path):
    try:
        with open(img_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except:
        return None

def analizar_imagen(image_path):
    img64 = encode_image(image_path)
    if not img64: return None

    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres un experto en repuestos de moto. Responde solo en JSON."},
                {"role": "user", "content": [
                    {"type": "text", "text": PROMPT_ANALISIS},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img64}", "detail": "low"}}
                ]}
            ],
            temperature=0.0,
            max_tokens=150
        )
        content = resp.choices[0].message.content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        return {"error": str(e)}

def mover_archivo(src, clasificacion):
    filename = os.path.basename(src)
    
    if clasificacion == "MAESTRA":
        dst = os.path.join(DIR_MAESTRAS, filename)
    elif clasificacion == "EDITAR":
        dst = os.path.join(DIR_EDITAR, filename)
    elif clasificacion == "NO_MOTO":
        dst = os.path.join(DIR_NO_MOTO, filename)
    else: # BAJA_CALIDAD o Error
        dst = os.path.join(DIR_BAJA_CALIDAD, filename)
    
    try:
        shutil.copy2(src, dst)
    except:
        pass

# ==========================================
# 🧵 WORKER
# ==========================================
def worker(q, results):
    while True:
        try:
            img_path = q.get_nowait()
        except queue.Empty:
            break

        data = analizar_imagen(img_path)
        
        if data and "clasificacion" in data:
            cls = data["clasificacion"]
            razon = data.get("razon", "")
            mover_archivo(img_path, cls)
            results.append(f"{os.path.basename(img_path)},{cls},{razon}")
            print(f"[{cls}] {os.path.basename(img_path)}")
        else:
            mover_archivo(img_path, "BAJA_CALIDAD") # Fallback
            results.append(f"{os.path.basename(img_path)},ERROR_API,")
            print(f"[ERROR] {os.path.basename(img_path)}")
            
        q.task_done()

# ==========================================
# 🚀 MAIN
# ==========================================
def main():
    setup_dirs()
    print("--- CLASIFICADOR DE PRECISIÓN V5 (GPT-4o) ---")
    
    # Cargar imágenes
    exts = (".jpg", ".jpeg", ".png", ".webp")
    files = [os.path.join(IMAGE_DIR, f) for f in os.listdir(IMAGE_DIR) if f.lower().endswith(exts)]
    print(f"📸 Total imágenes: {len(files)}")
    
    # Cola
    q = queue.Queue()
    for f in files: q.put(f)
    
    results = []
    threads = []
    
    # Iniciar
    for _ in range(NUM_WORKERS):
        t = threading.Thread(target=worker, args=(q, results))
        t.start()
        threads.append(t)
        
    for t in threads: t.join()
    
    # Log
    with open(os.path.join(DIR_LOGS, "log_clasificacion_v5.csv"), "w", encoding="utf-8") as f:
        f.write("Archivo,Clasificacion,Razon\n")
        for line in results: f.write(line + "\n")

    print("\n✅ Terminamos. Revisa las carpetas.")

if __name__ == "__main__":
    main()