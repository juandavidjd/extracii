#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
====================================================================================
  SRM–QK–ADSI — EXTRACTOR v1 (Producción)
  Extrae y normaliza datos de Base_Datos, Catálogos e Imágenes para cada cliente.
====================================================================================
"""

import os
import pandas as pd
import chardet

BASE_ROOT = r"C:\SRM_ADSI"
SRC_DIR = os.path.join(BASE_ROOT, "01_sources_originales")
OUT_DIR = os.path.join(BASE_ROOT, "02_cleaned_normalized")

# Crear carpetas de salida
os.makedirs(os.path.join(OUT_DIR, "bases_normalizadas"), exist_ok=True)
os.makedirs(os.path.join(OUT_DIR, "catalogos_normalizados"), exist_ok=True)
os.makedirs(os.path.join(OUT_DIR, "precios_normalizados"), exist_ok=True)


CLIENTES = [
    "Bara", "DFG", "Duna", "Japan",
    "Kaiqi", "Leo", "Store", "Vaisand",
    "Yokomar",
]

# Mapeo de columnas estándar SRM–QK–ADSI
COLUMNAS_BASE = {
    "codigo": ["codigo", "codigo_producto", "sku", "referencia", "ref"],
    "descripcion": ["descripcion", "nombre", "titulo", "producto"],
    "categoria": ["categoria", "tipo", "grupo"],
}

COLUMNAS_IMAGENES = {
    "codigo": ["codigo", "sku", "ref"],
    "imagen": ["imagen", "img", "imagen_url", "archivo"],
    "ruta": ["ruta", "path", "url"],
}

COLUMNAS_PRECIOS = {
    "codigo": ["codigo", "sku", "ref"],
    "precio": ["precio", "valor", "price"],
}


# ---------------------------------------------------------------------------
# UTILIDADES
# ---------------------------------------------------------------------------

def detectar_codificacion(path):
    """Detecta codificación (utf-8/latin) con chardet"""
    with open(path, "rb") as f:
        raw = f.read(4096)
    return chardet.detect(raw)["encoding"]


def cargar_csv(path):
    """Carga CSVs con detección robusta de codificación"""
    enc = detectar_codificacion(path)
    try:
        return pd.read_csv(path, encoding=enc)
    except Exception:
        return pd.read_csv(path, encoding="latin1")


def normalizar_columnas(df, mapping):
    """Renombra columnas según diccionarios estándar SRM–ADSI"""
    new_cols = {}
    for std_name, alias_list in mapping.items():
        for alias in alias_list:
            for col in df.columns:
                if col.lower().strip() == alias.lower().strip():
                    new_cols[col] = std_name
    df = df.rename(columns=new_cols)

    # agregar columnas faltantes
    for std_name in mapping.keys():
        if std_name not in df.columns:
            df[std_name] = ""

    return df[mapping.keys()]


# ---------------------------------------------------------------------------
# PROCESAR CADA CLIENTE
# ---------------------------------------------------------------------------

def procesar_cliente(cliente):
    print(f"\n==============================")
    print(f"▶ PROCESANDO CLIENTE: {cliente}")
    print(f"==============================")

    carpeta = os.path.join(SRC_DIR, cliente)

    base_file = os.path.join(carpeta, f"Base_Datos_{cliente}.csv")
    cat_file = os.path.join(carpeta, f"catalogo_imagenes_{cliente}.csv")
    price_file = os.path.join(carpeta, f"Lista_Precios_{cliente}.csv")

    # ------------------------
    # BASE DATOS
    # ------------------------
    if os.path.exists(base_file):
        print(f"  → Leyendo Base_Datos_{cliente}.csv")
        df_base = cargar_csv(base_file)
        df_base = normalizar_columnas(df_base, COLUMNAS_BASE)

        df_base.to_csv(
            os.path.join(OUT_DIR, "bases_normalizadas", f"{cliente}_base_norm.csv"),
            index=False, encoding="utf-8"
        )
        print("    ✔ Base normalizada.")
    else:
        print("    ⚠ Base de datos no encontrada.")

    # ------------------------
    # CATALOGO IMÁGENES
    # ------------------------
    if os.path.exists(cat_file):
        print(f"  → Leyendo catalogo_imagenes_{cliente}.csv")
        df_cat = cargar_csv(cat_file)
        df_cat = normalizar_columnas(df_cat, COLUMNAS_IMAGENES)

        df_cat.to_csv(
            os.path.join(OUT_DIR, "catalogos_normalizados", f"{cliente}_catalogo_norm.csv"),
            index=False, encoding="utf-8"
        )
        print("    ✔ Catálogo rico normalizado.")
    else:
        print("    ⚠ Catálogo de imágenes no encontrado.")

    # ------------------------
    # LISTA PRECIOS
    # ------------------------
    if os.path.exists(price_file):
        print(f"  → Leyendo Lista_Precios_{cliente}.csv")
        df_price = cargar_csv(price_file)
        df_price = normalizar_columnas(df_price, COLUMNAS_PRECIOS)

        df_price.to_csv(
            os.path.join(OUT_DIR, "precios_normalizados", f"{cliente}_precios_norm.csv"),
            index=False, encoding="utf-8"
        )
        print("    ✔ Lista de precios normalizada.")
    else:
        print("    ⚠ Lista de precios no encontrada (se promediará en unificador_v1.py).")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    print("\n==============================================")
    print("  SRM–QK–ADSI — EXTRACTOR v1 INICIADO")
    print("==============================================\n")

    for c in CLIENTES:
        procesar_cliente(c)

    print("\n==============================================")
    print("  ✔ EXTRACTOR FINALIZADO")
    print("==============================================\n")


if __name__ == "__main__":
    main()
