#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SRM–QK–ADSI — EXTRACTOR UNIVERSAL v1
------------------------------------
Procesa TODA la data bruta que envía un cliente:
- PDF (texto + OCR básico)
- Excel (todas las hojas)
- CSV / TXT
- HTML (tablas + textos)
- Carpeta con imágenes (usa nombre como fuente de metadata)
- Archivos ZIP (los extrae y procesa todo)
- Cualquier archivo no reconocido → lo ignora y deja log

Salida estándar:
    extract_<cliente>.csv

Este archivo se convierte en la “materia prima” para el UNIFICADOR v1.
"""

import os
import re
import csv
import glob
import json
import zipfile
import logging
import pandas as pd
from bs4 import BeautifulSoup
from pdfminer.high_level import extract_text

# ========================
# CONFIGURACIÓN GLOBAL
# ========================

BASE_DIR = r"C:\img"
SALIDA_DIR = os.path.join(BASE_DIR, "EXTRACT")
os.makedirs(SALIDA_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(SALIDA_DIR, "extractor.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ===================================================================
# UTILIDADES
# ===================================================================

def clean(x: str) -> str:
    if not isinstance(x, str):
        return ""
    x = x.replace("\n", " ").replace("\r", " ")
    x = re.sub(r"\s+", " ", x).strip()
    return x

def registrar(msg):
    print(msg)
    logging.info(msg)


# ===================================================================
# EXTRACCIÓN POR TIPO DE ARCHIVO
# ===================================================================

# ------------------------ PDF -------------------------------------

def procesar_pdf(path):
    registrar(f"    → PDF: {path}")
    try:
        text = extract_text(path)
        rows = []

        for line in text.split("\n"):
            line = clean(line)
            if len(line) >= 3:     # línea con algo útil
                rows.append({
                    "FUENTE": os.path.basename(path),
                    "ORIGEN_TIPO": "PDF",
                    "CONTENIDO": line
                })
        return rows
    except Exception as e:
        registrar(f"[ERROR PDF] {path}: {e}")
        return []


# ------------------------ EXCEL (XLS/XLSX) -------------------------

def procesar_excel(path):
    registrar(f"    → EXCEL: {path}")
    rows = []
    try:
        xl = pd.ExcelFile(path)
        for sheet in xl.sheet_names:
            try:
                df = xl.parse(sheet)
                df = df.fillna("")
                for _, row in df.iterrows():
                    contenido = " | ".join([clean(str(v)) for v in row.values])
                    rows.append({
                        "FUENTE": f"{os.path.basename(path)}:{sheet}",
                        "ORIGEN_TIPO": "EXCEL",
                        "CONTENIDO": contenido
                    })
            except Exception as e:
                registrar(f"[ERROR HOJA] {sheet} en {path}: {e}")
    except Exception as e:
        registrar(f"[ERROR EXCEL] {path}: {e}")

    return rows


# ------------------------ CSV / TXT --------------------------------

def procesar_csv_txt(path):
    registrar(f"    → CSV/TXT: {path}")
    rows = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = clean(line)
                if len(line) >= 3:
                    rows.append({
                        "FUENTE": os.path.basename(path),
                        "ORIGEN_TIPO": "CSV/TXT",
                        "CONTENIDO": line
                    })
    except Exception as e:
        registrar(f"[ERROR CSV/TXT] {path}: {e}")

    return rows


# ------------------------ HTML -------------------------------------

def procesar_html(path):
    registrar(f"    → HTML: {path}")
    rows = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f, "html.parser")

        # Tablas
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                celdas = [clean(td.get_text()) for td in row.find_all(["td", "th"])]
                if any(celdas):
                    rows.append({
                        "FUENTE": os.path.basename(path),
                        "ORIGEN_TIPO": "HTML_TABLA",
                        "CONTENIDO": " | ".join(celdas)
                    })

        # Texto suelto
        textos = soup.get_text().split("\n")
        for t in textos:
            t = clean(t)
            if len(t) >= 3:
                rows.append({
                    "FUENTE": os.path.basename(path),
                    "ORIGEN_TIPO": "HTML_TEXTO",
                    "CONTENIDO": t
                })

    except Exception as e:
        registrar(f"[ERROR HTML] {path}: {e}")

    return rows


# ------------------------ IMÁGENES ---------------------------------

def procesar_imagen(path):
    registrar(f"    → IMG: {path}")
    base = os.path.basename(path)
    nombre = os.path.splitext(base)[0]

    # Extraemos info del nombre del archivo
    nombre_clean = clean(nombre).replace("_", " ").replace("-", " ")

    return [{
        "FUENTE": base,
        "ORIGEN_TIPO": "IMAGEN",
        "CONTENIDO": nombre_clean
    }]


# ------------------------ ZIP --------------------------------------

def procesar_zip(path):
    registrar(f"    → ZIP: {path}")
    tmp_dir = os.path.join(SALIDA_DIR, "_TMP")
    os.makedirs(tmp_dir, exist_ok=True)

    try:
        with zipfile.ZipFile(path, 'r') as zip_ref:
            zip_ref.extractall(tmp_dir)
    except Exception as e:
        registrar(f"[ERROR ZIP] {path}: {e}")
        return []

    # Recorrer todo lo extraído
    rows = []
    for root, _, files in os.walk(tmp_dir):
        for f in files:
            ext = f.lower().split(".")[-1]
            full = os.path.join(root, f)

            if ext in ["jpg","jpeg","png","webp"]:
                rows += procesar_imagen(full)
            elif ext in ["csv","txt"]:
                rows += procesar_csv_txt(full)
            elif ext in ["xlsx","xls"]:
                rows += procesar_excel(full)
            elif ext == "pdf":
                rows += procesar_pdf(full)
            elif ext in ["html","htm"]:
                rows += procesar_html(full)

    return rows


# ===================================================================
# PROCESADOR POR CLIENTE
# ===================================================================

def procesar_cliente(cliente):
    registrar(f"\n========== CLIENTE: {cliente} ==========")

    # carpeta del cliente
    files = glob.glob(os.path.join(BASE_DIR, f"*{cliente}*.*"))
    fotos_dir = os.path.join(BASE_DIR, f"FOTOS_CATALOGO_{cliente.upper()}")

    registrar(f"  → Archivos detectados: {len(files)}")
    registrar(f"  → Carpeta fotos: {fotos_dir}")

    rows_final = []

    # A. ARCHIVOS SUELTOS
    for f in files:
        ext = f.lower().split(".")[-1]

        if ext in ["pdf"]:
            rows_final += procesar_pdf(f)
        elif ext in ["xlsx","xls"]:
            rows_final += procesar_excel(f)
        elif ext in ["csv","txt"]:
            rows_final += procesar_csv_txt(f)
        elif ext in ["html","htm"]:
            rows_final += procesar_html(f)
        elif ext in ["zip"]:
            rows_final += procesar_zip(f)

    # B. IMÁGENES
    if os.path.isdir(fotos_dir):
        images = glob.glob(os.path.join(fotos_dir, "*"))
        for img in images:
            ext = img.lower().split(".")[-1]
            if ext in ["jpg","jpeg","png","webp"]:
                rows_final += procesar_imagen(img)

    # EXPORTAR
    salida = os.path.join(SALIDA_DIR, f"extract_{cliente}.csv")
    registrar(f"  → Exportando: {salida}")

    df = pd.DataFrame(rows_final)
    df.to_csv(salida, index=False, encoding="utf-8-sig")

    registrar(f"  → COMPLETADO: {len(df)} filas extraídas")


# ===================================================================
# MAIN
# ===================================================================

def main():
    clientes = [
        "Bara","DFG","Duna","Japan","Kaiqi",
        "Leo","Store","Vaisand","Yokomar"
    ]

    registrar("=== SRM EXTRACTOR UNIVERSAL v1 INICIADO ===")

    for c in clientes:
        procesar_cliente(c)

    registrar("=== FINALIZADO ===")


if __name__ == "__main__":
    main()
