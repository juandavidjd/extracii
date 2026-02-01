import os
import shutil
import threading
import queue
import base64
import json
from openai import OpenAI

# =====================================================================
# ✔ CONFIGURACIÓN PRINCIPAL
# =====================================================================
IMAGE_DIR = r"C:\img\FOTOS_COMPETENCIA"
OUTPUT_DIR = r"C:\img"

# Carpetas de salida
DIR_MAESTRAS      = os.path.join(OUTPUT_DIR, "IMAGENES_KAIQI_MAESTRAS")
DIR_EDITAR        = os.path.join(OUTPUT_DIR, "IMAGENES_PARA_EDITAR")
DIR_NO_MOTO       = os.path.join(OUTPUT_DIR, "DESCARTADAS_NO_MOTO")
DIR_BAJA_CALIDAD  = os.path.join(OUTPUT_DIR, "DESCARTADAS_BAJA_CALIDAD")
DIR_LOGS          = os.path.join(OUTPUT_DIR, "LOGS")

# Número de hilos (tu recomendación: 4)
NUM_WORKERS = 4

# Cliente IA
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# =====================================================================
# ✔ PROMPT PROFESIONAL V5 — CLASIFICADOR KAIQI
# =====================================================================
PROMPT_ANALISIS = """
Actúa como un CURADOR PROFESIONAL DE CATÁLOGO DE REPUESTOS DE MOTO.

Tu trabajo es analizar la imagen y clasificarla EXACTAMENTE en una de estas 4 categorías:

---------------------------------------------------------------------
1) MAESTRA  → LISTA PARA USAR EN CATÁLOGO
---------------------------------------------------------------------
✔ Producto completamente visible  
✔ Fondo limpio / blanco / gris / taller sin ruido  
✔ Puede tener números moldados (54410, 16B01, etc.)
✔ Puede tener marcas impresas del OEM original
✘ NO debe tener marcas de vendedores, logos, textos superpuestos, números de teléfono

---------------------------------------------------------------------
2) EDITAR → BUENA PERO NECESITA LIMPIEZA
---------------------------------------------------------------------
✔ Marca de agua del vendedor
✔ Texto superpuesto
✔ Logos de tiendas
✔ Fondos muy sucios o elementos no deseados
✔ Información que debe borrarse después

---------------------------------------------------------------------
3) NO_MOTO → NO ES UN REPUESTO DE MOTO O MOTOCARGUERO
---------------------------------------------------------------------
✘ Carros, buses, juguetes, electrodomésticos  
✘ Personas, mascotas  
✘ Publicidad  
✘ Partes que no pertenecen a motos

---------------------------------------------------------------------
4) BAJA_CALIDAD
---------------------------------------------------------------------
✘ Muy borrosa  
✘ Muy oscura  
✘ Pixelada  
✘ Cortada (falta media pieza)  
✘ Imposible reconocer el producto  

---------------------------------------------------------------------

FORMATO DE RESPUESTA (OBLIGATORIO):

{
  "clasificacion": "MAESTRA" | "EDITAR" | "NO_MOTO" | "BAJA_CALIDAD",
  "razon": "explicacion corta",
  "tipo_repuesto": "nombre del repuesto si se identifica, sino null"
}
"""

# =====================================================================
# FUNCIONES
# =====================================================================
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
    if not img64:
        return {"clasificacion": "BAJA_CALIDAD", "razon": "No se pudo leer", "tipo_repuesto": None}

    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.0,
            messages=[
                {"role": "system", "content": "Responde solo JSON válido."},
                {"role": "user", "content": [
                    {"type": "text", "text": PROMPT_ANALISIS},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{img64}",
                        "detail": "low"
                    }}
                ]}
            ]
        )

        txt = resp.choices[0].message.content.strip()
        txt = txt.replace("```json", "").replace("```", "")
        return json.loads(txt)

    except Exception as e:
        return {"clasificacion": "BAJA_CALIDAD", "razon": f"Error API: {e}", "tipo_repuesto": None}

def mover_archivo(src, clasificacion):
    dst = {
        "MAESTRA":     DIR_MAESTRAS,
        "EDITAR":      DIR_EDITAR,
        "NO_MOTO":     DIR_NO_MOTO,
        "BAJA_CALIDAD":DIR_BAJA_CALIDAD
    }.get(clasificacion, DIR_BAJA_CALIDAD)

    try:
        shutil.copy2(src, os.path.join(dst, os.path.basename(src)))
    except:
        pass

# =====================================================================
# WORKER MULTIHILO
# =====================================================================
def worker(q, results):
    while True:
        try:
            img = q.get_nowait()
        except queue.Empty:
            break

        info = analizar_imagen(img)
        clas = info.get("clasificacion", "BAJA_CALIDAD")
        razon = info.get("razon", "")

        mover_archivo(img, clas)

        results.append(f"{os.path.basename(img)},{clas},{razon}")
        print(f"[{clas}] {os.path.basename(img)} — {razon}")

        q.task_done()

# =====================================================================
# MAIN
# =====================================================================
def main():
    setup_dirs()

    print("==============================================")
    print("🔥 CLASIFICADOR V5 — KAIQI Vision 4o")
    print("==============================================")

    exts = (".jpg", ".jpeg", ".png", ".webp")
    files = [
        os.path.join(IMAGE_DIR, f)
        for f in os.listdir(IMAGE_DIR)
        if f.lower().endswith(exts)
    ]

    print(f"📸 Total imágenes detectadas: {len(files)}")

    q = queue.Queue()
    for f in files: q.put(f)

    results = []
    threads = []

    for _ in range(NUM_WORKERS):
        t = threading.Thread(target=worker, args=(q, results))
        t.start()
        threads.append(t)

    for t in threads: t.join()

    log = os.path.join(DIR_LOGS, "clasificacion_v5.csv")
    with open(log, "w", encoding="utf-8") as f:
        f.write("archivo,clasificacion,razon\n")
        for r in results:
            f.write(r + "\n")

    print("✔ Proceso finalizado. Revisa las carpetas.")


if __name__ == "__main__":
    main()
