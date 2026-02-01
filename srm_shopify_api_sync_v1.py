# ======================================================================
# srm_shopify_api_sync_v1.py — SRM-QK-ADSI Shopify API Sync (SAFE MODE)
# ======================================================================
# Autor: SRM Engine
#
# Propósito:
#   - Sincronizar inventario SRM → Shopify vía Admin API.
#   - Actualizar inventario y precio de variantes.
#   - Verificar existencia de SKUs en Shopify.
#   - Ejecutarse en modo seguro (sin creación ni borrado de productos).
#
# Entradas:
#   catalogo_unificado.csv
#
# Salidas:
#   api_sync_report.json
#
# NOTA:
#   Esta versión trabaja en modo seguro. Solo actualiza INVENTARIO + PRECIO.
# ======================================================================

import os
import json
import pandas as pd
import requests
from datetime import datetime

# ----------------------------------------------------------------------
# CONFIGURACIÓN DE LA TIENDA SHOPIFY
# ----------------------------------------------------------------------
SHOPIFY_STORE_URL = "https://TU_TIENDA.myshopify.com"
ACCESS_TOKEN = "COLOCA_TU_TOKEN_AQUI"
API_VERSION = "2024-10"

# ----------------------------------------------------------------------
# RUTAS
# ----------------------------------------------------------------------
CATALOGO_SRM = r"C:\SRM_ADSI\02_cleaned_normalized\catalogo_unificado.csv"

OUTPUT_DIR = r"C:\SRM_ADSI\06_shopify"
os.makedirs(OUTPUT_DIR, exist_ok=True)

REPORT_PATH = os.path.join(OUTPUT_DIR, "api_sync_report.json")


# ----------------------------------------------------------------------
# UTILIDADES DE API
# ----------------------------------------------------------------------
def shopify_get(path):
    url = f"{SHOPIFY_STORE_URL}/admin/api/{API_VERSION}/{path}"
    headers = {"X-Shopify-Access-Token": ACCESS_TOKEN}
    return requests.get(url, headers=headers)


def shopify_put(path, payload):
    url = f"{SHOPIFY_STORE_URL}/admin/api/{API_VERSION}/{path}"
    headers = {
        "X-Shopify-Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    return requests.put(url, headers=headers, json=payload)


# ----------------------------------------------------------------------
# BUSCAR VARIANTE POR SKU (API)
# ----------------------------------------------------------------------
def find_variant_id_by_sku(sku):
    """Consulta Shopify para encontrar variante usando SKU."""
    res = shopify_get(f"variants.json?sku={sku}")

    if res.status_code != 200:
        return None, None

    data = res.json()

    if "variants" not in data or len(data["variants"]) == 0:
        return None, None

    variant = data["variants"][0]
    return variant["id"], variant["product_id"]


# ----------------------------------------------------------------------
# ACTUALIZAR INVENTARIO DE UNA VARIANTE
# ----------------------------------------------------------------------
def update_variant_inventory(variant_id, qty):
    payload = {"variant": {"id": variant_id, "inventory_quantity": int(qty)}}
    return shopify_put(f"variants/{variant_id}.json", payload)


# ----------------------------------------------------------------------
# ACTUALIZAR PRECIO DE UNA VARIANTE
# ----------------------------------------------------------------------
def update_variant_price(variant_id, price):
    payload = {"variant": {"id": variant_id, "price": str(price)}}
    return shopify_put(f"variants/{variant_id}.json", payload)


# ----------------------------------------------------------------------
# MAIN SYNC FUNCTION
# ----------------------------------------------------------------------
def ejecutar_sync_api():

    print("\n=====================================================")
    print("       SRM — SHOPIFY API SYNC v1 (SAFE MODE)")
    print("=====================================================\n")

    if ACCESS_TOKEN == "COLOCA_TU_TOKEN_AQUI":
        print("⚠ ADVERTENCIA: No has configurado el token de Shopify.")
        print("   El módulo correrá solo en modo lectura.\n")

    df = pd.read_csv(CATALOGO_SRM, dtype=str).fillna("")

    report = {
        "generated_at": datetime.now().isoformat(),
        "total_sku": len(df),
        "actualizados": 0,
        "no_encontrados": [],
        "errores": []
    }

    for _, row in df.iterrows():

        sku = row.get("sku", "")
        qty = row.get("inventario", "0")
        price = row.get("precio", "0")

        print(f"→ Procesando SKU: {sku}")

        variant_id, product_id = find_variant_id_by_sku(sku)

        if variant_id is None:
            print(f"   ✖ No encontrado en Shopify")
            report["no_encontrados"].append(sku)
            continue

        # ------------------------
        # 1. Actualizar inventario
        # ------------------------
        r_inv = update_variant_inventory(variant_id, qty)

        if r_inv.status_code == 200:
            print("   ✔ Inventario actualizado")
        else:
            print("   ✖ Error inventario:", r_inv.text)
            report["errores"].append({"sku": sku, "tipo": "inventario", "detalles": r_inv.text})

        # ------------------------
        # 2. Actualizar precio
        # ------------------------
        r_price = update_variant_price(variant_id, price)

        if r_price.status_code == 200:
            print("   ✔ Precio actualizado")
        else:
            print("   ✖ Error precio:", r_price.text)
            report["errores"].append({"sku": sku, "tipo": "precio", "detalles": r_price.text})

        report["actualizados"] += 1

    # Guardar reporte final
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)

    print("\n=====================================================")
    print(" ✔ SHOPIFY API SYNC v1 — COMPLETADO")
    print(f" ✔ Reporte: {REPORT_PATH}")
    print("=====================================================\n")


# ----------------------------------------------------------------------
# RUN
# ----------------------------------------------------------------------
if __name__ == "__main__":
    ejecutar_sync_api()
