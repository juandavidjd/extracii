# -*- coding: utf-8 -*-
import os
import re
import sys
import json
import math
import logging
from collections import defaultdict

import pandas as pd

# ============================================
# Configuración
# ============================================
CONFIG = {
    "BASE_DIR": r"C:/sqk/html_pages",
    "EXCEL_FILE": "LISTADO KAIQI NOV-DIC 2025.xlsx",
    "SHEET_NAME": "Hoja1",
    "OUTPUT_FILE": "LISTADO_KAIQI_FINAL.xlsx",
    "REPORT_FILE": "LISTADO_KAIQI_VALIDACION.csv",
    "REVIEW_FILE": "LISTADO_KAIQI_PENDIENTES.csv",
    "DUPLICATES_FILE": "LISTADO_KAIQI_DUPLICADOS.csv",
    "LOG_LEVEL": "INFO",  # DEBUG, INFO, WARNING, ERROR
    # Si True, preserva numeración secuencial existente de CODIGO NEW por prefijo y continúa desde el mayor
    "PRESERVAR_SECUENCIA_EXISTENTE": True,
    # Si True, exporta también un JSON con métricas y anomalías
    "EXPORT_JSON_METRICS": True,
    "METRICS_JSON_FILE": "LISTADO_KAIQI_METRICS.json",
}

# ============================================
# Logging
# ============================================
logging.basicConfig(
    level=getattr(logging, CONFIG["LOG_LEVEL"]),
    format="%(levelname)s %(message)s"
)
log = logging.getLogger("codificacion_final")

# ============================================
# Utilidades
# ============================================
def norm_text(x):
    if pd.isna(x):
        return ""
    return re.sub(r"\s+", " ", str(x)).strip().upper()

def safe_float(x):
    try:
        if pd.isna(x) or str(x).strip() == "":
            return math.nan
        s = re.sub(r"[^\d,.\-]", "", str(x))
        # Reglas: coma como decimal si no hay punto
        if s.count(",") == 1 and s.count(".") == 0:
            s = s.replace(",", ".")
        # Eliminar separadores residuales
        s = s.replace(",", "")
        return float(s)
    except:
        return math.nan

def format_precio(x):
    val = safe_float(x)
    if pd.isna(val):
        return "$0"
    return f"${int(round(val)):,}".replace(",", ".")

def next_seq(counter, prefix, start_from=1):
    # Si el prefijo no está, arrancar desde start_from-1 para sumar +1 y empezar en start_from
    if prefix not in counter:
        counter[prefix] = start_from - 1
    counter[prefix] += 1
    return f"{prefix}-{counter[prefix]:03d}"

def parse_existing_seq(df):
    """
    Detecta secuencias existentes en CODIGO NEW y devuelve un mapa {prefijo: max_num}
    para continuar numeración sin colisionar.
    """
    existing = defaultdict(int)
    if "CODIGO NEW" not in df.columns:
        return existing
    for val in df["CODIGO NEW"].dropna().astype(str):
        m = re.match(r"^([A-Z0-9\-]+)-(\d{3,})$", val.strip())
        if m:
            pref, num = m.group(1), int(m.group(2))
            existing[pref] = max(existing[pref], num)
    return existing

