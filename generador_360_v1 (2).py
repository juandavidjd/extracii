#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
==================================================================================
      SRM–QK–ADSI  →  GENERADOR 360° v1  (Ficha Técnica + Fitment + SEO)
==================================================================================
Autor: SRM + ADSI + GPT
Fecha: 2025-12-01

Entradas requeridas:
- renombrado_<cliente>.csv          (salida v26)
- Base_Datos_<cliente>.csv
- catalogo_imagenes_<cliente>.csv
- Lista_Precios_<cliente>.csv       (opcional)
- taxonomia_srm_qk_adsi_v1.csv
- knowledge_base_unificada.csv

Salidas:
- 360_<cliente>.csv
- 360_<cliente>.json
- shopify_<cliente>.csv
==================================================================================
"""

import os
import re
import json
import pandas as pd
from openai import OpenAI

BASE = r"C:\img"
RENOMBRADAS = os.path.join(BASE, "RENOMBRADAS")
OUTPUT_360 = os.path.join(BASE, "360")
os.makedirs(OUTPUT_360, exist_ok=True)

KB_FILE = os.path.join(BASE, "EXTRACT", "UNIFICADO", "knowledge_base_unificada.csv")
TAX_FILE = os.path.join(BASE, "taxonomia_srm_qk_adsi_v1.csv")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -------------------------------------------
#  UTILIDADES
# -------------------------------------------

def clean(t):
    if not isinstance(t, str): return ""
    t = t.strip()
    t = re.sub(r"\s+", " ", t)
    return t


def ask_ai(prompt):
    """
    Motor GPT para generar:
      - descripción premium
      - fitment
      - ficha técnica
      - SEO
    """
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system",
                 "content": "Eres experto en repuestos de motocicletas, copywriting técnico, SEO, y PNL aplicada a ventas."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=450
        )
        return resp.choices[0].message.content.strip()
    except:
        return ""


# -------------------------------------------
#  PROCESADOR PRINCIPAL
# -------------------------------------------

def procesar_cliente(cliente):

    print(f"\n🔵 Generando 360° para: {cliente}")

    # ---------------------------- Cargar archivos cliente
    ren = pd.read_csv(os.path.join(RENOMBRADAS, f"renombrado_{cliente}.csv"))
    ren["NOMBRE_RICO"] = ren["NOMBRE_RICO"].astype(str)

    base_file = os.path.join(BASE, f"Base_Datos_{cliente}.csv")
    base = pd.read_csv(base_file, encoding="latin-1", on_bad_lines="skip")

    cat_file = os.path.join(BASE, f"catalogo_imagenes_{cliente}.csv")
    cat = pd.read_csv(cat_file, encoding="latin-1", on_bad_lines="skip")

    # Lista de precios opcional
    precio_path = os.path.join(BASE, f"Lista_Precios_{cliente}.csv")
    precios = None
    if os.path.exists(precio_path):
        precios = pd.read_csv(precio_path, encoding="latin-1", on_bad_lines="skip")

    # ---------------------------- Taxonomía
    tax = pd.read_csv(TAX_FILE)

    # ---------------------------- Output
    rows = []

    for _, r in ren.iterrows():

        nombre_rico = clean(r["NOMBRE_RICO"])
        slugseo = clean(r["SLUG_SEO"])
        archivo = clean(r["ARCHIVO_ORIGINAL"])

        # --------- BUSCAR BASE_DATOS
        base_match = base.loc[
            base.astype(str).apply(lambda x: nombre_rico.lower() in x.astype(str).str.lower().values, axis=1)
        ]

        base_desc = ""
        if not base_match.empty:
            base_desc = clean(str(base_match.iloc[0].to_dict()))

        # --------- BUSCAR CATALOGO RICO
        cat_match = cat.loc[
            cat.astype(str).apply(lambda x: nombre_rico.lower() in x.astype(str).str.lower().values, axis=1)
        ]

        cat_desc = ""
        if not cat_match.empty:
            cat_desc = clean(str(cat_match.iloc[0].to_dict()))

        # --------- PRECIO
        precio = ""
        if precios is not None:
            p = precios.loc[
                precios.astype(str).apply(lambda x: nombre_rico.lower() in x.astype(str).str.lower().values, axis=1)
            ]
            if not p.empty:
                precio = str(p.iloc[0].to_dict())

        # --------- TAXONOMÍA SRM
        sys_, subsys, comp = "", "", ""
        tax_match = tax.loc[
            tax.astype(str).apply(lambda x: nombre_rico.lower() in x.astype(str).str.lower().values, axis=1)
        ]

        if not tax_match.empty:
            sys_ = str(tax_match.iloc[0]["SISTEMA"])
            subsys = str(tax_match.iloc[0]["SUBSISTEMA"])
            comp = str(tax_match.iloc[0]["COMPONENTE"])

        # ==========================================================
        # 🔥 GPT — Construcción del 360°
        # ==========================================================

        prompt = f"""
Genera una Ficha 360° para un producto de repuestos de motocicletas. 

Datos de entrada:
- Nombre Comercial Rico: {nombre_rico}
- Base Datos: {base_desc}
- Catálogo Rico: {cat_desc}
- Precio: {precio}
- Sistema: {sys_}
- SubSistema: {subsys}
- Componente: {comp}

Entrega EXACTAMENTE este formato JSON:

{{
 "descripcion_premium": "",
 "fitment_360": "",
 "ficha_tecnica": "",
 "seo_title": "",
 "seo_description": "",
 "tags": [],
 "bullets_shopify": []
}}
        """

        respuesta = ask_ai(prompt)

        try:
            data = json.loads(respuesta)
        except:
            data = {
                "descripcion_premium": "",
                "fitment_360": "",
                "ficha_tecnica": "",
                "seo_title": "",
                "seo_description": "",
                "tags": [],
                "bullets_shopify": []
            }

        fila = {
            "CLIENTE": cliente,
            "NOMBRE_RICO": nombre_rico,
            "SLUG_SEO": slugseo,
            "IMG_FINAL": r["IMG_FINAL"],
            "SISTEMA": sys_,
            "SUBSISTEMA": subsys,
            "COMPONENTE": comp,
            "DESCRIPCION_PREMIUM": data["descripcion_premium"],
            "FITMENT_360": data["fitment_360"],
            "FICHA_TECNICA": data["ficha_tecnica"],
            "SEO_TITLE": data["seo_title"],
            "SEO_DESCRIPTION": data["seo_description"],
            "SEO_TAGS": ", ".join(data["tags"]),
            "SHOPIFY_BULLETS": " | ".join(data["bullets_shopify"])
        }

        rows.append(fila)

    df = pd.DataFrame(rows)

    # Guardar CSV y JSON
    out_csv = os.path.join(OUTPUT_360, f"360_{cliente}.csv")
    out_json = os.path.join(OUTPUT_360, f"360_{cliente}.json")

    df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    df.to_json(out_json, orient="records", force_ascii=False, indent=4)

    print(f"✔ 360° generado → {out_csv}")
    print(f"✔ JSON generado → {out_json}")


# -------------------------------------------
#  MAIN
# -------------------------------------------

def main():
    clientes = ["Bara","DFG","Duna","Japan","Kaiqi","Leo","Store","Vaisand","Yokomar"]
    for c in clientes:
        procesar_cliente(c)

    print("\n🟩 GENERADOR 360° COMPLETADO\n")


if __name__ == "__main__":
    main()
