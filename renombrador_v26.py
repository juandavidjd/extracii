#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=================================================================================
      SRM–QK–ADSI — RENOMBRADOR DE IMÁGENES v26 (Producción)
      Nombres unificados SEO, por cliente, con control de colisiones.
=================================================================================
"""

import os
import pandas as pd
import unicodedata
import re
import shutil

BASE = r"C:\SRM_ADSI"
KB_FILE = os.path.join(BASE, r"03_knowledge_base\knowledge_base_unificada.csv")
IMG_ORIG = os.path.join(BASE, r"04_imagenes\originales")
IMG_OUT = os.path.join(BASE, r"04_imagenes\renombradas")

os.makedirs(IMG_OUT, exist_ok=True)

CLIENTES = [
    "Bara", "DFG", "Duna", "Japan",
    "Kaiqi", "Leo", "Store", "Vaisand",
    "Yokomar"
]


def slugify(text):
    """Convierte el texto en un slug compatible SEO."""
    text = str(text).lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def mapear_imagenes_cliente(df_cliente, cliente_folder):
    """Devuelve un diccionario: codigo → lista de paths de imágenes."""
    imagenes_cliente = {}

    for root, dirs, files in os.walk(cliente_folder):
        for f in files:
            f_lower = f.lower()
            codigo_detectado = None

            # Intento encontrar código dentro del nombre del archivo
            for cod in df_cliente["codigo"].astype(str).tolist():
                cod = cod.strip()
                if cod.lower() in f_lower:
                    codigo_detectado = cod
                    break

            if codigo_detectado:
                path = os.path.join(root, f)
                imagenes_cliente.setdefault(codigo_detectado, []).append(path)

    return imagenes_cliente


def renombrar_cliente(cliente, df_global):
    print(f"\n======================================")
    print(f"▶ RENOMBRANDO IMÁGENES — {cliente}")
    print(f"======================================\n")

    df_cliente = df_global[df_global["cliente"] == cliente].copy()

    # Paths
    carpeta_origen = os.path.join(IMG_ORIG, cliente)
    carpeta_destino = os.path.join(IMG_OUT, cliente)

    os.makedirs(carpeta_destino, exist_ok=True)

    # Crear mapa código → imágenes encontradas
    mapa = mapear_imagenes_cliente(df_cliente, carpeta_origen)

    for idx, row in df_cliente.iterrows():
        codigo = str(row["codigo"])
        desc = slugify(row.get("descripcion", "producto"))
        cliente_slug = slugify(cliente)

        imagenes = mapa.get(codigo, [])

        if not imagenes:
            continue  # no hay imágenes para ese código

        for i, img_path in enumerate(imagenes, start=1):
            ext = os.path.splitext(img_path)[1].lower()
            if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
                ext = ".jpg"

            new_name = f"{cliente_slug}_{codigo}_{desc}_{i}{ext}"
            new_path = os.path.join(carpeta_destino, new_name)

            shutil.copy2(img_path, new_path)

            print(f"✔ {os.path.basename(img_path)}  →  {new_name}")

    print(f"\n✔ Finalizado renombrado para {cliente}")


def main():
    print("\n==============================================")
    print("  SRM–QK–ADSI — RENOMBRADOR v26 INICIANDO")
    print("==============================================\n")

    df_global = pd.read_csv(KB_FILE)

    for cliente in CLIENTES:
        renombrar_cliente(cliente, df_global)

    print("\n==============================================")
    print("  ✔ RENOMBRADOR v26 COMPLETADO")
    print("  Directorio: 04_imagenes/renombradas/")
    print("==============================================\n")


if __name__ == "__main__":
    main()
