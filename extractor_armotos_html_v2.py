#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
extractor_armotos_html_v2.py

Extractor robusto para el catálogo ARMOTOS exportado como:
- 165 archivos: C:\scrap\Armotos_HTML_resources\Table X.html
- Imágenes:     C:\scrap\Armotos_HTML_resources\resources\cellImage_*.jpg

Objetivo:
- Construir un CSV lo más completo posible con:
  CODIGO, DESCRIPCION, EMPAQUE, PRECIO_TEXTO, PRECIO_NUM,
  FAMILIA (sección), TABLA_HTML, IMAGENES_HTML, TIPO_FILA

Salida principal:
- C:\scrap\Base_Datos_Catalogo_Armotos_v2.csv

Log:
- C:\scrap\Debug_ARMOTOS_HTML_Extract.log
"""

import os
import re
import csv
import math
import logging
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

# ==========================
# ⚙️ CONFIGURACIÓN
# ==========================

BASE_DIR = r"C:\scrap"
HTML_DIR = os.path.join(BASE_DIR, "Armotos_HTML_resources")
RESOURCES_DIR = os.path.join(HTML_DIR, "resources")

OUT_CSV = os.path.join(BASE_DIR, "Base_Datos_Catalogo_Armotos_v2.csv")
OUT_LOG = os.path.join(BASE_DIR, "Debug_ARMOTOS_HTML_Extract.log")

os.makedirs(BASE_DIR, exist_ok=True)

# ==========================
# 📝 LOGGING
# ==========================

logging.basicConfig(
    filename=OUT_LOG,
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter("%(message)s"))
logging.getLogger().addHandler(console)


# ==========================
# 🔧 UTILIDADES
# ==========================

def clean_text(txt: str) -> str:
    """Normaliza texto básico: quita espacios extremos y colapsa saltos de línea."""
    if txt is None:
        return ""
    txt = str(txt)
    txt = txt.replace("\xa0", " ")
    txt = re.sub(r"\s+", " ", txt)
    return txt.strip()


def is_possible_code(token: str) -> bool:
    """
    ¿Parece un código de ARMOTOS?
    - Solo dígitos, longitud 3 a 6
    """
    token = token.strip()
    return bool(re.match(r"^\d{3,6}$", token))


def extract_code_from_row_texts(texts):
    """
    Busca un código en la lista de textos de la fila:
    - Primero tokens tipo 04417, 03860, etc.
    - También soporta "COD: 03860"
    """
    # Buscar patrón "COD: 03860"
    joined = " ".join(texts)
    m = re.search(r"COD[:\s]+(\d{3,6})", joined, re.IGNORECASE)
    if m:
        return m.group(1)

    # Si no, revisar cada celda
    for t in texts:
        t_clean = clean_text(t)
        # partir por espacios
        for tok in t_clean.split():
            if is_possible_code(tok):
                return tok
    return ""


def extract_price(texts):
    """
    Extrae precio de una fila:
    - Retorna (precio_texto_original, precio_numérico_float)
    Admite patrones como:
    - $ 2.250
    - PRECIO X UNIDAD $ 859
    - 203.805
    """
    joined = " ".join(texts)
    # Buscar algo con $ primero
    m = re.search(r"\$\s*[\d\.\,]+", joined)
    if m:
        precio_txt = m.group(0)
    else:
        # Buscar un número con miles
        m2 = re.search(r"\b[\d\.\,]{4,}\b", joined)
        precio_txt = m2.group(0) if m2 else ""

    def to_float(val: str) -> float:
        if not val:
            return 0.0
        v = val.replace("$", "").replace(" ", "")
        if not v:
            return 0.0
        # Reglas básicas para miles/decimales
        if "," in v and "." in v:
            if v.rfind(",") > v.rfind("."):
                v = v.replace(".", "").replace(",", ".")
            else:
                v = v.replace(",", "")
        elif "," in v:
            parts = v.split(",")
            if len(parts[-1]) == 2:
                v = v.replace(",", ".")
            else:
                v = v.replace(",", "")
        elif "." in v:
            # si lo que hay después del punto no tiene 2 dígitos -> miles
            parts = v.split(".")
            if len(parts[-1]) != 2:
                v = v.replace(".", "")
        try:
            return float(v)
        except Exception:
            return 0.0

    return precio_txt, to_float(precio_txt)


def extract_empaque(texts):
    """
    Extrae el empaque tipo:
    - X1, X10, X50, X1BOLSA, etc.
    """
    joined = " ".join(texts)
    # Buscar X<numero> o X<numero>PALABRA
    m = re.search(r"\bX\s*\d+\w*\b", joined, re.IGNORECASE)
    if m:
        return clean_text(m.group(0)).upper()

    # Ocelda que contenga "EMPAQUE" o similar
    for t in texts:
        if "empaque" in t.lower():
            return clean_text(t)
    return ""


def detect_header_family(texts):
    """
    Recibe la lista de textos de una fila y trata de ver si es un encabezado de sección/familia.
    Ej: "CAUCHOS", "DIAFRAGMA CARBURADOR", etc.
    Heurística:
    - Texto corto (<= 3 palabras) mayormente mayúsculas
    - O fila que contenga CAUCHOS, GUAYA, GUARDAPOLVO, etc. sin precio
    """
    joined = clean_text(" ".join(texts))
    if not joined:
        return ""

    # Si tiene 'CAUCHOS', 'DIAFRAGMA', etc.
    keywords = [
        "CAUCHOS", "DIAFRAGMA", "CARBURADOR", "GUAYA",
        "FILTRO", "GUARDABARRO", "GUARDAPOLVO", "CABLES",
        "KIT CAUCHOS", "CAUCHO", "PASTAS", "PASTILLAS",
        "REPUESTOS", "ACCESORIOS",
    ]
    upper = joined.upper()
    for k in keywords:
        if k in upper:
            return joined

    # Si todo es mayúsculas y no parece tener código ni precio
    if upper == joined and len(joined.split()) <= 4:
        if not re.search(r"\d{3,6}", joined) and "$" not in joined:
            return joined

    return ""


def row_has_useful_signal(texts):
    """
    Decide si una fila tiene algo que valga la pena guardar:
    - Código o precio o descripción razonable
    """
    joined = clean_text(" ".join(texts))
    if not joined:
        return False
    if re.search(r"\d{3,6}", joined):
        return True
    if "$" in joined:
        return True
    if len(joined) >= 15:  # una descripción corta
        return True
    return False


# ==========================
# 🚀 EXTRACTOR PRINCIPAL
# ==========================

def process_html_file(path_html: Path):
    """
    Procesa un TableX.html y devuelve lista de dicts con filas (header + productos).
    """
    logging.info(f"   → Leyendo {path_html.name}")
    with open(path_html, "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table")
    if table is None:
        logging.warning(f"      [WARN] No se encontró <table> en {path_html.name}")
        return []

    rows_data = []
    current_family = ""
    tabla_name = path_html.name

    # Recorremos todas las filas tr
    trs = table.find_all("tr")
    for tr in trs:
        tds = tr.find_all(["td", "th"])
        if not tds:
            continue

        # Textos plano de cada celda
        cell_texts = []
        for td in tds:
            txt = td.get_text(separator=" ", strip=True)
            cell_texts.append(txt or "")

        # Imágenes de la fila
        img_srcs = []
        for td in tds:
            for img in td.find_all("img"):
                src = img.get("src") or ""
                src = src.strip()
                if src:
                    img_srcs.append(src)

        # Detectar posibles encabezados de familia
        fam = detect_header_family(cell_texts)
        if fam:
            current_family = fam
            rows_data.append({
                "TIPO_FILA": "HEADER",
                "TABLA_HTML": tabla_name,
                "FAMILIA": current_family,
                "CODIGO": "",
                "DESCRIPCION": fam,
                "EMPAQUE": "",
                "PRECIO_TEXTO": "",
                "PRECIO_NUM": 0.0,
                "IMAGENES_HTML": "|".join(img_srcs) if img_srcs else "",
                "RAW_TEXT": " | ".join(clean_text(t) for t in cell_texts),
            })
            continue

        # Filtrar filas muy vacías
        if not row_has_useful_signal(cell_texts):
            continue

        # Extraer elementos de producto
        codigo = extract_code_from_row_texts(cell_texts)
        precio_txt, precio_num = extract_price(cell_texts)
        empaque = extract_empaque(cell_texts)

        # Construir descripción eliminando pedazos obvios de código/empaque/precio
        joined = " ".join(cell_texts)

        if codigo:
            joined = re.sub(rf"\b{re.escape(codigo)}\b", " ", joined)
        if precio_txt:
            joined = joined.replace(precio_txt, " ")
        if empaque:
            joined = joined.replace(empaque, " ")

        descripcion = clean_text(joined)

        # Si quedó muy corta, usamos al menos la segunda columna como descripción
        if len(descripcion) < 5 and len(cell_texts) >= 2:
            descripcion = clean_text(cell_texts[1])

        # Tipo de fila: si no hay código pero sí descripción + precio, lo marcamos igual
        tipo = "PRODUCTO"
        if not codigo and not precio_txt:
            tipo = "OTRO"

        rows_data.append({
            "TIPO_FILA": tipo,
            "TABLA_HTML": tabla_name,
            "FAMILIA": current_family,
            "CODIGO": codigo,
            "DESCRIPCION": descripcion,
            "EMPAQUE": empaque,
            "PRECIO_TEXTO": precio_txt,
            "PRECIO_NUM": precio_num,
            "IMAGENES_HTML": "|".join(img_srcs) if img_srcs else "",
            "RAW_TEXT": " | ".join(clean_text(t) for t in cell_texts),
        })

    return rows_data


def main():
    logging.info("=== EXTRACTOR ARMOTOS HTML V2 ===")
    logging.info(f"HTML_DIR: {HTML_DIR}")
    logging.info(f"RESOURCES_DIR: {RESOURCES_DIR}")
    logging.info(f"OUT_CSV: {OUT_CSV}")
    logging.info("Escaneando archivos Table *.html ...")

    html_files = sorted(
        Path(HTML_DIR).glob("Table *.html"),
        key=lambda p: int(re.search(r"(\d+)", p.stem).group(1)) if re.search(r"(\d+)", p.stem) else 9999
    )

    if not html_files:
        logging.error("❌ No se encontraron archivos 'Table *.html'. Verifica la ruta.")
        return

    all_rows = []
    total_headers = 0
    total_productos = 0
    total_otros = 0

    for path_html in html_files:
        file_rows = process_html_file(path_html)
        for r in file_rows:
            all_rows.append(r)
            if r["TIPO_FILA"] == "HEADER":
                total_headers += 1
            elif r["TIPO_FILA"] == "PRODUCTO":
                total_productos += 1
            else:
                total_otros += 1

    if not all_rows:
        logging.error("❌ No se extrajo ninguna fila útil de los HTML.")
        return

    logging.info("")
    logging.info("Resumen bruto de extracción:")
    logging.info(f"   Total filas:      {len(all_rows)}")
    logging.info(f"   Encabezados:      {total_headers}")
    logging.info(f"   Productos (raw):  {total_productos}")
    logging.info(f"   Otras filas:      {total_otros}")

    # Construir DataFrame
    df = pd.DataFrame(all_rows)

    # Filtro suave: priorizar filas con algo de contenido
    # pero NO eliminar agresivamente para "no perder nada".
    mask_util = (
        (df["TIPO_FILA"] == "HEADER") |
        (df["CODIGO"].astype(str).str.strip() != "") |
        (df["DESCRIPCION"].astype(str).str.len() >= 8) |
        (df["PRECIO_NUM"].astype(float) > 0.0)
    )
    df_final = df[mask_util].copy()

    logging.info("")
    logging.info(f"Filas después de filtro suave: {len(df_final)}")

    # Ordenar por TABLA_HTML y por si hay código
    df_final["__has_code"] = df_final["CODIGO"].astype(str).str.len() > 0
    df_final.sort_values(by=["TABLA_HTML", "__has_code", "CODIGO"], ascending=[True, False, True], inplace=True)
    df_final.drop(columns=["__has_code"], inplace=True)

    # Guardar CSV
    df_final.to_csv(OUT_CSV, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)

    logging.info("")
    logging.info("✅ EXTRACCIÓN COMPLETADA")
    logging.info(f"Archivo generado: {OUT_CSV}")
    logging.info(f"Log detallado:    {OUT_LOG}")
    logging.info("Revisa sobre todo:")
    logging.info("  - FAMILIA: que esté razonable por sección")
    logging.info("  - CODIGO / DESCRIPCION / EMPAQUE / PRECIO_TEXTO / PRECIO_NUM")
    logging.info("  - IMAGENES_HTML: cellImage_*.jpg asociados a cada fila")


if __name__ == "__main__":
    main()
