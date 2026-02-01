#!/usr/bin/env python3
# ============================================================
# catalogo_360_kaiqi_v4.1.py — ENTERPRISE REAL & STABLE
# ============================================================

import os
import json
import base64
import time
import csv
from openai import OpenAI

# ============================================================
# CONFIGURACIÓN — ajustada a tu proyecto
# ============================================================

IMAGE_DIR = "C:/img/IMAGENES_KAIQI_MAESTRAS"
OUT_CSV   = "C:/img/catalogo_360_kaiqi_v4.1.csv"
MODEL     = "gpt-4o"
RATE_LIMIT = 20     # llamadas/minuto
MAX_RETRY  = 3

# ============================================================
# OPENAI CLIENT
# ============================================================

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
LAST_CALLS = []


def rate_limit():
    """Respeta el límite de llamadas por minuto."""
    now = time.time()
    LAST_CALLS.append(now)

    # limpiar historial >60s
    while LAST_CALLS and now - LAST_CALLS[0] > 60:
        LAST_CALLS.pop(0)

    if len(LAST_CALLS) >= RATE_LIMIT:
        sleep_t = 60 - (now - LAST_CALLS[0])
        if sleep_t > 0:
            time.sleep(sleep_t)


# ============================================================
# FUNCIONES UTILITARIAS
# ============================================================

def encode_image(filepath):
    try:
        with open(filepath, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except:
        return None


# ============================================================
# PROMPT 360° (REAL)
# ============================================================

PROMPT_360 = """
Debes analizar la imagen del repuesto y devolver SOLO JSON con ESTE FORMATO EXACTO:

{
  "identificacion_repuesto": "",
  "funcion_principal": "",
  "sistema": "",
  "posicion_vehiculo": "",
  "tipo_vehiculo_principal": "",  
  "caracteristicas_visuales": "",
  "numeros_referencia_visibles": [],
  "compatibilidad_probable_resumen": "",
  "fitment_detallado": [
    {
      "marca": "",
      "modelo": "",
      "cilindraje": "",
      "anios_aproximados": "",
      "sistema": "",
      "posicion": "",
      "es_motocarguero": false,
      "notas": ""
    }
  ],
  "nivel_confianza_fitment": 0.0,
  "riesgos_o_advertencias": "",
  "nombre_comercial_catalogo": "",
  "palabras_clave_sugeridas": [],
  "requiere_revision_humana": true
}

REGLAS IMPORTANTES:
- No inventes vehículos si no estás seguro.
- Si solo se puede afirmar compatibilidad genérica → usar "Generico" o "Universal".
- Si detectas números molde, inclúyelos.
- Usa siempre español técnico.
- No usar marcas grabadas de fabricación como "JAPAN" para fitment.
"""


# ============================================================
# FUNCIÓN DE ANÁLISIS 360
# ============================================================

def analizar_360(filepath):
    filename = os.path.basename(filepath)
    img64 = encode_image(filepath)
    if not img64:
        return {}

    payload_img = {
        "type": "image_url",
        "image_url": {
            "url": f"data:image/jpeg;base64,{img64}",
            "detail": "high"
        }
    }

    for _ in range(MAX_RETRY):
        try:
            rate_limit()

            response = client.chat.completions.create(
                model=MODEL,
                temperature=0,
                max_tokens=900,
                messages=[
                    {"role": "system", "content": "Responde únicamente JSON válido."},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": PROMPT_360},
                            payload_img
                        ]
                    }
                ]
            )

            raw = response.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            data = json.loads(raw)
            return data

        except Exception as e:
            time.sleep(2)

    return {}


# ============================================================
# EJECUCIÓN PRINCIPAL
# ============================================================

def main():
    print("==============================================")
    print("  🟣 Catálogo 360° Kaiqi v4.1 — Iniciando")
    print("==============================================")

    images = [
        f for f in os.listdir(IMAGE_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    ]

    rows = []

    for img in images:
        path = os.path.join(IMAGE_DIR, img)
        print(f"Procesando: {img}")

        data360 = analizar_360(path)
        rows.append([img, json.dumps(data360, ensure_ascii=False)])

    # --------------------------------------------------------
    # Exportar CSV final
    # --------------------------------------------------------
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "raw_json_360"])

        for r in rows:
            writer.writerow(r)

    print("\n🎯 Catálogo 360° generado exitosamente.")
    print(f"Archivo creado: {OUT_CSV}")


# ============================================================
if __name__ == "__main__":
    main()
