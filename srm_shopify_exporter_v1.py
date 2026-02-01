# ======================================================================
# srm_shopify_exporter_v1.py — SRM-QK-ADSI SHOPIFY ENGINE v1
# ======================================================================
# Autor: SRM Engine
#
# Propósito:
#   - Convertir catálogo SRM → Shopify CSV estándar.
#   - Enriquecer productos con narrativa, branding y metafields SRM.
#   - Generar mapas de imágenes, metafields y estructura lista para Shopify.
#
# Entradas:
#   catalogo_unificado.csv
#   frontend_bundle.json
#
# Resultados:
#   shopify_export.csv
#   shopify_metafields.json
#   shopify_images_map.json
# ======================================================================

import os
import json
import pandas as pd
from datetime import datetime

# ----------------------------------------------------------------------
# RUTAS
# ----------------------------------------------------------------------
CATALOGO = r"C:\SRM_ADSI\02_cleaned_normalized\catalogo_unificado.csv"
FRONTEND_BUNDLE = r"C:\SRM_ADSI\03_knowledge_base\brands\frontend\frontend_bundle.json"

OUTPUT_DIR = r"C:\SRM_ADSI\06_shopify"
os.makedirs(OUTPUT_DIR, exist_ok=True)

EXPORT_CSV = os.path.join(OUTPUT_DIR, "shopify_export.csv")
METAFIELDS_JSON = os.path.join(OUTPUT_DIR, "shopify_metafields.json")
IMAGES_MAP_JSON = os.path.join(OUTPUT_DIR, "shopify_images_map.json")


# ----------------------------------------------------------------------
# UTILIDADES
# ----------------------------------------------------------------------
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_get(d, *keys):
    """Acceso seguro a diccionarios profundos"""
    for k in keys:
        if d is None or k not in d:
            return None
        d = d[k]
    return d


# ----------------------------------------------------------------------
# CARGAR DATOS
# ----------------------------------------------------------------------
def cargar_datos():
    if not os.path.exists(CATALOGO):
        raise FileNotFoundError("No existe catalogo_unificado.csv — ejecute el Pipeline v28.")

    df = pd.read_csv(CATALOGO, dtype=str).fillna("")

    bundle = load_json(FRONTEND_BUNDLE)

    return df, bundle


# ----------------------------------------------------------------------
# GENERAR CSV PRINCIPAL DE SHOPIFY
# ----------------------------------------------------------------------
def build_shopify_csv(df, bundle):

    shopify_rows = []

    for _, row in df.iterrows():

        brand = row.get("marca_fabricante", "").strip()
        sku = row.get("sku", "")
        titulo = row.get("titulo", "")
        precio = row.get("precio", "0")
        descripcion = row.get("descripcion", "")
        imagen_principal = row.get("imagen_principal", "")

        brand_profile = bundle["brands"].get(brand, None)

        narrativa = safe_get(brand_profile, "narrative", "historia")
        tagline = safe_get(brand_profile, "lovable", "metadata", "tagline")

        descripcion_final = f"{tagline}\n\n{descripcion}\n\n{narrativa}"

        shopify_rows.append({
            "Handle": sku.lower(),
            "Title": f"{titulo} | {brand}",
            "Body (HTML)": descripcion_final,
            "Vendor": brand,
            "Product Category": row.get("categoria", ""),
            "Tags": f"{row.get('sistema','')}, {row.get('subsistema','')}, SRM",
            "Published": "TRUE",
            "Option1 Name": "Default",
            "Option1 Value": "Default",
            "Variant SKU": sku,
            "Variant Price": precio,
            "Variant Inventory Tracker": "shopify",
            "Variant Inventory Qty": row.get("inventario", "0"),
            "Image Src": imagen_principal
        })

    return pd.DataFrame(shopify_rows)


# ----------------------------------------------------------------------
# CONSTRUIR METAFIELDS POR PRODUCTO
# ----------------------------------------------------------------------
def build_metafields(df):

    metafields = {}

    for _, row in df.iterrows():
        sku = row.get("sku", "")

        metafields[sku] = {
            "srm.taxonomia": {
                "sistema": row.get("sistema", ""),
                "subsistema": row.get("subsistema", ""),
                "componente": row.get("componente", "")
            },
            "srm.fitment": row.get("fitment_json", ""),
            "srm.descripcion_enriquecida": row.get("descripcion", ""),
            "srm.oem": row.get("oem", ""),
            "srm.version": "v28"
        }

    return metafields


# ----------------------------------------------------------------------
# GENERAR MAPA DE IMÁGENES
# ----------------------------------------------------------------------
def build_images_map(df):

    images_map = {}

    for _, row in df.iterrows():
        sku = row.get("sku", "")
        img = row.get("imagen_principal", "")
        images_map[sku] = [img] if img else []

    return images_map


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------
def exportar_shopify():

    print("\n=====================================================")
    print("        SRM — SHOPIFY EXPORTER v1")
    print("=====================================================\n")

    df, bundle = cargar_datos()

    print("→ Construyendo Shopify CSV…")
    csv_df = build_shopify_csv(df, bundle)
    csv_df.to_csv(EXPORT_CSV, index=False, encoding="utf-8-sig")
    print(f"   ✔ CSV generado: {EXPORT_CSV}")

    print("→ Generando metafields…")
    metafields = build_metafields(df)
    with open(METAFIELDS_JSON, "w", encoding="utf-8") as f:
        json.dump(metafields, f, indent=4, ensure_ascii=False)
    print(f"   ✔ metafields JSON: {METAFIELDS_JSON}")

    print("→ Construyendo mapa de imágenes…")
    images_map = build_images_map(df)
    with open(IMAGES_MAP_JSON, "w", encoding="utf-8") as f:
        json.dump(images_map, f, indent=4, ensure_ascii=False)
    print(f"   ✔ imágenes JSON: {IMAGES_MAP_JSON}")

    print("\n=====================================================")
    print(" ✔ SHOPIFY EXPORTER — COMPLETADO")
    print("=====================================================\n")


# ----------------------------------------------------------------------
# RUN
# ----------------------------------------------------------------------
if __name__ == "__main__":
    exportar_shopify()
