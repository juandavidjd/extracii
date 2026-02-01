#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
generador_json_lovely_v2.py
100% compatible con PASO 0 Normalizador
"""

import os
import json
import pandas as pd

ROOT = r"C:/SRM_ADSI"

BASE_NORM_CATALOGOS = os.path.join(ROOT, "02_cleaned_normalized", "catalogos_normalizados")
BASE_KB = os.path.join(ROOT, "03_knowledge_base")

OUT_DIR = os.path.join(ROOT, "08_lovely_models")
os.makedirs(OUT_DIR, exist_ok=True)

CLIENTES = ["Bara", "DFG", "Duna", "Japan", "Kaiqi", "Leo", "Store", "Vaisand", "Yokomar"]


def load_norm_catalogo(cliente):
    path = os.path.join(BASE_NORM_CATALOGOS, f"{cliente}.csv")
    if not os.path.exists(path):
        print(f"⚠ No catálogo normalized: {path}")
        return None

    try:
        return pd.read_csv(path, low_memory=False)
    except:
        return pd.read_csv(path, encoding="latin1", low_memory=False)


def generar_para_cliente(cliente, df_kb):
    print(f"\n===================================================")
    print(f"▶ Generando JSON Lovely.dev para {cliente}")
    print("===================================================")

    df_cat = load_norm_catalogo(cliente)
    if df_cat is None:
        return

    registros = []
    for _, row in df_cat.iterrows():
        registros.append({
            "sku": str(row.get("SKU", "")),
            "nombre": str(row.get("NOMBRE", "")),
            "categoria": str(row.get("CATEGORIA", "")),
            "precio": float(row.get("PRECIO", 0)),
            "imagen": str(row.get("IMAGEN", "")),
        })

    out_path = os.path.join(OUT_DIR, f"{cliente}_lovely.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(registros, f, indent=2, ensure_ascii=False)

    print(f"✔ Lovely.json generado: {out_path}")


def main():
    df_kb = pd.read_csv(os.path.join(BASE_KB, "knowledge_base_unificada.csv"), low_memory=False)

    for c in CLIENTES:
        generar_para_cliente(c, df_kb)

    print("\n==============================================")
    print("  ✔ GENERADOR JSON LOVELY v2 COMPLETADO")
    print("==============================================\n")


if __name__ == "__main__":
    main()
