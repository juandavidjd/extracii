#!/usr/bin/env python3
# ============================================================
# renombrar_seo_kaiqi_v6.py — HÍBRIDO (Inventario + IA + Hash)
# ============================================================
# Objetivo:
# - Renombrar imágenes usando CODIGO_NEW + DESCRIPCION del inventario
# - IA solo como apoyo, no decide el slug
# - Evitar slugs genéricos ("pieza", "bici", "repuesto")
# - Evitar duplicados con hash corto
# - NO usar la IA para inventar modelos
#
# Requisitos:
# - config_renombrado_seo_v6.json en C:/img
# - Inventario_FINAL_CON_TAXONOMIA.csv en C:/img (sep=';')
# - Carpeta imágenes: C:/img/IMAGENES_KAIQI_MAESTRAS
#
# ============================================================

import os
import csv
import json
import base64
import time
import unicodedata
import re
import hashlib
import shutil

import pandas as pd
from openai import OpenAI


# ============================================================
# UTILIDADES
# ============================================================

def slugify(text: str) -> str:
    """Convierte texto en slug SEO seguro."""
    if not isinstance(text, str):
        text = str(text or "")

    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("ñ", "n")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")


def compute_hash_short(path: str, length: int = 6) -> str:
    """Hash corto del contenido de la imagen, para asegurar unicidad."""
    try:
        with open(path, "rb") as f:
            data = f.read()
        h = hashlib.sha1(data).hexdigest()
        return h[:length]
    except Exception:
        return ""


def encode_image(path: str) -> str | None:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return None


def is_generic_slug(slug: str) -> bool:
    """Detecta slugs genéricos que NO queremos usar."""
    if not slug:
        return True

    genericos = {
        "pieza", "pieza-moto", "pieza-motocicleta", "pieza-metalica",
        "pieza-plastica", "pieza-desconocida", "repuesto", "repuesto-moto",
        "kit", "kit-repuesto", "componente", "parte", "producto",
        "articulo", "item", "freno", "banda", "bicicleta", "bici",
        "sin-nombre", "undefined", "desconocido"
    }

    if slug in genericos:
        return True

    # muy cortos también los consideramos sospechosos
    if len(slug) <= 6:
        return True

    return False


# ============================================================
# RATE LIMIT BÁSICO IA
# ============================================================

RATE_LIMIT = 20  # llamadas/min
_LAST_CALLS = []


def rate_limit():
    now = time.time()
    _LAST_CALLS.append(now)
    while _LAST_CALLS and now - _LAST_CALLS[0] > 60:
        _LAST_CALLS.pop(0)

    if len(_LAST_CALLS) >= RATE_LIMIT:
        sleep_t = 60 - (now - _LAST_CALLS[0])
        if sleep_t > 0:
            time.sleep(sleep_t)


# ============================================================
# IA: SUGERENCIA COMPLEMENTARIA
# ============================================================

