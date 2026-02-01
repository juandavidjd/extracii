#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
====================================================================================
 SHOPIFY COMPILER v26 — SRM–QK–ADSI (FINAL GOLD)
====================================================================================

Objetivo:
- Generar el catálogo Shopify por cliente utilizando:
  - JSON 360° del cliente
  - Imagen renombrada v26
  - Precio del cliente (o precio promedio)
  - Stock del cliente (o stock estándar = 100)
  - Taxonomía SRM–QK–ADSI v1
- Produce:
  - /shopify_out_v26/<cliente>_shopify_v26.csv
  - /shopify_out_v26/<cliente>_metafields.json
====================================================================================
"""

import os
import json
import pandas as pd
from pathlib import Path

BASE = Path(r"C:\img")

DIR_360 = BASE / "json_360_por_cliente"
DIR_IMG = BASE / "IMAGENES_RENOMBRADAS_v26"
DIR_PRECIOS = BASE
DIR_OUT = BASE / "shopify_out_v26"

os.makedirs(DIR_OUT, exist_ok=True)

# ===============================================================================
# UTILIDADES
# ===============================================================================

def cargar_precios(cliente):
    """
    Carga el archivo: Lista_Precios_<cliente>.csv
    Si no existe: devuelve dict vacío.
    """
    file = DIR_PRECIOS / f"Lista_Precios_{cliente}.csv"
    if not file.exists():
        print(f"⚠ Cliente {cliente}: NO tiene archivo de precios.")
        return {}

    df = pd.read_csv(file, dtype=str).fillna("")
    precio_map = {}

    for _, row in df.iterrows():
        ref = str(row.get("REF", "")).strip().upper()
        precio = row.get("PRECIO", "").strip()

        if ref and precio:
            precio_map[ref] = precio

    return precio_map


def obtener_precio(item, precios_cliente):
    """
    Reglas:
    - Si SKU/REF del item está en precios_cliente → usarlo
    - Si no → usar 25.000 COP promedio (temporal)
    """
    ref = str(item.get("ref_original", "")).strip().upper()

    if ref in precios_cliente:
        return precios_cliente[ref]

    return "25000"  # Precio promedio temporal


def obtener_stock(item):
    """
    Regla:
    - Si JSON 360° tiene cantidad_real → usarla
    - Si no → 100 por defecto
    """
    stock = item.get("stock_real", "")
    if isinstance(stock, str) and stock.isdigit():
        return stock
    if isinstance(stock, int):
        return str(stock)

    return "100"


def imagen_principal(item):
    """
    Devuelve el nombre de la imagen renombrada v26.
    """
    return item.get("imagen_renombrada", "")


# ===============================================================================
# GENERAR SHOPIFY CSV
# ===============================================================================

def generar_csv_shopify(cliente):

    file_json = DIR_360 / f"{cliente}_360.json"
    if not file_json.exists():
        print(f"❌ No existe JSON 360° para {cliente}")
        return

    data = json.load(open(file_json, "r", encoding="utf-8"))

    precios = cargar_precios(cliente)

    filas = []

    for item in data:
        nombre = item["nombre_rico"]
        precio = obtener_precio(item, precios)
        stock = obtener_stock(item)
        imagen = imagen_principal(item)

        filas.append({
            "Handle": item["handle"],
            "Title": nombre,
            "Body (HTML)": item.get("descripcion_larga", ""),
            "Vendor": cliente.upper(),
            "Type": item.get("categoria_principal", ""),
            "Tags": ", ".join(item.get("tags", [])),
            "Published": "TRUE",

            # Variante principal
            "Option1 Name": "Título",
            "Option1 Value": nombre,
            "Variant SKU": item.get("sku_final", ""),
            "Variant Inventory Qty": stock,
            "Variant Inventory Policy": "deny",
            "Variant Fulfillment Service": "manual",
            "Variant Price": precio,
            "Variant Requires Shipping": "TRUE",

            # Imagen
            "Image Src": f"https://cdn.srm-adsi.com/{imagen}" if imagen else "",
        })

    # Exportar CSV
    out_file = DIR_OUT / f"{cliente}_shopify_v26.csv"
    pd.DataFrame(filas).to_csv(out_file, index=False, encoding="utf-8")

    print(f"✔ Shopify CSV generado: {out_file}")


# ===============================================================================
# GENERAR METAFIELDS
# ===============================================================================

def generar_metafields(cliente):

    file_json = DIR_360 / f"{cliente}_360.json"
    if not file_json.exists():
        return

    data = json.load(open(file_json, "r", encoding="utf-8"))

    metafields = []

    for item in data:

        metafields.append({
            "handle": item["handle"],
            "metafields": {
                "sistema": item.get("sistema", ""),
                "sub_sistema": item.get("sub_sistema", ""),
                "componente": item.get("componente", ""),
                "fitment": item.get("fitment", []),
                "marca_origen": item.get("marca_origen", ""),
                "compatibilidad": item.get("compatibilidad", ""),
                "oem": item.get("oem", ""),
            }
        })

    out_file = DIR_OUT / f"{cliente}_metafields.json"
    json.dump(metafields, open(out_file, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"✔ Metafields generados: {out_file}")


# ===============================================================================
# PROCESAR 9 CLIENTES
# ===============================================================================

def ejecutar():

    clientes = [
        "Bara",
        "DFG",
        "Duna",
        "Japan",
        "Kaiqi",
        "Leo",
        "Store",
        "Vaisand",
        "Yokomar",
    ]

    for cliente in clientes:
        print(f"\n============================")
        print(f"   🛒 CLIENTE: {cliente} ")
        print(f"============================")

        generar_csv_shopify(cliente)
        generar_metafields(cliente)

    print("\n=== COMPILADOR SHOPIFY v26 COMPLETADO ===")


if __name__ == "__main__":
    ejecutar()
