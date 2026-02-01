#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
extractor_v2.py
SRM–QK–ADSI — EXTRACTOR v2 (100% compatible con PASO 0 Normalizador)

Corrección principal:
    - YA NO LEE 01_sources_originales
    - SOLO LEE: 02_cleaned_normalized/bases_normalizados/
                02_cleaned_normalized/catalogos_normalizados/
                02_cleaned_normalized/precioss_normalizados/
"""

import os
import pandas as pd

ROOT = r"C:/SRM_ADSI"

# === RUTAS NORMALIZADAS ===
BASE_NORM_BASES = os.path.join(ROOT, "02_cleaned_normalized", "bases_normalizados")
BASE_NORM_CATALOGOS = os.path.join(ROOT, "02_cleaned_normalized", "catalogos_normalizados")
BASE_NORM_PRECIOS = os.path.join(ROOT, "02_cleaned_normalized", "precioss_normalizados")

# === OUTPUT ===
OUT_DIR = os.path.join(ROOT, "03_knowledge_base", "extractos")
os.makedirs(OUT_DIR, exist_ok=True)

CLIENTES = ["Bara", "DFG", "Duna", "Japan", "Kaiqi", "Leo", "Store", "Vaisand", "Yokomar"]


def cargar_csv(path):
    if not os.path.exists(path):
        return None
    try:
        return pd.read_csv(path, low_memory=False)
    except:
        return pd.read_csv(path, encoding="latin1", low_memory=False)


def procesar_cliente(cliente):
    print(f"\n==============================")
    print(f"▶ EXTRAYENDO CLIENTE: {cliente}")
    print("==============================")

    base_file = os.path.join(BASE_NORM_BASES, f"{cliente}.csv")
    catalogo_file = os.path.join(BASE_NORM_CATALOGOS, f"{cliente}.csv")
    precios_file = os.path.join(BASE_NORM_PRECIOS, f"{cliente}.csv")

    df_base = cargar_csv(base_file)
    df_cat = cargar_csv(catalogo_file)
    df_pre = cargar_csv(precios_file)

    # Construcción extracto rico
    df_final = pd.DataFrame()
    df_final["CLIENTE"] = [cliente]

    df_final["REGISTROS_BASE"] = [0 if df_base is None else len(df_base)]
    df_final["REGISTROS_CATALOGO"] = [0 if df_cat is None else len(df_cat)]
    df_final["REGISTROS_PRECIOS"] = [0 if df_pre is None else len(df_pre)]

    out_path = os.path.join(OUT_DIR, f"{cliente}_extracto.csv")
    df_final.to_csv(out_path, index=False)
    print(f"   ✔ Extracto generado → {out_path}")


def main():
    print("\n==============================================")
    print("  SRM–QK–ADSI — EXTRACTOR v2 INICIADO")
    print("==============================================")

    for c in CLIENTES:
        procesar_cliente(c)

    print("\n==============================================")
    print("  ✔ EXTRACTOR v2 FINALIZADO")
    print("==============================================\n")


if __name__ == "__main__":
    main()
