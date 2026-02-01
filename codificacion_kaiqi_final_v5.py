# -*- coding: utf-8 -*-
"""
codificacion_kaiqi_final_v5.py
Clasificación y codificación automática de partes KAIQI
Versión 5 - Noviembre 2025
Autor: Asistente GPT-5
"""

import os
import re
import sys
import math
import json
import logging
import pandas as pd
from collections import defaultdict

# ==============================
# CONFIGURACIÓN GLOBAL
# ==============================
CONFIG = {
    "BASE_DIR": r"C:/sqk/html_pages",
    "EXCEL_FILE": "LISTADO KAIQI NOV-DIC 2025.xlsx",
    "SHEET_NAME": "Hoja1",
    "OUTPUT_FILE": "LISTADO_KAIQI_FINAL.xlsx",
    "REPORT_FILE": "LISTADO_KAIQI_VALIDACION.csv",
    "REVIEW_FILE": "LISTADO_KAIQI_PENDIENTES.csv",
    "DUPLICATES_FILE": "LISTADO_KAIQI_DUPLICADOS.csv",
    "EXPORT_JSON_METRICS": True,
    "METRICS_JSON_FILE": "LISTADO_KAIQI_METRICS.json",
    "LOG_LEVEL": "INFO",
    "PRESERVAR_SECUENCIA_EXISTENTE": True
}

logging.basicConfig(level=getattr(logging, CONFIG["LOG_LEVEL"]), format="%(levelname)s - %(message)s")
log = logging.getLogger("kaiqi_v5")

# ==============================
# FUNCIONES AUXILIARES
# ==============================
def norm_text(x):
    if pd.isna(x): return ""
    return re.sub(r"\s+", " ", str(x)).strip().upper()

def as_money(x):
    try:
        if pd.isna(x) or str(x).strip() == "":
            return "$0"
        s = re.sub(r"[^\d,.\-]", "", str(x)).replace(",", "")
        return f"${int(round(float(s))):,}".replace(",", ".")
    except: return "$0"

def parse_float(x):
    try:
        return float(re.sub(r"[^\d.]", "", str(x)))
    except:
        return math.nan

# ==============================
# CARGA DEL ARCHIVO FUENTE
# ==============================
def load_input():
    path = os.path.join(CONFIG["BASE_DIR"], CONFIG["EXCEL_FILE"])
    if not os.path.exists(path):
        log.error(f"No se encontró el archivo fuente: {path}")
        sys.exit(1)

    df = pd.read_excel(path, sheet_name=CONFIG["SHEET_NAME"])
    df.columns = [norm_text(c) for c in df.columns]

    for c in ["CODIGO NEW", "CODIGO", "DESCRIPCION", "CATEGORIA", "PRECIO SIN IVA"]:
        if c not in df.columns:
            df[c] = ""

    df["DESCRIPCION"] = df["DESCRIPCION"].apply(norm_text)
    df["CATEGORIA"] = df["CATEGORIA"].apply(norm_text)
    df["CATEGORIA_NORM"] = df["CATEGORIA"]
    df["PRECIO SIN IVA RAW"] = df["PRECIO SIN IVA"]
    df["PRECIO SIN IVA"] = df["PRECIO SIN IVA"].apply(as_money)
    return df

# ==============================
# CLASIFICADOR AUTOMÁTICO
# ==============================
# Mapeo de palabras clave -> Categoría normalizada
KEYWORDS = {
    # Motor
    r"\bCILIN|PISTON|BIELA|VALVULA|SELLO|CULATA|JUNTA\b": "COMPONENTES MOTOR",
    r"\bBOMBA ACEITE|ACEITE MOTOR\b": "BOMBA ACEITE",
    r"\bFILTRO ACEITE\b": "FILTRO DE ACEITE",
    r"\bEMBRAGUE|CLUTCH|DISCO CLUTCH|PRENSA CLUTCH\b": "EMBRAGUE COMPLETO",
    r"\bCARBURADOR\b": "CARBURADORES",
    r"\bCADENA DISTRIB|CORREA\b": "CORREAS DISTRIBUCION",

    # Transmisión
    r"\bPIÑON|CORONA|ARRASTRE|KIT CADENA\b": "KIT DE ARRASTRE",
    r"\bCAMBIO|CAJA\b": "TRANSMISIÓN INTERNA",

    # Frenos
    r"\bPASTILLA|ZAPATA|DISCO FRENO|BOMBA FRENO\b": "SISTEMA DE FRENOS",

    # Suspensión
    r"\bAMORTIGUADOR\b": "SUSPENSIÓN TRASERA",
    r"\bBARRA|TAPA HORQUILLA|HORQUILLA\b": "SUSPENSIÓN DELANTERA",

    # Eléctrico
    r"\bFARO|LUZ|STOP|DIRECCIONAL|BOMBILLO|CONECTOR|SWITCH|CDI|BOBINA|REGULADOR|ESTATOR\b": "SISTEMA ELECTRICO",

    # Carrocería / Chasis
    r"\bGUARDAFANGO|TAPA LATERAL|ASIENTO|BASE|SOPORTE|TORNILLO|PEDAL|POSAPIE|CARENADO|TANQUE\b": "CARROCERIA Y CHASIS",
    r"\bESPEJO|MANUBRIO|GUAYA|PALANCA|CABLE\b": "SISTEMA DE DIRECCION",
}

