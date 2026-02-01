#!/usr/bin/env python3
# ============================================================
# 1_renombrar_seo_kaiqi_v7.5.py
# Renombrado SEO apoyado en 3 fuentes:
# - Inventario_FINAL_CON_TAXONOMIA.csv
# - LISTA DE PRECIOS  YOKOMAR ACTUALIZADA 2025.xlsx
# - LISTA DE PRECIOS NOVIEMBRE 13 2025 TRABAJO JC.xlsx
#
# No usa IA. No manda nada a duplicados. No pierde imágenes.
# ============================================================

import os
import re
import csv
import unicodedata
import pandas as pd

# ------------------------------------------------------------
# RUTAS BASE
# ------------------------------------------------------------
BASE_DIR = r"C:\img"

IMAGE_DIR = os.path.join(BASE_DIR, "IMAGENES_KAIQI_MAESTRAS")
INVENTARIO_CSV = os.path.join(BASE_DIR, "Inventario_FINAL_CON_TAXONOMIA.csv")
YOKO_XLSX = os.path.join(BASE_DIR, "LISTA DE PRECIOS  YOKOMAR ACTUALIZADA 2025.xlsx")
JC_XLSX = os.path.join(BASE_DIR, "LISTA DE PRECIOS NOVIEMBRE 13 2025 TRABAJO JC.xlsx")

LOGS_DIR = os.path.join(BASE_DIR, "LOGS")
os.makedirs(LOGS_DIR, exist_ok=True)
LOG_CSV = os.path.join(LOGS_DIR, "log_renombrado_seo_v7.5.csv")


# ------------------------------------------------------------
# UTILIDADES
# ------------------------------------------------------------
def slugify(text: str) -> str:
    """Convierte un texto en un slug SEO seguro."""
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


def cargar_inventario():
    """Carga Inventario_FINAL_CON_TAXONOMIA y devuelve dict code -> record."""
    if not os.path.exists(INVENTARIO_CSV):
        print(f"⚠ No se encontró inventario: {INVENTARIO_CSV}")
        return {}

    inv = pd.read_csv(INVENTARIO_CSV, sep=";", encoding="utf-8")

    required = ["CODIGO NEW", "DESCRIPCION"]
    for col in required:
        if col not in inv.columns:
            raise ValueError(f"Falta columna '{col}' en Inventario_FINAL_CON_TAXONOMIA.csv")

    records = {}
    for _, row in inv.iterrows():
        codigo_new = str(row["CODIGO NEW"]).strip()
        if not codigo_new:
            continue

        rec = {
            "source": "INV",
            "id_master": codigo_new,
            "code": codigo_new,
            "descripcion": str(row["DESCRIPCION"]).strip(),
            "marca": str(row.get("MARCA", "") or "").strip(),
            "modelo": str(row.get("MODELO", "") or "").strip(),
            "cilindraje": str(row.get("CILINDRAJE", "") or "").strip()
        }
        records[codigo_new] = rec

    return records


def cargar_yokomar():
    """Carga LISTA DE PRECIOS YOKOMAR... y devuelve dict referencia -> record."""
    if not os.path.exists(YOKO_XLSX):
        print(f"⚠ No se encontró YOKOMAR: {YOKO_XLSX}")
        return {}

    yoko = pd.read_excel(YOKO_XLSX)
    if yoko.shape[0] < 10:
        return {}

    # La fila 8 (index 8) contiene encabezados
    header_row = yoko.iloc[8]
    data = yoko.iloc[9:].copy()
    data.columns = header_row.values

    # Aseguramos nombres esperados
    if "DESCRIPCION" not in data.columns or "REFERENCIA" not in data.columns:
        print("⚠ Formato inesperado en YOKOMAR, no se pudo mapear DESCRIPCION/REFERENCIA.")
        return {}

    records = {}
    for _, row in data.iterrows():
        ref = str(row["REFERENCIA"]).strip()
        if not ref or ref == "nan":
            continue
        desc = str(row["DESCRIPCION"]).strip()
        if not desc or desc == "nan":
            continue

        rec = {
            "source": "YOKO",
            "id_master": ref,
            "code": ref,
            "descripcion": desc,
            "marca": "",
            "modelo": "",
            "cilindraje": ""
        }
        records[ref] = rec

    return records


def cargar_jc():
    """Carga LISTA DE PRECIOS NOVIEMBRE 13 2025 TRABAJO JC y devuelve dict codigo -> record."""
    if not os.path.exists(JC_XLSX):
        print(f"⚠ No se encontró JC: {JC_XLSX}")
        return {}

    jc = pd.read_excel(JC_XLSX)
    if jc.shape[0] < 10:
        return {}

    # La fila 8 (index 8) contiene encabezados
    header_row = jc.iloc[8]
    data = jc.iloc[9:].copy()
    data.columns = header_row.values

    # Esperamos columnas: "PRODUCTO / DESCRIPCION" y "CODIGO"
    if "PRODUCTO / DESCRIPCION" not in data.columns or "CODIGO" not in data.columns:
        print("⚠ Formato inesperado en lista JC, no se pudo mapear PRODUCTO / DESCRIPCION / CODIGO.")
        return {}

    records = {}
    for _, row in data.iterrows():
        cod = str(row["CODIGO"]).strip()
        if not cod or cod == "nan":
            continue
        desc = str(row["PRODUCTO / DESCRIPCION"]).strip()
        if not desc or desc == "nan":
            continue

        rec = {
            "source": "JC",
            "id_master": cod,
            "code": cod,
            "descripcion": desc,
            "marca": "",
            "modelo": "",
            "cilindraje": ""
        }
        records[cod] = rec

    return records


