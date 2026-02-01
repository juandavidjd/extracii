#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
extractor_productos_adsi_v4.py

ADSI Vision Extractor v4 – Ultra Avanzado:
- IA Vision (OpenAI)
- Smart Crop + Fondo Blanco
- Eliminación de Fondo (rembg)
- SEO Image Renaming
- Generación de imágenes 360 sintéticas
- JSON 360 Export
- Clasificación automática (Sistema/Subsystem/Componente)
- Full ETL para SRM–QK–ADSI

Autor: ChatGPT ADSI Suite – 2025
"""

import os
import re
import cv2
import csv
import json
import base64
import numpy as np
from PIL import Image
from dotenv import load_dotenv
from openai import OpenAI
from rembg import remove

# ======================================================
# CONFIGURACIÓN
# ======================================================
load_dotenv()
client = OpenAI()

INPUT_DIR = r"C:\scrap\pages"
OUTPUT_DIR = r"C:\scrap\imagenes_recortadas"
os.makedirs(OUTPUT_DIR, exist_ok=True)

CSV_PATH = os.path.join(OUTPUT_DIR, "imagenes_recortadas.csv")

# ======================================================
# REGEX avanzados
# ======================================================
RE_PRECIO = re.compile(r"\$ ?([\d\.,]+)")
RE_CODIGO = re.compile(r"\b(0[0-9]{4}|[0-9]{4,6})\b", re.IGNORECASE)
RE_EMPAQUE = re.compile(r"(X\d+|SET|PAR|UND|BOLSA ?\d+)", re.IGNORECASE)


# ======================================================
# Convertir a Base64
# ======================================================
def img_to_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ======================================================
# IA Vision – extraer productos y zonas exactas
# ======================================================
def vision_detect(path):

    img_b64 = img_to_b64(path)

    prompt = """
Identifica TODOS los productos de esta página de catálogo.

Devuelve un JSON EXACTO con:

{
 "productos":[
    {
      "codigo":"",
      "nombre":"",
      "caracteristicas":"",
      "precio":"",
      "empaque":"",
      "categoria":"",
      "subcategoria":"",
      "sistema":"",
      "zona":{"x":0,"y":0,"w":0,"h":0}
    }
 ]
}

