#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=================================================================================
                  GENERADOR JSON 360° SRM–QK–ADSI v1
Formato final para Lovely.dev / SRM Mall / PWA / Integraciones
=================================================================================
Entradas:
    - 360_<cliente>.csv
    - renombrado_<cliente>.csv
    - Lista_Precios_<cliente>.csv  (opcional)
Salida:
    - json_360_<cliente>.json
=================================================================================
"""

import os
import pandas as pd
import json
import re

BASE = r"C:\img"
GEN360_DIR = os.path.join(BASE, "360")
REN_DIR = os.path.join(BASE, "RENOMBRADAS")
OUT = os.path.join(BASE, "JSON_360")

os.makedirs(OUT, exist_ok=True)


def clean(s):
    if not isinstance(s, str): return ""
    return re.sub(r"\s+", " ", s).strip()


def procesar_cliente(cliente):

    print(f"\n🟦 Generando JSON 360° → {cliente}")

    # --------------------------------------------
    # Cargar archivos
    # --------------------------------------------
    f360 = os.path.join(GEN360_DIR, f"360_{cliente}.csv")
    df = pd.read_csv(f360, encoding="utf-8")

    f_ren = os.path.join(REN_DIR, f"renombrado_{cliente}.csv")
    ren = pd.read_csv(f_ren, encoding="utf-8")

    precio_path = os.path.join(BASE, f"Lista_Precios_{cliente}.csv")
    precios = None
    if os.path.exists(precio_path):
        precios = pd.read_csv(precio_path, encoding="latin-1", on_bad_lines="skip")

    precio_promedio = 25000

    productos_json = []

    # --------------------------------------------
    # Recorrer productos del 360°
    # --------------------------------------------
    for _, r in df.iterrows():

        nombre = clean(r["NOMBRE_RICO"])
        slug = clean(r["SLUG_SEO"])
        desc = clean(r["DESCRIPCION_PREMIUM"])

        # Fitment → JSON
        fitment_items = []
        if isinstance(r["FITMENT_360"], str):
            for item in r["FITMENT_360"].split("|"):
                part = item.split(" - ")
                if len(part) >= 2:
                    marca = part[0].strip()
                    resto = part[1].strip()
                    fitment_items.append({
                        "marca": marca,
                        "modelo": resto,
                        "cilindraje": "",
                        "años": ""
                    })

        # Ficha técnica
        ficha_dict = {}
        if isinstance(r["FICHA_TECNICA"], str):
            for linea in r["FICHA_TECNICA"].split("|"):
                if ":" in linea:
                    k, v = linea.split(":", 1)
                    ficha_dict[clean(k).lower()] = clean(v)

        # Imagen desde renombrador
        img_match = ren[ren["NOMBRE_RICO"].str.lower() == nombre.lower()]
        imagenes = []
        if not img_match.empty:
            imagenes.append({
                "tipo": "principal",
                "src": img_match.iloc[0]["IMG_FINAL"]
            })

        # Precio
        precio = precio_promedio
        if precios is not None:
            match = precios.astype(str).apply(lambda row: nombre.lower() in row.astype(str).str.lower().values, axis=1)
            p = precios[match]
            if not p.empty:
                try:
                    precio = float(list(p.iloc[0].values)[-1])
                except:
                    precio = precio_promedio

        # Ensamblar JSON final
        producto = {
            "cliente": cliente,
            "sku_cliente": clean(r.get("SKU", "")),
            "nombre_rico": nombre,
            "slug": slug,
            "descripcion_premium": desc,
            "fitment_360": fitment_items,
            "ficha_tecnica": ficha_dict,
            "meta": {
                "seo_title": clean(r["SEO_TITLE"]),
                "seo_description": clean(r["SEO_DESCRIPTION"]),
                "tags": clean(r["SEO_TAGS"]).split(",")
            },
            "imagenes": imagenes,
            "precio": precio,
            "inventario_inicial": 100,
            "estado": "activo"
        }

        productos_json.append(producto)

    # --------------------------------------------
    # Guardar JSON final
    # --------------------------------------------
    out_file = os.path.join(OUT, f"json_360_{cliente}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(productos_json, f, indent=4, ensure_ascii=False)

    print(f"✔ JSON generado: {out_file}")


def main():

    clientes = [
        "Bara", "DFG", "Duna", "Japan",
        "Kaiqi", "Leo", "Store", "Vaisand", "Yokomar"
    ]

    for c in clientes:
        procesar_cliente(c)

    print("\n🟩 JSON 360° COMPLETADO PARA LOS 9 CLIENTES\n")


if __name__ == "__main__":
    main()
