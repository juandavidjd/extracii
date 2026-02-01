#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=====================================================================================
 🧠 UNIFICADOR SRM–QK–ADSI v26 — “Knowledge Base Unificada”
=====================================================================================

Autor: Juan David + ADSI
Fecha: 2025-12-01

Objetivo:
---------
Unificar TODAS las bases de datos disponibles en C:\img, respetando:

- SKU / CÓDIGO / REFERENCIA originales del cliente.
- Descripción comercial del cliente.
- Información de catálogo enriquecido (si existe).
- Listas de precios (si existen).
- Relación de imágenes reales por tienda.
- Mantener TODO lo existente (sin borrar, sin inventar).

Entrada:
--------
En C:\img debe existir:
- Base_Datos_*.csv
- catalogo_imagenes_*.csv
- Lista_Precios_*.csv
- Carpetas FOTOS_CATALOGO_*

Salida:
--------
C:\img\output\knowledge_base_unificada.csv
=====================================================================================
"""

import os
import re
import pandas as pd

# --------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------

BASE = r"C:\img"
OUTPUT = os.path.join(BASE, "output")
os.makedirs(OUTPUT, exist_ok=True)

# Patrones esperados
BASE_PREFIX = "Base_Datos_"
CAT_PREFIX = "catalogo_imagenes_"
PRE_PREFIX = "Lista_Precios_"
FOTOS_PREFIX = "FOTOS_CATALOGO_"

# --------------------------------------------------------------
# FUNCIONES
# --------------------------------------------------------------

def cargar_csv_seguro(path):
    """Carga CSV tolerante a errores, separador automático."""
    try:
        return pd.read_csv(path, encoding="utf-8", sep=",", on_bad_lines="skip")
    except:
        try:
            return pd.read_csv(path, encoding="latin-1", sep=",", on_bad_lines="skip")
        except Exception as e:
            print(f"Error cargando {path}: {e}")
            return pd.DataFrame()


def detectar_cliente(nombre_archivo):
    """Extrae el nombre del cliente según convención."""
    return (
        nombre_archivo.replace(BASE_PREFIX, "")
        .replace(CAT_PREFIX, "")
        .replace(PRE_PREFIX, "")
        .replace(".csv", "")
        .strip()
        .upper()
    )


def obtener_imagenes_cliente(cliente):
    """Devuelve listado de imágenes reales asociadas al cliente."""
    carpeta = os.path.join(BASE, f"{FOTOS_PREFIX}{cliente}")
    if not os.path.exists(carpeta):
        return []
    return [f for f in os.listdir(carpeta) if f.lower().endswith((".jpg", ".jpeg", ".png"))]


def normalizar_columnas(df):
    """Normaliza encabezados para evitar errores."""
    df.columns = [str(c).strip().upper().replace("  ", " ") for c in df.columns]
    return df


# --------------------------------------------------------------
# ETAPA 1 — CARGAR TODAS LAS BASES
# --------------------------------------------------------------

bases = {}
catalogos = {}
precios = {}
imagenes = {}

print("🔍 Escaneando directorio:", BASE)
for f in os.listdir(BASE):

    # -------------------------
    # Bases de datos
    # -------------------------
    if f.startswith(BASE_PREFIX) and f.endswith(".csv"):
        cliente = detectar_cliente(f)
        df = cargar_csv_seguro(os.path.join(BASE, f))
        df = normalizar_columnas(df)
        bases[cliente] = df
        print(f"📥 Base cargada: {cliente} — {df.shape}")

    # -------------------------
    # Catálogos ricos
    # -------------------------
    elif f.startswith(CAT_PREFIX) and f.endswith(".csv"):
        cliente = detectar_cliente(f)
        df = cargar_csv_seguro(os.path.join(BASE, f))
        df = normalizar_columnas(df)
        catalogos[cliente] = df
        print(f"📚 Catálogo cargado: {cliente} — {df.shape}")

    # -------------------------
    # Listas de precios
    # -------------------------
    elif f.startswith(PRE_PREFIX) and f.endswith(".csv"):
        cliente = detectar_cliente(f)
        df = cargar_csv_seguro(os.path.join(BASE, f))
        df = normalizar_columnas(df)
        precios[cliente] = df
        print(f"💲 Lista precios: {cliente} — {df.shape}")

    # -------------------------
    # Imágenes por cliente
    # -------------------------
for cliente in bases.keys():
    imagenes[cliente] = obtener_imagenes_cliente(cliente)
    print(f"🖼️ Imágenes {cliente}: {len(imagenes[cliente])} archivos")


# --------------------------------------------------------------
# ETAPA 2 — UNIFICACIÓN
# --------------------------------------------------------------

filas_finales = []

for cliente, df_base in bases.items():

    print(f"\n🔵 Procesando cliente: {cliente}")

    df_cat = catalogos.get(cliente, pd.DataFrame())
    df_pre = precios.get(cliente, pd.DataFrame())
    imgs = imagenes.get(cliente, [])

    # Preparamos índice por texto para posible match
    base_desc = df_base.columns[df_base.columns.str.contains("DESC")].tolist()
    cat_fname = df_cat.columns[df_cat.columns.str.contains("FILENAME")].tolist()
    cat_desc = df_cat.columns[df_cat.columns.str.contains("NOMBRE") | df_cat.columns.str.contains("DESCRIP")].tolist()
    pre_desc = df_pre.columns[df_pre.columns.str.contains("DESC")].tolist()
    pre_price = df_pre.columns[df_pre.columns.str.contains("PREC")].tolist()

    for idx, row in df_base.iterrows():

        descripcion = None
        if base_desc:
            descripcion = str(row[base_desc[0]]).strip()

        # Buscar precio
        precio = None
        if not df_pre.empty and pre_desc:
            match = df_pre[df_pre[pre_desc[0]].astype(str).str.contains(descripcion[:10], case=False, na=False)]
            if not match.empty and pre_price:
                precio = match.iloc[0][pre_price[0]]

        # Buscar imagen
        imagen_asociada = None
        if cat_fname:
            matches = df_cat[df_cat[cat_fname[0]].astype(str).str.contains(descripcion[:10], case=False, na=False)]
            if not matches.empty:
                imagen_asociada = matches.iloc[0][cat_fname[0]]
        if not imagen_asociada:
            # fallback: coincidencia parcial en carpeta
            for im in imgs:
                if descripcion[:10].replace(" ", "-").lower() in im.lower():
                    imagen_asociada = im
                    break

        filas_finales.append({
            "CLIENTE": cliente,
            "DESCRIPCION": descripcion,
            "CODIGO": row.get("CODIGO", row.get("SKU", row.get("REFERENCIA", None))),
            "PRECIO": precio,
            "IMAGEN_ASOCIADA": imagen_asociada,
            "TIENE_IMAGEN": 1 if imagen_asociada else 0,
            "FUENTE_BASE": "Base_Datos",
            "FUENTE_CATALOGO": 1 if not df_cat.empty else 0,
            "FUENTE_PRECIOS": 1 if not df_pre.empty else 0
        })

# --------------------------------------------------------------
# ETAPA 3 — EXPORTAR
# --------------------------------------------------------------

df_final = pd.DataFrame(filas_finales)

salida = os.path.join(OUTPUT, "knowledge_base_unificada.csv")
df_final.to_csv(salida, index=False, encoding="utf-8-sig")

print("\n=========================================================")
print("⭐ KNOWLEDGE BASE UNIFICADA GENERADA")
print("📄 Archivo:", salida)
print("🔢 Total de registros:", df_final.shape)
print("=========================================================\n")
