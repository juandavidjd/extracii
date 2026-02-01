# -*- coding: utf-8 -*-
"""
codificacion_kaiqi_final.py
Script para clasificar, depurar y codificar el inventario LISTADO KAIQI.
Versión robusta, flexible y lista para integración con Shopify o ERP.
Autor: ChatGPT (GPT-5) | 2025
"""

import os
import re
import sys
import logging
from collections import defaultdict
import pandas as pd

# ============================================================
# CONFIGURACIÓN
# ============================================================
CONFIG = {
    "BASE_DIR": r"C:/sqk/html_pages",
    "EXCEL_FILE": "LISTADO KAIQI NOV-DIC 2025.xlsx",
    "SHEET_NAME": 0,
    "OUTPUT_FILE": "LISTADO_KAIQI_FINAL.xlsx",
    "PRESERVAR_SECUENCIA_EXISTENTE": True,
}

# ============================================================
# LOGGING CONFIG
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s"
)
log = logging.getLogger("KAIQI")

# ============================================================
# FUNCIONES AUXILIARES
# ============================================================
def norm(text):
    """Normaliza texto a mayúsculas, sin espacios dobles ni nulos."""
    return re.sub(r"\s+", " ", str(text)).strip().upper() if pd.notna(text) else ""

def next_seq(counter, prefix):
    """Devuelve el siguiente número correlativo por prefijo."""
    counter[prefix] = counter.get(prefix, 0) + 1
    return f"{prefix}-{counter[prefix]:03d}"

def parse_existing_seq(df):
    """Extrae numeraciones existentes para mantener correlatividad."""
    existing = defaultdict(int)
    if "CODIGO NEW" not in df.columns:
        return existing
    for val in df["CODIGO NEW"].dropna().astype(str):
        m = re.match(r"^([A-Z0-9\-]+)-(\d{3,})$", val.strip())
        if m:
            pref, num = m.group(1), int(m.group(2))
            existing[pref] = max(existing[pref], num)
    return existing

# ============================================================
# CLASIFICACIÓN DE SISTEMAS, SUBGRUPOS Y PARTES
# ============================================================
SISTEMAS = {
    "MOTOR": {
        "keywords": ["CILINDRO", "PISTON", "VALVULA", "CULATA", "CIGUEÑAL", "BIELA", "MOFLE", "TENSOR", "CADENILLA", "VOLANTE"],
        "prefix": "MOT",
        "subgrupos": {
            "Distribución": ["VALVULA", "GUÍA", "CADENILLA", "TENSOR"],
            "Combustión": ["CILINDRO", "PISTON", "CULATA"],
            "Escape": ["MOFLE", "TAPA VOLANTE"]
        }
    },
    "TRANSMISION": {
        "keywords": ["PIÑON", "EJE", "CAJA CAMBIO", "SELECTOR", "HORQUILLA", "CRUCETA", "DIFERENCIAL"],
        "prefix": "TRA"
    },
    "EMBRAGUE": {
        "keywords": ["CLUTCH", "EMBRAGUE", "DISCO CLUTCH", "PRENSA CLUTCH"],
        "prefix": "CLU"
    },
    "FRENOS": {
        "keywords": ["FRENO", "ZAPATA", "BOMBA FRENO", "DISCO FRENO", "MORDAZA", "BANDA", "CILINDRO FRENO"],
        "prefix": "FRE"
    },
    "SUSPENSION DELANTERA": {
        "keywords": ["BARRA", "HORQUILLA", "RETEN SUSPENSION", "TAPA BARRA", "DELANTERA"],
        "prefix": "SUS-DEL"
    },
    "SUSPENSION TRASERA": {
        "keywords": ["AMORTIGUADOR", "RESORTE", "TRASERA", "SOPORTE AMORTIGUADOR"],
        "prefix": "SUS-TRA"
    },
    "ELECTRICO": {
        "keywords": ["BOBINA", "CDI", "RELAY", "SWITCH", "REGULADOR", "LUZ", "FLASHER", "BATERIA", "CONECTOR"],
        "prefix": "ELE"
    },
    "ARRANQUE": {
        "keywords": ["ARRANQUE", "BENDIX", "ESCOBILLA", "MOTOR ARRANQUE"],
        "prefix": "ARR"
    },
    "LUBRICACION": {
        "keywords": ["ACEITE", "FILTRO ACEITE", "BOMBA ACEITE"],
        "prefix": "LUB"
    },
    "CARBURACION": {
        "keywords": ["CARBURADOR", "LLAVE GASOLINA", "INYECTOR"],
        "prefix": "CARB"
    },
    "FILTROS": {
        "keywords": ["FILTRO AIRE", "CAJA FILTRO"],
        "prefix": "FIL"
    },
    "GUAYAS": {
        "keywords": ["GUAYA", "CABLE", "ACELERADOR"],
        "prefix": "GUA"
    },
    "CHASIS": {
        "keywords": ["MANUBRIO", "ESPEJO", "CHAPA", "COMANDO", "PEDAL", "SOPORTE", "GUARDABARRO"],
        "prefix": "CHA"
    },
    "EMPAQUES / RETENEDORES": {
        "keywords": ["RETEN", "EMPAQUE", "JUNTA", "SELLO"],
        "prefix": "EMP"
    },
    "BUJIAS": {
        "keywords": ["BUJIA", "CAPUCHON BUJIA"],
        "prefix": "BUJ"
    },
    "SCOOTER / VARIADOR": {
        "keywords": ["VARIADOR", "CENTRIFUGA", "CORREA", "PESA"],
        "prefix": "SCO"
    },
    "RODADURA": {
        "keywords": ["RIN", "LLANTA", "BALINERA", "BUJE"],
        "prefix": "ROD"
    },
    "CARROCERIA": {
        "keywords": ["CABINA", "PLATAFORMA", "CAJA", "ASIENTO", "PARACHOQUE"],
        "prefix": "CAR"
    }
}

