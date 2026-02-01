import os
import re
import json
import base64
import unicodedata
import shutil
import threading
import queue
import time

from openai import OpenAI

# ====================================================
# 🔧 CONFIGURACIÓN
# ====================================================

IMAGE_DIR = r"C:\img\IMAGENES_KAIQI_MAESTRAS"
OUTPUT_DIR = r"C:\img"

DIR_DUPLICADOS = os.path.join(OUTPUT_DIR, "IMAGENES_DUPLICADAS")
DIR_LOGS       = os.path.join(OUTPUT_DIR, "LOGS")
NUM_WORKERS    = 4

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TAXONOMIA_PATH = os.path.join(OUTPUT_DIR, "taxonomia_kaiqi.json")


# ====================================================
# 🧩 UTILIDADES
# ====================================================

def ensure_dirs():
    os.makedirs(DIR_DUPLICADOS, exist_ok=True)
    os.makedirs(DIR_LOGS, exist_ok=True)

def load_taxonomia():
    if os.path.exists(TAXONOMIA_PATH):
        try:
            with open(TAXONOMIA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def slugify(text: str) -> str:
    """Convierte texto a slug SEO limpio."""
    if not text:
        return ""
    text = text.strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("ñ", "n")
    text = re.sub(r"[^\w\s-]", " ", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"[^a-z0-9-]", "", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")

def encode_image(path: str) -> str | None:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return None


# ====================================================
# 🧠 PROMPT — RENOMBRADO SEO V4
# ====================================================

PROMPT_RENOMBRE = """
Actúa como experto en catálogo técnico de repuestos de MOTO y MOTOCARGUERO.

Tu tarea es proponer el MEJOR nombre base SEO según la imagen y el nombre actual.

REGLAS:
- Mantén información útil si existe (ej: '110 Bob Encendido C-70 Platino').
- Si el nombre es basura, ignóralo y usa solo lo que ves.
- NO uses 'JAPAN' ni marcas grabadas decorativas, pero SÍ marcas/models reales de motos si las reconoces.
- Conserva números molde si los ves.
- Formato final:
  - minusculas
  - sin tildes ni ñ
  - separador '-'
  - nada de puntos ni doble guion
  - no incluyas la extensión

Debes identificar:
componente, marca_moto, modelo_moto, cilindraje, si es_motocarguero,
numeros_molde visibles.

Responde SOLO en JSON:

{
  "nombre_base_seo": "",
  "componente": "",
  "marca_moto": "",
  "modelo_moto": "",
  "cilindraje": "",
  "es_motocarguero": false,
  "numeros_molde": "",
  "observaciones": ""
}
"""


def pedir_nombre_seo_con_ia(img_path: str, nombre_actual: str) -> dict | None:
    """Llama a Vision 4o y obtiene JSON normalizado."""
    img64 = encode_image(img_path)
    if not img64:
        return None

    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.0,
            max_tokens=400,
            messages=[
                {
                    "role": "system",
                    "content": "Eres experto en catálogo técnico. Responde SOLO JSON válido."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": PROMPT_RENOMBRE + f"\n\nNombre actual: {nombre_actual}\nRecuerda: SOLO JSON."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img64}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ]
        )

        content = resp.choices[0].message.content.strip()
        content = content.replace("```json", "").replace("```", "")
        data = json.loads(content)
        return data

    except Exception as e:
        print(f"[ERROR IA] {nombre_actual} -> {e}")
        return None


# ====================================================
# 🔀 WORKER MULTIHILO
# ====================================================

def worker(q: queue.Queue, resultados: list, slugs_vistos: dict):

    while True:
        try:
            img_path = q.get_nowait()
        except queue.Empty:
            break

        nombre_actual = os.path.basename(img_path)
        ext = os.path.splitext(nombre_actual)[1].lower() or ".jpg"

        # ======================
        # ⚡ Llamada a Vision 4o
        # ======================
        data = pedir_nombre_seo_con_ia(img_path, nombre_actual)

        if not data or "nombre_base_seo" not in data:
            resultados.append({
                "archivo_original": nombre_actual,
                "archivo_nuevo": nombre_actual,
                "slug": "",
                "duplicado": "NO",
                "error": "IA_sin_respuesta",
                "meta": {}
            })
            print(f"[IA ERROR] {nombre_actual} (sin cambios)")
            q.task_done()
            continue

        nombre_base_ia = data.get("nombre_base_seo", "").strip()
        slug = slugify(nombre_base_ia)

        if not slug:
            slug = slugify(os.path.splitext(nombre_actual)[0])

        nuevo_nombre = f"{slug}{ext}"
        nuevo_path = os.path.join(IMAGE_DIR, nuevo_nombre)

        # ======================
        # ⚠ Validar duplicados
        # ======================
        if slug in slugs_vistos:
            destino = os.path.join(DIR_DUPLICADOS, nombre_actual)
            try:
                shutil.move(img_path, destino)
            except Exception:
                pass

            resultados.append({
                "archivo_original": nombre_actual,
                "archivo_nuevo": nombre_actual,
                "slug": slug,
                "duplicado": "SI",
                "error": "",
                "meta": data
            })

            print(f"[DUPLICADO] {nombre_actual} -> IMAGENES_DUPLICADAS (slug {slug})")
            q.task_done()
            continue

        slugs_vistos[slug] = nombre_actual

        # ======================
        # 🎯 Renombrar archivo
        # ======================
        if os.path.exists(nuevo_path) and nuevo_path != img_path:
            # colisión física
            destino = os.path.join(DIR_DUPLICADOS, nombre_actual)
            try:
                shutil.move(img_path, destino)
            except:
                pass

            resultados.append({
                "archivo_original": nombre_actual,
                "archivo_nuevo": nombre_actual,
                "slug": slug,
                "duplicado": "SI_FISICO",
                "error": "colision_nombre_fisico",
                "meta": data
            })

            print(f"[COLISION] {nombre_actual} -> DUPLICADOS (ya existía {nuevo_nombre})")
        else:
            try:
                os.rename(img_path, nuevo_path)
                resultados.append({
                    "archivo_original": nombre_actual,
                    "archivo_nuevo": nuevo_nombre,
                    "slug": slug,
                    "duplicado": "NO",
                    "error": "",
                    "meta": data
                })
                print(f"[OK] {nombre_actual} -> {nuevo_nombre}")
            except Exception as e:
                resultados.append({
                    "archivo_original": nombre_actual,
                    "archivo_nuevo": nombre_actual,
                    "slug": slug,
                    "duplicado": "NO",
                    "error": f"error_renombrando:{e}",
                    "meta": data
                })
                print(f"[ERROR RENOMBRE] {nombre_actual} -> {e}")

        q.task_done()


# ====================================================
# ▶ MAIN
# ====================================================

def main():
    ensure_dirs()

    exts = (".jpg", ".jpeg", ".png", ".webp")
    files = [
        os.path.join(IMAGE_DIR, f)
        for f in os.listdir(IMAGE_DIR)
        if os.path.isfile(os.path.join(IMAGE_DIR, f)) and f.lower().endswith(exts)
    ]

    print("==============================================")
    print(" 🔵 Renombrado SEO KAIQI v4 — Vision GPT-4o")
    print("==============================================")
    print(f"📸 Total imágenes encontradas: {len(files)}\n")

    if not files:
        print(f"❌ No se encontraron imágenes en {IMAGE_DIR}")
        return

    q = queue.Queue()
    for f in files:
        q.put(f)

    resultados = []
    slugs_vistos = {}

    hilos = []
    for _ in range(NUM_WORKERS):
        t = threading.Thread(target=worker, args=(q, resultados, slugs_vistos))
        t.start()
        hilos.append(t)

    for t in hilos:
        t.join()

    log_path = os.path.join(DIR_LOGS, "log_renombrado_seo_v4.csv")
    with open(log_path, "w", encoding="utf-8", newline="") as f:
        f.write("archivo_original,archivo_nuevo,slug,duplicado,error,componente,marca_moto,modelo_moto,cilindraje,es_motocarguero,numeros_molde,observaciones\n")
        for r in resultados:
            m = r.get("meta", {}) or {}
            row = [
                r.get("archivo_original",""),
                r.get("archivo_nuevo",""),
                r.get("slug",""),
                r.get("duplicado",""),
                r.get("error",""),
                m.get("componente",""),
                m.get("marca_moto",""),
                m.get("modelo_moto",""),
                m.get("cilindraje",""),
                str(m.get("es_motocarguero","")),
                m.get("numeros_molde",""),
                (m.get("observaciones","").replace(",", " ").replace("\n", " "))
            ]
            f.write(",".join(row) + "\n")

    print("\n✅ Renombrado finalizado.")
    print(f"📄 Log generado: {log_path}")
    print(f"📁 Duplicados:   {DIR_DUPLICADOS}")


if __name__ == "__main__":
    main()
