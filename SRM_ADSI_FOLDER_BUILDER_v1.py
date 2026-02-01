#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SRM_ADSI_FOLDER_BUILDER_v1.py
Crea el árbol de directorios oficial SRM–QK–ADSI (v1)
y copia/mueve los archivos existentes desde C:\img\ hacia su nueva estructura.

Ejecutar estando dentro de C:\img\
"""

import os
import shutil

# ------------------------------
# CONFIGURACIÓN
# ------------------------------

BASE_ORIGEN = r"C:\img"
BASE_DESTINO = r"C:\SRM_ADSI"

CLIENTES = [
    "Bara", "DFG", "Duna", "Japan", "Kaiqi",
    "Leo", "Store", "Vaisand", "Yokomar"
]

# Mapeos de archivos por cliente
BASE_DATOS = "Base_Datos_{c}.csv"
CATALOGO_IMGS = "catalogo_imagenes_{c}.csv"
LISTA_PRECIOS = "Lista_Precios_{c}.csv"
FOTOS_DIR = "FOTOS_CATALOGO_{c.upper()}"

# ------------------------------
# UTILIDAD – Crear carpeta segura
# ------------------------------

def mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)

# ------------------------------
# Copia segura (si existe)
# ------------------------------

def copy_if_exists(src, dst):
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f"✔ Copiado: {src} → {dst}")
    else:
        print(f"⚠ No encontrado: {src}")

# ------------------------------
# Copia de carpetas de imágenes
# ------------------------------

def copy_folder_if_exists(src, dst):
    if os.path.exists(src) and os.path.isdir(src):
        shutil.copytree(src, dst, dirs_exist_ok=True)
        print(f"📁 Copiada carpeta: {src} → {dst}")
    else:
        print(f"⚠ Carpeta no encontrada: {src}")

# ------------------------------
# CREAR ESTRUCTURA OFICIAL
# ------------------------------

def crear_estructura_srm():
    print("\n===================================")
    print(" CREANDO ESTRUCTURA SRM–QK–ADSI v1")
    print("===================================\n")

    # 00_docs
    for sub in ["Enciclopedia", "PDFs_Clientes", "Taxonomia_Referencia", "Arquitectura"]:
        mkdir(os.path.join(BASE_DESTINO, "00_docs", sub))

    # 01_sources_originales + subcarpetas por cliente
    for c in CLIENTES:
        mkdir(os.path.join(BASE_DESTINO, "01_sources_originales", c))

    # 02_cleaned_normalized
    mkdir(os.path.join(BASE_DESTINO, "02_cleaned_normalized", "catalogos_normalizados"))
    mkdir(os.path.join(BASE_DESTINO, "02_cleaned_normalized", "bases_normalizadas"))
    mkdir(os.path.join(BASE_DESTINO, "02_cleaned_normalized", "precios_normalizados"))

    # 03_knowledge_base
    mkdir(os.path.join(BASE_DESTINO, "03_knowledge_base"))

    # 04_imagenes
    for sub in ["originales", "renombradas", "360_render", "thumbnails"]:
        mkdir(os.path.join(BASE_DESTINO, "04_imagenes", sub))

    for c in CLIENTES:
        mkdir(os.path.join(BASE_DESTINO, "04_imagenes", "originales", c))

    # 05_pipeline + utils
    mkdir(os.path.join(BASE_DESTINO, "05_pipeline", "utils"))

    # 06_shopify + cliente
    for c in CLIENTES:
        mkdir(os.path.join(BASE_DESTINO, "06_shopify", c))

    # 07_json_360 + cliente
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

# ------------------------------
# COPIAR CONTENIDO EXISTENTE
# ------------------------------

def copiar_contenido():
    print("\n===================================")
    print(" COPIANDO ARCHIVOS EXISTENTES")
    print("===================================\n")

    for c in CLIENTES:

        # Archivos CSV
        copy_if_exists(
            os.path.join(BASE_ORIGEN, BASE_DATOS.format(c=c)),
            os.path.join(BASE_DESTINO, "01_sources_originales", c)
        )

        copy_if_exists(
            os.path.join(BASE_ORIGEN, CATALOGO_IMGS.format(c=c)),
            os.path.join(BASE_DESTINO, "01_sources_originales", c)
        )

        # Lista precios (si existe)
        copy_if_exists(
            os.path.join(BASE_ORIGEN, LISTA_PRECIOS.format(c=c)),
            os.path.join(BASE_DESTINO, "01_sources_originales", c)
        )

        # Carpetas de imágenes
        copy_folder_if_exists(
            os.path.join(BASE_ORIGEN, FOTOS_DIR.format(c=c)),
            os.path.join(BASE_DESTINO, "04_imagenes", "originales", c)
        )

    # Scripts y componentes SRM
    print("\n===================================")
    print(" COPIANDO SCRIPTS Y ARCHIVOS SRM–ADSI")
    print("===================================\n")

    scripts = [
        "extractor_v26.py", "unificador_v26.py", "renombrador_v26.py",
        "generador_360_v1.py", "shopify_compiler_v26.py",
        "generador_json_lovely_v1.py", "generar_taxonomia_srm_qk_adsi_v1.py"
    ]

    for s in scripts:
        copy_if_exists(
            os.path.join(BASE_ORIGEN, s),
            os.path.join(BASE_DESTINO, "05_pipeline")
        )

    # Archivos de taxonomía y Lovely
    srm_files = [
        "taxonomia_srm_qk_adsi_v1.csv",
        "components.json",
        "manifest.json",
        "loaders.json",
        "lovely_model_srm_v1.json",
        "routes.json"
    ]

    for f in srm_files:
        copy_if_exists(
            os.path.join(BASE_ORIGEN, f),
            os.path.join(BASE_DESTINO, "08_lovely_models")
        )

    print("\n✔ Copia completa.\n")

# ------------------------------
# MAIN
# ------------------------------

def main():
    crear_estructura_srm()
    copiar_contenido()
    print("\n===================================")
    print("   🚀 SRM–QK–ADSI v1 LISTO")
    print("   Directorio final: C:\\SRM_ADSI")
    print("===================================\n")

if __name__ == "__main__":
    main()