# ============================================
# Alias de categorías (unificación)
# ============================================
ALIAS_MAP = {
    # Frenos
    "BANDAS FRENO TRASERO": "BANDAS FRENO TRASERO",
    "BANDAS FRENO DELANTERO": "BANDAS FRENO DELANTERO",
    "PASTILLAS DE FRENO DEL HLK": "PASTILLAS DE FRENO DELANTERAS HLK",
    "PASTILLAS DE FRENO DEL/TRAS HLK": "PASTILLAS DE FRENO TRASERAS HLK",
    "PASTILLAS DE FRENO DELANTERAS HLK": "PASTILLAS DE FRERENO DELANTERAS HLK",  # corregimos a continuación
    "PASTILLAS DE FRENO DELANTERAS HLK": "PASTILLAS DE FRENO DELANTERAS HLK",
    "CAMPANA DELANTERA": "CAMPANA DELANTERA",
    "CAMPANA TRASERA": "CAMPANA TRASERA",
    "DISCO FRENO DELANTERO": "DISCO FRENO DELANTERO",
    "DISCO FRENO TRASERO": "DISCO FRENO TRASERO",
    "ZAPATAS": "ZAPATAS",
    "PERA FRENOS": "PERA FRENOS",
    "BOMBA FRENO -CILINDRO FRENO": "BOMBA FRENO -CILINDRO FRENO",
    "CILINDRO FRENO TRASERO": "CILINDRO FRENO TRASERO",
    "BOMBA FRENO TRASERO UNIVERSAL": "BOMBA FRENO TRASERO UNIVERSAL",
    "KIT MORDAZA": "KIT MORDAZA",
    "DEPOSITO LIQUIDO FRENO": "DEPOSITO LIQUIDO FRENO",
    "BOMBILLOS": "BOMBILLOS",

    # Motor
    "KIT CILINDROS EOM": "KIT CILINDRO EOM",
    "KIT CILINDRO EOM": "KIT CILINDRO EOM",
    "CULATA COMPLETA CON VALVULAS": "CULATA COMPLETA CON VALVULAS",
    "KIT PISTONES +ANILLOS": "KIT PISTONES +ANILLOS",
    "KIT ANILLOS": "KIT ANILLOS",
    "CIGÜEÑAL+BALINERA": "CIGÜEÑAL+BALINERA",
    "KIT VALVULAS": "KIT VALVULAS",
    "VALVULA PAIR": "VALVULA PAIR",
    "BALANCIN SUPERIOR": "BALANCIN SUPERIOR",
    "KIT BALANCINES INFERIOR": "KIT BALANCINES INFERIOR",
    "BASE C/BALANCINES": "BASE C/BALANCINES",
    "IMPULSADORES": "IMPULSADORES",
    "MOFLE": "MOFLE",
    "TAPAS REFRIGERANTE DE MOTOR": "TAPAS REFRIGERANTE DE MOTOR",
    "SOPORTE MOTOR": "SOPORTE MOTOR",
    "CARCAZA VOLANTE": "CARCAZA VOLANTE",
    "TAPON DE TIEMPO": "TAPON DE TIEMPO",
    "ARBOL LEVAS": "ARBOL LEVAS",
    "EJE CRANK COMPLETO": "EJE CRANK COMPLETO",
    "GUIA CADENILLA": "GUIA CADENILLA",
    "GUIA VALVULA": "GUIA VALVULA",
    "KIT BIELA+CANASTILLA": "KIT BIELA+CANASTILLA",
    "CADENILLAS": "CADENILLAS",

    # Transmisión
    "PIÑON SALIDA": "PIÑON DELANTERO",
    "PIÑON DELANTERO": "PIÑON DELANTERO",
    "KIT PIÑONES  DEL/TRAS": "KIT PIÑONES DELANTERO/TRASERO",
    "KIT PIÑONES DEL/TRAS": "KIT PIÑONES DELANTERO/TRASERO",
    "KIT PIÑONES DELANTERO/TRASERO": "KIT PIÑONES DELANTERO/TRASERO",
    "PIÑON PRIMARIO": "PIÑON PRIMARIO",
    "PIÑON REVERSA": "PIÑON REVERSA",
    "PIÑON VELOCIMETRO": "PIÑON VELOCIMETRO",
    "CAJA DE CAMBIOS": "CAJA DE CAMBIOS",
    "CAJA DE CAMBIOS-REVERSA": "CAJA DE CAMBIOS-REVERSA",
    "CAJA REVERSA": "CAJA REVERSA",
    "CAJA DIFERENCIAL": "CAJA DIFERENCIAL",
    "CRUCETAS CARGUERO": "CRUCETAS CARGUERO",
    "EJE CAMBIOS": "EJE CAMBIOS",
    "EJE SALIDA": "EJE SALIDA",
    "KIT HORQUILLAS": "KIT HORQUILLAS",
    "TOMA FUERZA": "TOMA FUERZA",
    "UNION REVERSA": "UNION REVERSA",
    "SELECTOR DE CAMBIOS": "SELECTOR DE CAMBIOS",
    "CANASTILLA": "CANASTILLA",
    "PEDAL CAMBIOS": "PEDAL CAMBIOS",
    "PEDAL CAMBIOS-CRANK- EJE SALIDA": "PEDAL CAMBIOS-CRANK- EJE SALIDA",
    "CAJA VELOCIMETRO": "CAJA VELOCIMETRO",
    "BALINERAS ESPECIALES": "BALINERAS ESPECIALES",

    # Eléctrico
    "CDI": "CDI",
    "BOBINA DE ALTA CON CAPUCHON": "BOBINA DE ALTA CON CAPUCHON",
    "BOBINA PULSORA": "BOBINA PULSORA",
    "SWICHES": "SWICHES",
    "SWICH ENCENDIDO": "SWICH ENCENDIDO",
    "KIT SWICH": "KIT SWICH",
    "REGULADOR": "REGULADOR",
    "REGULADOR TRIFASICO": "REGULADOR TRIFASICO",
    "FLASHER ELETRONICO": "FLASHER ELETRONICO",
    "RELAY UNIVERSAL": "RELAY UNIVERSAL",
    "SISTEMA ELECTRICO": "SISTEMA ELECTRICO",
    "CAPUCHON BUJIA": "CAPUCHON BUJIA",
    "STATOR -CORONA ENCENDIDO": "STATOR -CORONA ENCENDIDO",
    "INDICADOR CAMBIOS": "INDICADOR CAMBIOS",
    "LUCES LED": "LUCES LED",
    "CHOQUE ELETRICO": "CHOQUE ELECTRICO",
    "CHOQUE ELECTRIC": "CHOQUE ELECTRICO",

    # Arranque
    "MOTOR ARRANQUE": "MOTOR ARRANQUE",
    "ESCOBILLAS CON BASE": "ESCOBILLAS CON BASE",
    "BENDIX-ONE WAY": "BENDIX-ONE WAY",
    "PIÑON 1 MOTOR ARRANQUE": "PIÑON MOTOR ARRANQUE",
    "PIÑON MOTOR ARRANQUE": "PIÑON MOTOR ARRANQUE",
    "KIT PIÑON ARRANQUE": "KIT PIÑON ARRANQUE",

    # Refrigeración
    "RADIADOR": "RADIADOR",
    "VENTILADOR": "VENTILADOR",
    "BOMBA AGUA": "BOMBA AGUA",
    "TERMOSTATO": "TERMOSTATO",
    "BASE VENTILADOR": "BASE VENTILADOR",
    "TANQUE AGUA": "TANQUE AGUA",
    "TROMPO TEMPERATURA": "TROMPO TEMPERATURA",

    # Lubricación
    "BOMBA ACEITE": "BOMBA ACEITE",
    "FILTRO ACEITE": "FILTRO ACEITE",
    "FILTRO CENTRIFUGO": "FILTRO CENTRIFUGO",

    # Filtros
    "FILTRO DE AIRE": "FILTRO DE AIRE",
    "CAJA FILTROS": "CAJA FILTROS",

    # Guayas
    "GUAYAS / VARIOS": "GUAYAS / VARIOS",
    "GUAYA CLUTCH": "GUAYA CLUTCH",
    "GUAYA ACEL": "GUAYA ACEL",
    "GUAYA VEL": "GUAYA VEL",
    "GUAYA EMERGENCIA": "GUAYA EMERGENCIA",
    "GUAYA FRENO": "GUAYA FRENO",

    # Chasis / Controles
    "TREN DELANTERO CARGUERO": "TREN DELANTERO CARGUERO",
    "MANUBRIO": "MANUBRIO",
    "ESPEJOS / VARIOS": "ESPEJOS",
    "ESPEJOS": "ESPEJOS",
    "CHAPAS COMPUERTA": "CHAPAS COMPUERTA",
    "PARTES ELETRICAS COMANDOS": "PARTES ELETRICAS COMANDOS",
    "ANTIVIBRANTES": "ANTIVIBRANTES",
    "GUARDA BARRO DELANTERO METALICO": "GUARDA BARRO DELANTERO METALICO",
    "SUSPENSION TRASERA": "SUSPENSION TRASERA",
    "KIT CUNAS": "KIT CUNAS",
    "MANIGUETA CON BASE COMPLETA": "MANIGUETA CON BASE COMPLETA",

    # Scooter / Variador
    "PARTES DE SCOOTER-AGILLITY/DINAMIC": "PARTES DE SCOOTER-AGILLITY/DINAMIC",
    "CENTRIFUGA": "CENTRIFUGA",
    "CORREAS DISTRIBUCION": "CORREAS DISTRIBUCION",
    "ROLEX": "ROLEX",

    # Otros
    "BUJIA": "BUJIA",
    "DISCOS CLUTCH": "DISCOS CLUTCH",
    "KIT CARBURADOR": "KIT CARBURADOR",
    "BAQUELA CARBURADOR": "BAQUELA CARBURADOR",
    "CONECTOR CARBURADOR": "CONECTOR CARBURADOR",
    "LLAVE GASOLINA": "LLAVE GASOLINA",
    "KIT EMPAQUES CTO": "KIT EMPAQUES CTO",
    "EMPAQUES TAPA VOLANTE": "EMPAQUES TAPA VOLANTE",
    "EMPAQUES TAPA CULATIN ORING": "EMPAQUES TAPA CULATIN ORING",
    "EMPAQUES ANILLO EXOSTO": "EMPAQUES ANILLO EXOSTO",
    "EMPAQUES CONECTOR MOFLE": "EMPAQUES CONECTOR MOFLE",
    "KIT RETENEDORES": "KIT RETENEDORES",
    "KIT RETENEDORES MOTOR": "KIT RETENEDORES MOTOR",
    "CAJA VELOCIMETRO": "CAJA VELOCIMETRO",
}

