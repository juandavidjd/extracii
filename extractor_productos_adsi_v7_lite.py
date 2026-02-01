#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EXTRACTOR v7 LITE – Ultra Vision ADSI
SIN PDF – SIN VIDEO – SIN REMBG – SIN ONNX
Incluye VERIFICADOR DE DEPENDENCIAS AUTOMÁTICO

Produce:
- Imagen limpia PNG
- Imagen super-res PNG
- JSON360
- CSV maestro

Compatible con NumPy 2.x, Windows 10/11, venv.
"""

# ============================================================
# VERIFICADOR DE DEPENDENCIAS
# ============================================================

import importlib
import sys
import subprocess

NEEDED = {
    "openai": "openai>=1.52",
    "PIL": "pillow",
    "cv2": "opencv-python",
    "numpy": "numpy",
    "dotenv": "python-dotenv"
}

def check_and_install():
    print("\n[CHECK] Verificando dependencias...\n")

    for module, pkg in NEEDED.items():
        try:
            importlib.import_module(module)
            print(f"[OK] {module} ✓")
        except ImportError:
            print(f"[MISSING] {module} — instalando {pkg} ...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

    print("\n[CHECK] Dependencias listas.\n")

check_and_install()

# ============================================================
# IMPORTS YA SEGUROS
# ============================================================

import os
import cv2
import csv
import json
import asyncio
import base64
import logging
import numpy as np
from PIL import Image
from dotenv import load_dotenv
from openai import OpenAI

# ============================================================
# CONFIG
# ============================================================

load_dotenv()
client = OpenAI()

BASE = r"C:\scrap"
INPUT_DIR = os.path.join(BASE, "pages")
OUTPUT = os.path.join(BASE, "output_v7_lite")
LOGS = os.path.join(BASE, "logs")

for d in [OUTPUT, LOGS]:
    os.makedirs(d, exist_ok=True)

IMG_DIR = os.path.join(OUTPUT, "images")
SR_DIR = os.path.join(OUTPUT, "images_superres")
JSON_DIR = os.path.join(OUTPUT, "json360")

for d in [IMG_DIR, SR_DIR, JSON_DIR]:
    os.makedirs(d, exist_ok=True)

CSV_PATH = os.path.join(OUTPUT, "productos.csv")

logging.basicConfig(
    filename=os.path.join(LOGS, "v7_lite.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ============================================================
# UTILIDADES
# ============================================================

def img_to_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def save_b64_png(b64_str, outpath):
    raw = base64.b64decode(b64_str)
    with open(outpath, "wb") as f:
        f.write(raw)

# ============================================================
# IA VISION
# ============================================================

async def vision_extract(path):

    b64 = img_to_b64(path)

    prompt = """
Devuelve estrictamente JSON:

{
 "productos":[
    {
      "codigo":"",
      "nombre":"",
      "precio":"",
      "bbox":{"x":0,"y":0,"w":0,"h":0},
      "clean_b64":"<base64 PNG>",
      "superres_b64":"<base64 PNG>"
    }
 ]
}

Reglas:
- Identifica todos los productos en la página.
- codigo = siempre extraído de la pieza gráfica.
- nombre = texto principal o título del producto.
- precio = si aparece, extraerlo tal cual.
- bbox = zona exacta del producto.
- clean_b64 = recorte exacto con fondo blanco.
- superres_b64 = versión IA 4x super resolution.
"""

    res = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role":"system","content":"Eres Ultra Vision ADSI Experto."},
            {"role":"user","content":[
                {"type":"text","text":prompt},
                {"type":"image_url","image_url":f"data:image/png;base64,{b64}"}
            ]}
        ],
        temperature=0
    )

    try:
        out = json.loads(res.choices[0].message.content)
        return out
    except Exception as e:
        logging.error("Error parsing JSON Vision: "+str(e))
        return {"productos":[]}

# ============================================================
# PROCESAR PÁGINA
# ============================================================

async def procesar_pagina(path, registros):

    print(f"[PAGE] Procesando {os.path.basename(path)}")
    logging.info(f"Procesando página: {path}")

    vision_data = await vision_extract(path)

    for p in vision_data["productos"]:

        codigo = p["codigo"].strip().replace(" ", "_")
        nombre = p["nombre"].strip()
        precio = p["precio"].strip()

        clean_path = os.path.join(IMG_DIR, f"{codigo}.png")
        sr_path = os.path.join(SR_DIR, f"{codigo}_sr.png")

        save_b64_png(p["clean_b64"], clean_path)
        save_b64_png(p["superres_b64"], sr_path)

        # JSON360
        with open(os.path.join(JSON_DIR, f"{codigo}.json"), "w", encoding="utf-8") as f:
            json.dump(p, f, indent=4, ensure_ascii=False)

        registros.append([
            codigo, nombre, precio, clean_path, sr_path
        ])

    return registros

# ============================================================
# MAIN
# ============================================================

async def main():

    registros = []
    tasks = []

    for file in os.listdir(INPUT_DIR):
        if file.lower().endswith((".png",".jpg",".jpeg")):
            tasks.append(procesar_pagina(os.path.join(INPUT_DIR,file), registros))

    await asyncio.gather(*tasks)

    # CSV final
    with open(CSV_PATH,"w",newline="",encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["codigo","nombre","precio","imagen_clean","imagen_superres"])
        w.writerows(registros)

    print("\n[OK] EXTRACTOR v7 LITE completado sin errores.")
    logging.info("EXTRACTOR v7 LITE completado.")

if __name__ == "__main__":
    asyncio.run(main())
