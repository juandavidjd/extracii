#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
extractor_productos_v1.py
ADSI – Vision & OCR Extractor v1

Procesa TODAS las páginas del catálogo ubicadas en:
    C:\scrap\pages\

Extrae para cada producto:
    - Código
    - Nombre
    - Características / variantes
    - Empaque
    - Precio

Y genera:
    1) Imagen recortada de cada producto:
            C:\scrap\imagenes_recortadas\CODIGO_<codigo>.png

    2) Archivo CSV:
            C:\scrap\imagenes_recortadas\imagenes_recortadas.csv
"""

import os
import re
import cv2
import csv
import pytesseract
import numpy as np
from PIL import Image

# -------------------------------
# CONFIGURACIÓN RUTAS LOCALES
# -------------------------------
INPUT_DIR = r"C:\scrap\pages"
OUTPUT_DIR = r"C:\scrap\imagenes_recortadas"
CSV_PATH = os.path.join(OUTPUT_DIR, "imagenes_recortadas.csv")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# -------------------------------
# PATRONES REGEX
# -------------------------------
REGEX_CODIGO = re.compile(r"(COD[: ]*|CÓD[: ]*)(\d{4,6})", re.IGNORECASE)
REGEX_PRECIO = re.compile(r"\$\s*([\d\.,]+)")
REGEX_EMPAQUE = re.compile(r"(X\d+|SET|PAR|UND|BOLSA\s*\d*)", re.IGNORECASE)

# -------------------------------
# FUNCIONES DE OCR
# -------------------------------
def ocr_text(img):
    config = "--oem 3 --psm 6"
    text = pytesseract.image_to_string(img, config=config, lang="spa")
    return text


# -------------------------------
# LIMPIEZA DE TEXTO
# -------------------------------
def limpiar_precio(precio):
    try:
        return precio.replace(".", "").replace(",", "").strip()
    except:
        return ""


def normalizar_texto(text):
    return text.replace("\n", " ").replace("  ", " ").strip()


# -------------------------------
# DETECTAR BLOQUES (PRODUCTOS)
# Detección basada en contornos
# -------------------------------
def detectar_bloques(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    thresh = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 31, 15
    )

    contornos, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    bloques = []
    h, w = img.shape[:2]

    for c in contornos:
        x, y, w_box, h_box = cv2.boundingRect(c)
        # Filtrar recortes muy pequeños
        if w_box * h_box > 20000:
            bloques.append((x, y, w_box, h_box))

    # Ordenar por posición vertical
    bloques = sorted(bloques, key=lambda b: (b[1], b[0]))

    return bloques


# -------------------------------
# GUARDAR IMAGEN RECORTADA
# -------------------------------
def guardar_recorte(img, codigo, idx=0):
    if idx > 0:
        filename = f"CODIGO_{codigo}_{idx}.png"
    else:
        filename = f"CODIGO_{codigo}.png"

    outpath = os.path.join(OUTPUT_DIR, filename)
    cv2.imwrite(outpath, img)
    return filename


# -------------------------------
# PROCESAMIENTO DE CADA BLOQUE
# -------------------------------
def procesar_bloque(img_block):
    text = ocr_text(img_block)
    text_norm = normalizar_texto(text)

    # Buscar código
    codigo = ""
    m = REGEX_CODIGO.search(text_norm)
    if m:
        codigo = m.group(2).strip()

    # Buscar precio
    precio = ""
    p = REGEX_PRECIO.search(text_norm)
    if p:
        precio = limpiar_precio(p.group(1))

    # Empaque
    empaque = ""
    e = REGEX_EMPAQUE.search(text_norm)
    if e:
        empaque = e.group(1)

    # Nombre aproximado (texto sin codigo ni precio)
    nombre = text_norm
    nombre = REGEX_CODIGO.sub("", nombre)
    nombre = REGEX_PRECIO.sub("", nombre)

    # Recortar nombres muy genéricos
    if len(nombre) > 130:
        nombre = nombre[:130]

    nombre = nombre.strip()

    return codigo, nombre, empaque, precio


# -------------------------------
# PIPELINE PRINCIPAL
# -------------------------------
def procesar_paginas():
    registros = []

    for file in os.listdir(INPUT_DIR):
        if not file.lower().endswith((".jpg", ".png", ".jpeg")):
            continue

        print(f"[INFO] Procesando página: {file}")

        path = os.path.join(INPUT_DIR, file)
        img = cv2.imread(path)

        bloques = detectar_bloques(img)

        print(f"[OK] Bloques detectados: {len(bloques)}")

        codigo_repeticion = {}

        for (x, y, w_b, h_b) in bloques:
            block_img = img[y:y+h_b, x:x+w_b]

            codigo, nombre, empaque, precio = procesar_bloque(block_img)

            if codigo == "":
                continue

            # Control de duplicados
            if codigo not in codigo_repeticion:
                codigo_repeticion[codigo] = 0
            else:
                codigo_repeticion[codigo] += 1

            idx = codigo_repeticion[codigo]
            archivo = guardar_recorte(block_img, codigo, idx)

            registros.append([codigo, nombre, "", empaque, precio, archivo])

    # Guardar CSV
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["codigo","nombre","caracteristicas","empaque","precio","archivo_recorte"])
        writer.writerows(registros)

    print("\n[FINALIZADO] Extracción completa.")
    print(f"[CSV generado] {CSV_PATH}")
    print(f"[Total productos] {len(registros)}")


# -------------------------------
# EJECUCIÓN
# -------------------------------
if __name__ == "__main__":
    procesar_paginas()