# ============================================
# Prefijos finales
# ============================================
PREFIJOS = {
    # Frenos
    "BANDAS FRENO DELANTERO": "FRE-BAN-DEL",
    "BANDAS FRENO TRASERO": "FRE-BAN-TRAS",
    "CAMPANA DELANTERA": "FRE-CAM-DEL",
    "CAMPANA TRASERA": "FRE-CAM-TRAS",
    "PASTILLAS DE FRENO DELANTERAS HLK": "FRE-PAS-DEL",
    "PASTILLAS DE FRENO TRASERAS HLK": "FRE-PAS-TRAS",
    "DISCO FRENO DELANTERO": "FRE-DIS-DEL",
    "DISCO FRENO TRASERO": "FRE-DIS-TRAS",
    "ZAPATAS": "FRE-ZAP",
    "PERA FRENOS": "FRE-PER",
    "BOMBA FRENO -CILINDRO FRENO": "FRE-BOM-CIL",
    "CILINDRO FRENO TRASERO": "FRE-CIL-TRAS",
    "BOMBA FRENO TRASERO UNIVERSAL": "FRE-BOM-TRAS",
    "KIT MORDAZA": "FRE-MOR",
    "DEPOSITO LIQUIDO FRENO": "FRE-DEP",
    "BOMBILLOS": "ELE-BOM",

    # Motor
    "KIT CILINDRO EOM": "MOT-CIL",
    "CULATA COMPLETA CON VALVULAS": "MOT-CUL",
    "KIT PISTONES +ANILLOS": "MOT-PI",
    "KIT ANILLOS": "MOT-ANI",
    "CIGÜEÑAL+BALINERA": "MOT-CIG",
    "KIT VALVULAS": "MOT-VAL",
    "VALVULA PAIR": "MOT-VAL-PAIR",
    "BALANCIN SUPERIOR": "MOT-BAL",
    "KIT BALANCINES INFERIOR": "MOT-BAL",
    "BASE C/BALANCINES": "MOT-BAL-BASE",
    "KIT BALINERA MOTOR": "MOT-BAL-MOT",
    "IMPULSORES": "MOT-IMP",
    "MOFLE": "MOT-MOF",
    "TAPAS REFRIGERANTE DE MOTOR": "MOT-TAP",
    "SOPORTE MOTOR": "MOT-SOP",
    "CARCAZA VOLANTE": "MOT-CAR-VOL",
    "TAPON DE TIEMPO": "MOT-TAP-TIEM",
    "ARBOL LEVAS": "MOT-LEV",
    "EJE CRANK COMPLETO": "MOT-EJECRA",
    "GUIA CADENILLA": "MOT-GUI-CAD",
    "GUIA VALVULA": "MOT-GUI-VAL",
    "KIT BIELA+CANASTILLA": "MOT-BIE",
    "CADENILLAS": "MOT-CAD",

    # Transmisión
    "PIÑON DELANTERO": "TRA-PIN-DEL",
    "KIT PIÑONES DELANTERO/TRASERO": "TRA-PIN-TRAS",
    "PIÑON PRIMARIO": "TRA-PIN-PRI",
    "PIÑON REVERSA": "TRA-PIN-REV",
    "PIÑON VELOCIMETRO": "TRA-PIN-VEL",
    "CAJA DE CAMBIOS": "TRA-CAM",
    "CAJA DE CAMBIOS-REVERSA": "TRA-REV",
    "CAJA REVERSA": "TRA-REV",
    "CAJA DIFERENCIAL": "TRA-DIF",
    "CRUCETAS CARGUERO": "TRA-CRU",
    "EJE CAMBIOS": "TRA-EJE-CAM",
    "EJE SALIDA": "TRA-EJE-SAL",
    "KIT HORQUILLAS": "TRA-HOR",
    "TOMA FUERZA": "TRA-TOM",
    "UNION REVERSA": "TRA-UNI",
    "SELECTOR DE CAMBIOS": "TRA-SEL-CAM",
    "CANASTILLA": "TRA-CAN",
    "PEDAL CAMBIOS": "TRA-PED",
    "PEDAL CAMBIOS-CRANK- EJE SALIDA": "TRA-PED-CRANK",
    "CAJA VELOCIMETRO": "TRA-VEL-CAJ",
    "BALINERAS ESPECIALES": "TRA-BAL-ESP",

    # Eléctrico
    "CDI": "ELE-CDI",
    "BOBINA DE ALTA CON CAPUCHON": "ELE-BOB",
    "BOBINA PULSORA": "ELE-PUL",
    "SWICHES": "ELE-SWI",
    "SWICH ENCENDIDO": "ELE-SWI-ENC",
    "KIT SWICH": "ELE-SWI-KIT",
    "REGULADOR": "ELE-REG",
    "REGULADOR TRIFASICO": "ELE-REG-TRI",
    "FLASHER ELETRONICO": "ELE-FLA",
    "RELAY UNIVERSAL": "ELE-REL",
    "SISTEMA ELECTRICO": "ELE-SIS",
    "CAPUCHON BUJIA": "ELE-CAP",
    "STATOR -CORONA ENCENDIDO": "ELE-STA",
    "INDICADOR CAMBIOS": "ELE-IND-CAM",
    "LUCES LED": "ELE-LED",
    "CHOQUE ELECTRICO": "ELE-CHOQ",

    # Arranque
    "MOTOR ARRANQUE": "ARR-MOT",
    "ESCOBILLAS CON BASE": "ARR-ESC",
    "BENDIX-ONE WAY": "ARR-BEN",
    "PIÑON MOTOR ARRANQUE": "ARR-PIN",
    "KIT PIÑON ARRANQUE": "ARR-PIN-KIT",

    # Refrigeración
    "RADIADOR": "REF-RAD",
    "VENTILADOR": "REF-VENT",
    "BOMBA AGUA": "REF-AGU",
    "TERMOSTATO": "REF-TER",
    "BASE VENTILADOR": "REF-BASE",
    "TANQUE AGUA": "REF-TAN",
    "TROMPO TEMPERATURA": "REF-TRO-TEMP",

    # Lubricación
    "BOMBA ACEITE": "LUB-ACE",
    "FILTRO ACEITE": "LUB-FIL",
    "FILTRO CENTRIFUGO": "LUB-CEN",

    # Filtros
    "FILTRO DE AIRE": "FIL-AIR",
    "CAJA FILTROS": "FIL-BOX",

    # Guayas
    "GUAYAS / VARIOS": "GUA",
    "GUAYA CLUTCH": "GUA-CLU",
    "GUAYA ACEL": "GUA-ACE",
    "GUAYA VEL": "GUA-VEL",
    "GUAYA EMERGENCIA": "GUA-EME",
    "GUAYA FRENO": "GUA-FRE",

    # Chasis / Controles
    "TREN DELANTERO CARGUERO": "CHA-TREN",
    "MANUBRIO": "CHA-MAN",
    "ESPEJOS": "CHA-ESP",
    "CHAPAS COMPUERTA": "CHA-CHA",
    "PARTES ELETRICAS COMANDOS": "CHA-COM",
    "ANTIVIBRANTES": "CHA-ANT",
    "GUARDA BARRO DELANTERO METALICO": "CHA-GBAR-DEL",
    "SUSPENSION TRASERA": "CHA-SUS-TRAS",
    "KIT CUNAS": "CHA-CUN",
    "MANIGUETA CON BASE COMPLETA": "CHA-MANIG",

    # Scooter / Variador
    "PARTES DE SCOOTER-AGILLITY/DINAMIC": "SCO-PLA",  # Plato variador
    "CENTRIFUGA": "SCO-CEN",
    "CORREAS DISTRIBUCION": "SCO-COR",
    "ROLEX": "SCO-ROL",

    # Otros
    "BUJIA": "BUJ",
    "DISCOS CLUTCH": "CLU-DIS",
    "KIT CARBURADOR": "CAR-KIT",
    "BAQUELA CARBURADOR": "CAR-CON",
    "CONECTOR CARBURADOR": "CAR-CON",
    "LLAVE GASOLINA": "CAR-LLA",
    "KIT EMPAQUES CTO": "EMP-KIT",
    "EMPAQUES TAPA VOLANTE": "EMP-TAP",
    "EMPAQUES TAPA CULATIN ORING": "EMP-CUL",
    "EMPAQUES ANILLO EXOSTO": "EMP-EXO",
    "EMPAQUES CONECTOR MOFLE": "EMP-MOF",
    "KIT RETENEDORES": "EMP-RET",
    "KIT RETENEDORES MOTOR": "EMP-RET-MOT",
    "CAJA VELOCIMETRO": "TRA-VEL-CAJ",
}

