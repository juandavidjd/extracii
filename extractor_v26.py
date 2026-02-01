#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
====================================================================================
 EXTRACTOR v26 — Universal Data Harvester para SRM–QK–ADSI
====================================================================================

• Lee TODAS las bases de datos, catálogos e imágenes de C:\img
• Estandariza encabezados diferentes
• Mantiene TODA la referencia comercial original del cliente (SKU, códigos, texto)
• Produce un dataset único por cliente con estructura uniforme
• Genera una carpeta output/EXTRAIDOS/ por cliente

Compatible con:
- UNIFICADOR v26
- RENOMBRADOR v26
- GENERADOR 360° v26
====================================================================================
"""

import os
import pandas as pd

BASE = r"C:\img"
OUTPUT = os.path.join(BASE, "output_extractor")
os.makedirs(OUTPUT, exist_ok=True)

# ---------------------------------------------------------------
# TABLA DE CLIENTES DETECTADA POR ESTRUCTURA DE ARCHIVOS
# ---------------------------------------------------------------
CLIENTES = [
    "Bara", "DFG", "Duna", "Japan", "Kaiqi",
    "Leo", "Store", "Vaisand", "Yokomar"
]

# ---------------------------------------------------------------
# MAPAS DE NORMALIZACIÓN DE CABECERAS
# ---------------------------------------------------------------
MAPA_BASEDATOS = {
    "producto": "DESCRIPCION",
    "descripcion producto": "DESCRIPCION",
    "descripción": "DESCRIPCION",
    "nombre": "DESCRIPCION",
    "codigo": "CODIGO",
    "sku": "SKU"
}

MAPA_CATALOGO_IMAGENES = {
    "filename_original": "FILENAME",
    "nombre_comercial_catalogo": "NOMBRE_RICO",
    "identificacion_repuesto": "IDENTIFICACION",
    "componente_taxonomia": "COMPONENTE",
    "sistema": "SISTEMA",
    "subsistema": "SUBSISTEMA"
}

MAPA_LISTA_PRECIOS = {
    "precio": "PRECIO",
    "valor": "PRECIO",
    "total": "PRECIO",
    "producto / descripcion": "DESCRIPCION",
    "descripcion": "DESCRIPCION",
    "ver imagen": "IMAGEN_ARCHIVO",
    "codigo": "CODIGO",
}

# ---------------------------------------------------------------
def normalizar_columnas(df, mapa):
    ren = {}
    for col in df.columns:
        c = col.strip().lower().replace(" ", " ").replace("\xa0", " ")
        for key in mapa:
            if key in c:
                ren[col] = mapa[key]
    df = df.rename(columns=ren)
    return df

# ---------------------------------------------------------------
# LECTOR ROBUSTO PARA CSV (encodings variables)
# ---------------------------------------------------------------
def load_csv(path):
    for enc in ("utf-8", "latin-1", "ISO-8859-1"):
        try:
            return pd.read_csv(path, encoding=enc, on_bad_lines='skip')
        except:
            pass
    return pd.read_csv(path, encoding="latin-1", errors="ignore")


# ---------------------------------------------------------------
# PROCESADO POR CLIENTE
# ---------------------------------------------------------------
def procesar_cliente(cliente):

    print(f"\n===================================================")
    print(f" EXTRAYENDO DATOS DE CLIENTE → {cliente}")
    print(f"===================================================\n")

    pref = cliente.upper()

    # -------------------------------
    # 1) BASE DE DATOS
    # -------------------------------
    base_file = os.path.join(BASE, f"Base_Datos_{cliente}.csv")
    if os.path.exists(base_file):
        df_base = load_csv(base_file)
        df_base = normalizar_columnas(df_base, MAPA_BASEDATOS)
    else:
        df_base = pd.DataFrame()

    # -------------------------------
    # 2) CATALOGO DE IMÁGENES
    # -------------------------------
    cata_file = os.path.join(BASE, f"catalogo_imagenes_{cliente}.csv")
    if os.path.exists(cata_file):
        df_cata = load_csv(cata_file)
        df_cata = normalizar_columnas(df_cata, MAPA_CATALOGO_IMAGENES)
    else:
        df_cata = pd.DataFrame()

    # -------------------------------
    # 3) LISTAS DE PRECIOS
    # -------------------------------
    precio_file = os.path.join(BASE, f"Lista_Precios_{cliente}.csv")
    if os.path.exists(precio_file):
        df_pre = load_csv(precio_file)
        df_pre = normalizar_columnas(df_pre, MAPA_LISTA_PRECIOS)
    else:
        df_pre = pd.DataFrame()

    # -------------------------------
    # 4) CARPETA DE IMÁGENES
    # -------------------------------
    foto_dir = os.path.join(BASE, f"FOTOS_CATALOGO_{cliente}")
    fotos = []
    if os.path.exists(foto_dir):
        for f in os.listdir(foto_dir):
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                fotos.append(f)
    df_fotos = pd.DataFrame({"IMAGEN_ARCHIVO": fotos})

    # -------------------------------
    # 5) UNIFICACIÓN DEL CLIENTE
    # -------------------------------
    df_out = pd.DataFrame()

    # Mezclamos todo manteniendo todo lo que cada uno tenga
    for df in [df_base, df_cata, df_pre]:
        if not df.empty:
            df_out = pd.concat([df_out, df], axis=0, ignore_index=True)

    # Agregamos imágenes si no existen
    if not df_fotos.empty:
        df_fotos["FILENAME"] = df_fotos["IMAGEN_ARCHIVO"].str.lower()
        df_out = pd.merge(df_out, df_fotos, how="left", on="IMAGEN_ARCHIVO")

    # Añadir columna CLIENTE
    df_out["CLIENTE"] = cliente

    # Guardar salida
    out_file = os.path.join(OUTPUT, f"EXTRACTOR_{cliente}_v26.csv")
    df_out.to_csv(out_file, index=False, encoding="utf-8-sig")

    print(f"✔ CLIENTE {cliente} extraído correctamente")
    print(f"✔ Archivo generado: {out_file}")


# ---------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------
if __name__ == "__main__":
    print("\n🚀 EXTRACTOR v26 – INICIANDO\n")

    for cliente in CLIENTES:
        procesar_cliente(cliente)

    print("\n===================================================")
    print("  ✔ TODOS LOS CLIENTES EXTRAÍDOS CON ÉXITO")
    print("  ✔ Listos para UNIFICADOR v26")
    print("===================================================\n")
