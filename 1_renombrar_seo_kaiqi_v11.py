#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
 🔥 RENOMBRADOR ULTRA HÍBRIDO KAIQI v11 — Opción C FINAL
=========================================================

Autor: ChatGPT + Juan David
Versión: 11.0 ESTABLE
Descripción:
Este script implementa el MODELO HÍBRIDO INTELIGENTE:

PRIORIDAD DE INFORMACIÓN PARA RENOMBRAR:
----------------------------------------
1) Coincidencia en catálogos híbridos:
   - catalogo_kaiqi_imagenes_bara.csv
   - catalogo_kaiqi_imagenes_japan.csv
   - catalogo_kaiqi_imagenes_kaiqi.csv
   - catalogo_kaiqi_imagenes_leo.csv
   - catalogo_kaiqi_imagenes_store.csv
   - catalogo_kaiqi_imagenes_vaisand.csv
   Usa: Nombre_Comercial_Catalogo como base.

2) Coincidencia en Inventario Kaiqi:
   - Inventario_FINAL_CON_TAXONOMIA.csv
   Usa: DESCRIPCION, SISTEMA, SUBSISTEMA, COMPONENTE, TIPO_VEHICULO, MARCA, MODELO, CILINDRAJE

3) Coincidencia en JC:
   Usa PRODUCTO / DESCRIPCION

4) Coincidencia en YOKO:
   Usa DESCRIPCION

5) Si NO hay datos humanos → IA Visión 4o

REGLAS ABSOLUTAS:
-----------------
❌ NO incluir prefijos: 1-11-131, 2-3-85…
❌ NO incluir sufijos: 1010115…
❌ NO incluir SKUs DALU017…
❌ NO incluir códigos internos.
❌ NO reemplazar un nombre rico por uno pobre.
✔ SI mantener nombres ricos de catálogo.
✔ SI fusionar DESCRIPCIÓN Kaiqi con catálogo.
✔ SI fusionar todas las fuentes humanas.
✔ SI usar IA solo como último recurso.
✔ SI generar slug SEO limpio final para renombrar.

=========================================================
"""

import os
import re
import csv
import json
import base64
import unicodedata
import pandas as pd
from openai import OpenAI

# ====================================================
# CONFIGURACIÓN GENERAL
# ====================================================

BASE = r"C:\img"

DIRS_CATALOGOS = [
    os.path.join(BASE, "catalogo_kaiqi_imagenes_bara.csv"),
    os.path.join(BASE, "catalogo_kaiqi_imagenes_japan.csv"),
    os.path.join(BASE, "catalogo_kaiqi_imagenes_kaiqi.csv"),
    os.path.join(BASE, "catalogo_kaiqi_imagenes_leo.csv"),
    os.path.join(BASE, "catalogo_kaiqi_imagenes_store.csv"),
    os.path.join(BASE, "catalogo_kaiqi_imagenes_vaisand.csv"),
]

INVENTARIO = os.path.join(BASE, "Inventario_FINAL_CON_TAXONOMIA.csv")
JC = os.path.join(BASE, "LISTA DE PRECIOS NOVIEMBRE 13 2025 TRABAJO JC.xlsx")
YOKO = os.path.join(BASE, "LISTA DE PRECIOS  YOKOMAR ACTUALIZADA 2025.xlsx")

DIR_IMGS = os.path.join(BASE, "IMAGENES_KAIQI_MAESTRAS")
DIR_OUT_DUP = os.path.join(BASE, "IMAGENES_DUPLICADOS")
LOG_PATH = os.path.join(BASE, "log_renombrado_seo_v11.csv")

os.makedirs(DIR_OUT_DUP, exist_ok=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ====================================================
# UTILIDADES BASE
# ====================================================

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def quitar_codigos(text: str) -> str:
    # elimina patrones como 1-11-131 / 2-3-85 / 1010115 / DALU017
    text = re.sub(r"\b\d{1,4}-\d{1,4}-\d{1,4}\b", "", text)
    text = re.sub(r"\b\d{4,8}\b", "", text)
    text = re.sub(r"\b[A-Z]{3,5}\d+\b", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def encode_image(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except:
        return None

# ====================================================
# IA: Nombre final cuando no existen datos humanos
# ====================================================

PROMPT_IA = """
Eres un experto mecánico especializado en repuestos de motos y motocargueros.
Identifica el REPUESTO EXACTO EN LA IMAGEN y devuelve un nombre profesional y rico.
NO uses códigos. NO uses números de parte. NO uses SKU. NO uses prefijos ni sufijos.

