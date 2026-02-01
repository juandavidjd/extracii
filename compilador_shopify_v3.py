#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
compilador_shopify_v3.py
Versión robusta: detecta automáticamente el SKU.
"""

import os
import pandas as pd

ROOT = r"C:/SRM_ADSI"

BASE_NORM_CATALOGOS = os.path.join(ROOT, "02_cleaned_normalized", "catalogos_normalizados")
BASE_KB = os.path.join(ROOT, "03_knowledge_base")

OUT_DIR = os.path.join(ROOT, "09_shopify_ready")
os.makedirs(OUT_DIR, exist_ok=True)

CLIENTES = ["Bara", "DFG", "Duna", "Japan", "Kaiqi", "Leo", "Store", "Vaisand", "Yokomar"]

SKU_CANDIDATOS = ["SKU", "CODIGO", "REFERENCIA", "REF", "ID", "ID_PRODUCTO"]


def detectar_columna_sku(df):
    for col in SKU_CANDIDATOS:
        if col in df.columns:
            return col
    return None


def cargar_norm_catalogo(cliente):
    path = os.path.join(BASE_NORM_CATALOGOS, f"{cliente}.csv")
    if not os.path.exists(path):
        print(f"⚠ No existe catálogo normalizado para {cliente}: {path}")
        return None

    try:
        return pd.read_csv(path, low_memory=False)
    except:
        return pd.read_csv(path, encoding="latin1", low_memory=False)


def generar_shopify(cliente, df_kb):
    print(f"\n==========================================")
    print(f"▶ COMPILANDO SHOPIFY — {cliente}")
    print("==========================================")

    df_cat = cargar_norm_catalogo(cliente)
    if df_cat is None:
        print("⚠ Catálogo inexistente → no se genera Shopify.")
        return

    df = df_cat.copy()

    # Detectar columna SKU
    sku_col = detectar_columna_sku(df)

    if sku_col is None:
        print(f"⚠ No existe columna SKU/REFERENCIA → Generando SKUs sintéticos")
        df["SKU_FINAL"] = [f"{cliente}_{i}" for i in range(len(df))]
    else:
        df["SKU_FINAL"] = df[sku_col].astype(str).str.strip()

    # Construcción columnas Shopify
    df["handle"] = df["SKU_FINAL"].str.lower().str.replace(" ", "-")
    df["title"] = df["NOMBRE"].fillna("") if "NOMBRE" in df.columns else df["SKU_FINAL"]
    df["body"] = ""
    df["vendor"] = cliente
    df["type"] = "Repuestos Moto"
    df["tags"] = cliente

    # precio
    df["price"] = df["PRECIO"].fillna(0) if "PRECIO" in df.columns else 0

    # imagen
    df["image"] = df["IMAGEN"].fillna("") if "IMAGEN" in df.columns else ""

    # Archivo final
    out_file = os.path.join(OUT_DIR, f"{cliente}_shopify.csv")
    df.to_csv(out_file, index=False)

    print(f"✔ Shopify generado: {out_file}")


def main():
    df_kb = pd.read_csv(os.path.join(BASE_KB, "knowledge_base_unificada.csv"), low_memory=False)

    for c in CLIENTES:
        generar_shopify(c, df_kb)

    print("\n==============================================")
    print("  ✔ COMPILADOR SHOPIFY v3 COMPLETADO")
    print("==============================================\n")


if __name__ == "__main__":
    main()
