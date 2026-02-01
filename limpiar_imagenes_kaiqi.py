# limpiar_imagenes_kaiqi.py
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
IMAGE_DIR  = r"C:\img\FOTOS_COMPETENCIA"   # SOLO esta carpeta, sin subcarpetas
OUTPUT_DIR = r"C:\img"

# Carpetas de destino
DIR_MAESTRAS      = os.path.join(OUTPUT_DIR, "IMAGENES_KAIQI_MAESTRAS")
DIR_EDITAR        = os.path.join(OUTPUT_DIR, "IMAGENES_PARA_EDITAR")
DIR_NO_MOTO       = os.path.join(OUTPUT_DIR, "DESCARTADAS_NO_MOTO")
DIR_BAJA_CALIDAD  = os.path.join(OUTPUT_DIR, "DESCARTADAS_BAJA_CALIDAD")
DIR_LOGS          = os.path.join(OUTPUT_DIR, "LOGS")

# Hilos
NUM_WORKERS = 4  # ✅ como pediste

# Cliente IA (usa tu OPENAI_API_KEY del entorno)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ==========================================
# 🧠 PROMPT CLASIFICACIÓN (conserva textos)
# ==========================================
PROMPT_ANALISIS = """
Actúa como un curador de catálogo de repuestos de moto. Clasifica esta imagen.

REGLAS DE ORO (IMPORTANTE: NO ELIMINAR IMÁGENES BUENAS POR TENER TEXTO):
1. "MAESTRA":
   - Imagen nítida.
   - El repuesto se ve completo y claro.
   - Fondo aceptable (blanco, neutro, taller limpio, mesa, etc.).
   - Puede tener:
     - Números de parte grabados en la pieza.
     - Marca moldeada en el metal/plástico.
     - Texto técnico en la pieza o empaque.
   ESTAS SON LAS QUE USAREMOS COMO BASE MAESTRA.

2. "EDITAR":
   - Imagen del repuesto es útil, pero:
     - Tiene logo grande del vendedor.
     - Tiene teléfono, WhatsApp, URL, marca de agua de tienda.
     - O hay mucho texto gráfico encima que habrá que borrar manualmente.
   Debemos conservar estas para edición manual porque el repuesto es válido.

3. "NO_MOTO":
   - No es repuesto de moto ni de motocarro.
   - Es carro completo, persona, juguete, electrodoméstico, publicidad pura, etc.

4. "BAJA_CALIDAD":
   - Imagen muy borrosa, pixelada, muy oscura.
   - El repuesto está cortado o casi no se entiende.
   - No sirve como base fotográfica para catálogo.

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
    except Exception:
        return None

def analizar_imagen(image_path):
    img64 = encode_image(image_path)
    if not img64:
        return {"error": "no_se_pudo_leer"}

    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres un experto en repuestos de moto. Responde solo en JSON válido."},
                {"role": "user", "content": [
                    {"type": "text", "text": PROMPT_ANALISIS},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{img64}",
                        "detail": "low"
                    }}
                ]}
            ],
            temperature=0.0,
            max_tokens=200
        )
        content = resp.choices[0].message.content
        content = content.replace("```json", "").replace("```", "").strip()
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
    else:  # BAJA_CALIDAD o ERROR
        dst = os.path.join(DIR_BAJA_CALIDAD, filename)

    try:
        shutil.copy2(src, dst)
    except Exception:
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
        filename = os.path.basename(img_path)

        if data and "clasificacion" in data:
            cls   = data.get("clasificacion", "BAJA_CALIDAD")
            razon = data.get("razon", "")
            mover_archivo(img_path, cls)
            results.append(f"{filename},{cls},{razon}")
            print(f"[{cls}] {filename} → {razon}")
        else:
            mover_archivo(img_path, "BAJA_CALIDAD")
            results.append(f"{filename},ERROR_API,{data.get('error','') if isinstance(data, dict) else ''}")
            print(f"[ERROR] {filename}")

        q.task_done()

# ==========================================
# 🚀 MAIN
# ==========================================
def main():
    setup_dirs()
    print("==========================================")
    print("  🧽 CLASIFICADOR KAIQI V5 (Vision 4o)")
    print("==========================================")

    exts = (".jpg", ".jpeg", ".png", ".webp")
    files = [
        os.path.join(IMAGE_DIR, f)
        for f in os.listdir(IMAGE_DIR)
        if f.lower().endswith(exts)
    ]

    print(f"📸 Total imágenes encontradas en FOTOS_COMPETENCIA: {len(files)}")

    q = queue.Queue()
    for f in files:
        q.put(f)

    results = []
    threads = []

    for _ in range(NUM_WORKERS):
        t = threading.Thread(target=worker, args=(q, results))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    # Guardar log
    os.makedirs(DIR_LOGS, exist_ok=True)
    log_path = os.path.join(DIR_LOGS, "log_clasificacion_kaiqi_v5.csv")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("Archivo,Clasificacion,Razon\n")
        for line in results:
            f.write(line + "\n")

    print("\n✅ Clasificación terminada.")
    print(f"🧾 Log: {log_path}")
    print(f"📂 MAESTRAS:      {DIR_MAESTRAS}")
    print(f"📂 PARA EDITAR:   {DIR_EDITAR}")
    print(f"📂 NO MOTO:       {DIR_NO_MOTO}")
    print(f"📂 BAJA CALIDAD:  {DIR_BAJA_CALIDAD}")

if __name__ == "__main__":
    main()
