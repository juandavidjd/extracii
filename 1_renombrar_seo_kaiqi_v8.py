#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ========================================================================
#  1_renombrar_seo_kaiqi_v8.py
#
#  Renombrador SEO ULTRA PRO para Kaiqi — con IA Vision 4o + 3 catálogos:
#   - Inventario_FINAL_CON_TAXONOMIA.csv
#   - LISTA DE PRECIOS NOVIEMBRE 13 2025 TRABAJO JC.xlsx
#   - LISTA DE PRECIOS YOKOMAR ACTUALIZADA 2025.xlsx
#
#  Motor híbrido inteligente:
#      SI IA_confianza >= 0.70 → IA manda
#      SI IA_confianza < 0.70 → Inventario manda
#      Si no está → JC
#      Si no está → YOKO
#      Si todo falla → fallback IA+heurística
#
#  Resultados:
#   - Slug SEO perfecto
#   - Fitment-ready
#   - Moto vs Motocarro
#   - Marca, Modelo, Cilindraje
#   - Números molde
#   - Log detallado
#   - Sin pérdida de imágenes
# ========================================================================

import os
import re
import csv
import json
import hashlib
import base64
import unicodedata
import pandas as pd
from openai import OpenAI

# ========================================================================
# CONFIGURACIÓN GENERAL
# ========================================================================

BASE_DIR = r"C:\img"
IMAGE_DIR = os.path.join(BASE_DIR, "IMAGENES_KAIQI_MAESTRAS")
INVENTARIO_CSV = os.path.join(BASE_DIR, "Inventario_FINAL_CON_TAXONOMIA.csv")
YOKO_XLSX = os.path.join(BASE_DIR, "LISTA DE PRECIOS  YOKOMAR ACTUALIZADA 2025.xlsx")
JC_XLSX = os.path.join(BASE_DIR, "LISTA DE PRECIOS NOVIEMBRE 13 2025 TRABAJO JC.xlsx")

LOG_DIR = os.path.join(BASE_DIR, "LOGS")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_CSV = os.path.join(LOG_DIR, "log_renombrado_seo_v8.csv")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ========================================================================
# UTILIDADES
# ========================================================================

def slugify(text: str) -> str:
    """Convierte texto en slug SEO."""
    if not text:
        return ""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("ñ", "n")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")


def encode_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def file_hash(path: str) -> str:
    """Hash SHA1 del archivo para detectar duplicados reales."""
    sha = hashlib.sha1()
    with open(path, "rb") as f:
        while True:
            block = f.read(65536)
            if not block:
                break
            sha.update(block)
    return sha.hexdigest()


# ========================================================================
# CARGA DE FUENTES
# ========================================================================

