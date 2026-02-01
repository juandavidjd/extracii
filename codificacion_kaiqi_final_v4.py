# -*- coding: utf-8 -*-
import os
import re
import sys
import json
import math
import logging
from collections import defaultdict
import pandas as pd

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
log = logging.getLogger("kaiqi_v4")

def norm_text(x):
    if pd.isna(x):
        return ""
    return re.sub(r"\s+", " ", str(x)).strip().upper()

def as_money(x):
    try:
        if pd.isna(x) or str(x).strip() == "":
            return "$0"
        s = str(x).replace(".", "").replace(" ", "")
        s = re.sub(r"[^\d,.\-]", "", s)
        if s.count(",") == 1 and s.count(".") == 0:
            s = s.replace(",", ".")
        s = s.replace(",", "")
        v = float(s)
        return f"${int(round(v)):,}".replace(",", ".")
    except:
        return "$0"

def parse_float(x):
    try:
        if pd.isna(x) or str(x).strip() == "":
            return math.nan
        s = re.sub(r"[^\d,.\-]", "", str(x))
        if s.count(",") == 1 and s.count(".") == 0:
            s = s.replace(",", ".")
        s = s.replace(",", "")
        return float(s)
    except:
        return math.nan

# --- CARGA DEL ARCHIVO ---
def load_input():
    path = os.path.join(CONFIG["BASE_DIR"], CONFIG["EXCEL_FILE"])
    if not os.path.exists(path):
        log.error(f"No se encontró el archivo fuente: {path}")
        sys.exit(1)
    df = pd.read_excel(path, sheet_name=CONFIG["SHEET_NAME"])
    df.columns = [norm_text(c) for c in df.columns]
    for c in ["CODIGO NEW","CODIGO","DESCRIPCION","CATEGORIA","PRECIO SIN IVA"]:
        if c not in df.columns:
            df[c] = ""
    df["DESCRIPCION"] = df["DESCRIPCION"].apply(norm_text)
    df["CATEGORIA"] = df["CATEGORIA"].apply(norm_text)
    df["CATEGORIA_NORM"] = df["CATEGORIA"]
    df["PRECIO SIN IVA RAW"] = df["PRECIO SIN IVA"]
    df["PRECIO SIN IVA"] = df["PRECIO SIN IVA"].apply(as_money)
    return df

# --- CLASIFICACIÓN Y CÓDIGOS ---
def guess_category(desc, cat_norm):
    d = desc or ""
    if "CARBURADOR" in d:
        return "CARBURADORES"
    if "BOMBA ACEITE" in d:
        return "BOMBA ACEITE"
    if "PIÑON" in d:
        return "PIÑON DELANTERO"
    if "PASTILLA" in d:
        return "PASTILLAS DE FRENO DELANTERAS HLK"
    return cat_norm

PREFIJOS = {
    "CARBURADORES": "CAR-CAR",
    "BOMBA ACEITE": "LUB-ACE",
    "PIÑON DELANTERO": "TRA-PIN-DEL",
    "PASTILLAS DE FRENO DELANTERAS HLK": "FRE-PAS-DEL",
    "SELLOS DOBLE RESORTE VERDES": "MOT-SEL-VAL"
}

def sistema_from_categoria(cat):
    if "FRE" in PREFIJOS.get(cat, ""):
        return "Frenos"
    if "LUB" in PREFIJOS.get(cat, ""):
        return "Lubricación"
    if "TRA" in PREFIJOS.get(cat, ""):
        return "Transmisión"
    if "MOT" in PREFIJOS.get(cat, ""):
        return "Motor"
    if "CAR" in PREFIJOS.get(cat, ""):
        return "Carburación"
    return ""

def subsistema_from_categoria(cat):
    if cat == "PASTILLAS DE FRENO DELANTERAS HLK":
        return "Freno delantero"
    if cat == "PIÑON DELANTERO":
        return "Transmisión primaria"
    if cat == "BOMBA ACEITE":
        return "Lubricación interna"
    if cat == "CARBURADORES":
        return "Carburación"
    if cat == "SELLOS DOBLE RESORTE VERDES":
        return "Válvulas y retenes"
    return ""

def tipo_vehiculo(desc, cat):
    d = f"{desc} {cat}".upper()
    if re.search(r"\bCARGUER|3W|AYCO|VAISAN|CERONTE|ZOLON\b", d):
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

def assign_codes(df):
    df["CATEGORIA_NORM"] = df.apply(lambda r: guess_category(r["DESCRIPCION"], r["CATEGORIA_NORM"]), axis=1)
    df["PREFIJO_BASE"] = df["CATEGORIA_NORM"].map(PREFIJOS).fillna("")
    existing_seq = parse_existing_seq(df["CODIGO NEW"]) if CONFIG["PRESERVAR_SECUENCIA_EXISTENTE"] else defaultdict(int)
    counters = defaultdict(int)
    for k,v in existing_seq.items():
        counters[k] = v
    codigos_new = []
    pendientes = []
    for _, row in df.iterrows():
        pref = row["PREFIJO_BASE"]
        if not pref:
            codigos_new.append("PEND-000")
            pendientes.append(row.to_dict())
        else:
            codigos_new.append(next_seq(counters, pref))
    df["CODIGO NEW"] = codigos_new
    df["SISTEMA PRINCIPAL"] = df["CATEGORIA_NORM"].apply(sistema_from_categoria)
    df["SUBSISTEMA"] = df["CATEGORIA_NORM"].apply(subsistema_from_categoria)
    df["TIPO VEHICULO"] = df.apply(lambda r: tipo_vehiculo(r["DESCRIPCION"], r["CATEGORIA_NORM"]), axis=1)
    return df, pendientes

# --- DUPLICADOS Y REPORTES ---
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

# --- SALIDA FINAL ---
def save_output(df):
    out_path = os.path.join(CONFIG["BASE_DIR"], CONFIG["OUTPUT_FILE"])
    with pd.ExcelWriter(out_path, engine="openpyxl", mode="w") as writer:
        df.to_excel(writer, index=False, sheet_name="FINAL")
    return out_path

# --- EJECUCIÓN PRINCIPAL ---
def main():
    log.info("=== Iniciando procesamiento de inventario KAIQI (v4) ===")
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