Formato de salida:
{
 "nombre_rico": "string"
}
"""

def pedir_nombre_ia(img_path):
    img64 = encode_image(img_path)
    if not img64:
        return None

    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.1,
            max_tokens=200,
            messages=[
                {"role": "system", "content": "Responde solo JSON válido."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT_IA},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img64}", "detail": "high"}}
                    ]
                }
            ]
        )
        txt = resp.choices[0].message.content.strip()
        txt = txt.replace("```json", "").replace("```", "").strip()
        return json.loads(txt)["nombre_rico"]
    except:
        return None

# ====================================================
# CARGA DE BASES HUMANAS
# ====================================================

def cargar_catalogos():
    registros = {}
    for path in DIRS_CATALOGOS:
        if not os.path.exists(path):
            continue

        df = pd.read_csv(path, encoding="utf-8")
        if "Filename_Original" not in df.columns or "Nombre_Comercial_Catalogo" not in df.columns:
            print(f"⚠ Catálogo inválido: {path}")
            continue

        for _, row in df.iterrows():
            fn = str(row["Filename_Original"]).strip()
            nombre = str(row["Nombre_Comercial_Catalogo"]).strip()
            if fn and nombre:
                registros[fn.lower()] = nombre

    return registros


def cargar_inventario_kaiqi():
    if not os.path.exists(INVENTARIO):
        return {}

    df = pd.read_csv(INVENTARIO, encoding="utf-8")
    if "IMAGEN_ARCHIVO" not in df.columns:
        print("⚠ IMAGEN_ARCHIVO ausente en Inventario Kaiqi")
        return {}

    registros = {}
    for _, row in df.iterrows():
        img = str(row["IMAGEN_ARCHIVO"]).strip().lower()
        desc = str(row["DESCRIPCION"]).strip()
        comp = str(row["COMPONENTE"]).strip()
        sis = str(row["SISTEMA"]).strip()
        sub = str(row["SUBSISTEMA"]).strip()
        veh = str(row["TIPO_VEHICULO"]).strip()
        marca = str(row["MARCA"]).strip()
        modelo = str(row["MODELO"]).strip()
        cil = str(row["CILINDRAJE"]).strip()

        nombre = " ".join([desc, comp, sis, sub, marca, modelo, cil])
        nombre = re.sub(r"\s+", " ", nombre).strip()

        if img:
            registros[img] = nombre

    return registros


def cargar_jc():
    if not os.path.exists(JC):
        return {}
    df = pd.read_excel(JC)
    if "VER IMAGEN" not in df.columns or "PRODUCTO / DESCRIPCION" not in df.columns:
        return {}

    registros = {}
    for _, row in df.iterrows():
        img = str(row["VER IMAGEN"]).strip().lower()
        desc = str(row["PRODUCTO / DESCRIPCION"]).strip()
        if img and desc:
            registros[img] = desc

    return registros


def cargar_yoko():
    if not os.path.exists(YOKO):
        return {}
    df = pd.read_excel(YOKO)
    if "DESCRIPCION" not in df.columns:
        return {}

    registros = {}
    for _, row in df.iterrows():
        desc = str(row["DESCRIPCION"]).strip()
        ref = str(row["REFERENCIA"]).strip()
        nombre = f"{desc} {ref}".strip()
        if nombre:
            registros[nombre] = nombre

    return registros

# ====================================================
# MOTOR DE MATCH HÍBRIDO
# ====================================================

def resolver_nombre_hibrido(fn, catalogos, kaiqi, jc, yoko, img_path):
    base = os.path.basename(fn).lower()

    # 1) Catálogos híbridos
    for key, val in catalogos.items():
        if key in base:
            return "CATALOGO_HIBRIDO", quitar_codigos(val)

    # 2) Kaiqi directo
    for key, val in kaiqi.items():
        if key in base:
            return "KAIQI", quitar_codigos(val)

    # 3) JC
    for key, val in jc.items():
        if key in base:
            return "JC", quitar_codigos(val)

    # 4) Yoko
    for key, val in yoko.items():
        if key in base:
            return "YOKO", quitar_codigos(val)

    # 5) IA
    nombre_ia = pedir_nombre_ia(img_path)
    if nombre_ia:
        return "IA", quitar_codigos(nombre_ia)

    # 6) fallback
    return "FALLBACK", quitar_codigos(os.path.splitext(base)[0])

# ====================================================
# PROCESO PRINCIPAL
# ====================================================

def main():

    print("\n=========================================")
    print(" 🔥 RENOMBRADOR KAIQI v11 — Opción C FINAL")
    print("=========================================\n")

    catalogos = cargar_catalogos()
    kaiqi = cargar_inventario_kaiqi()
    jc_base = cargar_jc()
    yoko_base = cargar_yoko()

    print(f"Catalogos cargados: {len(catalogos)}")
    print(f"Inventario Kaiqi:   {len(kaiqi)}")
    print(f"JC:                 {len(jc_base)}")
    print(f"YOKO:               {len(yoko_base)}\n")

    imgs = [f for f in os.listdir(DIR_IMGS) if f.lower().endswith((".jpg", ".jpeg", ".png"))]

    with open(LOG_PATH, "w", newline="", encoding="utf-8") as logf:
        writer = csv.writer(logf)
        writer.writerow(["original", "nuevo", "estrategia"])

        for fn in imgs:
            old_path = os.path.join(DIR_IMGS, fn)
            estrategia, nombre = resolver_nombre_hibrido(fn, catalogos, kaiqi, jc_base, yoko_base, old_path)

            nombre = quitar_codigos(nombre)
            slug = slugify(nombre)
            ext = os.path.splitext(fn)[1].lower()
            new_name = f"{slug}{ext}"
            new_path = os.path.join(DIR_IMGS, new_name)

            if new_name != fn:
                os.rename(old_path, new_path)

            writer.writerow([fn, new_name, estrategia])
            print(f"[{estrategia}] {fn} -> {new_name}")

    print("\n✅ Proceso completado.")
    print(f"Log: {LOG_PATH}")

# ====================================================
# MAIN
# ====================================================

if __name__ == "__main__":
    main()
