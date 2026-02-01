#!/usr/bin/env python3
# ============================================================
# 1_renombrar_seo_kaiqi_v7.py — Renombrado seguro por ID_MASTER
# ============================================================

import os
import re
import csv
import unicodedata
import pandas as pd

# -----------------------------
# RUTAS BASE
# -----------------------------
BASE_DIR = r"C:\img"
IMAGE_DIR = os.path.join(BASE_DIR, "IMAGENES_KAIQI_MAESTRAS")
INVENTARIO_CSV = os.path.join(BASE_DIR, "Inventario_FINAL_CON_TAXONOMIA.csv")
LOGS_DIR = os.path.join(BASE_DIR, "LOGS")
os.makedirs(LOGS_DIR, exist_ok=True)
LOG_CSV = os.path.join(LOGS_DIR, "log_renombrado_seo_v7.csv")


def slugify(text: str) -> str:
    if not isinstance(text, str):
        text = str(text or "")
    text = text.strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("ñ", "n")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")


def main():
    # -----------------------------
    # Cargar inventario maestro
    # -----------------------------
    if not os.path.exists(INVENTARIO_CSV):
        raise FileNotFoundError(f"No se encuentra {INVENTARIO_CSV}")

    inv = pd.read_csv(INVENTARIO_CSV, sep=";", encoding="utf-8")

    required_cols = ["CODIGO NEW", "DESCRIPCION"]
    for col in required_cols:
        if col not in inv.columns:
            raise ValueError(f"Falta columna '{col}' en Inventario_FINAL_CON_TAXONOMIA.csv")

    # ID_MASTER = CODIGO NEW (si no existe)
    if "ID_MASTER" not in inv.columns:
        inv["ID_MASTER"] = inv["CODIGO NEW"].astype(str)
    else:
        inv["ID_MASTER"] = inv["ID_MASTER"].astype(str)

    # Mapa rápido ID_MASTER -> fila
    id_list = inv["ID_MASTER"].astype(str).tolist()

    # -----------------------------
    # Recorrer imágenes
    # -----------------------------
    if not os.path.isdir(IMAGE_DIR):
        raise NotADirectoryError(f"No existe carpeta de imágenes: {IMAGE_DIR}")

    files = [
        f for f in os.listdir(IMAGE_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    ]

    if not files:
        print("No se encontraron imágenes en IMAGENES_KAIQI_MAESTRAS.")
        return

    used_slugs = {}
    log_rows = []

    print("==============================================")
    print("  🔵 Renombrado SEO KAIQI v7 — por ID_MASTER")
    print("==============================================")
    print(f"📸 Imágenes detectadas: {len(files)}\n")

    for fname in files:
        src_path = os.path.join(IMAGE_DIR, fname)
        base, ext = os.path.splitext(fname)
        ext = ext.lower()

        # Buscar ID_MASTER en el nombre actual
        id_match = None
        name_lower = fname.lower()
        for _id in id_list:
            if str(_id).lower() in name_lower:
                id_match = _id
                break

        if id_match is None:
            # Sin match: usar solo el nombre actual como base
            id_master = ""
            descripcion = base
            matched = "NO"
        else:
            matched = "SI"
            id_master = str(id_match)
            row = inv[inv["ID_MASTER"].astype(str) == id_master].iloc[0]
            descripcion = str(row["DESCRIPCION"])

        # Construir slug
        if id_master:
            slug_base = slugify(f"{id_master}-{descripcion}")
        else:
            slug_base = slugify(descripcion)

        if not slug_base:
            slug_base = slugify(base) or "sin-nombre"

        slug_final = slug_base
        if slug_final in used_slugs:
            # Evitar colisión sin mandar a duplicados
            contador = used_slugs[slug_final] + 1
            used_slugs[slug_final] = contador
            slug_final = f"{slug_base}-v{contador}"
            conflicto = "slug_conflict"
        else:
            used_slugs[slug_final] = 1
            conflicto = ""

        new_name = f"{slug_final}{ext}"
        dst_path = os.path.join(IMAGE_DIR, new_name)

        if os.path.abspath(src_path) == os.path.abspath(dst_path):
            estado = "SIN_CAMBIO"
        else:
            try:
                os.rename(src_path, dst_path)
                estado = "RENOMBRADO"
            except Exception as e:
                estado = f"ERROR_RENOMBRANDO:{e}"

        log_rows.append([
            fname,
            new_name,
            id_master,
            descripcion,
            slug_final,
            matched,
            conflicto,
            estado
        ])

        print(f"[{estado}] {fname} -> {new_name}")

    # Guardar log
    with open(LOG_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow([
            "archivo_original",
            "archivo_nuevo",
            "id_master",
            "descripcion",
            "slug_final",
            "match_inventario",
            "conflicto_slug",
            "estado"
        ])
        writer.writerows(log_rows)

    print("\n✅ Renombrado v7 finalizado.")
    print(f"   → Log: {LOG_CSV}")


if __name__ == "__main__":
    main()
