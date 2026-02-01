# -*- coding: utf-8 -*-
"""
codificacion_kaiqi_final_v3.py
Versión limpia, robusta y con comentarios de consola.

Flujo:
1) Carga y normalización de columnas (tolerante a encabezados variantes).
2) Limpieza de texto y unificación de categorías (ALIAS_MAP).
3) Detección de vehículo (Moto / Motocarguero).
4) Asignación de Sistema / Sub-sistema / Componente y PREFIJO_BASE por palabras clave + categoría.
5) Preservación de secuencia existente en "CODIGO NEW" y asignación secuencial por prefijo.
6) Reportes: validación, pendientes, duplicados, métricas.
7) Exporta Excel final y CSVs auxiliares.

Requisitos:
- Archivo fuente por defecto: C:/sqk/html_pages/LISTADO KAIQI NOV-DIC 2025.xlsx (Hoja1)
"""

import os
import re
import sys
import json
import math
import logging
from collections import defaultdict, Counter

import pandas as pd

# ==========================
# Configuración
# ==========================
CONFIG = {
    "BASE_DIR": r"C:/sqk/html_pages",
    "EXCEL_FILE": "LISTADO KAIQI NOV-DIC 2025.xlsx",   # Hoja 1
    "SHEET_NAME": "Hoja1",

    "OUTPUT_FILE": "LISTADO_KAIQI_FINAL.xlsx",
    "REPORT_FILE": "LISTADO_KAIQI_VALIDACION.csv",
    "REVIEW_FILE": "LISTADO_KAIQI_PENDIENTES.csv",
    "DUPLICATES_FILE": "LISTADO_KAIQI_DUPLICADOS.csv",
    "METRICS_JSON_FILE": "LISTADO_KAIQI_METRICS.json",

    # Preserva secuencia existente por prefijo (si hay MOT-CIL-012, continúa en 013)
    "PRESERVAR_SECUENCIA_EXISTENTE": True,

    # Niveles: DEBUG, INFO, WARNING, ERROR
    "LOG_LEVEL": "INFO",
}

# ==========================
# Logging
# ==========================
logging.basicConfig(
    level=getattr(logging, CONFIG["LOG_LEVEL"]),
    format="%(levelname)s - %(message)s"
)
log = logging.getLogger("kaiqi_v3")

# ==========================
# Utilidades básicas
# ==========================
def norm_text(x):
    """Normaliza a MAYÚSCULAS, quita espacios extra y maneja NaN."""
    if pd.isna(x):
        return ""
    return re.sub(r"\s+", " ", str(x)).strip().upper()

def norm_header(h):
    """Normaliza nombres de columnas a un formato estable."""
    if h is None:
        return ""
    h = str(h)
    h = h.replace(";", " ").replace(",", " ")
    h = re.sub(r"\s+", " ", h).strip().upper()
    # Armonizar variantes frecuentes
    repl = {
        "CATEGORIA ORIGINAL": "CATEGORIA",
        "CATEGORIA_ORIGINAL": "CATEGORIA",
        "CATEGORIA NORM": "CATEGORIA_NORM",
        "SISTEMA PROPUESTO": "SISTEMA PRINCIPAL",
        "SUBSISTEMA PROPUESTO": "SUBSISTEMA",
        "COMPONENTE PROPUESTO": "COMPONENTE",
        "PRECIO": "PRECIO SIN IVA",  # por si acaso
    }
    return repl.get(h, h)

def safe_float(x):
    """Convierte a float tolerando formatos locales."""
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

def format_precio(x):
    """Formatea precio como $123.456 (puntos miles)."""
    val = safe_float(x)
    if pd.isna(val):
        return "$0"
    return f"${int(round(val)):,}".replace(",", ".")

def next_seq(counter, prefix, start_from=1):
    """Genera secuencia incremental por prefijo."""
    if prefix not in counter:
        counter[prefix] = start_from - 1
    counter[prefix] += 1
    return f"{prefix}-{counter[prefix]:03d}"

