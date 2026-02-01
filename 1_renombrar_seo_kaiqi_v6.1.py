#!/usr/bin/env python3
# ============================================================
# 1_renombrar_seo_kaiqi_v6.1.py — PRODUCCIÓN
# ============================================================
# Objetivo:
# - Renombrar imágenes usando inventario real + IA Vision 4o
# - Usar slugs tipo: componente-marca-modelo-cilindraje-codigonuevo.jpg
# - Detectar duplicados
# - Log detallado CSV
#
# Requisitos:
# - Inventario: Inventario_FINAL_CON_TAXONOMIA.csv (sep=";")
# - Columnas requeridas: CODIGO NEW, DESCRIPCION
# ============================================================

import os
import re
import time
import json
import base64
import shutil
import unicodedata
import pandas as pd
from openai import OpenAI


# ============================================================
# CONFIGURACIÓN GLOBAL
# ============================================================

CONFIG_JSON = "config_renombrado_seo_v5.json"
if not os.path.exists(CONFIG_JSON):
    raise FileNotFoundError("❌ No existe config_renombrado_seo_v5.json")

with open(CONFIG_JSON, "r", encoding="utf-8") as f:
    CFG = json.load(f)

IMAGE_DIR = CFG["image_dir"]
INVENTARIO = CFG["inventario_path"]
OUTPUT_DIR = CFG["output_dir"]
DIR_DUPLICADOS = os.path.join(OUTPUT_DIR, "IMAGENES_DUPLICADAS")
DIR_LOGS = os.path.join(OUTPUT_DIR, "LOGS")
MODEL = CFG["model"]
SLUG_FORMAT = CFG["slug_format"]   # B (tu elección)
LOG_CSV = os.path.join(DIR_LOGS, "log_renombrado_seo_v6.1.csv")

