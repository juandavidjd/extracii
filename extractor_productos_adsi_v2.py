#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
extractor_productos_adsi_v2.py
ADSI Vision Extractor — v2 AVANZADO

Basado en:
- Segmentación visual inteligente (OpenCV)
- OCR híbrido (Tesseract doble pasada)
- Detección semántica ADSI (regex + NLP)
- Reconocimiento de filas en tablas (catálogos ARM)
- Limpieza y normalización para ETL e-commerce SRM–QK–ADSI

Autor: ChatGPT ADSI Suite — 2025
"""

import os
import re
import csv
import cv2
import numpy as np
from PIL import Image
import pytesseract

# ==============================
# CONFIGURACIÓN DE RUTAS
# ==============================
INPUT_DIR = r"C:\scrap\pages"
OUTPUT_DIR = r"C:\scrap\imagenes_recortadas"
CSV_PATH = os.path.join(OUTPUT_DIR, "imagenes_recortadas.csv")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==============================
# REGEX INTELIGENTES
# ==============================
RE_CODIGO = re.compile(r"\b(0\d{4}|[1-9]\d{3,5})\b")
RE_COD = re.compile(r"(COD[: ]*)(\d{4,6})", re.IGNORECASE)
RE_PRECIO = re.compile(r"\$ ?([\d\.,]+)")
RE_EMPAQUE = re.compile(r"(X\d+|SET|PAR|UND|BOLSA ?\d+)", re.IGNORECASE)

PALABRAS_RUIDO = [
    "nuevo", "producto", "colombiano", "marca registrada",
    "arm", "importaller", "precio", "teléfonos",
    "ventas", "despachos", "cartera"
]

# ==============================
# FUNCIÓN OCR (DOBLE PASADA)
# ==============================
def ocr_text(img):
    config = "--oem 3 --psm 6"
    text = pytesseract.image_to_string(img, config=config, lang="spa")
    return text

def ocr_preciso(img):
    # aumento contraste y escala para mejorar OCR de textos pequeños
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=1.8, fy=1.8)
    gray = cv2.GaussianBlur(gray, (3,3), 0)
    _, th = cv2.threshold(gray, 0,255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return ocr_text(th)

# ==============================
# LIMPIAR TEXTO DE RUIDO
# ==============================
def limpiar_texto(text):
    t = text.lower()
    for w in PALABRAS_RUIDO:
        t = t.replace(w, "")
    return t.strip().upper()

def price_clean(p):
    return p.replace(".", "").replace(",", "").strip()

# ==============================
# DETECTAR FILAS DE TABLAS
# PARA CATÁLOGOS ARM
# ==============================
def detectar_filas(img):
    """
    Detecta filas horizontales (celdas) en catálogos.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 60, 180)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, 120, minLineLength=300, maxLineGap=20)

    if lines is None:
        return []

    cortes = []
    h, w = img.shape[:2]

    ys = [l[0][1] for l in lines] + [l[0][3] for l in lines]
    ys = sorted(list(set(ys)))

    # construir bandas entre líneas
    bandas = []
    for i in range(len(ys)-1):
        y1 = ys[i]
        y2 = ys[i+1]
        if (y2 - y1) > 60:
            bandas.append((0, y1, w, y2 - y1))

    return bandas


# ==============================
# SEGMENTACIÓN MULTI-BLOQUE
# ==============================
def detectar_bloques(img):
    """
    Mezcla:
    - Contornos
    - Detección de filas (para tablas)
    - Detección de fotos de productos
    """

    filas = detectar_filas(img)
    bloques = []

    # Si detectó filas → usar eso directamente
    if len(filas) > 3:
        bloques.extend(filas)

    # Extra detección por contornos para catálogos sin tabla
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    thresh = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY_INV, 31, 15
    )

    contornos, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for c in contornos:
        x, y, w, h = cv2.boundingRect(c)
        if w*h > 23000:
            bloques.append((x,y,w,h))

    # Quitar duplicados o solapados grandes
    final = []
    for b in bloques:
        if not any(abs(b[1]-b2[1])<30 and abs(b[0]-b2[0])<30 for b2 in final):
            final.append(b)

    final = sorted(final, key=lambda b: (b[1],b[0]))

    return final


# ==============================
# DETECCIÓN SEMÁNTICA
# ==============================
def extraer_info(text):

    original = text
    text = limpiar_texto(original)

    # Código
    codigo = ""
    m1 = RE_COD.search(original)
    if m1:
        codigo = m1.group(2)

    if codigo == "":
        m2 = RE_CODIGO.search(text)
        if m2:
            codigo = m2.group(1)

    # Precio
    precio = ""
    p = RE_PRECIO.search(original)
    if p:
        precio = price_clean(p.group(1))

    # Empaque
    empaque = ""
    e = RE_EMPAQUE.search(original)
    if e:
        empaque = e.group(1)

    # Nombre limpio
    nombre = text
    nombre = RE_COD.sub("", nombre)
    nombre = RE_PRECIO.sub("", nombre)
    nombre = nombre.strip().upper()

    # Quitar duplicidades largas
    if len(nombre) > 140:
        nombre = nombre[:140]

    return codigo, nombre, empaque, precio


# ==============================
# GUARDAR RECORTE
# ==============================
def guardar_recorte(img, codigo, rep=0):
    if rep == 0:
        fname = f"CODIGO_{codigo}.png"
    else:
        fname = f"CODIGO_{codigo}_{rep}.png"

    out = os.path.join(OUTPUT_DIR, fname)
    cv2.imwrite(out, img)
    return fname


# ==============================
# PIPELINE PRINCIPAL
# ==============================
def procesar():
    registros = []

    for file in os.listdir(INPUT_DIR):
        if not file.lower().endswith((".png",".jpg",".jpeg")):
            continue

        print(f"\n[INFO] Procesando página: {file}")
        path = os.path.join(INPUT_DIR, file)
        img = cv2.imread(path)

        bloques = detectar_bloques(img)
        print(f"[OK] Bloques detectados: {len(bloques)}")

        repeticiones = {}

        for (x,y,w,h) in bloques:
            crop = img[y:y+h, x:x+w]

            # OCR doble pasada
            t1 = ocr_text(crop)
            t2 = ocr_preciso(crop)
            texto = t1 + " " + t2

            codigo, nombre, empaque, precio = extraer_info(texto)

            if codigo == "":
                continue

            # control de repetidos
            if codigo not in repeticiones:
                repeticiones[codigo] = 0
            else:
                repeticiones[codigo] += 1

            rep = repeticiones[codigo]

            archivo = guardar_recorte(crop, codigo, rep)

            registros.append([
                codigo,
                nombre,
                "",       # características extra (versión v3)
                empaque,
                precio,
                archivo
            ])

            print(f"[OK] Producto detectado → Código {codigo} → {archivo}")

    # Guardar CSV final
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["codigo","nombre","caracteristicas","empaque","precio","archivo_recorte"])
        writer.writerows(registros)

    print("\n==============================")
    print("[FINALIZADO] EXTRACCIÓN COMPLETA")
    print(f"[CSV] {CSV_PATH}")
    print(f"[TOTAL PRODUCTOS EXTRAÍDOS] {len(registros)}")
    print("==============================")



if __name__ == "__main__":
    procesar()