# ============================================
# Reglas por palabras clave (refinan subtipos)
# ============================================
KEYWORD_RULES = [
    # Guayas: derivar subtipo
    {"category": "GUAYAS / VARIOS", "pattern": r"\bCLUTCH\b|EMBRAG", "prefix": "GUA-CLU"},
    {"category": "GUAYAS / VARIOS", "pattern": r"\bACEL\b|ACELERADOR", "prefix": "GUA-ACE"},
    {"category": "GUAYAS / VARIOS", "pattern": r"\bVEL\b|VELOCIM", "prefix": "GUA-VEL"},
    {"category": "GUAYAS / VARIOS", "pattern": r"\bFRENO\b", "prefix": "GUA-FRE"},
    {"category": "GUAYAS / VARIOS", "pattern": r"\bEMERGENCIA\b", "prefix": "GUA-EME"},

    # ZAPATAS: no separa del/tras en código, pero dejamos la posibilidad
    {"category": "ZAPATAS", "pattern": r"\bDEL\b|DELANT", "prefix": "FRE-ZAP"},
    {"category": "ZAPATAS", "pattern": r"\bTRAS\b|TRASER", "prefix": "FRE-ZAP"},

    # Pera frenos: variantes
    {"category": "PERA FRENOS", "pattern": r"\bDEL\b|IZQUIERDA|DERECHA", "prefix": "FRE-PER"},
    {"category": "PERA FRENOS", "pattern": r"\bTRAS\b|TRASER", "prefix": "FRE-PER"},

    # Scooter - Plato variador: marcar como SCO-PLA
    {"category": "PARTES DE SCOOTER-AGILLITY/DINAMIC", "pattern": r"PLATO\s+VARIADOR|VARIADOR", "prefix": "SCO-PLA"},
]