os.makedirs(DIR_DUPLICADOS, exist_ok=True)
os.makedirs(DIR_LOGS, exist_ok=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

LAST_CALLS = []
RATE_LIMIT = 20


# ============================================================
# UTILIDADES
# ============================================================

def rate_limit():
    now = time.time()
    LAST_CALLS.append(now)
    while LAST_CALLS and now - LAST_CALLS[0] > 60:
        LAST_CALLS.pop(0)
    if len(LAST_CALLS) >= RATE_LIMIT:
        sleep_t = 60 - (now - LAST_CALLS[0])
        time.sleep(max(1, sleep_t))


def encode_image(path: str) -> str | None:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except:
        return None


def slugify(txt: str) -> str:
    if not txt:
        return ""
    txt = unicodedata.normalize("NFD", txt)
    txt = "".join(c for c in txt if unicodedata.category(c) != "Mn")
    txt = txt.replace("ñ", "n")
    txt = txt.lower()

    txt = re.sub(r"[^a-z0-9\s-]", " ", txt)
    txt = re.sub(r"[\s_]+", "-", txt)
    txt = re.sub(r"-{2,}", "-", txt)
    return txt.strip("-")


# ============================================================
# PROMPT IA — Renombrado SEO
# ============================================================

PROMPT_RENAME = """
Actúa como EXPERTO en catálogo de repuestos de motocicletas y motocarros.

Analiza la imagen y el texto proporcionado para generar un NOMBRE SEO perfecto.

Reglas:
- Usa componente + marca + modelo + cilindraje + codigo_new si aplica.
- No uses texto grabado irrelevante (ej "JAPAN").
- Mantén números molde reales si se ven.
- No inventes modelos exactos.
- Formato final: slug SEO (sin extensión).
- Solo devuelve JSON:

{
  "nombre_base_seo": "",
  "componente": "",
  "marca_moto": "",
  "modelo_moto": "",
  "cilindraje": "",
  "numeros_molde": "",
  "observaciones": ""
}
"""


# ============================================================
# IA CALL
# ============================================================

def pedir_nombre_seo(img64, filename, desc, codigo_new):
    rate_limit()
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            temperature=0,
            max_tokens=400,
            messages=[
                {
                    "role": "system",
                    "content": "Responde SOLO JSON válido."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": PROMPT_RENAME + 
                            f"\n\nArchivo: {filename}\n"
                            f"Descripción del inventario: {desc}\n"
                            f"Codigo NEW: {codigo_new}\n"
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

        raw = resp.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "")
        return json.loads(raw)

    except Exception as e:
        print(f"[ERROR IA] {filename} -> {e}")
        return None


# ============================================================
# PROCESO PRINCIPAL
# ============================================================

def main():

    print("==============================================")
    print(" 🔵 RENOMBRAR SEO KAIQI v6.1 — PRODUCCIÓN")
    print("==============================================\n")

    # Cargar inventario
    inv = pd.read_csv(INVENTARIO, sep=";", encoding="utf-8")

    # Validar columnas
    if "CODIGO NEW" not in inv.columns or "DESCRIPCION" not in inv.columns:
        raise ValueError("El inventario debe tener 'CODIGO NEW' y 'DESCRIPCION'.")

    # Cargar imágenes
    imgs = [
        f for f in os.listdir(IMAGE_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    ]

    if not imgs:
        print("❌ No hay imágenes en carpeta.")
        return

    print(f"📦 Imágenes detectadas: {len(imgs)}\n")

    # Cache CODIGO→descripcion
    map_desc = dict(zip(inv["CODIGO NEW"].astype(str), inv["DESCRIPCION"].astype(str)))

    slugs_vistos = {}
    log_rows = []

    for fname in imgs:

        full_path = os.path.join(IMAGE_DIR, fname)
        img64 = encode_image(full_path)

        codigo_detectado = ""
        desc = ""

        # detectar codigo_new dentro del nombre
        for cod in map_desc.keys():
            if cod.lower() in fname.lower():
                codigo_detectado = cod
                desc = map_desc[cod]
                break

        if not desc:
            desc = ""

        data_ia = pedir_nombre_seo(img64, fname, desc, codigo_detectado)

        if not data_ia or "nombre_base_seo" not in data_ia:
            print(f"[IA ERROR] {fname}")
            continue

        slug = slugify(data_ia["nombre_base_seo"])

        ext = os.path.splitext(fname)[1].lower()
        new_name = f"{slug}{ext}"
        new_path = os.path.join(IMAGE_DIR, new_name)

        # duplicado por slug
        if slug in slugs_vistos:
            shutil.move(full_path, os.path.join(DIR_DUPLICADOS, fname))
            print(f"[DUP] {fname} -> duplicados/")
            log_rows.append([fname, fname, slug, "SI", json.dumps(data_ia, ensure_ascii=False)])
            continue

        slugs_vistos[slug] = fname

        # colisión física
        if os.path.exists(new_path) and new_path != full_path:
            shutil.move(full_path, os.path.join(DIR_DUPLICADOS, fname))
            print(f"[COLISION] {fname} -> duplicados/")
            log_rows.append([fname, fname, slug, "COLISION", json.dumps(data_ia, ensure_ascii=False)])
            continue

        # renombrar
        os.rename(full_path, new_path)
        print(f"[OK] {fname} -> {new_name}")

        log_rows.append([fname, new_name, slug, "NO", json.dumps(data_ia, ensure_ascii=False)])


    # Guardar log
    with open(LOG_CSV, "w", encoding="utf-8", newline="") as f:
        import csv
        w = csv.writer(f)
        w.writerow(["archivo_original", "archivo_nuevo", "slug", "duplicado", "json"])
        for row in log_rows:
            w.writerow(row)

    print("\n✅ PROCESO FINALIZADO.")
    print(f"📄 Log: {LOG_CSV}")
    print(f"🗂 Duplicados: {DIR_DUPLICADOS}")


if __name__ == "__main__":
    main()