def encontrar_match_para_imagen(fname: str, inv_records, jc_records, yoko_records):
    """
    Busca el mejor match para el nombre de archivo en el orden:
    1) Inventario
    2) JC
    3) YOKOMAR
    Retorna rec dict o None.
    """
    name_lower = fname.lower()

    # 1) Buscar en Inventario (CODIGO NEW)
    for code, rec in inv_records.items():
        if str(code).lower() in name_lower:
            return rec

    # 2) Buscar en JC (CODIGO)
    for code, rec in jc_records.items():
        if str(code).lower() in name_lower:
            return rec

    # 3) Buscar en YOKOMAR (REFERENCIA)
    for code, rec in yoko_records.items():
        if str(code).lower() in name_lower:
            return rec

    return None


def construir_slug_desde_rec(rec, base_fallback: str) -> (str, str, str):
    """
    Dado un record de INV/JC/YOKO o None, devuelve:
      - slug_base
      - id_master
      - descripcion_usada
    """
    if rec is None:
        # Sin match: usar solo el nombre base
        id_master = ""
        descripcion = base_fallback
        slug_base = slugify(descripcion)
        return slug_base or "sin-nombre", id_master, descripcion

    fuente = rec["source"]
    id_master = rec["id_master"]
    descripcion = rec["descripcion"]
    marca = rec.get("marca", "")
    modelo = rec.get("modelo", "")
    cil = rec.get("cilindraje", "")

    if fuente == "INV":
        # Enriquecido
        parts = [id_master, descripcion, marca, modelo, cil]
        txt = "-".join([p for p in parts if p])
        slug_base = slugify(txt)
    else:
        # JC o YOKO: code + descripcion
        slug_base = slugify(f"{id_master}-{descripcion}")

    if not slug_base:
        slug_base = slugify(descripcion) or "sin-nombre"

    return slug_base, id_master, descripcion


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def main():
    # Cargar catálogos
    inv_records = cargar_inventario()
    jc_records = cargar_jc()
    yoko_records = cargar_yokomar()

    print("==============================================")
    print("  🟣 Renombrado SEO KAIQI v7.5 (3 fuentes)")
    print("==============================================")
    print(f"Inventario (INV): {len(inv_records)} códigos")
    print(f"Lista JC:         {len(jc_records)} códigos")
    print(f"Lista YOKOMAR:    {len(yoko_records)} códigos\n")

    # Validar carpeta imágenes
    if not os.path.isdir(IMAGE_DIR):
        raise NotADirectoryError(f"No existe carpeta de imágenes: {IMAGE_DIR}")

    files = [
        f for f in os.listdir(IMAGE_DIR)
        if os.path.isfile(os.path.join(IMAGE_DIR, f))
        and f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    ]

    if not files:
        print("❌ No se encontraron imágenes en IMAGENES_KAIQI_MAESTRAS.")
        return

    used_slugs = {}
    log_rows = []

    print(f"📸 Imágenes detectadas: {len(files)}\n")

    for fname in files:
        src_path = os.path.join(IMAGE_DIR, fname)
        base, ext = os.path.splitext(fname)
        ext = ext.lower()

        # Buscar match en catálogo maestro (3 fuentes)
        rec = encontrar_match_para_imagen(fname, inv_records, jc_records, yoko_records)
        slug_base, id_master, desc_usada = construir_slug_desde_rec(rec, base)

        fuente = rec["source"] if rec else "NONE"

        # Resolver colisiones de slug (no mandar a duplicados, solo versionar)
        slug_final = slug_base
        if slug_final in used_slugs:
            used_slugs[slug_final] += 1
            slug_final = f"{slug_base}-v{used_slugs[slug_base]}"
        else:
            used_slugs[slug_final] = 1

        nuevo_nombre = f"{slug_final}{ext}"
        dst_path = os.path.join(IMAGE_DIR, nuevo_nombre)

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
            nuevo_nombre,
            id_master,
            fuente,
            desc_usada,
            slug_final,
            estado
        ])

        print(f"[{estado}] {fname} -> {nuevo_nombre} | fuente={fuente} | id_master={id_master}")

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
            "estado"
        ])
        writer.writerows(log_rows)

    print("\n✅ Renombrado v7.5 finalizado.")
    print(f"   → Log: {LOG_CSV}")


if __name__ == "__main__":
    main()