def cargar_inventario():
    """Carga Inventario Kaiqi: CODIGO NEW, DESCRIPCION, etc."""
    if not os.path.exists(INVENTARIO_CSV):
        print("⚠ Inventario no encontrado.")
        return {}

    df = pd.read_csv(INVENTARIO_CSV, sep=";", encoding="utf-8")
    required = ["CODIGO NEW", "DESCRIPCION"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Falta columna {col} en Inventario.")

    records = {}
    for _, row in df.iterrows():
        code = str(row["CODIGO NEW"]).strip()
        if not code:
            continue
        rec = {
            "source": "INV",
            "id_master": code,
            "code": code,
            "descripcion": str(row["DESCRIPCION"]).strip(),
            "marca": str(row.get("MARCA", "")).strip(),
            "modelo": str(row.get("MODELO", "")).strip(),
            "cilindraje": str(row.get("CILINDRAJE", "")).strip()
        }
        records[code] = rec
    return records


def cargar_jc():
    """Carga catálogo JC (CODIGO, PRODUCTO / DESCRIPCION)"""
    if not os.path.exists(JC_XLSX):
        print("⚠ No se encontró JC.")
        return {}

    xls = pd.read_excel(JC_XLSX)
    header_row = xls.iloc[8]
    data = xls.iloc[9:].copy()
    data.columns = header_row.values

    if "CODIGO" not in data.columns or "PRODUCTO / DESCRIPCION" not in data.columns:
        print("⚠ Formato JC inesperado.")
        return {}

    records = {}
    for _, row in data.iterrows():
        code = str(row["CODIGO"]).strip()
        desc = str(row["PRODUCTO / DESCRIPCION"]).strip()
        if not code or not desc or code == "nan":
            continue
        records[code] = {
            "source": "JC",
            "id_master": code,
            "code": code,
            "descripcion": desc,
            "marca": "",
            "modelo": "",
            "cilindraje": ""
        }
    return records


def cargar_yoko():
    """Carga YOKOMAR: REFERENCIA + DESCRIPCION"""
    if not os.path.exists(YOKO_XLSX):
        print("⚠ No se encontró YOKOMAR.")
        return {}

    xls = pd.read_excel(YOKO_XLSX)
    header_row = xls.iloc[8]
    data = xls.iloc[9:].copy()
    data.columns = header_row.values

    if "REFERENCIA" not in data.columns or "DESCRIPCION" not in data.columns:
        print("⚠ Formato YOKO inesperado.")
        return {}

    records = {}
    for _, row in data.iterrows():
        code = str(row["REFERENCIA"]).strip()
        desc = str(row["DESCRIPCION"]).strip()
        if not code or not desc or code == "nan":
            continue
        records[code] = {
            "source": "YOKO",
            "id_master": code,
            "code": code,
            "descripcion": desc,
            "marca": "",
            "modelo": "",
            "cilindraje": ""
        }
    return records


# ========================================================================
# IA VISION 4o
# ========================================================================

VISION_PROMPT = """
Actúa como experto en repuestos de moto/motocarro.

Devuelve SOLO un JSON con:
{
 "componente": "",
 "marca_moto": "",
 "modelo_moto": "",
 "cilindraje": "",
 "es_motocarguero": false,
 "numeros_molde": "",
 "nombre_sugerido": "",
 "confianza": 0.0
}
"""

def analizar_imagen_con_ia(path: str):
    img64 = encode_image(path)
    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.0,
            max_tokens=350,
            messages=[
                {"role": "system", "content": "Experto en repuestos. Devuelve SOLO JSON."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": VISION_PROMPT},
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
        txt = resp.choices[0].message.content.strip()
        txt = txt.replace("```json", "").replace("```", "").strip()
        return json.loads(txt)
    except Exception as e:
        print(f"[IA ERROR] {path} → {e}")
        return {
            "componente": "",
            "marca_moto": "",
            "modelo_moto": "",
            "cilindraje": "",
            "es_motocarguero": False,
            "numeros_molde": "",
            "nombre_sugerido": "",
            "confianza": 0.0
        }


# ========================================================================
# MOTOR DE DECISIÓN (OPCIÓN C)
# ========================================================================

def resolver_fuente(opt_ia, inv_rec, jc_rec, yoko_rec):
    """
    Lógica híbrida opción C:
    - IA_conf >= 0.70 → IA manda
    - < 0.70 → inventario
    - Si inventario no coincide → JC
    - Luego YOKO
    - Si nada coincide → fallback IA
    """

    ia_conf = opt_ia.get("confianza", 0.0)
    if ia_conf >= 0.70:
        return "IA"

    if inv_rec:
        return "INV"

    if jc_rec:
        return "JC"

    if yoko_rec:
        return "YOKO"

    return "IA"


# ========================================================================
# SLUG BUILDER
# ========================================================================

def construir_slug_final(fuente, ia, inv, jc, yoko, base_fallback):
    """
    Construye slug SEO final en base al motor híbrido.
    """
    if fuente == "IA":
        parts = [
            ia.get("nombre_sugerido", ""),
            ia.get("componente", ""),
            ia.get("marca_moto", ""),
            ia.get("modelo_moto", ""),
            ia.get("cilindraje", ""),
            ia.get("numeros_molde", "")
        ]
        txt = "-".join([p for p in parts if p])
        slug = slugify(txt)
        if slug:
            return slug, ia.get("nombre_sugerido", "")
        else:
            return slugify(base_fallback), base_fallback

    if fuente == "INV":
        parts = [
            inv["id_master"],
            inv["descripcion"],
            inv.get("marca", ""),
            inv.get("modelo", ""),
            inv.get("cilindraje", "")
        ]
        return slugify("-".join([p for p in parts if p])), inv["descripcion"]

    if fuente == "JC":
        return slugify(f"{jc['id_master']}-{jc['descripcion']}"), jc["descripcion"]

    if fuente == "YOKO":
        return slugify(f"{yoko['id_master']}-{yoko['descripcion']}"), yoko["descripcion"]

    return slugify(base_fallback), base_fallback


# ========================================================================
# MAIN
# ========================================================================

def main():

    print("\n============================================")
    print("  🚀 RENOMBRADOR ULTRA PRO KAIQI v8")
    print("  Vision 4o + Inventario + JC + YOKO")
    print("============================================\n")

    inv = cargar_inventario()
    jc = cargar_jc()
    yoko = cargar_yoko()

    print(f"Inventario: {len(inv)} códigos")
    print(f"JC:         {len(jc)} códigos")
    print(f"YOKOMAR:    {len(yoko)} códigos\n")

    files = [
        f for f in os.listdir(IMAGE_DIR)
        if os.path.isfile(os.path.join(IMAGE_DIR, f)) and f.lower().endswith(
            (".jpg", ".jpeg", ".png", ".webp"))
    ]
    print(f"📸 Imágenes detectadas: {len(files)}\n")

    used_slugs = {}
    hash_seen = {}
    log_rows = []

    for fname in files:
        fpath = os.path.join(IMAGE_DIR, fname)
        base, ext = os.path.splitext(fname)
        ext = ext.lower()

        # Hash para duplicados reales
        h = file_hash(fpath)
        if h in hash_seen:
            print(f"[DUPLICADO REAL] {fname} es igual a {hash_seen[h]}")
            # renombramos con "-dupX"
            dup_slug = slugify(base) or "duplicado"
            if dup_slug in used_slugs:
                used_slugs[dup_slug] += 1
                dup_slug = f"{dup_slug}-dup{used_slugs[dup_slug]}"
            else:
                used_slugs[dup_slug] = 1

            newname = f"{dup_slug}{ext}"
            os.rename(fpath, os.path.join(IMAGE_DIR, newname))

            log_rows.append([fname, newname, "", "DUPLICADO_REAL", "", dup_slug, "DUP_REAL"])
            continue
        else:
            hash_seen[h] = fname

        # --- IA ---
        ia = analizar_imagen_con_ia(fpath)

        # --- match con catálogos ---
        fname_lower = fname.lower()
        inv_rec = next((v for k, v in inv.items() if k.lower() in fname_lower), None)
        jc_rec  = next((v for k, v in jc.items()  if k.lower() in fname_lower), None)
        yoko_rec= next((v for k, v in yoko.items()if k.lower() in fname_lower), None)

        # --- decide la fuente ---
        fuente = resolver_fuente(ia, inv_rec, jc_rec, yoko_rec)

        # --- construir slug ---
        slug, desc_used = construir_slug_final(
            fuente, ia, inv_rec, jc_rec, yoko_rec, base
        )

        # --- evitar colisiones ---
        final_slug = slug
        if final_slug in used_slugs:
            used_slugs[final_slug] += 1
            final_slug = f"{slug}-v{used_slugs[slug]}"
        else:
            used_slugs[final_slug] = 1

        newname = f"{final_slug}{ext}"
        os.rename(fpath, os.path.join(IMAGE_DIR, newname))

        log_rows.append([
            fname,
            newname,
            inv_rec["id_master"] if inv_rec else (
                jc_rec["id_master"] if jc_rec else (
                    yoko_rec["id_master"] if yoko_rec else ""
                )
            ),
            fuente,
            desc_used,
            final_slug,
            ia.get("confianza", 0.0),
            ia.get("componente", ""),
            ia.get("marca_moto", ""),
            ia.get("modelo_moto", ""),
            ia.get("cilindraje", ""),
            ia.get("es_motocarguero", False),
            ia.get("numeros_molde", "")
        ])

        print(f"[OK] {fname} → {newname} | fuente={fuente} | conf_ia={ia.get('confianza',0.0)}")

    # Guardar log
    with open(LOG_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow([
            "archivo_original",
            "archivo_nuevo",
            "id_master",
            "fuente",
            "descripcion_usada",
            "slug_final",
            "ia_confianza",
            "ia_componente",
            "ia_marca",
            "ia_modelo",
            "ia_cilindraje",
            "ia_es_motocarguero",
            "ia_numeros_molde"
        ])
        writer.writerows(log_rows)

    print("\n✅ Renombrado v8 finalizado.")
    print(f"   → Log: {LOG_CSV}")


if __name__ == "__main__":
    main()
