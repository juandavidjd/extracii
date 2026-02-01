#!/usr/bin/env python3
# ============================================================
# renombrar_seo_kaiqi_v5.py — ENTERPRISE REAL & STABLE
# ============================================================

import os
import json
import base64
import time
import unicodedata
import re
import shutil
from openai import OpenAI

# ============================================================
# UTILIDADES
# ============================================================

def slugify(text):
    """Convierte texto en slug SEO seguro."""
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("ñ", "n")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")


def encode_image(filepath):
    """Convierte imagen → base64."""
    try:
        with open(filepath, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except:
        return None


# ============================================================
# SCRIPT PRINCIPAL
# ============================================================

def main():
    # ---------------------------------------------------------
    # Cargar config
    # ---------------------------------------------------------
    CONFIG_PATH = "config_renombrado_seo_v5.json"
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError("No existe config_renombrado_seo_v5.json")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    IMAGE_DIR   = cfg["image_dir"]
    OUTPUT_DIR  = cfg["output_dir"]
    MODEL       = cfg["model"]
    LOG_NAME    = cfg["log_filename"]

    DUP_DIR = os.path.join(OUTPUT_DIR, "IMAGENES_DUPLICADAS")
    os.makedirs(DUP_DIR, exist_ok=True)

    LOG_PATH = os.path.join(OUTPUT_DIR, LOG_NAME)

    # ---------------------------------------------------------
    # Cliente OpenAI
    # ---------------------------------------------------------
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # ---------------------------------------------------------
    # Recorrer imágenes
    # ---------------------------------------------------------
    files = [
        f for f in os.listdir(IMAGE_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    ]

    used_slugs = set()

    with open(LOG_PATH, "w", encoding="utf-8") as log:
        log.write("archivo_original,archivo_nuevo,slug,estado\n")

        for fname in files:
            src_path = os.path.join(IMAGE_DIR, fname)

            img64 = encode_image(src_path)
            if not img64:
                log.write(f"{fname},{fname},,''error_image''\n")
                continue

            # -----------------------------------------------------
            # Prompt Vision 4o
            # -----------------------------------------------------
            prompt = """
Devuelve SOLO JSON:
{
 "nombre_base_seo": "string"
}
"""

            try:
                r = client.chat.completions.create(
                    model=MODEL,
                    temperature=0,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
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

                raw = r.choices[0].message.content.strip()
                raw = raw.replace("```json", "").replace("```", "")
                js = json.loads(raw)
                seo = js.get("nombre_base_seo", "").strip()

            except:
                # Si falla la IA, usamos el nombre actual
                seo = os.path.splitext(fname)[0]

            slug = slugify(seo)
            if not slug:
                slug = slugify(os.path.splitext(fname)[0])

            ext = os.path.splitext(fname)[1]
            new_name = f"{slug}{ext}"
            dst_path = os.path.join(IMAGE_DIR, new_name)

            # -----------------------------------------------------
            # Manejo de duplicados
            # -----------------------------------------------------
            if slug in used_slugs:
                shutil.move(src_path, os.path.join(DUP_DIR, fname))
                log.write(f"{fname},{fname},{slug},DUPLICADO\n")
                continue

            used_slugs.add(slug)

            if os.path.exists(dst_path) and dst_path != src_path:
                shutil.move(src_path, os.path.join(DUP_DIR, fname))
                log.write(f"{fname},{fname},{slug},COLISION\n")
                continue

            # -----------------------------------------------------
            # Renombrar
            # -----------------------------------------------------
            os.rename(src_path, dst_path)
            log.write(f"{fname},{new_name},{slug},OK\n")

    print("🎯 RENOMBRADO SEO v5 COMPLETADO — Logs generados.")


# ============================================================
if __name__ == "__main__":
    main()