def parse_existing_seq(df):
    """
    Detecta secuencias existentes en CODIGO NEW -> retorna {prefijo: max_n}.
    Ej: MOT-CIL-012 -> {"MOT-CIL": 12}
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

# ==========================
# Diccionarios maestros
# ==========================

# Alias de categorías: unifica variaciones/typos a una categoría normalizada
ALIAS_MAP = {
    # Frenos
    "PASTILLAS DE FRERENO DELANTERAS HLK": "PASTILLAS DE FRENO DELANTERAS HLK",
    "BOMBA FRENO -CILINDRO FRENO": "BOMBA FRENO -CILINDRO FRENO",
    "CHOQUE ELETRICO": "CHOQUE ELECTRICO",
    "PARTES ELETRICAS COMANDOS": "PARTES ELETRICAS COMANDOS",
    "CARCAZA  VOLANTE": "CARCAZA VOLANTE",
    "CADENILLAS ": "CADENILLAS",
    "GUAYAS/VARIOS": "GUAYAS / VARIOS",
    "ESPEJOS / VARIOS": "ESPEJOS",
    # … (las llaves que vienen del set real ya están en mayúsculas)
}

def apply_alias(cat):
    cat = norm_text(cat)
    return ALIAS_MAP.get(cat, cat)

# Prefijos por categoría normalizada (respetando formato actual)
# IMPORTANTE: Suspensión delantera y trasera por separado (CHA-SUS-DEL / CHA-SUS-TRAS)
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
    "IMPULSADORES": "MOT-IMP",
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
    "SUSPENSION DELANTERA": "CHA-SUS-DEL",   # NUEVO sistema separado
    "SUSPENSION TRASERA": "CHA-SUS-TRAS",
    "KIT CUNAS": "CHA-CUN",
    "MANIGUETA CON BASE COMPLETA": "CHA-MANIG",

    # Scooter / Variador
    "PARTES DE SCOOTER-AGILLITY/DINAMIC": "SCO-PLA",  # plato variador
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
    "RIN": "RIN",
    "TAPA GASOLINA": "TAP-GAS",
    "VOLANTE": "MOT-VOL",
    "TENSOR CADENILLA": "MOT-TEN-CAD",
}

# Reglas: palabras clave para derivar sistema/prefijo (refinamiento)
KEYWORD_RULES = [
    # GUAYAS / VARIOS -> subtipos
    {"category": "GUAYAS / VARIOS", "pattern": r"\bCLUTCH\b|EMBRAG", "prefix": "GUA-CLU", "subsistema": "Guayas", "componente": "Clutch"},
    {"category": "GUAYAS / VARIOS", "pattern": r"\bACEL|ACELERADOR", "prefix": "GUA-ACE", "subsistema": "Guayas", "componente": "Acelerador"},
    {"category": "GUAYAS / VARIOS", "pattern": r"\bVEL|VELOCIM", "prefix": "GUA-VEL", "subsistema": "Guayas", "componente": "Velocímetro"},
    {"category": "GUAYAS / VARIOS", "pattern": r"\bFRENO", "prefix": "GUA-FRE", "subsistema": "Guayas", "componente": "Freno"},
    {"category": "GUAYAS / VARIOS", "pattern": r"\bEMERGENCIA\b", "prefix": "GUA-EME", "subsistema": "Guayas", "componente": "Emergencia"},

    # ZAPATAS: mantenemos prefijo único
    {"category": "ZAPATAS", "pattern": r"\bDEL|DELANT", "prefix": "FRE-ZAP"},
    {"category": "ZAPATAS", "pattern": r"\bTRAS|TRASER", "prefix": "FRE-ZAP"},

    # SCOOTER - plato variador
    {"category": "PARTES DE SCOOTER-AGILLITY/DINAMIC", "pattern": r"PLATO\s+VARIADOR|VARIADOR", "prefix": "SCO-PLA", "subsistema": "Variador", "componente": "Plato variador"},

    # SUSPENSIÓN delantera / trasera (por descripción)
    {"category": "SUSPENSION TRASERA", "pattern": r"\bDELANT", "force_category": "SUSPENSION DELANTERA"},
    {"category": "SUSPENSION DELANTERA", "pattern": r"\bTRAS", "force_category": "SUSPENSION TRASERA"},
]

# Palabras clave para VEHÍCULO
VEHICLE_HINTS = {
    "Moto": [r"\bMOTO\b", r"\bAKT\b", r"\bAGILITY\b", r"\bDINAMIC\b", r"\bSYM\b", r"\bJET\s*4\b", r"\bBWS\b",
             r"\bPULSAR\b", r"\bYBR\b", r"\bGN\b", r"\bGS\b", r"\bFZ\b", r"\bDISCOVER\b", r"\bCR5\b"],
    "Motocarguero": [r"\bCARGUERO\b", r"\b3W\b", r"\bAYCO\b", r"\bVAISAN(D)?\b", r"\bCERONTE\b", r"\bSIGMA\b",
                     r"\bZOLON\b", r"\bNATSUKY\b", r"\bSB300\b"]
}

# ==========================
# Clasificación de Sistema/Subsistema/Componente
# ==========================
def base_system_from_category(cat_norm):
    """Devuelve sistema sugerido a partir de categoría normalizada."""
    if cat_norm in (
        "BANDAS FRENO DELANTERO","BANDAS FRENO TRASERO","CAMPANA DELANTERA","CAMPANA TRASERA",
        "PASTILLAS DE FRENO DELANTERAS HLK","PASTILLAS DE FRENO TRASERAS HLK","DISCO FRENO DELANTERO",
        "DISCO FRENO TRASERO","ZAPATAS","PERA FRENOS","BOMBA FRENO -CILINDRO FRENO",
        "CILINDRO FRENO TRASERO","BOMBA FRENO TRASERO UNIVERSAL","KIT MORDAZA","DEPOSITO LIQUIDO FRENO"
    ):
        return "Frenos"

    if cat_norm in (
        "KIT CILINDRO EOM","CULATA COMPLETA CON VALVULAS","KIT PISTONES +ANILLOS","KIT ANILLOS","CIGÜEÑAL+BALINERA",
        "KIT VALVULAS","VALVULA PAIR","BALANCIN SUPERIOR","KIT BALANCINES INFERIOR","BASE C/BALANCINES",
        "KIT BALINERA MOTOR","IMPULSADORES","MOFLE","TAPAS REFRIGERANTE DE MOTOR","SOPORTE MOTOR",
        "CARCAZA VOLANTE","TAPON DE TIEMPO","ARBOL LEVAS","EJE CRANK COMPLETO","GUIA CADENILLA","GUIA VALVULA",
        "CADENILLAS","VOLANTE","TENSOR CADENILLA"
    ):
        return "Motor"

    if cat_norm in (
        "PIÑON DELANTERO","KIT PIÑONES DELANTERO/TRASERO","PIÑON PRIMARIO","PIÑON REVERSA","PIÑON VELOCIMETRO",
        "CAJA DE CAMBIOS","CAJA DE CAMBIOS-REVERSA","CAJA REVERSA","CAJA DIFERENCIAL","CRUCETAS CARGUERO",
        "EJE CAMBIOS","EJE SALIDA","KIT HORQUILLAS","TOMA FUERZA","UNION REVERSA","SELECTOR DE CAMBIOS",
        "CANASTILLA","PEDAL CAMBIOS","PEDAL CAMBIOS-CRANK- EJE SALIDA","CAJA VELOCIMETRO","BALINERAS ESPECIALES"
    ):
        return "Transmisión"

    if cat_norm in (
        "CDI","BOBINA DE ALTA CON CAPUCHON","BOBINA PULSORA","SWICHES","SWICH ENCENDIDO","KIT SWICH",
        "REGULADOR","REGULADOR TRIFASICO","FLASHER ELETRONICO","RELAY UNIVERSAL","SISTEMA ELECTRICO",
        "CAPUCHON BUJIA","STATOR -CORONA ENCENDIDO","INDICADOR CAMBIOS","LUCES LED","CHOQUE ELECTRICO"
    ):
        return "Eléctrico"

    if cat_norm in ("MOTOR ARRANQUE","ESCOBILLAS CON BASE","BENDIX-ONE WAY","PIÑON MOTOR ARRANQUE","KIT PIÑON ARRANQUE"):
        return "Arranque"

    if cat_norm in ("RADIADOR","VENTILADOR","BOMBA AGUA","TERMOSTATO","BASE VENTILADOR","TANQUE AGUA","TROMPO TEMPERATURA"):
        return "Refrigeración"

    if cat_norm in ("BOMBA ACEITE","FILTRO ACEITE","FILTRO CENTRIFUGO"):
        return "Lubricación"

    if cat_norm in ("FILTRO DE AIRE","CAJA FILTROS"):
        return "Filtros"

    if cat_norm in (
        "GUAYAS / VARIOS","GUAYA CLUTCH","GUAYA ACEL","GUAYA VEL","GUAYA EMERGENCIA","GUAYA FRENO"
    ):
        return "Guayas"

    if cat_norm in (
        "TREN DELANTERO CARGUERO","MANUBRIO","ESPEJOS","CHAPAS COMPUERTA","PARTES ELETRICAS COMANDOS","ANTIVIBRANTES",
        "GUARDA BARRO DELANTERO METALICO","SUSPENSION DELANTERA","SUSPENSION TRASERA","KIT CUNAS","MANIGUETA CON BASE COMPLETA","RIN",
        "TAPA GASOLINA"
    ):
        return "Chasis / Controles"

    if cat_norm in ("PARTES DE SCOOTER-AGILLITY/DINAMIC","CENTRIFUGA","CORREAS DISTRIBUCION","ROLEX"):
        return "Scooter / Variador"

    if cat_norm in ("BUJIA",):
        return "Bujías"

    if cat_norm in ("DISCOS CLUTCH",):
        return "Embrague"

    if cat_norm in ("KIT CARBURADOR","BAQUELA CARBURADOR","CONECTOR CARBURADOR","LLAVE GASOLINA"):
        return "Carburación"

    if cat_norm in ("KIT EMPAQUES CTO","EMPAQUES TAPA VOLANTE","EMPAQUES TAPA CULATIN ORING","EMPAQUES ANILLO EXOSTO","EMPAQUES CONECTOR MOFLE","KIT RETENEDORES","KIT RETENEDORES MOTOR"):
        return "Empaques / Retenedores"

    # Por defecto vacío
    return ""

def derive_subsystem_and_component(cat_norm, desc):
    """
    Deriva subsistema/componente por heurística de nombre.
    Si no hay señal clara: retornos vacíos (se podrán completar manualmente).
    """
    d = desc or ""
    # Ejemplos simples
    if cat_norm.startswith("BOMBA FRENO") or "CILINDRO FRENO" in cat_norm:
        return "Hidráulico freno", "Bomba/Cilindro"
    if cat_norm == "DISCO FRENO DELANTERO":
        return "Freno delantero", "Disco"
    if cat_norm == "DISCO FRENO TRASERO":
        return "Freno trasero", "Disco"
    if cat_norm == "ZAPATAS":
        return "Freno tambor", "Zapata"
    if cat_norm == "PASTILLAS DE FRENO DELANTERAS HLK":
        return "Freno delantero", "Pastillas"
    if cat_norm == "PASTILLAS DE FRENO TRASERAS HLK":
        return "Freno trasero", "Pastillas"

    if cat_norm in ("KIT CILINDRO EOM", "CULATA COMPLETA CON VALVULAS", "KIT PISTONES +ANILLOS", "KIT ANILLOS"):
        return "Top-end", "Cilindro/Culata/Pistón/Anillos"
    if cat_norm in ("CIGÜEÑAL+BALINERA", "EJE CRANK COMPLETO"):
        return "Bottom-end", "Cigüeñal"
    if cat_norm in ("GUIA CADENILLA", "CADENILLAS", "TENSOR CADENILLA"):
        return "Distribución", "Cadenilla/Tensor/Guía"
    if cat_norm in ("ARBOL LEVAS", "BALANCIN SUPERIOR", "KIT BALANCINES INFERIOR", "BASE C/BALANCINES", "GUIA VALVULA", "KIT VALVULAS"):
        return "Distribución", "Levas/Valvulas/Balancines"

    if cat_norm in ("PIÑON DELANTERO","KIT PIÑONES DELANTERO/TRASERO"):
        return "Transmisión secundaria", "Piñón/Corona"
    if cat_norm in ("CAJA DE CAMBIOS","KIT HORQUILLAS","SELECTOR DE CAMBIOS","EJE CAMBIOS"):
        return "Caja de cambios", "Conjunto cambios"
    if cat_norm in ("CAJA DIFERENCIAL", "CRUCETAS CARGUERO", "UNION REVERSA", "PIÑON REVERSA"):
        return "Transmisión carguero", "Diferencial/Crucetas/Reversa"

    if cat_norm in ("CDI","REGULADOR","REGULADOR TRIFASICO","RELAY UNIVERSAL","FLASHER ELETRONICO"):
        return "Control eléctrico", cat_norm.title()
    if cat_norm in ("BOBINA DE ALTA CON CAPUCHON", "CAPUCHON BUJIA"):
        return "Encendido", cat_norm.title()
    if cat_norm == "STATOR -CORONA ENCENDIDO":
        return "Generación", "Estátor/Corona"

    if cat_norm in ("MOTOR ARRANQUE","ESCOBILLAS CON BASE","BENDIX-ONE WAY","PIÑON MOTOR ARRANQUE","KIT PIÑON ARRANQUE"):
        return "Sistema de arranque", cat_norm.title()

    if cat_norm in ("RADIADOR","VENTILADOR","BOMBA AGUA","TERMOSTATO","TANQUE AGUA","BASE VENTILADOR","TROMPO TEMPERATURA"):
        return "Refrigeración", cat_norm.title()

    if cat_norm in ("BOMBA ACEITE","FILTRO ACEITE","FILTRO CENTRIFUGO"):
        return "Lubricación", cat_norm.title()

    if cat_norm in ("FILTRO DE AIRE","CAJA FILTROS"):
        return "Admisión", cat_norm.title()

    if cat_norm in ("TREN DELANTERO CARGUERO","SUSPENSION DELANTERA","SUSPENSION TRASERA"):
        return "Suspensión/Tren", cat_norm.title()
    if cat_norm in ("MANUBRIO","ESPEJOS","CHAPAS COMPUERTA","ANTIVIBRANTES","GUARDA BARRO DELANTERO METALICO","RIN","MANIGUETA CON BASE COMPLETA"):
        return "Controles/Carrocería", cat_norm.title()

    if cat_norm in ("PARTES DE SCOOTER-AGILLITY/DINAMIC","CENTRIFUGA","CORREAS DISTRIBUCION","ROLEX"):
        return "Variador/Transmisión CVT", cat_norm.title()

    if cat_norm == "DISCOS CLUTCH":
        return "Embrague", "Discos"
    if "PRENSA CLUTCH" in d or "PRENSA CLUCTH" in d:
        return "Embrague", "Prensa"

    if cat_norm in ("KIT CARBURADOR","BAQUELA CARBURADOR","CONECTOR CARBURADOR","LLAVE GASOLINA"):
        return "Alimentación", cat_norm.title()

    if cat_norm in ("KIT EMPAQUES CTO","EMPAQUES TAPA VOLANTE","EMPAQUES TAPA CULATIN ORING","EMPAQUES ANILLO EXOSTO","EMPAQUES CONECTOR MOFLE","KIT RETENEDORES","KIT RETENEDORES MOTOR"):
        return "Empaques/Retenedores", cat_norm.title()

    return "", ""

def detect_vehicle(desc):
    """Detecta tipo de vehículo por palabras clave en DESCRIPCION."""
    d = desc or ""
    for veh, patterns in VEHICLE_HINTS.items():
        for pat in patterns:
            if re.search(pat, d, flags=re.IGNORECASE):
                return veh
    # Fallback: si dice 3W, AYCO, VAISSAN, CERONTE… es muy probable Motocarguero
    if re.search(r"\b(3W|CARGUERO|AYCO|VAISAN(D)?|CERONTE|SIGMA|ZOLON|NATSUKY)\b", d, flags=re.IGNORECASE):
        return "Motocarguero"
    return "Moto"  # default

def refine_category_by_keywords(cat_norm, desc):
    """
    Permite ajustar categoría SUSPENSIÓN delantera/trasera por palabras de descripción.
    Y aplicar KEYWORD_RULES que fuerzan categoría o cambian prefijo.
    """
    c = cat_norm
    d = desc or ""
    for rule in KEYWORD_RULES:
        # Forzar cambio de categoría si aplica
        if rule.get("force_category") and c == rule["category"] and re.search(rule["pattern"], d, flags=re.IGNORECASE):
            c = rule["force_category"]
    return c

def resolve_prefix(cat_norm, desc):
    """Devuelve PREFIJO_BASE aplicando reglas por palabras clave y diccionario maestro."""
    d = desc or ""
    # Reglas de refinamiento por keywords
    for rule in KEYWORD_RULES:
        if cat_norm == rule.get("category") and re.search(rule["pattern"], d, flags=re.IGNORECASE):
            return rule["prefix"]
    # Directo del diccionario
    return PREFIJOS.get(cat_norm, None)

# ==========================
# Carga de datos
# ==========================
def load_dataframe():
    base_dir = CONFIG["BASE_DIR"]
    excel_path = os.path.join(base_dir, CONFIG["EXCEL_FILE"])
    sheet = CONFIG["SHEET_NAME"]

    if not os.path.exists(excel_path):
        log.error(f"❌ No se encontró el archivo de entrada: {excel_path}")
        sys.exit(1)

    df = pd.read_excel(excel_path, sheet_name=sheet)

    # Normalizar headers
    df.columns = [norm_header(c) for c in df.columns]

    # Garantizar columnas mínimas
    needed = ["CODIGO", "DESCRIPCION", "CATEGORIA"]
    for col in needed:
        if col not in df.columns:
            df[col] = ""

    # Columnas de trabajo que completaremos
    opt_cols = [
        "CODIGO NEW", "CATEGORIA_NORM", "SISTEMA PRINCIPAL", "SUBSISTEMA", "COMPONENTE",
        "PREFIJO_BASE", "TIPO VEHICULO", "PRECIO SIN IVA"
    ]
    for col in opt_cols:
        if col not in df.columns:
            df[col] = ""

    # Normalizar valores
    df["DESCRIPCION"] = df["DESCRIPCION"].apply(norm_text)
    df["CATEGORIA"] = df["CATEGORIA"].apply(norm_text)
    df["CATEGORIA_NORM"] = df["CATEGORIA"].apply(apply_alias)

    # Precio
    if "PRECIO SIN IVA" not in df.columns:
        df["PRECIO SIN IVA"] = ""
    df["PRECIO SIN IVA RAW"] = df["PRECIO SIN IVA"]
    df["PRECIO SIN IVA"] = df["PRECIO SIN IVA"].apply(format_precio)

    return df

# ==========================
# Duplicados
# ==========================
def detect_duplicates(df):
    """Duplicados por CODIGO (mismo SKU original)."""
    try:
        dups = df[df["CODIGO"].astype(str).str.strip().duplicated(keep=False)].copy()
    except Exception:
        dups = df.iloc[0:0].copy()
    return dups

# ==========================
# Clasificación principal
# ==========================
def classify_rows(df):
    sistemas, subs, comps, vehs, prefijos = [], [], [], [], []

    for cat, desc in zip(df["CATEGORIA_NORM"], df["DESCRIPCION"]):
        # Ajuste fino de categoría por keywords
        cat_ref = refine_category_by_keywords(cat, desc)
        sistema = base_system_from_category(cat_ref)

        # Subsistema / Componente heurístico
        sub, comp = derive_subsystem_and_component(cat_ref, desc)

        # Tipo de vehículo por keywords
        veh = detect_vehicle(desc)

        # Prefijo base
        pref = resolve_prefix(cat_ref, desc)

        sistemas.append(sistema)
        subs.append(sub)
        comps.append(comp)
        vehs.append(veh)
        prefijos.append(pref)

    df["SISTEMA PRINCIPAL"] = sistemas
    df["SUBSISTEMA"] = subs
    df["COMPONENTE"] = comps
    df["TIPO VEHICULO"] = vehs
    df["PREFIJO_BASE"] = prefijos

    return df

# ==========================
# Asignación de CODIGO NEW
# ==========================
def assign_codes(df):
    """
    Asigna CODIGO NEW por prefijo, preservando secuencia existente si está configurado.
    Si no se logra resolver prefijo, asigna 'PEND-000' y lo reporta como pendiente.
    """
    existing_seq = parse_existing_seq(df) if CONFIG["PRESERVAR_SECUENCIA_EXISTENTE"] else defaultdict(int)
    counters = defaultdict(int)
    # Inicializar contadores con el máximo previo
    for pref, maxn in existing_seq.items():
        counters[pref] = maxn

    codigos_new, pendientes = [], []

    for i, row in df.iterrows():
        pref = row.get("PREFIJO_BASE", "")
        catn = row.get("CATEGORIA_NORM", "")
        desc = row.get("DESCRIPCION", "")
        if not pref:
            pendientes.append({
                "CODIGO": row.get("CODIGO", ""),
                "DESCRIPCION": desc,
                "CATEGORIA_ORIGINAL": row.get("CATEGORIA", ""),
                "CATEGORIA_NORM": catn,
                "SISTEMA SUGERIDO": row.get("SISTEMA PRINCIPAL", "")
            })
            codigos_new.append("PEND-000")
            continue

        code = next_seq(counters, pref, start_from=(existing_seq.get(pref, 0) + 1))
        codigos_new.append(code)

    df["CODIGO NEW"] = codigos_new
    return df, pendientes

# ==========================
# Exportadores
# ==========================
def export_reports(df, pendientes, dups):
    base_dir = CONFIG["BASE_DIR"]

    # Reporte de validación (conteo por prefijo/categoría/sistema)
    rep = (
        df.groupby(["SISTEMA PRINCIPAL", "CATEGORIA_NORM", "PREFIJO_BASE"])
          .size().reset_index(name="CUENTA")
          .sort_values(["SISTEMA PRINCIPAL", "CATEGORIA_NORM", "PREFIJO_BASE", "CUENTA"], ascending=[True, True, True, False])
    )
    rep.to_csv(os.path.join(base_dir, CONFIG["REPORT_FILE"]), index=False, encoding="utf-8-sig")

    # Pendientes
    if pendientes:
        pd.DataFrame(pendientes).to_csv(os.path.join(base_dir, CONFIG["REVIEW_FILE"]), index=False, encoding="utf-8-sig")

    # Duplicados
    if not dups.empty:
        dups.to_csv(os.path.join(base_dir, CONFIG["DUPLICATES_FILE"]), index=False, encoding="utf-8-sig")

    # Métricas JSON
    metrics = {
        "total_rows": int(len(df)),
        "unique_categories_norm": sorted([c for c in df["CATEGORIA_NORM"].dropna().unique().tolist() if c]),
        "unique_prefixes": sorted([p for p in df["PREFIJO_BASE"].dropna().unique().tolist() if p]),
        "pendientes_count": int(len(pendientes)),
        "duplicates_count": int(len(dups)),
        "prefix_counts": {str(k): int(v) for k, v in df["PREFIJO_BASE"].value_counts().to_dict().items()},
        "zeros_precio_count": int((df["PRECIO SIN IVA"] == "$0").sum()),
        "empty_codigo_count": int((df["CODIGO"].astype(str).str.strip() == "").sum()),
    }
    with open(os.path.join(base_dir, CONFIG["METRICS_JSON_FILE"]), "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, ensure_ascii=False, indent=2)

def save_output(df):
    base_dir = CONFIG["BASE_DIR"]
    cols_order = [
        "CODIGO NEW",
        "CODIGO",
        "DESCRIPCION",
        "CATEGORIA",
        "CATEGORIA_NORM",
        "SISTEMA PRINCIPAL",
        "SUBSISTEMA",
        "COMPONENTE",
        "TIPO VEHICULO",
        "PREFIJO_BASE",
        "PRECIO SIN IVA",
        "PRECIO SIN IVA RAW",
    ]
    for c in cols_order:
        if c not in df.columns:
            df[c] = ""
    df = df[cols_order]
    out_path = os.path.join(base_dir, CONFIG["OUTPUT_FILE"])
    df.to_excel(out_path, index=False)

# ==========================
# MAIN
# ==========================
def main():
    log.info("=== Iniciando procesamiento de inventario KAIQI (v3) ===")

    # 1) Carga
    df = load_dataframe()
    log.info(f"Filas cargadas: {len(df)}")

    # 2) Duplicados por CODIGO
    dups = detect_duplicates(df)
    if not dups.empty:
        log.warning(f"Posibles duplicados por CODIGO: {len(dups)}")
    else:
        log.info("Sin duplicados por CODIGO.")

    # 3) Clasificar sistema/subsistema/componente y tipo vehículo
    df = classify_rows(df)

    # 4) Asignar CODIGO NEW (preservando secuencia existente si aplica)
    df, pendientes = assign_codes(df)
    if pendientes:
        log.warning(f"Filas pendientes de clasificación: {len(pendientes)}")
    else:
        log.info("Sin pendientes de clasificación.")

    # 5) Exportar reportes y métricas
    export_reports(df, pendientes, dups)

    # 6) Excel final
    save_output(df)

    log.info(f"✅ Archivo generado: {os.path.join(CONFIG['BASE_DIR'], CONFIG['OUTPUT_FILE'])}")
    log.info(f"📊 Reporte: {os.path.join(CONFIG['BASE_DIR'], CONFIG['REPORT_FILE'])}")
    if pendientes:
        log.info(f"🟡 Pendientes: {os.path.join(CONFIG['BASE_DIR'], CONFIG['REVIEW_FILE'])}")
    if not dups.empty:
        log.info(f"🔎 Duplicados: {os.path.join(CONFIG['BASE_DIR'], CONFIG['DUPLICATES_FILE'])}")
    log.info(f"📈 Métricas JSON: {os.path.join(CONFIG['BASE_DIR'], CONFIG['METRICS_JSON_FILE'])}")
    log.info("=== Proceso completado exitosamente ===")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log.error(f"❌ Error fatal: {e}")
        sys.exit(1)