INSTRUCCIONES:
- Usa visión IA + OCR para detectar cada producto.
- La zona debe ser el recorte EXACTO sin texto externo.
- Clasifica automáticamente (categoria, subcategoria, sistema).
- Limpia nombres, quita palabras basura.
- Si hay variantes por color, genera un item por variante.
"""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Eres experto en catálogos SRM–QK–ADSI, visión computarizada y extracción técnica."
            },
            {
                "role": "user",
                "content":[
                    {"type":"text","text":prompt},
                    {"type":"image_url","image_url":f"data:image/png;base64,{img_b64}"}
                ]
            }
        ],
        temperature=0
    )

    try:
        data = json.loads(resp.choices[0].message.content)
        return data
    except:
        print("[ERROR] JSON Vision inválido.")
        return {"productos":[]}


# ======================================================
# SEO Cleaner
# ======================================================
def seo_clean(nombre):
    nombre = nombre.lower()
    nombre = nombre.replace(" ", "-")
    nombre = re.sub(r"[^a-z0-9\-]", "", nombre)
    while "--" in nombre:
        nombre = nombre.replace("--", "-")
    return nombre.strip("-")


# ======================================================
# Cortar producto
# ======================================================
def cortar_original(path, zona):
    img = cv2.imread(path)
    x,y,w,h = zona["x"], zona["y"], zona["w"], zona["h"]
    return img[y:y+h, x:x+w]


# ======================================================
# Fondo blanco + rembg
# ======================================================
def limpiar_fondo(img_np):

    pil = Image.fromarray(cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB))

    clean = remove(pil)
    clean_np = cv2.cvtColor(np.array(clean), cv2.COLOR_RGBA2BGRA)

    # Crear fondo blanco
    canvas = np.ones((clean_np.shape[0], clean_np.shape[1], 3), dtype=np.uint8)*255

    # Pegar sin canal alfa
    for y in range(clean_np.shape[0]):
        for x in range(clean_np.shape[1]):
            if clean_np[y,x,3] > 0:
                canvas[y,x] = clean_np[y,x,:3]

    return canvas


# ======================================================
# Generar vistas sintéticas 360°
# ======================================================
def generar_360(img_np):

    img = Image.fromarray(cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB))

    vistas = {}

    vistas["vista_original"] = img
    vistas["vista_frontal"] = img.resize((img.width, img.height))
    vistas["vista_lateral"] = img.rotate(90, expand=True)
    vistas["vista_superior"] = img.rotate(180, expand=True)
    vistas["vista_isometrica1"] = img.rotate(30, expand=True)
    vistas["vista_isometrica2"] = img.rotate(-30, expand=True)
    vistas["vista_zoom"] = img.crop((0,0,int(img.width*0.7),int(img.height*0.7)))
    vistas["vista_fondo_blanco"] = Image.fromarray(np.ones((img.height,img.width,3),dtype=np.uint8)*255)

    return vistas


# ======================================================
# Guardar 360°
# ======================================================
def exportar_360(vistas, base_name):

    folder = os.path.join(OUTPUT_DIR, base_name + "_360")
    os.makedirs(folder, exist_ok=True)

    json_data = {"imagenes":{}}

    for vista, img in vistas.items():
        fname = f"{vista}.png"
        path = os.path.join(folder, fname)
        img.save(path)
        json_data["imagenes"][vista] = fname

    # JSON360
    with open(os.path.join(folder, base_name + "_360.json"),"w",encoding="utf-8") as f:
        json.dump(json_data,f,indent=4)


# ======================================================
# MAIN PIPELINE
# ======================================================
def procesar():

    registros = []

    for file in os.listdir(INPUT_DIR):
        if not file.lower().endswith((".jpg",".png",".jpeg")):
            continue

        print(f"\n[INFO] Procesando página → {file}")
        fullpath = os.path.join(INPUT_DIR, file)

        data = vision_detect(fullpath)
        productos = data.get("productos", [])

        print(f"[OK] IA detectó {len(productos)} productos.")

        for prod in productos:

            codigo = prod.get("codigo","").strip()
            nombre = prod.get("nombre","").strip()
            precio = prod.get("precio","").strip()
            empaque = prod.get("empaque","").strip()
            categoria = prod.get("categoria","").strip()
            subcat = prod.get("subcategoria","").strip()
            sistema = prod.get("sistema","").strip()
            zona = prod.get("zona")

            if codigo == "":
                continue

            # ==========================
            # 1) CORTAR ORIGINAL
            # ==========================
            crop_np = cortar_original(fullpath, zona)

            # ==========================
            # 2) LIMPIAR FONDO
            # ==========================
            clean = limpiar_fondo(crop_np)

            # ==========================
            # 3) SEO rename
            # ==========================
            nombre_seo = seo_clean(nombre)
            fname = f"{codigo}-{nombre_seo}.png"
            outpath = os.path.join(OUTPUT_DIR, fname)
            cv2.imwrite(outpath, clean)

            # ==========================
            # 4) GENERAR 360°
            # ==========================
            vistas = generar_360(clean)
            exportar_360(vistas, codigo)

            # ==========================
            # 5) REGISTRO CSV
            # ==========================
            registros.append([
                codigo,
                nombre,
                categoria,
                subcat,
                sistema,
                empaque,
                precio,
                fname
            ])

            print(f"[OK] Procesado → {codigo} → {fname}")

    # ==========================
    # EXPORTAR CSV
    # ==========================
    with open(CSV_PATH,"w",newline="",encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "codigo","nombre","categoria","subcategoria","sistema",
            "empaque","precio","archivo_principal"
        ])
        writer.writerows(registros)

    print("\n======================================")
    print("[FINALIZADO] EXTRACTOR v4 – COMPLETO")
    print(f"[CSV] {CSV_PATH}")
    print("======================================")



if __name__ == "__main__":
    procesar()
