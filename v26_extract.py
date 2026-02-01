#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
v26_extract.py — SRM–QK–ADSI
Extractor universal para cada cliente.

Objetivo:
- Leer automáticamente la estructura completa de C:\img
- Encontrar Base_Datos_*.csv, Lista_Precios_*.csv, catalogo_imagenes_*.csv
- Mapear carpeta FOTOS_CATALOGO_*
- Producir extract_CLIENTE_raw.csv y extract_CLIENTE.json

Compatible con: Bara, DFG, Duna, Japan, Kaiqi, Leo, Store, Vaisand, Yokomar
"""

import os
import re
import json
import pandas as pd
from pathlib import Path

BASE_DIR = Path(r"C:\img")

# --------------------------------------------------------------------
# UTILIDADES
# --------------------------------------------------------------------

def normalize_text(t):
    if pd.isna(t):
        return ""
    t = str(t).strip()
    t = re.sub(r"\s+", " ", t)
    return t

def detect_system_subsystem(description):
    """
    Detección preliminar basada en palabras clave.
    Esto se completará después en el unificador v26_unifier.py
    """
    desc = description.lower()

    # MOTOR
    if any(w in desc for w in ["piston", "cilindro", "biela", "empaque", "retenedor motor", "culata"]):
        return "MOTOR", ""

    # TRANSMISIÓN
    if any(w in desc for w in ["clutch", "embrague", "arrastre", "piñon", "sprocket", "cadena"]):
        return "TRANSMISIÓN", ""

    # FRENOS
    if any(w in desc for w in ["pastilla", "banda", "zapatas", "bomba de freno", "disco freno"]):
        return "FRENOS", ""

    # SUSPENSIÓN
    if any(w in desc for w in ["amortiguador", "barra", "tijera", "suspensión"]):
        return "SUSPENSIÓN", ""

    # ELÉCTRICO
    if any(w in desc for w in ["bobina", "cdi", "relay", "estator", "rectificador", "luces"]):
        return "ELÉCTRICO / ENCENDIDO", ""

    # RUEDAS
    if any(w in desc for w in ["balinera", "rin", "llanta", "eje rueda"]):
        return "RUEDAS / LLANTAS", ""

    # ILUMINACIÓN
    if any(w in desc for w in ["faro", "stop", "direccional"]):
        return "ILUMINACIÓN / SEÑALIZACIÓN", ""

    # MOTOCARRO
    if "175" in desc or "205" in desc or "re" in desc:
        return "MOTOCARRO — ESPECIAL", ""

    return "GENÉRICO / UNIVERSAL", ""

def extract_name_rico(description):
    """
    Genera el nombre rico sin prefijos ni códigos.
    """
    desc = normalize_text(description)
    # Elimina códigos tipo 1-11-131, 1010115, DALU017, 85, 2, 3, etc.
    desc = re.sub(r"\b\d{1,6}\b", "", desc)
    desc = re.sub(r"\b[A-Za-z]{2,6}\d{2,6}\b", "", desc)
    desc = re.sub(r"\s+", " ", desc).strip()
    return desc.upper()

def load_csv_safe(path):
    """
    Carga CSV o TXT con tolerancia.
    """
    try:
        return pd.read_csv(path, encoding="utf-8", sep=",")
    except:
        try:
            return pd.read_csv(path, encoding="latin-1", sep=",")
        except:
            try:
                return pd.read_csv(path, sep=";", encoding="utf-8")
            except:
                return pd.DataFrame()

# --------------------------------------------------------------------
# NÚCLEO DEL EXTRACTOR
# --------------------------------------------------------------------

def extract_cliente(cliente):
    print(f"\n=== EXTRAYENDO CLIENTE: {cliente.upper()} ===")

    # -----------------------------
    # 1) Detectar archivos
    # -----------------------------
    base = BASE_DIR / f"Base_Datos_{cliente}.csv"
    precios = BASE_DIR / f"Lista_Precios_{cliente}.csv"
    imagenes = BASE_DIR / f"catalogo_imagenes_{cliente}.csv"
    fotos_dir = BASE_DIR / f"FOTOS_CATALOGO_{cliente}"

    print("Detectando archivos...")

    df_base = load_csv_safe(base) if base.exists() else pd.DataFrame()
    df_pre = load_csv_safe(precios) if precios.exists() else pd.DataFrame()
    df_img = load_csv_safe(imagenes) if imagenes.exists() else pd.DataFrame()

    # -----------------------------
    # 2) Normalizar Base Datos
    # -----------------------------
    if not df_base.empty:
        df_base.columns = [c.strip().lower() for c in df_base.columns]
        if "descripcion" in df_base.columns:
            df_base.rename(columns={"descripcion": "descripcion_producto"}, inplace=True)
        elif "descripcion producto" in df_base.columns:
            df_base.rename(columns={"descripcion producto": "descripcion_producto"}, inplace=True)
    else:
        df_base = pd.DataFrame(columns=["descripcion_producto"])

    # -----------------------------
    # 3) Normalizar Lista Precios
    # -----------------------------
    if not df_pre.empty:
        df_pre.columns = [c.strip().lower() for c in df_pre.columns]
        # normalizar precio
        if "precio" not in df_pre.columns:
            df_pre["precio"] = ""
    else:
        df_pre = pd.DataFrame(columns=["precio"])

    # -----------------------------
    # 4) Normalizar catálogo imágenes
    # -----------------------------
    if not df_img.empty:
        df_img.columns = [c.strip().lower() for c in df_img.columns]
        if "filename_original" not in df_img.columns:
            # buscar columna probable
            for c in df_img.columns:
                if "filename" in c or "imagen" in c:
                    df_img.rename(columns={c: "filename_original"}, inplace=True)
                    break
    else:
        df_img = pd.DataFrame(columns=["filename_original"])

    # -----------------------------
    # 5) Unificar todo en dataframe final
    # -----------------------------

    df = pd.DataFrame()
    df["descripcion"] = df_base["descripcion_producto"] if "descripcion_producto" in df_base.columns else ""

    # Precio
    if "precio" in df_pre.columns:
        df["precio"] = df_pre["precio"]
    else:
        df["precio"] = ""

    # Imagen
    df["imagen_original"] = df_img["filename_original"] if "filename_original" in df_img.columns else ""

    # Fotos en carpeta
    fotos = []
    if fotos_dir.exists():
        for f in os.listdir(fotos_dir):
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                fotos.append(f)
    df["fotos_detectadas"] = ", ".join(fotos) if fotos else ""

    # -----------------------------
    # 6) Enriquecimiento preliminar
    # -----------------------------
    df["nombre_rico_base"] = df["descripcion"].apply(extract_name_rico)
    df["sistema_pre"], df["subsistema_pre"] = zip(*df["descripcion"].apply(detect_system_subsystem))

    # -----------------------------
    # 7) Exportar
    # -----------------------------
    out_csv = BASE_DIR / f"extract_{cliente}_raw.csv"
    out_json = BASE_DIR / f"extract_{cliente}.json"

    df.to_csv(out_csv, index=False, encoding="utf-8")

    with open(out_json, "w", encoding="utf-8") as fx:
        fx.write(df.to_json(orient="records", force_ascii=False, indent=4))

    print(f"[✔] Generado: {out_csv}")
    print(f"[✔] Generado: {out_json}")

# --------------------------------------------------------------------
# EJECUCIÓN MASIVA
# --------------------------------------------------------------------

if __name__ == "__main__":
    clientes = ["Bara", "DFG", "Duna", "Japan", "Kaiqi", "Leo", "Store", "Vaisand", "Yokomar"]
    for cli in clientes:
        extract_cliente(cli)

    print("\n=== EXTRACCIÓN COMPLETA v26 ===")
