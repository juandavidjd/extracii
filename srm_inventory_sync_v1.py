# ======================================================================
# srm_inventory_sync_v1.py — SRM-QK-ADSI INVENTORY SYNC ENGINE v1
# ======================================================================
# Autor: SRM Engine
#
# Propósito:
#   - Sincronizar inventario SRM ↔ Shopify (modo offline v1).
#   - Detectar inconsistencias entre catálogo SRM y Shopfy Export.
#   - Generar archivo actualizado para importación manual.
#   - Preparar la base para integración Shopify Admin API.
#
# Entradas:
#   catalogo_unificado.csv (inventario SRM)
#   shopify_export.csv (Shopify base)
#
# Resultados:
#   shopify_inventory_update.csv
#   report_inventory_sync.json
# ======================================================================

import os
import json
import pandas as pd
from datetime import datetime

# ----------------------------------------------------------------------
# RUTAS
# ----------------------------------------------------------------------
CATALOGO_SRM = r"C:\SRM_ADSI\02_cleaned_normalized\catalogo_unificado.csv"
SHOPIFY_EXPORT = r"C:\SRM_ADSI\06_shopify\shopify_export.csv"

OUTPUT_DIR = r"C:\SRM_ADSI\06_shopify"
os.makedirs(OUTPUT_DIR, exist_ok=True)

OUTPUT_INVENTORY = os.path.join(OUTPUT_DIR, "shopify_inventory_update.csv")
OUTPUT_REPORT   = os.path.join(OUTPUT_DIR, "report_inventory_sync.json")


# ----------------------------------------------------------------------
# UTILIDADES
# ----------------------------------------------------------------------
def load_csv(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"[ERROR] No existe el archivo requerido: {path}")
    return pd.read_csv(path, dtype=str).fillna("")


def guardar_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ----------------------------------------------------------------------
# SINCRONIZACIÓN
# ----------------------------------------------------------------------
def sincronizar_inventario(df_srm, df_shopify):

    report = {
        "generated_at": datetime.now().isoformat(),
        "total_srm": len(df_srm),
        "total_shopify": len(df_shopify),
        "coincidencias": 0,
        "faltantes_en_shopify": [],
        "faltantes_en_srm": [],
        "inventario_actualizado": 0
    }

    # Convertir SKU a índice para un acceso rápido
    df_shopify_idx = df_shopify.set_index("Variant SKU")

    updated_rows = []

    for _, row in df_srm.iterrows():
        sku = row.get("sku", "")
        inv_srm = row.get("inventario", "0")

        if sku in df_shopify_idx.index:

            report["coincidencias"] += 1

            # Tomar la fila Shopify original
            shop_row = df_shopify_idx.loc[sku].copy()
            shop_row["Variant Inventory Qty"] = inv_srm

            updated_rows.append(shop_row)

        else:
            report["faltantes_en_shopify"].append(sku)

    # Detectar productos que están en Shopify pero ya no en SRM
    for sku in df_shopify["Variant SKU"].tolist():
        if sku not in df_srm["sku"].tolist():
            report["faltantes_en_srm"].append(sku)

    updated_df = pd.DataFrame(updated_rows)
    report["inventario_actualizado"] = len(updated_rows)

    return updated_df, report


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------
def ejecutar_sync():

    print("\n=====================================================")
    print("          SRM — INVENTORY SYNC ENGINE v1")
    print("=====================================================\n")

    print("→ Cargando inventario SRM…")
    df_srm = load_csv(CATALOGO_SRM)

    print("→ Cargando Shopify Export…")
    df_shopify = load_csv(SHOPIFY_EXPORT)

    print("→ Ejecutando sincronización…")
    df_updated, report = sincronizar_inventario(df_srm, df_shopify)

    print("→ Guardando archivo actualizado para Shopify…")
    df_updated.to_csv(OUTPUT_INVENTORY, index=False, encoding="utf-8-sig")
    print(f"   ✔ Archivo: {OUTPUT_INVENTORY}")

    print("→ Guardando reporte de sincronización…")
    guardar_json(OUTPUT_REPORT, report)
    print(f"   ✔ Reporte: {OUTPUT_REPORT}")

    print("\n=====================================================")
    print(" ✔ INVENTORY SYNC — COMPLETADO")
    print("=====================================================\n")


# ----------------------------------------------------------------------
# RUN
# ----------------------------------------------------------------------
if __name__ == "__main__":
    ejecutar_sync()