# ============================================================
# DETECCIÓN Y CLASIFICACIÓN
# ============================================================
def detect_system(desc):
    for sistema, data in SISTEMAS.items():
        for kw in data["keywords"]:
            if re.search(rf"\b{kw}\b", desc, re.IGNORECASE):
                return sistema
    return "PENDIENTE"

def detect_subgrupo(sistema, desc):
    """Detecta subgrupo dentro de un sistema."""
    if sistema in SISTEMAS and "subgrupos" in SISTEMAS[sistema]:
        for sub, kws in SISTEMAS[sistema]["subgrupos"].items():
            for kw in kws:
                if re.search(rf"\b{kw}\b", desc, re.IGNORECASE):
                    return sub
    return ""

def detect_parte(desc):
    """Extrae palabra principal del componente."""
    words = desc.split()
    return words[0] if words else ""

def detect_prefijo(sistema):
    if sistema in SISTEMAS:
        return SISTEMAS[sistema]["prefix"]
    return "PEND"

# ============================================================
# PROCESO PRINCIPAL
# ============================================================
def main():
    log.info("=== Iniciando procesamiento de inventario KAIQI ===")
    path = os.path.join(CONFIG["BASE_DIR"], CONFIG["EXCEL_FILE"])
    df = pd.read_excel(path, sheet_name=CONFIG["SHEET_NAME"])

    df.columns = [norm(c) for c in df.columns]
    if "DESCRIPCION" not in df.columns:
        log.error("❌ No existe la columna DESCRIPCION en el archivo.")
        sys.exit(1)

    df["DESCRIPCION"] = df["DESCRIPCION"].apply(norm)

    df["SISTEMA PRINCIPAL"] = df["DESCRIPCION"].apply(detect_system)
    df["SUBGRUPO / SUBSISTEMA"] = df.apply(lambda r: detect_subgrupo(r["SISTEMA PRINCIPAL"], r["DESCRIPCION"]), axis=1)
    df["PARTE / COMPONENTE"] = df["DESCRIPCION"].apply(detect_parte)
    df["PREFIJO_BASE"] = df["SISTEMA PRINCIPAL"].apply(detect_prefijo)
    df["OBSERVACION"] = df.apply(lambda r: f"Detectado por palabra clave del sistema {r['SISTEMA PRINCIPAL']}" if r["SISTEMA PRINCIPAL"] != "PENDIENTE" else "Revisión manual requerida", axis=1)

    existing_seq = parse_existing_seq(df)
    counters = defaultdict(int, existing_seq)

    codigos_new = []
    for _, row in df.iterrows():
        pref = row["PREFIJO_BASE"]
        if pref == "PEND":
            codigos_new.append("PEND-000")
        else:
            codigos_new.append(next_seq(counters, pref))
    df["CODIGO NEW"] = codigos_new

    # Reordenar columnas
    ordered_cols = [
        "CODIGO NEW", "CODIGO", "DESCRIPCION",
        "SISTEMA PRINCIPAL", "SUBGRUPO / SUBSISTEMA", "PARTE / COMPONENTE",
        "PREFIJO_BASE", "PRECIO SIN IVA", "OBSERVACION"
    ]
    existing_cols = [c for c in ordered_cols if c in df.columns]
    df = df[existing_cols]

    # Exportación
    out_path = os.path.join(CONFIG["BASE_DIR"], CONFIG["OUTPUT_FILE"])
    df.to_excel(out_path, index=False)
    pend_count = (df["SISTEMA PRINCIPAL"] == "PENDIENTE").sum()

    log.info(f"✅ Archivo generado: {out_path}")
    log.info(f"🔎 Filas pendientes de clasificación: {pend_count}")
    log.info("=== Proceso completado exitosamente ===")

# ============================================================
# EJECUCIÓN
# ============================================================
if __name__ == "__main__":
    main()
