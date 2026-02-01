#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=================================================================================
      SRM–QK–ADSI — UNIFICADOR v1 (Producción)
      Une base, catálogo e imágenes para cada cliente y crea la base global.
=================================================================================
"""

import os
import pandas as pd
from difflib import get_close_matches

BASE_ROOT = r"C:\SRM_ADSI"
SRC_DIR = os.path.join(BASE_ROOT, "02_cleaned_normalized")
OUT_DIR = os.path.join(BASE_ROOT, "03_knowledge_base")

os.makedirs(OUT_DIR, exist_ok=True)


CLIENTES = [
    "Bara", "DFG", "Duna", "Japan",
    "Kaiqi", "Leo", "Store", "Vaisand",
    "Yokomar"
]


def cargar_norm(path, fallback_cols):
    """Carga CSV normalizado y si no existe retorna DF vacío con columnas estándar."""
    if os.path.exists(path):
        return pd.read_csv(path)
    else:
        return pd.DataFrame({col: [] for col in fallback_cols})


def precio_promedio_global(precios_dir):
    """Calcula precio promedio global usando todos los archivos disponibles."""
    precios = []
    for file in os.listdir(precios_dir):
        if file.endswith(".csv"):
            df = pd.read_csv(os.path.join(precios_dir, file))
            if "precio" in df.columns:
                precios.extend(df["precio"].dropna().tolist())

    return round(sum(precios) / len(precios), 2) if len(precios) > 0 else 10000


def merge_fuzzy(df_base, df_cat):
    """Unión tolerante por código; si no coincide exacto, usa fuzzy matching."""
    if df_base.empty:
        return df_cat

    if df_cat.empty:
        return df_base

    df_base = df_base.copy()
    df_cat = df_cat.copy()

    df_base["codigo"] = df_base["codigo"].astype(str).str.strip()
    df_cat["codigo"] = df_cat["codigo"].astype(str).str.strip()

    df_base["codigo_merge"] = df_base["codigo"]
    df_cat["codigo_merge"] = df_cat["codigo"]

    for i, row in df_base.iterrows():
        cod = row["codigo"]
        if cod not in df_cat["codigo"].values:
            similares = get_close_matches(cod, df_cat["codigo"].tolist(), n=1, cutoff=0.7)
            if similares:
                df_base.at[i, "codigo_merge"] = similares[0]

    df = pd.merge(df_base, df_cat, on="codigo_merge", how="outer", suffixes=("_base", "_cat"))
    df = df.rename(columns={"codigo_merge": "codigo"})
    df = df.drop_duplicates(subset=["codigo"])

    return df


def procesar_cliente(cliente, precio_global):
    print(f"\n==============================")
    print(f"▶ UNIFICANDO CLIENTE: {cliente}")
    print(f"==============================")

    # Paths normalizados
    base_path = os.path.join(SRC_DIR, "bases_normalizadas", f"{cliente}_base_norm.csv")
    cat_path = os.path.join(SRC_DIR, "catalogos_normalizados", f"{cliente}_catalogo_norm.csv")
    price_path = os.path.join(SRC_DIR, "precios_normalizados", f"{cliente}_precios_norm.csv")

    base = cargar_norm(base_path, ["codigo", "descripcion", "categoria"])
    cat = cargar_norm(cat_path, ["codigo", "imagen", "ruta"])
    price = cargar_norm(price_path, ["codigo", "precio"])

    # Merge base + catálogo rico (fuzzy)
    df = merge_fuzzy(base, cat)

    # Insertar precios
    df["precio"] = None
    df["origen_precio"] = None

    for i, row in df.iterrows():
        cod = str(row["codigo"]).strip()

        if cod in price["codigo"].astype(str).tolist():
            df.at[i, "precio"] = float(price[price["codigo"].astype(str) == cod]["precio"].values[0])
            df.at[i, "origen_precio"] = cliente
        else:
            df.at[i, "precio"] = precio_global
            df.at[i, "origen_precio"] = "promedio_global"

    # Stock default
    df["stock"] = 100

    # metadatos
    df["cliente"] = cliente

    # Guardar por cliente
    out_path = os.path.join(OUT_DIR, f"{cliente}_unificado.csv")
    df.to_csv(out_path, index=False, encoding="utf-8")

    print(f"   ✔ Unificado guardado → {out_path}")

    return df


def main():
    print("\n==============================================")
    print("  SRM–QK–ADSI — UNIFICADOR v1 INICIADO")
    print("==============================================\n")

    precios_dir = os.path.join(SRC_DIR, "precios_normalizados")
    precio_global = precio_promedio_global(precios_dir)

    print(f"Precio promedio global calculado: {precio_global}")

    # Unificar por cliente
    df_global = pd.DataFrame()

    for cliente in CLIENTES:
        df_cliente = procesar_cliente(cliente, precio_global)
        df_global = pd.concat([df_global, df_cliente], ignore_index=True)

    # Guardar knowledge base unificada
    global_path = os.path.join(OUT_DIR, "knowledge_base_unificada.csv")
    df_global.to_csv(global_path, index=False, encoding="utf-8")

    print("\n==============================================")
    print("  ✔ UNIFICADOR FINALIZADO")
    print(f"  Archivo global → {global_path}")
    print("==============================================\n")


if __name__ == "__main__":
    main()
