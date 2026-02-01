# -*- coding: utf-8 -*-
"""
codificacion_kaiqi_shopify.py
Transforma LISTADO_KAIQI_FINAL.xlsx o archivo base (con CODIGO NEW, DESCRIPCION, CATEGORIA, PRECIO SIN IVA)
a formato de importación Shopify.
"""

import os
import re
import sys
import logging
import pandas as pd

# ============================================================
# CONFIGURACIÓN
# ============================================================
CONFIG = {
    "BASE_DIR": r"C:/sqk/html_pages",
    "INPUT_FILE": "LISTADO_KAIQI_FINAL.xlsx",  # o tu archivo CSV/Excel de base
    "OUTPUT_FILE": "LISTADO_KAIQI_SHOPIFY.xlsx",
    "VENDOR": "KAIQI PARTS",
    "CURRENCY": "COP",
    "PUBLISH_PRODUCTS": True,
}

# ============================================================
# LOGGING
# ============================================================
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
log = logging.getLogger("SHOPIFY")

# ============================================================
# FUNCIONES AUXILIARES
# ============================================================
def norm(text):
    if pd.isna(text):
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()

def parse_price(price):
    """Convierte texto tipo '$ 25.000' o '$25,000' a float 25000"""
    if pd.isna(price):
        return 0
    clean = re.sub(r"[^0-9,\.]", "", str(price))
    clean = clean.replace(",", ".")
    try:
        return round(float(clean))
    except:
        return 0

def gen_handle(text):
    """Genera un identificador único (handle) compatible con Shopify."""
    text = norm(text).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"^-|-$", "", text)
    return text

def gen_tags(row):
    """Combina categoría, sistema y palabras clave para tags."""
    tags = []
    if "CATEGORIA" in row and row["CATEGORIA"]:
        tags.append(row["CATEGORIA"])
    if "DESCRIPCION" in row:
        desc = norm(row["DESCRIPCION"])
        words = [w for w in desc.split() if len(w) > 3]
        tags.extend(words[:5])
    return ", ".join(sorted(set(tags)))

# ============================================================
# PROCESO PRINCIPAL
# ============================================================
def main():
    log.info("=== Iniciando conversión a formato Shopify ===")
    path_in = os.path.join(CONFIG["BASE_DIR"], CONFIG["INPUT_FILE"])
    df = pd.read_excel(path_in)

    df.columns = [c.strip().upper() for c in df.columns]

    # Validación
    required = ["CODIGO NEW", "DESCRIPCION", "CATEGORIA", "PRECIO SIN IVA"]
    for col in required:
        if col not in df.columns:
            log.error(f"❌ Falta columna requerida: {col}")
            sys.exit(1)

    df["DESCRIPCION"] = df["DESCRIPCION"].apply(norm)
    df["CATEGORIA"] = df["CATEGORIA"].apply(norm)
    df["CODIGO NEW"] = df["CODIGO NEW"].apply(norm)
    df["PRECIO SIN IVA"] = df["PRECIO SIN IVA"].apply(parse_price)

    # Elimina filas vacías
    df = df[df["DESCRIPCION"] != ""].copy()

    # Generar campos Shopify
    shopify = pd.DataFrame()
    shopify["Handle"] = df["DESCRIPCION"].apply(gen_handle)
    shopify["Title"] = df["DESCRIPCION"]
    shopify["Body (HTML)"] = ""
    shopify["Vendor"] = CONFIG["VENDOR"]
    shopify["Type"] = df["CATEGORIA"]
    shopify["Tags"] = df.apply(gen_tags, axis=1)
    shopify["Published"] = "TRUE" if CONFIG["PUBLISH_PRODUCTS"] else "FALSE"
    shopify["Option1 Name"] = "Title"
    shopify["Option1 Value"] = df["CATEGORIA"]
    shopify["SKU"] = df["CODIGO NEW"]
    shopify["Price"] = df["PRECIO SIN IVA"]
    shopify["Status"] = "active"

    # Orden sugerido por Shopify
    ordered_cols = [
        "Handle", "Title", "Body (HTML)", "Vendor", "Type",
        "Tags", "Published", "Option1 Name", "Option1 Value",
        "SKU", "Price", "Status"
    ]
    shopify = shopify[ordered_cols]

    # Exportar
    output_path = os.path.join(CONFIG["BASE_DIR"], CONFIG["OUTPUT_FILE"])
    shopify.to_excel(output_path, index=False)

    log.info(f"✅ Archivo Shopify generado: {output_path}")
    log.info(f"🛒 Total productos exportados: {len(shopify)}")
    log.info("=== Conversión completada correctamente ===")

# ============================================================
# EJECUCIÓN
# ============================================================
if __name__ == "__main__":
    main()