def apply_alias(cat):
    cat = ALIAS_MAP.get(cat, cat)
    # Corrección typos ocasionales
    if cat == "PASTILLAS DE FRERENO DELANTERAS HLK":
        cat = "PASTILLAS DE FRENO DELANTERAS HLK"
    return cat

def resolve_prefix(cat_norm, desc):
    # Reglas de refinamiento por keywords
    for rule in KEYWORD_RULES:
        if cat_norm == rule["category"] and re.search(rule["pattern"], desc or "", flags=re.IGNORECASE):
            return rule["prefix"]
    # Diccionario maestro directo
    return PREFIJOS.get(cat_norm, None)

# ============================================
# Carga de datos
# ============================================
def load_dataframe():
    base_dir = CONFIG["BASE_DIR"]
    excel_file = os.path.join(base_dir, CONFIG["EXCEL_FILE"])
    sheet = CONFIG["SHEET_NAME"]
    if not os.path.exists(excel_file):
        log.error(f"Archivo no encontrado: {excel_file}")
        sys.exit(1)
    df = pd.read_excel(excel_file, sheet_name=sheet)
    # Normalizar encabezados
    df.columns = [norm_text(c) for c in df.columns]
    # Garantizar columnas
    for col in ["CODIGO NEW", "CODIGO", "DESCRIPCION", "CATEGORIA", "PRECIO SIN IVA"]:
        if col not in df.columns:
            df[col] = ""
    # Normalización de valores
    df["DESCRIPCION"] = df["DESCRIPCION"].apply(norm_text)
    df["CATEGORIA"] = df["CATEGORIA"].apply(norm_text)
    df["CATEGORIA_NORM"] = df["CATEGORIA"].apply(apply_alias)
    df["PRECIO SIN IVA RAW"] = df["PRECIO SIN IVA"]  # conservar original
    df["PRECIO SIN IVA"] = df["PRECIO SIN IVA"].apply(format_precio)
    return df

