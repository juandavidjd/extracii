#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
===============================================================================
       SRM–QK–ADSI — COMPILADOR SHOPIFY v1 (Producción)
       Construye shopify_import.csv para cada cliente usando:
       - knowledge_base_unificada.csv
       - catalogo rico (v26)
       - 360°
       - taxonomía
===============================================================================
"""

import os
import json
import pandas as pd

BASE = r"C:\SRM_ADSI"

KB_FILE = os.path.join(BASE, r"03_knowledge_base\knowledge_base_unificada.csv")
JSON_360_DIR = os.path.join(BASE, r"07_json_360")
SHOPIFY_DIR = os.path.join(BASE, r"06_shopify")
SOURCES_DIR = os.path.join(BASE, r"01_sources_originales")

CLIENTES = [
    "Bara", "DFG", "Duna", "Japan",
    "Kaiqi", "Leo", "Store", "Vaisand",
    "Yokomar"
]


def load_json_safe(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        print(f"⚠ No se pudo cargar: {path}")
        return []


def cargar_catalogo_360(cliente):
    path = os.path.join(JSON_360_DIR, cliente, "catalogo_360.json")
    data = load_json_safe(path)

    m = {}
    for item in data:
        m[item["codigo"]] = item
    return m


def cargar_catalogo_rico(cliente):
    """
    Lee catalogo_imagenes_<cliente>.csv
    """
    fname = f"catalogo_imagenes_{cliente}.csv"
    fpath = os.path.join(SOURCES_DIR, cliente, fname)

    if not os.path.exists(fpath):
        print(f"⚠ Catálogo rico NO encontrado: {fpath}")
        return pd.DataFrame()

    try:
        return pd.read_csv(fpath)
    except:
        return pd.read_csv(fpath, encoding="latin1")


def cargar_lista_precios(cliente):
    fname = f"Lista_Precios_{cliente}.csv"
    fpath = os.path.join(SOURCES_DIR, cliente, fname)

    if not os.path.exists(fpath):
        print(f"⚠ Lista precios NO encontrada: {fpath}")
        return None

    try:
        return pd.read_csv(fpath)
    except:
        return pd.read_csv(fpath, encoding="latin1")


def cargar_base_datos(cliente):
    fname = f"Base_Datos_{cliente}.csv"
    fpath = os.path.join(SOURCES_DIR, cliente, fname)

    if not os.path.exists(fpath):
        print(f"⚠ Base datos NO encontrada: {fpath}")
        return pd.DataFrame()

    try:
        return pd.read_csv(fpath)
    except:
        return pd.read_csv(fpath, encoding="latin1")


def generar_shopify(cliente, df_kb):
    print(f"\n==========================================")
    print(f"▶ COMPILANDO SHOPIFY — {cliente}")
    print(f"==========================================")

    # Cargar fuentes
    cat360 = cargar_catalogo_360(cliente)
    cat_rico = cargar_catalogo_rico(cliente)
    precios = cargar_lista_precios(cliente)
    base = cargar_base_datos(cliente)

    # Preparar carpeta salida
    out_folder = os.path.join(SHOPIFY_DIR, cliente)
    os.makedirs(out_folder, exist_ok=True)

    filas = []

    for _, row in df_kb[df_kb["cliente"] == cliente.lower()].iterrows():

        codigo = str(row["codigo"])
        desc = row.get("descripcion_rica", row.get("descripcion", "Producto"))

        # 360°
        data360 = cat360.get(codigo, {})
        thumb = data360.get("thumbnail", "")
        frames = data360.get("frames", [])

        # Precio
        precio = 0
        if precios is not None:
            # Coincidir por referencia o código
            col_match = None
            for col in precios.columns:
                if col.lower() in ["codigo", "referencia", "sku"]:
                    col_match = col
                    break

            if col_match:
                p = precios[precios[col_match].astype(str) == codigo]
                if not p.empty:
                    # busca columnas de precio
                    for c in p.columns:
                        if "precio" in c.lower():
                            precio = float(p.iloc[0][c])
                            break

        # Inventario
        inventario = 100  # estándar temporal

        # Tags
        tags = []
        for k in ["sistema", "subsistema", "componente"]:
            if pd.notna(row.get(k)):
                tags.append(str(row[k]).strip())

        # Construcción del registro Shopify
        fila = {
            "Handle": codigo,
            "Title": desc,
            "Body (HTML)": f"<p>{desc}</p>",
            "Vendor": cliente,
            "Product Category": "Repuestos para Moto",
            "Type": row.get("componente", "Repuesto"),
            "Tags": ", ".join(tags),
            "Published": "TRUE",
            "Option1 Name": "Title",
            "Option1 Value": desc,
            "Variant SKU": codigo,
            "Variant Inventory Tracker": "shopify",
            "Variant Inventory Qty": inventario,
            "Variant Inventory Policy": "deny",
            "Variant Fulfillment Service": "manual",
            "Variant Price": precio,
            "Variant Requires Shipping": "TRUE",
            "Variant Taxable": "TRUE",
            "Image Src": thumb if thumb else "",
            "Image Position": 1,
            "Image Alt Text": desc,
            "360_Frames": ";".join(frames)
        }

        filas.append(fila)

    # Exportar CSV
    df_out = pd.DataFrame(filas)
    out_csv = os.path.join(out_folder, "shopify_import.csv")
    df_out.to_csv(out_csv, index=False, encoding="utf-8-sig")

    print(f"✔ Shopify listo: {out_csv}")


def main():
    print("\n===================================================")
    print("      SRM–QK–ADSI — COMPILADOR SHOPIFY v1")
    print("===================================================\n")

    df_kb = pd.read_csv(KB_FILE)

    if "cliente" not in df_kb.columns:
        # Normalización temporal
        df_kb["cliente"] = df_kb["proveedor"].str.lower()

    for cliente in CLIENTES:
        generar_shopify(cliente, df_kb)

    print("\n===================================================")
    print("  ✔ COMPILADOR SHOPIFY COMPLETADO")
    print("  Directorios: 06_shopify/<cliente>/shopify_import.csv")
    print("===================================================\n")


if __name__ == "__main__":
    main()
