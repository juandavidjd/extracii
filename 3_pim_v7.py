#!/usr/bin/env python3
# ============================================================
# pim_kaiqi_v7.py — ENTERPRISE REAL & STABLE
# ============================================================

import os
import json
import csv
import time
import base64
import hashlib

import pandas as pd
from openai import OpenAI

# ============================================================
# CARGAR CONFIG
# ============================================================

CONFIG_PATH = "config_pim_v7.json"
if not os.path.exists(CONFIG_PATH):
    raise FileNotFoundError("No existe config_pim_v7.json")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    cfg = json.load(f)

INVENTARIO_PATH = cfg["inventario"]
IMAGE_DIR       = cfg["image_dir"]
CSV_SHOPIFY     = cfg["shopify_csv"]
JSON_PIM        = cfg["pim_json"]
MODEL           = cfg["model"]

RATE_LIMIT = 20
CACHE_SIMILARITY = {}
LAST_CALLS = []

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ============================================================
# RATE LIMIT
# ============================================================

def rate_limit():
    now = time.time()
    LAST_CALLS.append(now)

    while LAST_CALLS and now - LAST_CALLS[0] > 60:
        LAST_CALLS.pop(0)

    if len(LAST_CALLS) >= RATE_LIMIT:
        sleep_t = 60 - (now - LAST_CALLS[0])
        if sleep_t > 0:
            time.sleep(sleep_t)


# ============================================================
# ENCODE IMAGE
# ============================================================

def encode_image(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except:
        return None


# ============================================================
# IA MATCHING (DESCRIPCIÓN INVENTARIO ↔ IMAGEN)
# ============================================================

def ia_match_confidence(descripcion, image_path):
    """Devuelve un score 0–1 indicando similitud inventario ↔ foto."""

    if not os.path.exists(image_path):
        return 0.0

    # Cache key
    key = hashlib.md5((descripcion + "||" + image_path).encode()).hexdigest()
    if key in CACHE_SIMILARITY:
        return CACHE_SIMILARITY[key]

    img64 = encode_image(image_path)
    if not img64:
        return 0.0

    prompt = f"""
Evalúa qué tan probable es que la imagen corresponda a esta descripción de inventario:

DESCRIPCIÓN INVENTARIO:
{descripcion}

Devuelve SOLO JSON así:
{{"match_conf": 0.0 a 1.0}}
"""

    try:
        rate_limit()
        r = client.chat.completions.create(
            model=MODEL,
            temperature=0,
            max_tokens=50,
            messages=[
                {"role": "system", "content": "Responde únicamente JSON válido."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img64}",
                                "detail": "low"
                            }
                        }
                    ]
                }
            ]
        )
        raw = r.choices[0].message.content.replace("```json", "").replace("```", "").strip()
        js = json.loads(raw)
        conf = float(js.get("match_conf", 0))

    except:
        conf = 0.0

    CACHE_SIMILARITY[key] = conf
    return conf


# ============================================================
# PROCESAR PIM
# ============================================================

def main():
    print("==============================================")
    print("  🟢 PIM Kaiqi v7 — Fusionando Inventario + 360 + SEO")
    print("==============================================\n")

    # -------------------------------------------------------
    # 1. Cargar inventario
    # -------------------------------------------------------
    if not os.path.exists(INVENTARIO_PATH):
        raise FileNotFoundError(f"No existe inventario → {INVENTARIO_PATH}")

    df = pd.read_csv(INVENTARIO_PATH, encoding="utf-8")

    # Generar descripción concatenada
    df["DESC_FULL"] = df.apply(
        lambda r: " ".join([
            str(v) for v in r.values
            if isinstance(v, str) and v.strip() not in ("nan", "")
        ]),
        axis=1
    )

    # -------------------------------------------------------
    # 2. Lista de imágenes SEO ya renombradas
    # -------------------------------------------------------
    imagenes = [
        f for f in os.listdir(IMAGE_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    ]

    print(f"Total imágenes detectadas: {len(imagenes)}\n")

    # -------------------------------------------------------
    # 3. Matching IA — EMPAREJAR MEJOR IMAGEN PARA CADA ITEM
    # -------------------------------------------------------
    filas_shopify = []
    pim_json_list = []

    for idx, row in df.iterrows():
        desc = row["DESC_FULL"]
        codigo = row.get("CODIGO_NEW", "")
        titulo = row.get("DESCRIPCION", row.get("TITULO", desc))

        print(f"[{idx+1}/{len(df)}] Producto: {titulo}")

        mejor_img = None
        mejor_conf = 0.0

        for img in imagenes:
            pimg = os.path.join(IMAGE_DIR, img)
            conf = ia_match_confidence(desc, pimg)
            if conf > mejor_conf:
                mejor_conf = conf
                mejor_img = img

        # Construir URL local
        img_url = f"file://{os.path.join(IMAGE_DIR, mejor_img)}" if mejor_img else ""

        # ---------------------------------------------------
        # Shopify row
        # ---------------------------------------------------
        filas_shopify.append([
            codigo,
            titulo,
            titulo,
            "KAIQI",
            row.get("COMPONENTE", ""),
            row.get("SISTEMA", ""),
            row.get("PRECIO", 0),
            img_url
        ])

        # ---------------------------------------------------
        # PIM JSON estructurado
        # ---------------------------------------------------
        pim_json_list.append({
            "codigo": codigo,
            "titulo": titulo,
            "descripcion_completa": desc,
            "imagen_elegida": mejor_img,
            "imagen_url": img_url,
            "match_conf": mejor_conf
        })

    # -------------------------------------------------------
    # 4. Exportar CSV Shopify
    # -------------------------------------------------------
    with open(CSV_SHOPIFY, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["HANDLE", "TITLE", "BODY", "VENDOR", "TYPE", "TAGS", "PRICE", "IMAGE"])
        for row in filas_shopify:
            w.writerow(row)

    # -------------------------------------------------------
    # 5. Exportar JSON PIM
    # -------------------------------------------------------
    with open(JSON_PIM, "w", encoding="utf-8") as f:
        json.dump(pim_json_list, f, ensure_ascii=False, indent=2)

    print("\n🎯 PIM v7 COMPLETADO")
    print(f"CSV Shopify: {CSV_SHOPIFY}")
    print(f"PIM JSON:    {JSON_PIM}")


# ============================================================
if __name__ == "__main__":
    main()