# ============================================
# Validaciones y preparación
# ============================================
def detect_duplicates(df):
    # Duplicados por CODIGO (SKU fuente)
    dups = df[df["CODIGO"].duplicated(keep=False)].copy()
    return dups

def compute_prefixes(df):
    df["PREFIJO_BASE"] = [
        resolve_prefix(cat, desc)
        for cat, desc in zip(df["CATEGORIA_NORM"], df["DESCRIPCION"])
    ]
    return df

def assign_codes(df):
    existing_seq = parse_existing_seq(df) if CONFIG["PRESERVAR_SECUENCIA_EXISTENTE"] else defaultdict(int)
    counters = defaultdict(int)
    # Inicializar contadores con secuencias existentes
    for pref, maxn in existing_seq.items():
        counters[pref] = maxn

    codigos_new = []
    pendientes = []

    for i, row in df.iterrows():
        pref = row["PREFIJO_BASE"]
        catn = row["CATEGORIA_NORM"]
        desc = row["DESCRIPCION"]
        if not pref or str(pref).strip() == "":
            # Fallback: si no existe prefijo para esta categoría, intentar inferir por heurística suave
            # Heurística extra: si es categoría conocida en ALIAS_MAP pero ausente en PREFIJOS
            if catn in PREFIJOS:
                pref = PREFIJOS[catn]
            else:
                # Marcar pendiente
                pendientes.append({
                    "CODIGO": row.get("CODIGO", ""),
                    "DESCRIPCION": desc,
                    "CATEGORIA_ORIGINAL": row.get("CATEGORIA", ""),
                    "CATEGORIA_NORM": catn,
                })
                codigos_new.append("PEND-000")
                continue
        # Generar secuencia estable
        code = next_seq(counters, pref, start_from=(existing_seq.get(pref, 0) + 1))
        codigos_new.append(code)

    df["CODIGO NEW"] = codigos_new
    return df, pendientes

