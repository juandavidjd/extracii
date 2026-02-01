#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
extractor_productos_adsi_v3.py

ADSI Vision Extractor v3 — IA Vision + OCR + NLP + Auto-Classifier
2025
"""

import os
import re
import csv
import cv2
from PIL import Image
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
import pytesseract
import base64
import json

# ==============================================
# CONFIG
# ==============================================
load_dotenv()
client = OpenAI()

INPUT_DIR = r"C:\scrap\pages"
OUTPUT_DIR = r"C:\scrap\imagenes_recortadas"
CSV_PATH = os.path.join(OUTPUT_DIR, "imagenes_recortadas.csv")
JSON_PATH = os.path.join(OUTPUT_DIR, "imagenes_recortadas.json")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==============================================
# REGEX INTELIGENTES
# ==============================================
RE_CODIGO = re.compile(r"\b([0-9]{4,6})\b")
RE_PRECIO = re.compile(r"\$ ?([\d\.,]+)")
RE_EMPAQUE = re.compile(r"(X\d+|SET|PAR|UND|BOLSA ?\d+)", re.IGNORECASE)

PALABRAS_RUIDO = [
    "nuevo", "producto", "colombiano", "marca registrada",
    "arm", "importaller", "precio", "teléfonos",
    "ventas", "despachos", "cartera"
]

# ==============================================
# OBTENER BASE64 DE IMAGEN
# ==============================================
def img_to_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ==============================================
# IA VISION – detectar productos en la página
# ==============================================
def vision_detect(path):

    img_b64 = img_to_b64(path)

    prompt = """
Analiza esta página de catálogo.

Devuelve un JSON estrictamente estructurado con este formato:

{
  "productos": [
    {
      "codigo": "",
      "nombre": "",
      "caracteristicas": "",
      "empaque": "",
      "precio": "",
      "zona": {"x":0, "y":0, "w":0, "h":0}
    }
  ]
}

Reglas:
- Identifica cada producto como un elemento separado.
- La zona corresponde al recorte EXACTO del producto.
- Usa OCR vision + semántica para detectar código, nombre y precio.
- Si un dato no existe, déjalo vacío.
- Si hay variantes (colores), crea un producto por variante.
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Eres un experto en catalogación técnica y visión computarizada ADSI."},
            {"role": "user", "content": [
                {"type":"input_text", "text": prompt},
                {"type":"input_image", "image_url": f"data:image/png;base64,{img_b64}"}
            ]}
        ],
        temperature=0
    )

    try:
        out = res.choices[0].message.content
        data = json.loads(out)
        return data
    except:
        print("[ERROR] No se pudo parsear JSON del modelo.")
        return {"productos":[]}


# ==============================================
# AUTO-CLASSIFIER (categoría)
# ==============================================
def auto_classifier(nombre):

    n = nombre.lower()

    if "guardabarro" in n:
        return "GUARDABARRO"
    if "caucho" in n or "amortiguador" in n:
        return "CAUCHOS"
    if "caliper" in n:
        return "CALIPER"
    if "manilar" in n or "puño" in n:
        return "MANILARES"
    if "protector" in n:
        return "PROTECTORES"
    if "silla" in n:
        return "ACCESORIOS DE TALLER"
    if "soporte" in n:
        return "SOPORTES"

    return "OTROS"


# ==============================================
# RECORTAR Y GUARDAR PNG
# ==============================================
def recortar_png(img_path, zona, codigo, idx):

    img = cv2.imread(img_path)
    x,y,w,h = zona["x"], zona["y"], zona["w"], zona["h"]

    crop = img[y:y+h, x:x+w]

    if idx == 0:
        fname = f"CODIGO_{codigo}.png"
    else:
        fname = f"CODIGO_{codigo}_{idx}.png"

    outpath = os.path.join(OUTPUT_DIR, fname)
    cv2.imwrite(outpath, crop)
    return fname


# ==============================================
# MAIN PIPELINE
# ==============================================
def procesar():

    registros = []
    repetidos = {}

    for file in os.listdir(INPUT_DIR):

        if not file.lower().endswith((".jpg",".png",".jpeg")):
            continue

        print(f"\n[INFO] Procesando página → {file}")

        fullpath = os.path.join(INPUT_DIR, file)

        # ======== IA VISION ==========
        data = vision_detect(fullpath)

        productos = data.get("productos", [])
        print(f"[OK] IA detectó {len(productos)} productos.")

        for prod in productos:

            codigo = prod.get("codigo","").strip()
            nombre = prod.get("nombre","").strip()
            caracteristicas = prod.get("caracteristicas","").strip()
            precio = prod.get("precio","").strip()
            empaque = prod.get("empaque","").strip()
            zona = prod.get("zona", {})

            if codigo == "":
                continue

            # Control de repetidos
            if codigo not in repetidos:
                repetidos[codigo] = 0
            else:
                repetidos[codigo] += 1

            idx = repetidos[codigo]

            archivo = recortar_png(fullpath, zona, codigo, idx)

            categoria = auto_classifier(nombre)

            registros.append([
                codigo,
                nombre,
                caracteristicas,
                empaque,
                precio,
                categoria,
                archivo
            ])

            print(f"[OK] Producto recortado → {codigo} → {archivo}")


    # =========================
    # GUARDAR CSV
    # =========================
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["codigo","nombre","caracteristicas","empaque","precio","categoria","archivo_recorte"])
        writer.writerows(registros)

    # =========================
    # GUARDAR JSON
    # =========================
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(registros, f, indent=3)

    print("\n======================================")
    print("[FINALIZADO] Extracción IA Vision COMPLETA")
    print(f"[CSV generado] {CSV_PATH}")
    print(f"[JSON generado] {JSON_PATH}")
    print(f"[Total productos extraídos] {len(registros)}")
    print("======================================")



if __name__ == "__main__":
    procesar()