# Prefijos estándar por categoría
PREFIJOS = {
    "COMPONENTES MOTOR": "MOT-COM",
    "BOMBA ACEITE": "LUB-ACE",
    "FILTRO DE ACEITE": "LUB-FIL",
    "EMBRAGUE COMPLETO": "TRA-EMB",
    "CARBURADORES": "CAR-CAR",
    "CORREAS DISTRIBUCION": "MOT-COR",
    "KIT DE ARRASTRE": "TRA-ARR",
    "TRANSMISIÓN INTERNA": "TRA-INT",
    "SISTEMA DE FRENOS": "FRE-SIS",
    "SUSPENSIÓN TRASERA": "SUS-TRAS",
    "SUSPENSIÓN DELANTERA": "SUS-DEL",
    "SISTEMA ELECTRICO": "ELE-SIS",
    "CARROCERIA Y CHASIS": "CAR-CHA",
    "SISTEMA DE DIRECCION": "DIR-SIS"
}

def guess_category(desc, cat_norm):
    for pattern, cat in KEYWORDS.items():
        if re.search(pattern, desc):
            return cat
    return cat_norm

def sistema_from_categoria(cat):
    if cat in ["COMPONENTES MOTOR", "BOMBA ACEITE", "FILTRO DE ACEITE", "CORREAS DISTRIBUCION", "CARBURADORES"]:
        return "Motor"
    if "TRA" in PREFIJOS.get(cat, ""):
        return "Transmisión"
    if "FRE" in PREFIJOS.get(cat, ""):
        return "Frenos"
    if "SUS-DEL" in PREFIJOS.get(cat, ""):
        return "Suspensión delantera"
    if "SUS-TRAS" in PREFIJOS.get(cat, ""):
        return "Suspensión trasera"
    if "ELE" in PREFIJOS.get(cat, ""):
        return "Sistema eléctrico"
    if "CAR" in PREFIJOS.get(cat, ""):
        return "Carrocería / Chasis"
    if "DIR" in PREFIJOS.get(cat, ""):
        return "Dirección"
    return ""

def tipo_vehiculo(desc):
    d = desc.upper()
    if re.search(r"\bCARGUER|3W|AYCO|CERONTE|VAISAN\b", d):
        return "Motocarguero"
    return "Moto"

def parse_existing_seq(series):
    existing = defaultdict(int)
    for val in series.dropna().astype(str):
        m = re.match(r"^([A-Z0-9\-]+)-(\d{3,})$", val.strip())
        if m:
            pref, num = m.group(1), int(m.group(2))
            existing[pref] = max(existing[pref], num)
    return existing

def next_seq(counter, prefix, start_from=1):
    if prefix not in counter:
        counter[prefix] = start_from - 1
    counter[prefix] += 1
    return f"{prefix}-{counter[prefix]:03d}"

# ==============================
# ASIGNACIÓN DE CÓDIGOS
# ==============================
def assign_codes(df):
    df["CATEGORIA_NORM"] = df.apply(lambda r: guess_category(r["DESCRIPCION"], r["CATEGORIA_NORM"]), axis=1)
    df["PREFIJO_BASE"] = df["CATEGORIA_NORM"].map(PREFIJOS).fillna("")

    existing_seq = parse_existing_seq(df["CODIGO NEW"]) if CONFIG["PRESERVAR_SECUENCIA_EXISTENTE"] else defaultdict(int)
    counters = defaultdict(int, **existing_seq)

    codigos_new, pendientes = [], []
    for _, row in df.iterrows():
        pref = row["PREFIJO_BASE"]
        if not pref:
            codigos_new.append("PEND-000")
            pendientes.append(row.to_dict())
        else:
            codigos_new.append(next_seq(counters, pref))

    df["CODIGO NEW"] = codigos_new
    df["SISTEMA PRINCIPAL"] = df["CATEGORIA_NORM"].apply(sistema_from_categoria)
    df["TIPO VEHICULO"] = df["DESCRIPCION"].apply(tipo_vehiculo)
    return df, pendientes

# ==============================
# DUPLICADOS Y REPORTES
# ==============================
def detect_duplicates(df):
    dups = df[df["CODIGO"].astype(str).duplicated(keep=False)].copy()
    return dups

def export_reports(df, pendientes, dups):
    base = CONFIG["BASE_DIR"]
    df.to_csv(os.path.join(base, CONFIG["REPORT_FILE"]), index=False, encoding="utf-8-sig")
    if pendientes:
        pd.DataFrame(pendientes).to_csv(os.path.join(base, CONFIG["REVIEW_FILE"]), index=False, encoding="utf-8-sig")
    if not dups.empty:
        dups.to_csv(os.path.join(base, CONFIG["DUPLICATES_FILE"]), index=False, encoding="utf-8-sig")

# ==============================
# GUARDADO FINAL
# ==============================
def save_output(df):
    out_path = os.path.join(CONFIG["BASE_DIR"], CONFIG["OUTPUT_FILE"])
    with pd.ExcelWriter(out_path, engine="openpyxl", mode="w") as writer:
        df.to_excel(writer, index=False, sheet_name="FINAL")
    return out_path

# ==============================
# MAIN
# ==============================
def main():
    log.info("=== Iniciando procesamiento de inventario KAIQI (v5) ===")
    df = load_input()
    log.info(f"Filas cargadas: {len(df)}")

    df, pendientes = assign_codes(df)
    dups = detect_duplicates(df)

    if not dups.empty:
        log.warning(f"Posibles duplicados por CODIGO: {len(dups)}")
    if pendientes:
        log.warning(f"Filas pendientes de clasificación: {len(pendientes)}")

    export_reports(df, pendientes, dups)
    out_path = save_output(df)

    log.info(f"✅ Archivo generado: {out_path}")
    log.info("=== Proceso completado exitosamente ===")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log.error(f"Error fatal: {e}")
        sys.exit(1)