def export_reports(df, pendientes, dups):
    base_dir = CONFIG["BASE_DIR"]
    # Reporte de validación (conteo por prefijo y categoría)
    reporte = (
        df.groupby(["PREFIJO_BASE", "CATEGORIA_NORM"])
        .size()
        .reset_index(name="CUENTA")
        .sort_values(["PREFIJO_BASE", "CATEGORIA_NORM"])
    )
    reporte.to_csv(os.path.join(base_dir, CONFIG["REPORT_FILE"]), index=False, encoding="utf-8-sig")

    # Pendientes
    if pendientes:
        pd.DataFrame(pendientes).to_csv(os.path.join(base_dir, CONFIG["REVIEW_FILE"]), index=False, encoding="utf-8-sig")

    # Duplicados
    if not dups.empty:
        dups.to_csv(os.path.join(base_dir, CONFIG["DUPLICATES_FILE"]), index=False, encoding="utf-8-sig")

    # Métricas
    if CONFIG["EXPORT_JSON_METRICS"]:
        metrics = {
            "total_rows": int(len(df)),
            "unique_categories_norm": sorted(df["CATEGORIA_NORM"].dropna().unique().tolist()),
            "unique_prefixes": sorted(df["PREFIJO_BASE"].dropna().unique().tolist()),
            "pendientes_count": int(len(pendientes)),
            "duplicates_count": int(len(dups)),
            "prefix_counts": {
                str(k): int(v) for k, v in df["PREFIJO_BASE"].value_counts().to_dict().items()
            },
            "zeros_precio_count": int((df["PRECIO SIN IVA"] == "$0").sum()),
            "empty_codigo_count": int((df["CODIGO"].astype(str).str.strip() == "").sum()),
        }
        with open(os.path.join(base_dir, CONFIG["METRICS_JSON_FILE"]), "w", encoding="utf-8") as fh:
            json.dump(metrics, fh, ensure_ascii=False, indent=2)