def ia_sugerir_componente(client: OpenAI, model: str, img64: str, descripcion: str) -> str:
    """
    Usa IA como APOYO para refinar componente.
    No reemplaza inventario.
    """

    prompt = f"""
Actúa como experto en repuestos de MOTO / MOTOCARGUERO.

Te doy:
1) Descripción del inventario (texto confiable).
2) Imagen (solo apoyo visual).

Devuelve SOLO un string: "componente_refinado".
- NO digas "bicicleta", "pieza", "repuesto" o genéricos.
- NO inventes modelos ni marcas.
- Si no puedes mejorar, devuelve "".

Responde solo:
{{ "componente_refinado": "..." }}

Descripción de inventario:
{descripcion}
"""

    try:
        rate_limit()
        resp = client.chat.completions.create(
            model=model,
            temperature=0,
            max_tokens=80,
            messages=[
                {
                    "role": "system",
                    "content": "Responde solo JSON válido."
                },
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
        raw = resp.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        comp = data.get("componente_refinado", "").strip().lower()

        if is_generic_slug(slugify(comp)):
            return ""
        return comp
    except Exception:
        return ""


# ============================================================
# PROCESO PRINCIPAL
# ============================================================

def main():

    # -------------------------------
    # Cargar config
    # -------------------------------
    CONFIG_PATH = "config_renombrado_seo_v6.json"
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError("No existe config_renombrado_seo_v6.json en C:\\img")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    IMAGE_DIR   = cfg["image_dir"]
    OUTPUT_DIR  = cfg["output_dir"]
    MODEL       = cfg["model"]
    LOG_NAME    = cfg["log_filename"]
    INVENTARIO  = cfg["inventario_path"]
    HASH_LEN    = int(cfg.get("hash_length", 6))

    DUP_DIR = os.path.join(OUTPUT_DIR, "IMAGENES_DUPLICADAS")
    os.makedirs(DUP_DIR, exist_ok=True)

    LOG_PATH = os.path.join(OUTPUT_DIR, LOG_NAME)

    # -------------------------------
    # Cliente OpenAI
    # -------------------------------
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # -------------------------------
    # Cargar inventario (SEPARADOR ;)
    # -------------------------------
    if not os.path.exists(INVENTARIO):
        raise FileNotFoundError(f"No se encontró inventario: {INVENTARIO}")

    inv = pd.read_csv(INVENTARIO, encoding="utf-8", sep=";")

    if "CODIGO_NEW" not in inv.columns or "DESCRIPCION" not in inv.columns:
        raise ValueError("El inventario debe tener CODIGO_NEW y DESCRIPCION.")

    # índice CODIGO_NEW
    codigos = inv["CODIGO_NEW"].astype(str).tolist()

    def buscar_fila_por_nombre(fname: str):
        base = os.path.splitext(fname)[0].lower()
        for cod in codigos:
            if cod.lower() in base:
                row = inv[inv["CODIGO_NEW"].astype(str) == cod]
                if not row.empty:
                    return row.iloc[0]
        return None

    # -------------------------------
    # Recorrer imágenes
    # -------------------------------
    files = [
        f for f in os.listdir(IMAGE_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    ]

    used_names = set()

    with open(LOG_PATH, "w", encoding="utf-8", newline="") as flog:
        writer = csv.writer(flog)
        writer.writerow([
            "archivo_original",
            "archivo_nuevo",
            "slug_final",
            "codigo_new",
            "descripcion_base",
            "componente_refinado_ia",
            "hash",
            "origen_slug",
            "estado"
        ])

        print("==============================================")
        print("  🟣 Renombrador SEO KAIQI v6 — HÍBRIDO")
        print("==============================================")
        print(f"📸 Imágenes detectadas: {len(files)}\n")

        for fname in files:

            src_path = os.path.join(IMAGE_DIR, fname)
            ext = os.path.splitext(fname)[1].lower()

            fila = buscar_fila_por_nombre(fname)
            codigo_new = ""
            desc = ""
            origen_slug = "inventario+ia"

            if fila is not None:
                codigo_new = str(fila["CODIGO_NEW"])
                desc = str(fila["DESCRIPCION"])
            else:
                codigo_new = ""
                desc = os.path.splitext(fname)[0]
                origen_slug = "nombre_archivo+ia"

            base_cod  = slugify(codigo_new)
            base_desc = slugify(desc)

            if base_cod and base_desc:
                base_slug = f"{base_cod}-{base_desc}"
            elif base_desc:
                base_slug = base_desc
            else:
                base_slug = base_cod

            img64 = encode_image(src_path)
            componente_refinado = ""

            if img64:
                componente_refinado = ia_sugerir_componente(client, MODEL, img64, desc)

            if componente_refinado:
                base_slug = f"{base_slug}-{slugify(componente_refinado)}"

            if is_generic_slug(base_slug):
                base_slug = slugify(os.path.splitext(fname)[0])

            hshort = compute_hash_short(src_path, length=HASH_LEN)
            if hshort:
                slug_final = f"{base_slug}-{hshort}"
            else:
                slug_final = base_slug

            original_slug = slug_final
            cnt = 1
            while slug_final in used_names:
                cnt += 1
                slug_final = f"{original_slug}-{cnt}"

            used_names.add(slug_final)
            new_name = f"{slug_final}{ext}"
            dst_path = os.path.join(IMAGE_DIR, new_name)

            estado = "OK"

            if os.path.exists(dst_path) and os.path.abspath(dst_path) != os.path.abspath(src_path):
                shutil.move(src_path, os.path.join(DUP_DIR, fname))
                estado = "MOVIDO_DUPLICADOS"
                writer.writerow([
                    fname, fname, slug_final, codigo_new, desc,
                    componente_refinado, hshort, origen_slug, estado
                ])
                print(f"[DUPLICADO REAL] {fname}")
                continue

            try:
                os.rename(src_path, dst_path)
            except Exception as e:
                estado = f"ERROR_RENOMBRANDO:{e}"
                writer.writerow([
                    fname, fname, slug_final, codigo_new, desc,
                    componente_refinado, hshort, origen_slug, estado
                ])
                print(f"[ERROR] {fname} -> {e}")
                continue

            writer.writerow([
                fname, new_name, slug_final, codigo_new, desc,
                componente_refinado, hshort, origen_slug, estado
            ])

            print(f"[OK] {fname} -> {new_name}")

    print("\n✅ Renombrado SEO v6 finalizado.")
    print(f"   → Log: {LOG_PATH}")
    print(f"   → Duplicados reales: {DUP_DIR}")


if __name__ == "__main__":
    main()
