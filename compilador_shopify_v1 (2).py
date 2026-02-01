#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
===============================================================================
              SRM – QK – ADSI  →  COMPILADOR SHOPIFY v1
===============================================================================
Convierte 360° + precios + imágenes → Shopify CSV 100% listo para importar.

Entradas:
- 360_<cliente>.csv
- renombrado_<cliente>.csv
- Lista_Precios_<cliente>.csv   (opcional)
- Ruta o URL de imágenes desde renombrador v26

Salida:
- shopify_<cliente>.csv
===============================================================================
"""

import os
import pandas as pd
import re

BASE = r"C:\img"
REN_DIR = os.path.join(BASE, "RENOMBRADAS")
GEN360_DIR = os.path.join(BASE, "360")
SHOPIFY_OUT = os.path.join(BASE, "SHOPIFY")

os.makedirs(SHOPIFY_OUT, exist_ok=True)


def clean(t):
    if not isinstance(t, str): return ""
    t = re.sub(r"\s+", " ", t.strip())
    return t


def build_body_html(desc, fitment, ficha):
    """Arma el HTML profesional para Shopify."""
    return f"""
<h2>Descripción</h2>
<p>{desc}</p>

<h2>Compatibilidad - Fitment 360°</h2>
<p>{fitment.replace('|','<br>')}</p>

<h2>Ficha Técnica</h2>
<p>{ficha.replace('|','<br>')}</p>
""".strip()


def procesar_cliente(cliente):

    print(f"\n🟦 Compilando Shopify → {cliente}")

    # ---------------------------------------------------------
    # Cargar 360° del cliente
    # ---------------------------------------------------------
    f360 = os.path.join(GEN360_DIR, f"360_{cliente}.csv")
    df360 = pd.read_csv(f360, encoding="utf-8")

    # ---------------------------------------------------------
    # Renombrador (para imágenes)
    # ---------------------------------------------------------
    f_ren = os.path.join(REN_DIR, f"renombrado_{cliente}.csv")
    ren = pd.read_csv(f_ren, encoding="utf-8")

    # ---------------------------------------------------------
    # Lista de precios (opcional)
    # ---------------------------------------------------------
    precio_path = os.path.join(BASE, f"Lista_Precios_{cliente}.csv")
    precios = None
    if os.path.exists(precio_path):
        precios = pd.read_csv(precio_path, encoding="latin-1", on_bad_lines="skip")

    # Promedio para clientes sin precio
    precio_promedio = 25000  

    rows = []

    for _, r in df360.iterrows():

        nombre = r["NOMBRE_RICO"]
        desc = r["DESCRIPCION_PREMIUM"]
        fitment = r["FITMENT_360"]
        ficha = r["FICHA_TECNICA"]
        seo_title = r["SEO_TITLE"]
        seo_desc = r["SEO_DESCRIPTION"]
        seo_tags = r["SEO_TAGS"]
        slug = r["SLUG_SEO"]

        # ---------------------------------------------------------
        # Buscar imagen final desde renombrador
        # ---------------------------------------------------------
        ren_match = ren[ren["NOMBRE_RICO"].str.lower() == nombre.lower()]

        img = ""
        if not ren_match.empty:
            img = ren_match.iloc[0]["IMG_FINAL"]
        else:
            img = ""  

        # ---------------------------------------------------------
        # Precio
        # ---------------------------------------------------------
        precio_final = precio_promedio

        if precios is not None:
            p = precios.loc[
                precios.astype(str).apply(lambda x: nombre.lower() in x.astype(str).str.lower().values, axis=1)
            ]
            if not p.empty:
                try:
                    precio_final = float(list(p.iloc[0].values)[-1])
                except:
                    precio_final = precio_promedio

        # ---------------------------------------------------------
        # Construir HTML del producto
        # ---------------------------------------------------------
        body_html = build_body_html(desc, fitment, ficha)

        # ---------------------------------------------------------
        # Shopify ROW
        # ---------------------------------------------------------
        fila = {
            "Handle": slug,
            "Title": seo_title if seo_title else nombre,
            "Body (HTML)": body_html,
            "Vendor": cliente,
            "Standard Product Type": "Repuestos para Motocicleta",
            "Tags": seo_tags,
            "Status": "active",

            # Inventario
            "Variant Inventory Tracker": "shopify",
            "Variant Inventory Qty": 100,
            "Variant Inventory Policy": "deny",
            "Variant Fulfillment Service": "manual",

            # Precio
            "Variant Price": precio_final,

            # Imagen
            "Image Src": img,
            "Image Position": 1,

            # SEO
            "SEO Title": seo_title,
            "SEO Description": seo_desc,

            # Otros
            "Gift Card": "FALSE",
            "Published": "TRUE",
        }

        rows.append(fila)

    df = pd.DataFrame(rows)

    # ---------------------------------------------------------
    # Output
    # ---------------------------------------------------------
    out_csv = os.path.join(SHOPIFY_OUT, f"shopify_{cliente}.csv")
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")

    print(f"✔ Shopify CSV generado: {out_csv}")


def main():
    clientes = ["Bara","DFG","Duna","Japan","Kaiqi","Leo","Store","Vaisand","Yokomar"]
    for c in clientes:
        procesar_cliente(c)

    print("\n🟩 COMPILADOR SHOPIFY v1 COMPLETADO\n")


if __name__ == "__main__":
    main()