def save_output(df):
    base_dir = CONFIG["BASE_DIR"]
    # Orden sugerido
    cols_order = [
        "CODIGO NEW",
        "CODIGO",
        "DESCRIPCION",
        "CATEGORIA",
        "CATEGORIA_NORM",
        "PREFIJO_BASE",
        "PRECIO SIN IVA",
        "PRECIO SIN IVA RAW",
    ]
    for c in cols_order:
        if c not in df.columns:
            df[c] = ""
    df = df[cols_order]
    df.to_excel(os.path.join(base_dir, CONFIG["OUTPUT_FILE"]), index=False)

# ============================================
# Main
# ============================================
def main():
    log.info("Cargando y normalizando archivo...")
    df = load_dataframe()

    log.info("Detectando duplicados por CODIGO...")
    dups = detect_duplicates(df)
    if not dups.empty:
        log.warning(f"Se detectaron {len(dups)} posibles duplicados por CODIGO.")

    log.info("Resolviendo prefijos base...")
    df = compute_prefixes(df)

    log.info("Asignando códigos secuenciales...")
    df, pendientes = assign_codes(df)

    if pendientes:
        log.warning(f"Quedaron {len(pendientes)} filas sin prefijo resuelto (PEND-000). Se exporta archivo de revisión.")
    else:
        log.info("Sin pendientes: todas las filas con prefijo técnico asignado.")

    log.info("Exportando reportes y métricas...")
    export_reports(df, pendientes, dups)

    log.info("Guardando archivo final...")
    save_output(df)

    log.info(f"✅ Finalizado. Archivo: {os.path.join(CONFIG['BASE_DIR'], CONFIG['OUTPUT_FILE'])}")
    log.info(f"📊 Reporte: {os.path.join(CONFIG['BASE_DIR'], CONFIG['REPORT_FILE'])}")
    if pendientes:
        log.info(f"⚠️ Pendientes: {os.path.join(CONFIG['BASE_DIR'], CONFIG['REVIEW_FILE'])}")
    if not dups.empty:
        log.info(f"🔎 Duplicados: {os.path.join(CONFIG['BASE_DIR'], CONFIG['DUPLICATES_FILE'])}")
    if CONFIG["EXPORT_JSON_METRICS"]:
        log.info(f"📈 Métricas JSON: {os.path.join(CONFIG['BASE_DIR'], CONFIG['METRICS_JSON_FILE'])}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log.error(f"Error fatal: {e}")
        sys.exit(1)
