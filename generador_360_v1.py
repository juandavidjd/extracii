#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=================================================================================
        SRM–QK–ADSI — GENERADOR 360° v1 (Producción)
        Crea JSON 360° por cliente usando imágenes renombradas del v26.
=================================================================================
"""

import os
import json
import re
import pandas as pd
from PIL import Image

BASE = r"C:\SRM_ADSI"
RENOMBRADAS = os.path.join(BASE, r"04_imagenes\renombradas")
OUT_JSON = os.path.join(BASE, r"07_json_360")
KB_FILE = os.path.join(BASE, r"03_knowledge_base\knowledge_base_unificada.csv")

CLIENTES = [
    "Bara", "DFG", "Duna", "Japan",
    "Kaiqi", "Leo", "Store", "Vaisand",
    "Yokomar"
]


def extraer_codigo(nombre):
    """
    Extrae código de un nombre del tipo:
    kaiqi_10395024_valvula_admision_akt_125_1.jpg
    """
    partes = nombre.split("_")
    for p in partes:
        if p.isdigit():
            return p
    return None


def extraer_descripcion(nombre):
    """
    Extrae la descripción intermedia del nombre renombrado v26.
    """
    sin_ext = re.sub(r"\.[a-z0-9]+$", "", nombre)
    partes = sin_ext.split("_")

    # cliente, codigo, desc..., frame#
    if len(partes) > 3:
        return " ".join(partes[2:-1])
    return "producto"


def crear_thumbnail(path_img, path_out):
    """
    Crea miniatura 256x256 para Shopify y Lovely.dev
    """
    try:
        img = Image.open(path_img)
        img.thumbnail((256, 256))
        img.save(path_out)
    except:
        pass


def procesar_cliente(cliente, df_global):
    print(f"\n========================================")
    print(f"▶ GENERANDO 360° — {cliente}")
    print(f"========================================")

    folder = os.path.join(RENOMBRADAS, cliente)
    if not os.path.isdir(folder):
        print(f"⚠ No renombradas para {cliente}")
        return

    out_folder = os.path.join(OUT_JSON, cliente)
    os.makedirs(out_folder, exist_ok=True)

    productos = {}

    # Recorrer imágenes renombradas
    for f in sorted(os.listdir(folder)):
        if not re.search(r"\.(jpg|jpeg|png|webp)$", f.lower()):
            continue

        codigo = extraer_codigo(f)
        if not codigo:
            continue

        descripcion = extraer_descripcion(f)
        path_full = os.path.join(folder, f)

        productos.setdefault(codigo, {
            "codigo": codigo,
            "cliente": cliente.lower(),
            "descripcion": descripcion,
            "frames": [],
            "thumbnail": None
        })

        productos[codigo]["frames"].append(path_full)

    # Generar thumbnail y ordenar frames
    for codigo, data in productos.items():
        if data["frames"]:
            data["frames"] = sorted(data["frames"])

            thumb_path = os.path.join(out_folder, f"{codigo}_thumb.jpg")
            crear_thumbnail(data["frames"][0], thumb_path)
            data["thumbnail"] = thumb_path

    # Guardar JSON principal
    out_file = os.path.join(out_folder, "catalogo_360.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(list(productos.values()), f, ensure_ascii=False, indent=2)

    # Guardar productos.json (solo info básica)
    out_file2 = os.path.join(out_folder, "productos.json")
    with open(out_file2, "w", encoding="utf-8") as f:
        json.dump(
            [
                {
                    "codigo": p["codigo"],
                    "descripcion": p["descripcion"],
                    "thumbnail": p["thumbnail"]
                }
                for p in productos.values()
            ],
            f,
            ensure_ascii=False,
            indent=2
        )

    print(f"✔ 360° generado para {cliente}")


def main():
    print("\n===================================================")
    print("   SRM–QK–ADSI — GENERADOR 360° v1 INICIANDO")
    print("===================================================\n")

    df_global = pd.read_csv(KB_FILE)

    for cliente in CLIENTES:
        procesar_cliente(cliente, df_global)

    print("\n===================================================")
    print("  ✔ GENERADOR 360° COMPLETADO")
    print("  Directorio: 07_json_360/")
    print("===================================================\n")


if __name__ == "__main__":
    main()
