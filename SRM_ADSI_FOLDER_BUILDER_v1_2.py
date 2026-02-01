#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SRM_ADSI_FOLDER_BUILDER_v1_2.py
Corrección del bug: FOTOS_DIR usa .upper() incorrectamente.
"""

import os
import shutil

BASE_ORIGEN = r"C:\img"
BASE_DESTINO = r"C:\SRM_ADSI"

CLIENTES = [
    "Bara", "DFG", "Duna", "Japan", "Kaiqi",
    "Leo", "Store", "Vaisand", "Yokomar"
]

BASE_DATOS = "Base_Datos_{c}.csv"
CATALOGO_IMGS = "catalogo_imagenes_{c}.csv"
LISTA_PRECIOS = "Lista_Precios_{c}.csv"

# 🔥 CORREGIDO:
# Antes → "FOTOS_CATALOGO_{c.upper()}"
# Ahora → función que genera el nombre correcto
def fotos_dir(c):
    return f"FOTOS_CATALOGO_{c.upper()}"


def mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def copy_if_exists(src, dst):
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f"✔ Copiado: {src} → {dst}")
    else:
        print(f"⚠ No encontrado: {src}")


def copy_folder_if_exists(src, dst):
    if os.path.exists(src) and os.path.isdir(src):
        shutil.copytree(src, dst, dirs_exist_ok=True)
        print(f"📁 Carpeta copiada: {src} → {dst}")
    else:
        print(f"⚠ Carpeta no encontrada: {src}")


def crear_estructura_srm():
    print("\n===================================")
    print(" CREANDO ESTRUCTURA SRM–QK–ADSI v1")
    print("===================================\n")

    # 00_docs
    for sub in ["Enciclopedia", "PDFs_Clientes", "Taxonomia_Referencia", "Arquitectura"]:
        mkdir(os.path.join(BASE_DESTINO, "00_docs", sub))

    # 01_sources_originales
    for c in CLIENTES:
        mkdir(os.path.join(BASE_DESTINO, "01_sources_originales", c))

    # 02_cleaned_normalized
    mkdir(os.path.join(BASE_DESTINO, "02_cleaned_normalized", "catalogos_normalizados"))
    mkdir(os.path.join(BASE_DESTINO, "02_cleaned_normalized", "bases_normalizadas"))
    mkdir(os.path.join(BASE_DESTINO, "02_cleaned_normalized", "precios_normalizados"))

    mkdir(os.path.join(BASE_DESTINO, "03_knowledge_base"))

    # 04_imagenes
    for sub in ["originales", "renombradas", "360_render", "thumbnails"]:
        mkdir(os.path.join(BASE_DESTINO, "04_imagenes", sub))

    for c in CLIENTES:
        mkdir(os.path.join(BASE_DESTINO, "04_imagenes", "originales", c))

    # 05_pipeline
    mkdir(os.path.join(BASE_DESTINO, "05_pipeline", "utils"))

    # 06_shopify
    for c in CLIENTES:
        mkdir(os.path.join(BASE_DESTINO, "06_shopify", c))

    # 07_json_360
    for c in CLIENTES:
        mkdir(os.path.join(BASE_DESTINO, "07_json_360", c))

    # 08_lovely_models
    mkdir(os.path.join(BASE_DESTINO, "08_lovely_models", "lovely_templates"))
    mkdir(os.path.join(BASE_DESTINO, "08_lovely_models", "ui_blocks"))

    # 09_dashboards
    mkdir(os.path.join(BASE_DESTINO, "09_dashboards", "widgets"))

    # 10_deploy
    for sub in ["docker", "lambda", "nginx", "installers"]:
        mkdir(os.path.join(BASE_DESTINO, "10_deploy", sub))

    print("\n✔ Árbol de directorios creado correctamente.\n")


def copiar_contenido():
    print("\n===================================")
    print(" COPIANDO ARCHIVOS EXISTENTES")
    print("===================================\n")

    for c in CLIENTES:

        # CSV
        copy_if_exists(
            os.path.join(BASE_ORIGEN, BASE_DATOS.format(c=c)),
            os.path.join(BASE_DESTINO, "01_sources_originales", c)
        )

        copy_if_exists(
            os.path.join(BASE_ORIGEN, CATALOGO_IMGS.format(c=c)),
            os.path.join(BASE_DESTINO, "01_sources_originales", c)
        )

        copy_if_exists(
            os.path.join(BASE_ORIGEN, LISTA_PRECIOS.format(c=c)),
            os.path.join(BASE_DESTINO, "01_sources_originales", c)
        )

        # 📸 Carpetas de imágenes — CORREGIDO
        copy_folder_if_exists(
            os.path.join(BASE_ORIGEN, fotos_dir(c)),
            os.path.join(BASE_DESTINO, "04_imagenes", "originales", c)
        )

    print("\n✔ Copias de archivos completadas.\n")


def main():
    crear_estructura_srm()
    copiar_contenido()
    print("\n===================================")
    print("   🚀 SRM–QK–ADSI v1 LISTO")
    print("   Directorio final: C:\\SRM_ADSI")
    print("===================================\n")


if __name__ == "__main__":
    main()

