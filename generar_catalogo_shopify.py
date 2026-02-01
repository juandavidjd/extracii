#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
generar_catalogo_shopify.py

Toma:
- Inventario_FINAL_CON_TAXONOMIA.csv  (taxonomía oficial KAIQI)
- catalogo_kaiqi_imagenes.txt         (resultado IA por imagen)

Y genera:
- catalogo_shopify_kaiqi.csv          (formato compatible con fomato_shopify.xlsx)

Lógica:
- Cada fila de Inventario = 1 producto en Shopify.
- Intenta mapear una imagen buscando el SKU dentro del nombre del archivo.
"""

import os
import re
import unicodedata
import pandas as pd

# ==========
# RUTAS
# ==========
BASE_DIR = r"C:\img"

INVENTARIO_CSV = os.path.join(BASE_DIR, "Inventario_FINAL_CON_TAXONOMIA.csv")
CATALOGO_IMAGENES_TXT = os.path.join(BASE_DIR, "catalogo_kaiqi_imagenes.txt")
SALIDA_SHOPIFY_CSV = os.path.join(BASE_DIR, "catalogo_shopify_kaiqi.csv")

# ==========
# UTILIDADES
# ==========

def limpiar_espacios(s):
    if pd.isna(s):
        return ""
    return str(s).strip()

def normalizar_sku(sku):
    """
    Normaliza el SKU a texto.
    - Si viene como número con coma (ej: '0,1271') lo deja igual como texto.
    - Si quieres otra lógica (reemplazar coma por punto o por nada) cámbiala aquí.
    """
    if pd.isna(sku):
        return ""
    sku_str = str(sku).strip()
    return sku_str

def slugify(text):
    """
    Convierte el texto en un slug SEO:
    - minúsculas
    - sin acentos
    - solo letras/números/guiones
    """
    if pd.isna(text):
        text = ""
    text = str(text).strip().lower()

    # Eliminar tildes
    text = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    # Reemplazar cualquier cosa que no sea letra, número o espacio por espacio
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    # Espacios a guiones
    text = re.sub(r"\s+", "-", text)
    # Colapsar guiones múltiples
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def construir_descripcion_html(row):
    """
    Construye un cuerpo HTML simple para Shopify usando la taxonomía.
    """
    desc = limpiar_espacios(row.get("Descripcion", ""))
    desc_extra = limpiar_espacios(row.get("Descripcion.1", ""))

    sistema = limpiar_espacios(row.get("Sistema Principal", ""))
    subsistema = limpiar_espacios(row.get("Subsistema", ""))
    componente = limpiar_espacios(row.get("Componente", ""))
    tipo_vehiculo = limpiar_espacios(row.get("Tipo Vehiculo", ""))
    categoria = limpiar_espacios(row.get("Categoria", ""))

    partes = []
    if desc:
        partes.append(f"<p>{desc}</p>")
    if desc_extra:
        partes.append(f"<p>{desc_extra}</p>")

    ficha = []
    if sistema:
        ficha.append(f"<li><strong>Sistema:</strong> {sistema}</li>")
    if subsistema:
        ficha.append(f"<li><strong>Subsistema:</strong> {subsistema}</li>")
    if componente:
        ficha.append(f"<li><strong>Componente:</strong> {componente}</li>")
    if tipo_vehiculo:
        ficha.append(f"<li><strong>Tipo de vehículo:</strong> {tipo_vehiculo}</li>")
    if categoria:
        ficha.append(f"<li><strong>Categoría:</strong> {categoria}</li>")

    if ficha:
        partes.append("<ul>" + "".join(ficha) + "</ul>")

    if not partes:
        return ""

    return "\n".join(partes)


def construir_tags(row):
    """
    Genera una cadena de tags separada por coma.
    """
    campos = [
        row.get("Sistema Principal", ""),
        row.get("Subsistema", ""),
        row.get("Componente", ""),
        row.get("Tipo Vehiculo", ""),
        row.get("Categoria", ""),
    ]
    tags = [limpiar_espacios(c) for c in campos if limpiar_espacios(c)]
    # Eliminar duplicados manteniendo orden
    vistos = set()
    tags_unicos = []
    for t in tags:
        if t not in vistos:
            vistos.add(t)
            tags_unicos.append(t)
    return ", ".join(tags_unicos)


def construir_titulo(row):
    """
    Usa Descripcion.1 si existe, sino Descripcion.
    """
    desc_extra = limpiar_espacios(row.get("Descripcion.1", ""))
    desc = limpiar_espacios(row.get("Descripcion", ""))
    if desc_extra:
        return desc_extra
    if desc:
        return desc
    # Fallback: Componente + SKU
    componente = limpiar_espacios(row.get("Componente", ""))
    sku = normalizar_sku(row.get("SKU", ""))
    return f"{componente} {sku}".strip()


def cargar_mapeo_imagenes():
    """
    Lee catalogo_kaiqi_imagenes.txt y construye un diccionario:
    sku -> filename (cuando el SKU aparece en el nombre del archivo).
    """
    if not os.path.exists(CATALOGO_IMAGENES_TXT):
        print(f"⚠️  No se encontró {CATALOGO_IMAGENES_TXT}, se generará catálogo sin imágenes.")
        return {}

    df_img = pd.read_csv(CATALOGO_IMAGENES_TXT, sep=";")
    df_img["Filename_Original"] = df_img["Filename_Original"].astype(str)

    # Devolvemos solo el filename, pero afuera hacemos el match SKU in filename
    return df_img["Filename_Original"].tolist()


# ==========
# PROCESO
# ==========

def generar_catalogo_shopify():
    # 1) Cargar inventario KAIQI
    if not os.path.exists(INVENTARIO_CSV):
        print(f"❌ No se encontró el archivo de inventario: {INVENTARIO_CSV}")
        return

    inv = pd.read_csv(INVENTARIO_CSV, sep=";")

    # 2) Cargar lista de nombres de imagen
    lista_filenames = cargar_mapeo_imagenes()

    # 3) Armar catálogo Shopify
    output_rows = []

    # Columnas finales según fomato_shopify.xlsx
    shopify_cols = [
        "Title", "URL handle", "Description", "Vendor", "Product category",
        "Type", "Tags", "Published on online store", "Status", "SKU", "Barcode",
        "Option1 name", "Option1 value", "Option2 name", "Option2 value",
        "Option3 name", "Option3 value", "Price", "Compare-at price",
        "Cost per item", "Charge tax", "Tax code", "Unit price total measure",
        "Unit price total measure unit", "Unit price base measure",
        "Unit price base measure unit", "Inventory tracker",
        "Inventory quantity", "Continue selling when out of stock",
        "Weight value (grams)", "Weight unit for display", "Requires shipping",
        "Fulfillment service", "Product image URL", "Image position",
        "Image alt text", "Variant image URL", "Gift card", "SEO title",
        "SEO description", "Google Shopping / Google product category",
        "Google Shopping / Gender", "Google Shopping / Age group",
        "Google Shopping / MPN", "Google Shopping / AdWords Grouping",
        "Google Shopping / AdWords labels", "Google Shopping / Condition",
        "Google Shopping / Custom product", "Google Shopping / Custom label 0",
        "Google Shopping / Custom label 1", "Google Shopping / Custom label 2",
        "Google Shopping / Custom label 3", "Google Shopping / Custom label 4",
    ]

    total = len(inv)
    print("==========================================")
    print(f" Generando catálogo Shopify para {total} SKUs...")
    print("==========================================")

    for idx, (_, row) in enumerate(inv.iterrows(), start=1):
        sku = normalizar_sku(row.get("SKU", ""))
        codigo_new = limpiar_espacios(row.get("CODIGO NEW", ""))

        # Título y textos
        title = construir_titulo(row)
        handle = slugify(f"{title} {sku}")
        body_html = construir_descripcion_html(row)
        tags = construir_tags(row)

        # Vendor, tipo, categoría
        vendor = "KAIQI PARTS"
        product_category = limpiar_espacios(row.get("Categoria", ""))
        product_type = limpiar_espacios(row.get("Componente", ""))

        # Precio
        precio = row.get("Precio", 0.0)
        try:
            precio = float(precio)
        except Exception:
            precio = 0.0

        # Buscar imagen cuyo nombre contenga el SKU (simple y efectivo para casos como 1011010)
        imagen_asignada = ""
        if sku:
            for fname in lista_filenames:
                if sku in fname:
                    imagen_asignada = fname
                    break

        # Descripción SEO (simple: mismo título + sistema/categoría)
        sistema = limpiar_espacios(row.get("Sistema Principal", ""))
        seo_title = title[:70]  # por si acaso
        seo_desc_partes = [title]
        if sistema:
            seo_desc_partes.append(f"Sistema: {sistema}")
        if product_category:
            seo_desc_partes.append(f"Categoría: {product_category}")
        seo_description = " | ".join(seo_desc_partes)[:320]

        # Construir fila Shopify
        fila = {
            "Title": title,
            "URL handle": handle,
            "Description": body_html,
            "Vendor": vendor,
            "Product category": product_category,
            "Type": product_type,
            "Tags": tags,
            "Published on online store": True,
            "Status": "active",
            "SKU": sku,
            "Barcode": "",
            "Option1 name": "Title",
            "Option1 value": "Default Title",
            "Option2 name": "",
            "Option2 value": "",
            "Option3 name": "",
            "Option3 value": "",
            "Price": precio,
            "Compare-at price": "",
            "Cost per item": "",
            "Charge tax": True,
            "Tax code": "",
            "Unit price total measure": "",
            "Unit price total measure unit": "",
            "Unit price base measure": "",
            "Unit price base measure unit": "",
            "Inventory tracker": "",
            "Inventory quantity": 0,
            "Continue selling when out of stock": False,
            "Weight value (grams)": "",
            "Weight unit for display": "g",
            "Requires shipping": True,
            "Fulfillment service": "manual",
            # 👉 Aquí queda el nombre de la imagen; luego tú decides si usas URLs
            #    o subes un ZIP con carpeta /images donde vayan estos archivos.
            "Product image URL": imagen_asignada,
            "Image position": "",
            "Image alt text": title,
            "Variant image URL": "",
            "Gift card": False,
            "SEO title": seo_title,
            "SEO description": seo_description,
            "Google Shopping / Google product category": "",
            "Google Shopping / Gender": "",
            "Google Shopping / Age group": "",
            "Google Shopping / MPN": codigo_new,
            "Google Shopping / AdWords Grouping": "",
            "Google Shopping / AdWords labels": "",
            "Google Shopping / Condition": "new",
            "Google Shopping / Custom product": "",
            "Google Shopping / Custom label 0": "",
            "Google Shopping / Custom label 1": "",
            "Google Shopping / Custom label 2": "",
            "Google Shopping / Custom label 3": "",
            "Google Shopping / Custom label 4": "",
        }

        output_rows.append(fila)

        if idx % 50 == 0 or idx == total:
            print(f"   → Procesados {idx}/{total}")

    # 4) DataFrame y export
    df_out = pd.DataFrame(output_rows, columns=shopify_cols)
    df_out.to_csv(SALIDA_SHOPIFY_CSV, index=False, encoding="utf-8-sig")

    print("\n==========================================")
    print(" ✅ Catálogo Shopify generado con éxito")
    print(f"    Archivo: {SALIDA_SHOPIFY_CSV}")
    print("==========================================")

if __name__ == "__main__":
    generar_catalogo_shopify()
