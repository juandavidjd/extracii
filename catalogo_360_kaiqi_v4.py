import os
import json
import base64
import unicodedata
import csv
import threading
import queue

from openai import OpenAI

# ====================================================
# 🔧 CONFIGURACIÓN
# ====================================================

IMAGE_DIR = r"C:\img\IMAGENES_KAIQI_MAESTRAS"   # mismas imágenes, ya renombradas
OUTPUT_DIR = r"C:\img"

CATALOGO_360_CSV = os.path.join(OUTPUT_DIR, "catalogo_360_kaiqi_v4.csv")
DIR_LOGS         = os.path.join(OUTPUT_DIR, "LOGS")

NUM_WORKERS = 4

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TAXONOMIA_PATH = os.path.join(OUTPUT_DIR, "taxonomia_kaiqi.json")


# ====================================================
# 🧩 UTILIDADES
# ====================================================

def ensure_dirs():
    os.makedirs(DIR_LOGS, exist_ok=True)

def encode_image(path: str) -> str | None:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return None

def load_taxonomia():
    if os.path.exists(TAXONOMIA_PATH):
        try:
            with open(TAXONOMIA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def normalizar_clave_componente(text: str) -> str:
    if not text:
        return ""
    text = text.strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("ñ", "n")
    return text


# ====================================================
# 🧠 PROMPT 360° V4 (VISION 4o)
# ====================================================

PROMPT_360 = """
Actúa como INGENIERO DE DATOS DE PRODUCTO especializado en repuestos de MOTO y MOTOCARGUERO.

Tu trabajo es generar un ANÁLISIS 360° de la pieza que ves en la imagen, pensando en un catálogo e-commerce profesional.

REGLAS:

1) TIPOS DE VEHÍCULO
- Considera motos y también:
  - motocarro
  - triciclo motorizado
  - autorickshaw
  - torito
  - carguero
  - baby taxi
  - three wheeler
  - caponera
  - cocotaxi.

2) BRANDING / TEXTO EN LA PIEZA
- En la pieza puede haber texto grabado: 'JAPAN', 'HONDA', 'SUZUKI', códigos, etc.
- REGLA:
  - No uses 'JAPAN' ni el branding genérico como texto decorativo.
  - SÍ puedes usar la marca real de la moto en el FITMENT ('Honda CB150', 'Suzuki AX100') si es razonable.
- Conservar números de referencia/molde (ej: '54410', '16B01', '1-11-131') si se ven claramente.

3) FITMENT (COMPATIBILIDAD)
- Si estás MUY seguro de marca/modelo (por forma típica y pistas visuales), indícalo.
- Si NO estás seguro:
  - Usa descripciones genéricas: 'motos tipo scooter 125-150cc', 'motos street 100-125cc', 'motocargueros de eje sólido trasero', etc.
- No inventes modelos exactos si no hay evidencia.
- Cada entrada de fitment debe tener:
  - marca (o 'Genérico')
  - modelo (o 'Universal')
  - cilindraje aproximado
  - rango de años aproximado si aplica
  - sistema (ej. 'freno tambor trasero', 'freno disco delantero', etc.)
  - indicación si es para motocarguero.

4) ANÁLISIS 360° (12 PUNTOS)
Quiero que construyas esta estructura conceptual:

1. Identificacion_repuesto: nombre técnico claro (ej. 'banda de freno trasera', 'pastillas de freno delanteras', 'bobina de encendido', etc.)
2. Funcion_principal: qué hace en el sistema de la moto.
3. Sistema: frenos, motor, suspensión, transmisión, eléctrico, dirección, chasis, etc.
4. Posicion_vehiculo: delantero, trasero, lateral izquierdo, lateral derecho, central, etc.
5. Tipo_vehiculo_principal: 'moto', 'motocarguero' o ambos.
6. Caracteristicas_visuales: descripción física clave (material, acabado, número de piezas, forma general, etc.).
7. Numeros_referencia_visibles: lista con números/códigos relevantes que veas en la pieza.
8. Compatibilidad_probable_resumen: texto corto explicando a qué tipo de motos / motocarros aplica.
9. Fitment_detallado: lista estructurada de compatibilidades (marca, modelo, cilindraje, años aproximados, sistema, posicion, es_motocarguero, notas).
10. Riesgos_o_advertencias: riesgos de montaje errado, diferencias visuales a revisar, etc.
11. Nombre_comercial_catalogo: cómo mostrarías el nombre del producto en el catálogo.
12. Palabras_clave_sugeridas: lista de keywords para SEO y filtros (en español).

5) SALIDA JSON ESTRICTA

Devuelve SOLO un JSON con este esquema EXACTO:

{
  "identificacion_repuesto": "string",
  "funcion_principal": "string",
  "sistema": "string",
  "posicion_vehiculo": "string",
  "tipo_vehiculo_principal": "string",  // 'moto', 'motocarguero' o 'mixto'
  "caracteristicas_visuales": "string",
  "numeros_referencia_visibles": ["..."],
  "compatibilidad_probable_resumen": "string",
  "fitment_detallado": [
    {
      "marca": "string (o 'Generico')",
      "modelo": "string (o 'Universal')",
      "cilindraje": "string (ej: '125', '100-125', '150-200')",
      "anios_aproximados": "string (ej: '2005-2015' o '' si no aplica)",
      "sistema": "string (ej: 'freno tambor trasero')",
      "posicion": "string (ej: 'trasero', 'delantero')",
      "es_motocarguero": true,
      "notas": "string"
    }
  ],
  "nivel_confianza_fitment": 0.0,
  "riesgos_o_advertencias": "string",
  "nombre_comercial_catalogo": "string",
  "palabras_clave_sugeridas": ["...", "..."],
  "requiere_revision_humana": true
}

REGLAS FINALES:
- 'nivel_confianza_fitment' entre 0.0 y 1.0.
- Si el fitment es muy especulativo, usa un valor bajo (ej: 0.2) y pon 'requiere_revision_humana': true.
- Si no puedes determinar modelos concretos, usa 'Generico' / 'Universal' y explica en notas.
- NO agregues texto fuera del JSON.
"""


def pedir_analisis_360(img_path: str) -> dict | None:
    img64 = encode_image(img_path)
    if not img64:
        return None

    filename = os.path.basename(img_path)

    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.0,
            max_tokens=900,
            messages=[
                {
                    "role": "system",
                    "content": "Eres un ingeniero de datos de producto para catálogo de repuestos de moto y motocarguero. Respondes SOLO en JSON válido."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": PROMPT_360 + f"\n\nNombre del archivo (ya renombrado SEO): {filename}\nRecuerda: SOLO JSON."
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
        content = content.replace("```json", "").replace("```", "").strip()
        data = json.loads(content)
        return data
    except Exception as e:
        print(f"   [ERROR IA 360] {os.path.basename(img_path)} -> {e}")
        return None


# ====================================================
# 🧵 MULTIHILO 360
# ====================================================

def worker_360(q: queue.Queue, resultados: list, taxonomia: dict):
    while True:
        try:
            img_path = q.get_nowait()
        except queue.Empty:
            break

        filename = os.path.basename(img_path)
        data = pedir_analisis_360(img_path)

        if not data:
            resultados.append({
                "filename": filename,
                "error": "IA_sin_respuesta",
                "raw_json": "{}",
                "componente_estandar": "",
                "codigo_new": "",
                "product_type": ""
            })
            print(f"[IA ERROR 360] {filename}")
            q.task_done()
            continue

        # Intentar mapear componente a taxonomía
        componente = data.get("identificacion_repuesto", "")
        clave_comp = normalizar_clave_componente(componente)
        codigo_new = ""
        product_type = ""

        if taxonomia:
            # Se asume que taxonomia_kaiqi.json tiene algo como:
            # { "pastillas de freno": {"codigo_new": "...", "product_type": "..."} }
            for k, v in taxonomia.items():
                if normalizar_clave_componente(k) in clave_comp or clave_comp in normalizar_clave_componente(k):
                    codigo_new = v.get("codigo_new", "")
                    product_type = v.get("product_type", "")
                    break

        resultados.append({
            "filename": filename,
            "error": "",
            "raw_json": json.dumps(data, ensure_ascii=False),
            "componente_estandar": componente,
            "codigo_new": codigo_new,
            "product_type": product_type
        })

        print(f"[OK 360] {filename}")
        q.task_done()


def main():
    ensure_dirs()
    taxonomia = load_taxonomia()

    exts = (".jpg", ".jpeg", ".png", ".webp")
    files = [
        os.path.join(IMAGE_DIR, f)
        for f in os.listdir(IMAGE_DIR)
        if os.path.isfile(os.path.join(IMAGE_DIR, f)) and f.lower().endswith(exts)
    ]

    if not files:
        print(f"❌ No se encontraron imágenes en {IMAGE_DIR}")
        return

    print("==============================================")
    print("  🟣 Catálogo 360° KAIQI v4 (Vision gpt-4o)")
    print("==============================================")
    print(f"📸 Total imágenes a procesar: {len(files)}\n")

    q = queue.Queue()
    for f in files:
        q.put(f)

    resultados = []
    threads = []
    for _ in range(NUM_WORKERS):
        t = threading.Thread(target=worker_360, args=(q, resultados, taxonomia))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    # Guardar CSV maestro
    with open(CATALOGO_360_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "filename",
            "error",
            "componente_estandar",
            "codigo_new",
            "product_type",
            "raw_json_360"
        ])
        for r in resultados:
            writer.writerow([
                r["filename"],
                r["error"],
                r["componente_estandar"],
                r["codigo_new"],
                r["product_type"],
                r["raw_json"]
            ])

    print("\n✅ Catálogo 360° generado.")
    print(f"   → Archivo: {CATALOGO_360_CSV}")


if __name__ == "__main__":
    main()
