#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
====================================================================================
 RENOMBRADOR v26 — SRM–QK–ADSI (FINAL GOLD)
====================================================================================

Objetivo:
- Vincular imágenes → nombres ricos → 360° → Shopify
- Usa: knowledge_base_unificada.csv + JSON360 + Vision IA (opcional)
- Elimina prefijos, códigos y SKUs (regla de oro del proyecto)
- Produce: /IMAGENES_RENOMBRADAS_v26, /DUPLICADOS_v26, log_renombrado_v26.csv

====================================================================================
"""

import os
import re
import json
import base64
import hashlib
import pandas as pd
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from openai import OpenAI

# ================================================================================
# CONFIG
# ================================================================================

BASE = Path(r"C:\img")

DIR_SALIDA = BASE / "IMAGENES_RENOMBRADAS_v26"
DIR_DUP = BASE / "DUPLICADOS_v26"
DIR_LOG = BASE / "logs_v26"
DIR_360 = BASE / "json_360_por_cliente"

os.makedirs(DIR_SALIDA, exist_ok=True)
os.makedirs(DIR_DUP, exist_ok=True)
os.makedirs(DIR_LOG, exist_ok=True)

LOG_FILE = DIR_LOG / "log_renombrado_v26.csv"
KB_FILE = BASE / "knowledge_base_unificada.csv"

# Cliente OpenAI opcional
API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=API_KEY) if API_KEY else None

# ===================================================================
# UTILIDADES DE TEXTO
# ===================================================================

def limpiar_texto_final(texto):
    """
    *ELIMINA* prefijos, códigos, sufijos y SKUs
    """
    if not isinstance(texto, str):
        return ""

    t = texto.strip()

    # Eliminar prefijos tipo 1-11-131
    t = re.sub(r"^\d{1,4}-\d{1,4}-\d{1,4}[-\s]*", "", t)

    # Eliminar códigos largos tipo 1010115
    t = re.sub(r"^\d{5,10}[-\s]*", "", t)

    # Eliminar códigos tipo DALU017
    t = re.sub(r"^[A-Z]{2,6}\d{2,6}[-\s]*", "", t)

    # Normalizar espacios
    t = re.sub(r"\s+", " ", t)

    return t.strip()


def slug(texto):
    texto = limpiar_texto_final(texto)
    texto = texto.lower()

    texto = re.sub(r"[^\w\s-]", "", texto)
    texto = texto.replace(" ", "-")
    texto = re.sub(r"-+", "-", texto)

    return texto[:180].strip("-")


def sha1_bytes(b):
    return hashlib.sha1(b).hexdigest()


# ================================================================================
# IA VISION
# ================================================================================

def vision_identificar(img_bytes):
    if not client:
        return ""

    try:
        b64 = base64.b64encode(img_bytes).decode("utf-8")

        resp = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=60,
            messages=[
                {
                    "role": "system",
                    "content": "Eres experto en repuestos de motos. Devuelve SOLO el nombre comercial rico."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Identifica este repuesto sin códigos:"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                    ]
                }
            ]
        )

        return resp.choices[0].message.content.strip()

    except Exception:
        return ""


# ================================================================================
# CARGA DE 360°
# ================================================================================

def cargar_json360():
    """
    Carga todos los JSON 360° de los clientes en un gran diccionario
    clave = nombre_rico_final
    valor = perfil 360°
    """
    mapa = {}

    for file in DIR_360.glob("*.json"):
        try:
            data = json.load(open(file, "r", encoding="utf-8"))
            for item in data:
                clave = item["nombre_rico"].lower().strip()
                mapa[clave] = item
        except:
            pass

    return mapa


# ================================================================================
# MATCHING FINAL
# ================================================================================

def resolver_nombre(fn, img_bytes, mapa360):
    """
    1. Exacto por coincidencia del nombre de la imagen
    2. Aproximado por subcadenas
    3. IA Vision
    4. Fallback: nombre base limpio
    """

    base = Path(fn).stem.lower().strip()

    # 1. EXACTO
    if base in mapa360:
        return "EXACTO", mapa360[base]["nombre_rico"]

    # 2. APROXIMADO
    for k in mapa360.keys():
        if k.replace("-", "") in base.replace("-", "") or base.replace("-", "") in k.replace("-", ""):
            return "APROX", mapa360[k]["nombre_rico"]

    # 3. VISIÓN
    vision_name = vision_identificar(img_bytes)
    if vision_name:
        return "VISION", limpiar_texto_final(vision_name)

    # 4. FALLBACK
    return "FALLBACK", limpiar_texto_final(base)


# ================================================================================
# CONVERTIR A JPG
# ================================================================================

def convertir_a_jpg(img_bytes):
    try:
        img = Image.open(io.BytesIO(img_bytes))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=90)
        return out.getvalue()
    except:
        return None


# ================================================================================
# PROCESO PRINCIPAL
# ================================================================================

def ejecutar():
    print("\n=== RENOMBRADOR v26 — SRM–QK–ADSI ===")

    mapa360 = cargar_json360()
    print(f"✔ JSON360 cargados: {len(mapa360)} productos\n")

    filas_log = []
    hashes = set()

    carpetas = [
        "FOTOS_CATALOGO_BARA",
        "FOTOS_CATALOGO_DFG",
        "FOTOS_CATALOGO_DUNA",
        "FOTOS_CATALOGO_JAPAN",
        "FOTOS_CATALOGO_KAIQI",
        "FOTOS_CATALOGO_LEO",
        "FOTOS_CATALOGO_STORE",
        "FOTOS_CATALOGO_VAISAND",
        "FOTOS_CATALOGO_YOKOMAR",
    ]

    for carpeta in carpetas:
        folder = BASE / carpeta
        if not folder.exists():
            continue

        print(f"📂 Procesando: {carpeta}")

        for fn in os.listdir(folder):
            path = folder / fn

            if not fn.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                continue

            try:
                img_bytes = open(path, "rb").read()
            except:
                continue

            sha = sha1_bytes(img_bytes)

            # DUPLICADOS
            if sha in hashes:
                destino = DIR_DUP / fn
                open(destino, "wb").write(img_bytes)
                filas_log.append([fn, "DUPLICADO", destino.name])
                continue

            hashes.add(sha)

            estrategia, nombre_rico = resolver_nombre(fn, img_bytes, mapa360)
            slugname = slug(nombre_rico) + ".jpg"
            destino = DIR_SALIDA / slugname

            # Manejar conflicto de nombre
            base_s, ext = os.path.splitext(slugname)
            n = 2
            while destino.exists():
                destino = DIR_SALIDA / f"{base_s}-{n}.jpg"
                n += 1

            # Guardar JPG final
            try:
                Image.open(path).convert("RGB").save(destino, "JPEG", quality=90)
            except:
                continue

            filas_log.append([fn, estrategia, destino.name])

    # Guardar log
    df_log = pd.DataFrame(filas_log, columns=["original", "estrategia", "final"])
    df_log.to_csv(LOG_FILE, index=False, encoding="utf-8")

    print("\n=== PROCESO COMPLETADO v26 ===")
    print(f"✔ Imágenes renombradas: {DIR_SALIDA}")
    print(f"✔ Duplicados: {DIR_DUP}")
    print(f"✔ Log: {LOG_FILE}\n")


# ==================================================================================
# MAIN
# ==================================================================================

if __name__ == "__main__":
    ejecutar()
