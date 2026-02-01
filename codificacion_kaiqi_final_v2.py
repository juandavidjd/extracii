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
    "PRESERVAR_SECUENCIA_EXISTENTE": True,
}

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
log = logging.getLogger("kaiqi_v2")

def norm_text(x):
    if pd.isna(x):
        return ""
    return re.sub(r"\s+", " ", str(x)).strip().upper()

def safe_float(x):
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
    v = safe_float(x)
    if pd.isna(v):
        return "$0"
    return f"${int(round(v)):,}".replace(",", ".")

def parse_existing_seq(df):
    existing = defaultdict(int)
    if "CODIGO NEW" not in df.columns:
        return existing
    for val in df["CODIGO NEW"].dropna().astype(str):
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

ALIAS_MAP = {
    "PASTILLAS DE FRENO DEL HLK": "PASTILLAS DE FRENO DELANTERAS HLK",
    "PASTILLAS DE FRENO DEL/TRAS HLK": "PASTILLAS DE FRENO TRASERAS HLK",
    "PASTILLAS DE FRERENO DELANTERAS HLK": "PASTILLAS DE FRENO DELANTERAS HLK",
    "KIT CILINDROS EOM": "KIT CILINDRO EOM",
    "CARCAZA  VOLANTE": "CARCAZA VOLANTE",
    "BOBINA DE ALTA  CON CAPUCHON": "BOBINA DE ALTA CON CAPUCHON",
    "FLASHER ELETRONICO": "FLASHER ELETRONICO",
    "PARTES ELETRICAS COMANDOS": "PARTES ELETRICAS COMANDOS",
    "CADENILLAS ": "CADENILLAS",
    "GUIA CADENILLA ": "GUIA CADENILLA",
    "GUIA VAL ": "GUIA VALVULA",
    "CILINDRO FRENO TRAS ": "CILINDRO FRENO TRASERO",
    "CORREAS DISTRIBUCION ": "CORREAS DISTRIBUCION",
    "BOMBA ACEITE ": "BOMBA ACEITE",
    "CONECTOR CARB": "CONECTOR CARBURADOR",
    "PASTILLAS DE FRENO DELANTERAS HLK ": "PASTILLAS DE FRENO DELANTERAS HLK",
    "ESPEJOS / VARIOS": "ESPEJOS",
    "PRENSA CLUTH CON DISCOS": "PRENSA CLUTCH CON DISCOS",
    "CHOQUE ELECTRIC": "CHOQUE ELECTRICO",
}

PREFIX = {
    "FRENOS:BANDAS DEL": "FRE-BAN-DEL",
    "FRENOS:BANDAS TRAS": "FRE-BAN-TRAS",
    "FRENOS:DISCO DEL": "FRE-DIS-DEL",
    "FRENOS:DISCO TRAS": "FRE-DIS-TRAS",
    "FRENOS:ZAPATAS": "FRE-ZAP",
    "FRENOS:PERA": "FRE-PER",
    "FRENOS:BOMBA/CILINDRO": "FRE-BOM-CIL",
    "FRENOS:CILINDRO TRAS": "FRE-CIL-TRAS",
    "FRENOS:BOMBA TRAS": "FRE-BOM-TRAS",
    "FRENOS:MORDAZA": "FRE-MOR",
    "FRENOS:DEPOSITO": "FRE-DEP",
    "MOTOR:CILINDRO": "MOT-CIL",
    "MOTOR:CULATA": "MOT-CUL",
    "MOTOR:PISTON/ANILLOS": "MOT-PI",
    "MOTOR:ANILLOS": "MOT-ANI",
    "MOTOR:CIGUENAL": "MOT-CIG",
    "MOTOR:VALVULAS": "MOT-VAL",
    "MOTOR:VALVULA PAIR": "MOT-VAL-PAIR",
    "MOTOR:BALANCIN": "MOT-BAL",
    "MOTOR:BAL-BASE": "MOT-BAL-BASE",
    "MOTOR:BALINERA MOTOR": "MOT-BAL-MOT",
    "MOTOR:IMPULSORES": "MOT-IMP",
    "MOTOR:MOFLE": "MOT-MOF",
    "MOTOR:TAPAS REFRIG": "MOT-TAP",
    "MOTOR:SOPORTE MOTOR": "MOT-SOP",
    "MOTOR:CARCAZA VOLANTE": "MOT-CAR-VOL",
    "MOTOR:TAPON TIEMPO": "MOT-TAP-TIEM",
    "MOTOR:ARBOL LEVAS": "MOT-LEV",
    "MOTOR:EJE CRANK": "MOT-EJECRA",
    "MOTOR:GUIA CADENILLA": "MOT-GUI-CAD",
    "MOTOR:GUIA VALVULA": "MOT-GUI-VAL",
    "MOTOR:CADENILLA": "MOT-CAD",
    "TRANSMISION:PINON DEL": "TRA-PIN-DEL",
    "TRANSMISION:KIT PINONES": "TRA-PIN-TRAS",
    "TRANSMISION:PINON PRIM": "TRA-PIN-PRI",
    "TRANSMISION:PINON REV": "TRA-PIN-REV",
    "TRANSMISION:PINON VEL": "TRA-PIN-VEL",
    "TRANSMISION:CAJA CAMBIOS": "TRA-CAM",
    "TRANSMISION:REVERSA": "TRA-REV",
    "TRANSMISION:DIFERENCIAL": "TRA-DIF",
    "TRANSMISION:CRUCETAS": "TRA-CRU",
    "TRANSMISION:EJE CAMBIOS": "TRA-EJE-CAM",
    "TRANSMISION:EJE SALIDA": "TRA-EJE-SAL",
    "TRANSMISION:HORQUILLAS": "TRA-HOR",
    "TRANSMISION:TOMA FUERZA": "TRA-TOM",
    "TRANSMISION:UNION REVERSA": "TRA-UNI",
    "TRANSMISION:SELECTOR CAMBIOS": "TRA-SEL-CAM",
    "TRANSMISION:CANASTILLA": "TRA-CAN",
    "TRANSMISION:PEDAL": "TRA-PED",
    "TRANSMISION:PEDAL-CRANK": "TRA-PED-CRANK",
    "TRANSMISION:VELOCIMETRO": "TRA-VEL-CAJ",
    "TRANSMISION:BALINERAS ESP": "TRA-BAL-ESP",
    "ELECTRICO:CDI": "ELE-CDI",
    "ELECTRICO:BOBINA ALTA": "ELE-BOB",
    "ELECTRICO:PULSORA": "ELE-PUL",
    "ELECTRICO:SWICH": "ELE-SWI",
    "ELECTRICO:SWICH ENC": "ELE-SWI-ENC",
    "ELECTRICO:KIT SWICH": "ELE-SWI-KIT",
    "ELECTRICO:REGULADOR": "ELE-REG",
    "ELECTRICO:REG TRIFASICO": "ELE-REG-TRI",
    "ELECTRICO:FLASHER": "ELE-FLA",
    "ELECTRICO:RELAY": "ELE-REL",
    "ELECTRICO:SISTEMA": "ELE-SIS",
    "ELECTRICO:CAPUCHON": "ELE-CAP",
    "ELECTRICO:STATOR": "ELE-STA",
    "ELECTRICO:INDICADOR CAMBIOS": "ELE-IND-CAM",
    "ELECTRICO:LUCES LED": "ELE-LED",
    "ELECTRICO:CHOQUE": "ELE-CHOQ",
    "ARRANQUE:MOTOR": "ARR-MOT",
    "ARRANQUE:ESCOBILLAS": "ARR-ESC",
    "ARRANQUE:BENDIX": "ARR-BEN",
    "ARRANQUE:PINON": "ARR-PIN",
    "ARRANQUE:KIT PINON": "ARR-PIN-KIT",
    "REFRIGERACION:RADIADOR": "REF-RAD",
    "REFRIGERACION:VENTILADOR": "REF-VENT",
    "REFRIGERACION:BOMBA AGUA": "REF-AGU",
    "REFRIGERACION:TERMOSTATO": "REF-TER",
    "REFRIGERACION:BASE VENT": "REF-BASE",
    "REFRIGERACION:TANQUE": "REF-TAN",
    "REFRIGERACION:TROMPO TEMP": "REF-TRO-TEMP",
    "LUBRICACION:BOMBA ACEITE": "LUB-ACE",
    "LUBRICACION:FILTRO ACEITE": "LUB-FIL",
    "LUBRICACION:FILTRO CENTRIF": "LUB-CEN",
    "FILTROS:AIRE": "FIL-AIR",
    "FILTROS:CAJA": "FIL-BOX",
    "GUAYAS:CLUTCH": "GUA-CLU",
    "GUAYAS:ACELERADOR": "GUA-ACE",
    "GUAYAS:VELOCIDAD": "GUA-VEL",
    "GUAYAS:EMERGENCIA": "GUA-EME",
    "GUAYAS:FRENO": "GUA-FRE",
    "CHASIS:TREN DEL CARGUERO": "CHA-TREN",
    "CHASIS:MANUBRIO": "CHA-MAN",
    "CHASIS:ESPEJOS": "CHA-ESP",
    "CHASIS:CHAPAS": "CHA-CHA",
    "CHASIS:COMANDOS": "CHA-COM",
    "CHASIS:ANTIVIBRANTES": "CHA-ANT",
    "CHASIS:GUARDA BARRO DEL": "CHA-GBAR-DEL",
    "CHASIS:SUSP DEL": "CHA-SUS-DEL",
    "CHASIS:SUSP TRAS": "CHA-SUS-TRAS",
    "CHASIS:CUNAS": "CHA-CUN",
    "CHASIS:MANIGUETA BASE": "CHA-MANIG",
    "SCOOTER:PLATO VARIADOR": "SCO-PLA",
    "SCOOTER:CENTRIFUGA": "SCO-CEN",
    "SCOOTER:CORREA": "SCO-COR",
    "SCOOTER:ROLEX": "SCO-ROL",
    "BUJIAS:BUJIA": "BUJ",
    "CARBURACION:KIT": "CAR-KIT",
    "CARBURACION:BAQUELA/CON": "CAR-CON",
    "CARBURACION:LLAVE": "CAR-LLA",
    "EMPAQUES:KIT": "EMP-KIT",
    "EMPAQUES:TAPA VOLANTE": "EMP-TAP",
    "EMPAQUES:TAPA CULATIN": "EMP-CUL",
    "EMPAQUES:ANILLO EXOSTO": "EMP-EXO",
    "EMPAQUES:CONECTOR MOFLE": "EMP-MOF",
    "RETENEDORES:KIT": "EMP-RET",
    "RETENEDORES:KIT MOTOR": "EMP-RET-MOT",
    "CLUTCH:DISCOS": "CLU-DIS",
    "CLUTCH:PRENSA": "CLU-PRE",
    "RINES:RIN": "RIN",
    "TAPA GASOLINA:TAPA": "TAPA-GAS",
    "TENSOR:TENSOR CADENILLA": "TEN-CAD",
    "VOLANTE:VOLANTE": "VOL",
    "CAMPANA:CAMPANA DEL": "FRE-CAM-DEL",
    "CAMPANA:CAMPANA TRAS": "FRE-CAM-TRAS",
}

KEYWORDS = [
    (r"\bBANDA(S)?\b.*\bDEL", "FRENOS", "BANDAS DEL", "BANDAS"),
    (r"\bBANDA(S)?\b.*\bTRAS", "FRENOS", "BANDAS TRAS", "BANDAS"),
    (r"\bDISCO\b.*\bDEL", "FRENOS", "DISCO DEL", "DISCO"),
    (r"\bDISCO\b.*\bTRAS", "FRENOS", "DISCO TRAS", "DISCO"),
    (r"\bZAPATA(S)?\b", "FRENOS", "ZAPATAS", "ZAPATAS"),
    (r"\bPERA\b.*FREN", "FRENOS", "PERA", "PERA"),
    (r"\bBOMBA\b.*FRENO|\bCILINDRO\b.*FRENO", "FRENOS", "BOMBA/CILINDRO", "BOMBA/CILINDRO"),
    (r"\bCILINDRO\b.*\bTRAS", "FRENOS", "CILINDRO TRAS", "CILINDRO TRAS"),
    (r"\bMORDAZA\b|\bCALIPER\b", "FRENOS", "MORDAZA", "MORDAZA"),
    (r"\bDEPOSITO\b.*FRENO", "FRENOS", "DEPOSITO", "DEPOSITO"),
    (r"\bKIT\b.*CILINDRO|\bCILINDRO\b(?!.*FRENO)", "MOTOR", "CILINDRO", "CILINDRO"),
    (r"\bCULATA\b", "MOTOR", "CULATA", "CULATA"),
    (r"\bKIT\b.*PISTON|\bPISTON\b|\bANILLO(S)?\b", "MOTOR", "PISTON/ANILLOS", "PISTON/ANILLOS"),
    (r"\bCIG[ÜU]E?ÑAL\b", "MOTOR", "CIGUENAL", "CIGÜEÑAL"),
    (r"\bKIT\b.*VALVULA|\bVALVULA PAIR\b|\bVALVULAS\b", "MOTOR", "VALVULAS", "VALVULAS"),
    (r"\bBALANCIN\b", "MOTOR", "BALANCIN", "BALANCIN"),
    (r"\bBALINERA\b.*MOTOR", "MOTOR", "BALINERA MOTOR", "BALINERAS"),
    (r"\bIMPULSAD", "MOTOR", "IMPULSORES", "IMPULSORES"),
    (r"\bMOFLE\b|EXOSTO|EXHOSTO|EXAUSTO|ESCAPE", "MOTOR", "MOFLE", "MOFLE"),
    (r"\bTAPA(S)?\b.*REFRIGERANTE", "MOTOR", "TAPAS REFRIG", "TAPAS"),
    (r"\bSOPORTE\b.*MOTOR", "MOTOR", "SOPORTE MOTOR", "SOPORTE"),
    (r"\bCARCAZA\b.*VOLANTE", "MOTOR", "CARCAZA VOLANTE", "CARCAZA VOLANTE"),
    (r"\bTAPON\b.*TIEMPO", "MOTOR", "TAPON TIEMPO", "TAPON"),
    (r"\bARBOL\b.*LEVAS", "MOTOR", "ARBOL LEVAS", "ARBOL LEVAS"),
    (r"\bEJE\b.*CRANK", "MOTOR", "EJE CRANK", "EJE CRANK"),
    (r"\bGUIA\b.*CADENILLA", "MOTOR", "GUIA CADENILLA", "GUIA CADENILLA"),
    (r"\bGUIA\b.*VALVULA", "MOTOR", "GUIA VALVULA", "GUIA VALVULA"),
    (r"\bCADENILLA\b|DISTRIBUCION DISTRI", "MOTOR", "CADENILLA", "CADENILLA"),
    (r"\bPI[ÑN]ON\b.*\bSALIDA\b", "TRANSMISION", "PINON DEL", "PIÑON"),
    (r"\bKIT\b.*PI[ÑN]ONES", "TRANSMISION", "KIT PINONES", "KIT PIÑONES"),
    (r"\bPI[ÑN]ON\b.*\bPRIM", "TRANSMISION", "PINON PRIM", "PIÑON"),
    (r"\bPI[ÑN]ON\b.*\bREVERSA\b", "TRANSMISION", "PINON REV", "PIÑON"),
    (r"\bPI[ÑN]ON\b.*VELOCIM", "TRANSMISION", "PINON VEL", "PIÑON"),
    (r"\bCAJA\b.*CAMBIO", "TRANSMISION", "CAJA CAMBIOS", "CAJA"),
    (r"\bREVERSA\b", "TRANSMISION", "REVERSA", "REVERSA"),
    (r"\bDIFERENCIAL\b", "TRANSMISION", "DIFERENCIAL", "DIFERENCIAL"),
    (r"\bCRUCETA(S)?\b", "TRANSMISION", "CRUCETAS", "CRUCETAS"),
    (r"\bEJE\b.*CAMBIO", "TRANSMISION", "EJE CAMBIOS", "EJE"),
    (r"\bEJE\b.*SALIDA", "TRANSMISION", "EJE SALIDA", "EJE"),
    (r"\bHORQUILLA(S)?\b", "TRANSMISION", "HORQUILLAS", "HORQUILLAS"),
    (r"\bTOMA\b.*FUERZA|\bREIPIN\b", "TRANSMISION", "TOMA FUERZA", "TOMA FUERZA"),
    (r"\bUNION\b.*REVERSA", "TRANSMISION", "UNION REVERSA", "UNION REVERSA"),
    (r"\bSELECTOR\b.*CAMBIO", "TRANSMISION", "SELECTOR CAMBIOS", "SELECTOR"),
    (r"\bCANASTILLA\b", "TRANSMISION", "CANASTILLA", "CANASTILLA"),
    (r"\bPEDAL\b.*CAMBIO", "TRANSMISION", "PEDAL", "PEDAL"),
    (r"\bPEDAL\b.*CRANK|\bCRANK\b", "TRANSMISION", "PEDAL-CRANK", "PEDAL/CRANK"),
    (r"\bCAJA\b.*VELOCIMETRO", "TRANSMISION", "VELOCIMETRO", "VELOCIMETRO"),
    (r"\bBALINERA(S)?\b.*(ESPECIAL|C[3-9])", "TRANSMISION", "BALINERAS ESP", "BALINERAS"),
    (r"\bCDI\b", "ELECTRICO", "CDI", "CDI"),
    (r"\bBOBINA\b.*ALTA|\bCAPUCHON\b.*BUJIA", "ELECTRICO", "BOBINA ALTA", "BOBINA"),
    (r"\bBOBINA\b.*PULSORA|\bPULSOR(A)?\b", "ELECTRICO", "PULSORA", "BOBINA PULSORA"),
    (r"\bSWICH(ES)?\b", "ELECTRICO", "SWICH", "SWICH"),
    (r"\bSWICH\b.*ENCENDIDO", "ELECTRICO", "SWICH ENC", "SWICH ENCENDIDO"),
    (r"\bKIT\b.*SWICH", "ELECTRICO", "KIT SWICH", "KIT SWICH"),
    (r"\bREGULADOR\b(?!.*TRIFAS)", "ELECTRICO", "REGULADOR", "REGULADOR"),
    (r"\bREGULADOR\b.*TRIFAS", "ELECTRICO", "REG TRIFASICO", "REGULADOR TRIFASICO"),
    (r"\bFLASHER\b", "ELECTRICO", "FLASHER", "FLASHER"),
    (r"\bRELAY\b", "ELECTRICO", "RELAY", "RELAY"),
    (r"\bSISTEMA\b.*ELECTRICO", "ELECTRICO", "SISTEMA", "SISTEMA ELECTRICO"),
    (r"\bCAPUCHON\b.*BUJIA", "ELECTRICO", "CAPUCHON", "CAPUCHON"),
    (r"\bSTATOR\b|\bCORONA\b.*ENCENDIDO", "ELECTRICO", "STATOR", "STATOR"),
    (r"\bINDICADOR\b.*CAMBIO", "ELECTRICO", "INDICADOR CAMBIOS", "INDICADOR"),
    (r"\bLUCE?S?\b.*LED|\bSTOP\b.*LED", "ELECTRICO", "LUCES LED", "LED"),
    (r"\bCHOQUE\b.*ELECTR", "ELECTRICO", "CHOQUE", "CHOQUE ELECTRICO"),
    (r"\bMOTOR\b.*ARRANQUE", "ARRANQUE", "MOTOR", "MOTOR ARRANQUE"),
    (r"\bESCOBILLAS\b", "ARRANQUE", "ESCOBILLAS", "ESCOBILLAS"),
    (r"\bBENDIX\b|\bONE WAY\b", "ARRANQUE", "BENDIX", "BENDIX"),
    (r"\bPI[ÑN]ON\b.*ARRANQUE", "ARRANQUE", "PINON", "PIÑON ARRANQUE"),
    (r"\bKIT\b.*PI[ÑN]ON\b.*ARRANQUE", "ARRANQUE", "KIT PINON", "KIT PIÑON ARRANQUE"),
    (r"\bRADIADOR\b", "REFRIGERACION", "RADIADOR", "RADIADOR"),
    (r"\bVENTILADOR\b", "REFRIGERACION", "VENTILADOR", "VENTILADOR"),
    (r"\bBOMBA\b.*AGUA", "REFRIGERACION", "BOMBA AGUA", "BOMBA AGUA"),
    (r"\bTERMOSTATO\b", "REFRIGERACION", "TERMOSTATO", "TERMOSTATO"),
    (r"\bBASE\b.*VENTILADOR", "REFRIGERACION", "BASE VENT", "BASE VENTILADOR"),
    (r"\bTANQUE\b.*AGUA", "REFRIGERACION", "TANQUE", "TANQUE AGUA"),
    (r"\bTROMPO\b.*TEMP", "REFRIGERACION", "TROMPO TEMP", "TROMPO TEMPERATURA"),
    (r"\bBOMBA\b.*ACEITE", "LUBRICACION", "BOMBA ACEITE", "BOMBA ACEITE"),
    (r"\bFILTRO\b.*ACEITE", "LUBRICACION", "FILTRO ACEITE", "FILTRO ACEITE"),
    (r"\bFILTRO\b.*CENTRIF", "LUBRICACION", "FILTRO CENTRIF", "FILTRO CENTRIFUGO"),
    (r"\bFILTRO\b.*AIRE", "FILTROS", "AIRE", "FILTRO DE AIRE"),
    (r"\bCAJA\b.*FILTRO", "FILTROS", "CAJA", "CAJA FILTROS"),
    (r"\bGUAYA\b.*CLUTCH", "GUAYAS", "CLUTCH", "GUAYA CLUTCH"),
    (r"\bGUAYA\b.*ACEL", "GUAYAS", "ACELERADOR", "GUAYA ACEL"),
    (r"\bGUAYA\b.*VEL", "GUAYAS", "VELOCIDAD", "GUAYA VEL"),
    (r"\bGUAYA\b.*EMER", "GUAYAS", "EMERGENCIA", "GUAYA EMERGENCIA"),
    (r"\bGUAYA\b.*FRENO", "GUAYAS", "FRENO", "GUAYA FRENO"),
    (r"\bANTIVIBRANTES\b", "CHASIS", "ANTIVIBRANTES", "ANTIVIBRANTES"),
    (r"\bMANUBRIO\b", "CHASIS", "MANUBRIO", "MANUBRIO"),
    (r"\bESPEJO(S)?\b", "CHASIS", "ESPEJOS", "ESPEJOS"),
    (r"\bCHAPAS\b", "CHASIS", "CHAPAS", "CHAPAS COMPUERTA"),
    (r"\bCOMANDO(S)?\b", "CHASIS", "COMANDOS", "PARTES ELETRICAS COMANDOS"),
    (r"\bGUARDA\b.*BARRO.*DEL", "CHASIS", "GUARDA BARRO DEL", "GUARDA BARRO DELANTERO METALICO"),
    (r"\bMONOSHOCK\b|\bSUSPENSION\b.*TRAS", "CHASIS", "SUSP TRAS", "SUSPENSION TRASERA"),
    (r"\bSUSPENSION\b.*DEL", "CHASIS", "SUSP DEL", "SUSPENSION DELANTERA"),
    (r"\bCUNA(S)?\b", "CHASIS", "CUNAS", "KIT CUNAS"),
    (r"\bMANIGUETA\b.*BASE", "CHASIS", "MANIGUETA BASE", "MANIGUETA CON BASE COMPLETA"),
    (r"\bTREN\b.*DELANTERO\b.*CARGUERO", "CHASIS", "TREN DEL CARGUERO", "TREN DELANTERO CARGUERO"),
    (r"\bPLATO\b.*VARIADOR|VARIADOR\b", "SCOOTER", "PLATO VARIADOR", "PLATO VARIADOR"),
    (r"\bCENTRIFUGA\b", "SCOOTER", "CENTRIFUGA", "CENTRIFUGA"),
    (r"\bCORREA(S)?\b.*(743|835|818|CORREA)", "SCOOTER", "CORREA", "CORREAS DISTRIBUCION"),
    (r"\bROLEX\b|\bPESAS\b.*VARIADOR", "SCOOTER", "ROLEX", "ROLEX"),
    (r"\bBUJIA\b", "BUJIAS", "BUJIA", "BUJIA"),
    (r"\bKIT\b.*CARBURADOR|\bCARBURADOR(ES)?\b", "CARBURACION", "KIT", "KIT CARBURADOR"),
    (r"\bBAQUELA\b.*CARBURADOR|\bCONECTOR\b.*CARBURADOR", "CARBURACION", "BAQUELA/CON", "CONECTOR CARBURADOR"),
    (r"\bLLAVE\b.*GASOLINA", "CARBURACION", "LLAVE", "LLAVE GASOLINA"),
    (r"\bKIT\b.*EMPAQUE(S)?", "EMPAQUES", "KIT", "KIT EMPAQUES CTO"),
    (r"\bEMPAQUE(S)?\b.*TAPA\b.*VOLANTE", "EMPAQUES", "TAPA VOLANTE", "EMPAQUES TAPA VOLANTE"),
    (r"\bEMPAQUE(S)?\b.*CULATIN|\bORING\b", "EMPAQUES", "TAPA CULATIN", "EMPAQUES TAPA CULATIN ORING"),
    (r"\bANILLO\b.*EXO?STO", "EMPAQUES", "ANILLO EXOSTO", "EMPAQUES ANILLO EXOSTO"),
    (r"\bCONECTOR\b.*MOFLE", "EMPAQUES", "CONECTOR MOFLE", "EMPAQUES CONECTOR MOFLE"),
    (r"\bRETENEDOR(ES)?\b(?!.*MOTOR)", "RETENEDORES", "KIT", "KIT RETENEDORES"),
    (r"\bRETENEDOR(ES)?\b.*MOTOR|\bKIT LUBRICACION\b", "RETENEDORES", "KIT MOTOR", "KIT RETENEDORES MOTOR"),
    (r"\bDISCO(S)?\b.*CLUTCH", "CLUTCH", "DISCOS", "DISCOS CLUTCH"),
    (r"\bPRENSA\b.*CLUTCH", "CLUTCH", "PRENSA", "PRENSA CLUTCH CON DISCOS"),
    (r"\bRIN\b", "RINES", "RIN", "RIN"),
    (r"\bTAPA\b.*GASOLINA", "TAPA GASOLINA", "TAPA", "TAPA GASOLINA"),
    (r"\bTENSOR\b.*CADENILLA", "TENSOR", "TENSOR CADENILLA", "TENSOR CADENILLA"),
    (r"\bVOLANTE\b(?!.*CARCAZA)", "VOLANTE", "VOLANTE", "VOLANTE"),
    (r"\bCAMPANA\b.*DEL", "CAMPANA", "CAMPANA DEL", "CAMPANA DELANTERA"),
    (r"\bCAMPANA\b.*TRAS", "CAMPANA", "CAMPANA TRAS", "CAMPANA TRASERA"),
]

def vehicle_type(text):
    t = norm_text(text)
    if re.search(r"\b(3W|CARGUER|AYCO|VAISAN|VAISSAN|CERONTE|ZOLON|NATSUKY|SB300|SGMA|ZH)\b", t):
        return "Motocarguero"
    return "Moto"

def apply_alias(cat):
    if not cat:
        return ""
    c = cat.strip().upper()
    return ALIAS_MAP.get(c, c)

def classify_row(desc, cat_norm):
    txt = " ".join([norm_text(desc), norm_text(cat_norm)]).strip()
    for pattern, sistema, sub, comp in KEYWORDS:
        if re.search(pattern, txt):
            key = f"{sistema}:{sub}"
            pref = PREFIX.get(key)
            return sistema, sub, comp, pref, "CLAS_AUTO_KEYWORD"
    return "", "", "", None, "SIN_MATCH"

def compute_prefix_from_category(cat_norm, desc):
    sistema, sub, comp, pref, obs = classify_row(desc, cat_norm)
    return sistema, sub, comp, pref, obs

def load_dataframe():
    base_dir = CONFIG["BASE_DIR"]
    excel_file = os.path.join(base_dir, CONFIG["EXCEL_FILE"])
    if not os.path.exists(excel_file):
        log.error(f"❌ No se encontró el archivo fuente: {excel_file}")
        sys.exit(1)
    try:
        try:
            df = pd.read_excel(excel_file, sheet_name=CONFIG["SHEET_NAME"])
        except:
            df = pd.read_excel(excel_file)
    except Exception as e:
        log.error(f"❌ Error leyendo Excel: {e}")
        sys.exit(1)
    df.columns = [norm_text(c) for c in df.columns]
    needed = ["CODIGO NEW", "CODIGO", "DESCRIPCION", "CATEGORIA", "PRECIO SIN IVA"]
    for c in needed:
        if c not in df.columns:
            df[c] = ""
    df["DESCRIPCION"] = df["DESCRIPCION"].apply(norm_text)
    df["CATEGORIA"] = df["CATEGORIA"].apply(norm_text)
    df["CATEGORIA_NORM"] = df["CATEGORIA"].apply(apply_alias)
    df["PRECIO SIN IVA RAW"] = df["PRECIO SIN IVA"]
    df["PRECIO SIN IVA"] = df["PRECIO SIN IVA"].apply(format_precio)
    return df

def detect_duplicates(df):
    dups = df[df["CODIGO"].astype(str).str.strip().ne("") & df["CODIGO"].duplicated(keep=False)].copy()
    return dups

def enrich_classification(df):
    sistemas, subs, comps, prefs, obs_list, tipos = [], [], [], [], [], []
    for desc, cat in zip(df["DESCRIPCION"], df["CATEGORIA_NORM"]):
        s, sub, comp, pref, obs = compute_prefix_from_category(cat, desc)
        sistemas.append(s)
        subs.append(sub)
        comps.append(comp)
        prefs.append(pref)
        obs_list.append(obs)
    for desc in df["DESCRIPCION"]:
        tipos.append(vehicle_type(desc))
    df["SISTEMA PRINCIPAL"] = sistemas
    df["SUBSISTEMA"] = subs
    df["COMPONENTE"] = comps
    df["PREFIJO_BASE"] = prefs
    df["TIPO VEHICULO"] = tipos
    df["OBSERVACION CLASIF"] = obs_list
    return df

def assign_codes(df):
    existing_seq = parse_existing_seq(df) if CONFIG["PRESERVAR_SECUENCIA_EXISTENTE"] else defaultdict(int)
    counters = defaultdict(int)
    for pref, maxn in existing_seq.items():
        counters[pref] = maxn
    result_codes = []
    pendientes = []
    for _, row in df.iterrows():
        code_existing = str(row.get("CODIGO NEW", "")).strip().upper()
        if re.match(r"^[A-Z0-9\-]+-\d{3,}$", code_existing):
            result_codes.append(code_existing)
            continue
        pref = row.get("PREFIJO_BASE")
        if not pref or str(pref).strip() == "" or pd.isna(pref):
            result_codes.append("PEND-000")
            pendientes.append({
                "CODIGO": row.get("CODIGO", ""),
                "DESCRIPCION": row.get("DESCRIPCION", ""),
                "CATEGORIA_ORIGINAL": row.get("CATEGORIA", ""),
                "CATEGORIA_NORM": row.get("CATEGORIA_NORM", ""),
                "SISTEMA PROPUESTO": row.get("SISTEMA PRINCIPAL", ""),
                "SUBSISTEMA PROPUESTO": row.get("SUBSISTEMA", ""),
                "COMPONENTE PROPUESTO": row.get("COMPONENTE", ""),
                "TIPO VEHICULO": row.get("TIPO VEHICULO", ""),
            })
        else:
            start_from = existing_seq.get(pref, 0) + 1
            code = next_seq(counters, pref, start_from=start_from)
            result_codes.append(code)
    df["CODIGO NEW"] = result_codes
    return df, pendientes

def export_reports(df, pendientes, dups):
    base_dir = CONFIG["BASE_DIR"]
    rep = (
        df.groupby(["SISTEMA PRINCIPAL", "SUBSISTEMA", "PREFIJO_BASE"])
        .size()
        .reset_index(name="CUENTA")
        .sort_values(["SISTEMA PRINCIPAL", "SUBSISTEMA", "PREFIJO_BASE"])
    )
    rep.to_csv(os.path.join(base_dir, CONFIG["REPORT_FILE"]), index=False, encoding="utf-8-sig")
    if pendientes:
        pd.DataFrame(pendientes).to_csv(os.path.join(base_dir, CONFIG["REVIEW_FILE"]), index=False, encoding="utf-8-sig")
    if not dups.empty:
        dups.to_csv(os.path.join(base_dir, CONFIG["DUPLICATES_FILE"]), index=False, encoding="utf-8-sig")
    if CONFIG["EXPORT_JSON_METRICS"]:
        metrics = {
            "total_rows": int(len(df)),
            "unique_systems": sorted([x for x in df["SISTEMA PRINCIPAL"].dropna().unique().tolist() if x]),
            "unique_prefixes": sorted([x for x in df["PREFIJO_BASE"].dropna().unique().tolist() if x]),
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
    cols = [
        "CODIGO NEW","CODIGO","DESCRIPCION","CATEGORIA","CATEGORIA_NORM",
        "SISTEMA PRINCIPAL","SUBSISTEMA","COMPONENTE","PREFIJO_BASE",
        "TIPO VEHICULO","OBSERVACION CLASIF","PRECIO SIN IVA","PRECIO SIN IVA RAW"
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    df = df[cols]
    out_path = os.path.join(base_dir, CONFIG["OUTPUT_FILE"])
    df.to_excel(out_path, index=False)
    return out_path

def main():
    log.info("=== Iniciando procesamiento de inventario KAIQI (v2) ===")
    df = load_dataframe()
    log.info(f"Filas cargadas: {len(df)}")
    dups = detect_duplicates(df)
    if not dups.empty:
        log.warning(f"Posibles duplicados por CODIGO: {len(dups)}")
    df = enrich_classification(df)
    df, pendientes = assign_codes(df)
    if pendientes:
        log.warning(f"Filas pendientes de clasificación: {len(pendientes)}")
    export_reports(df, pendientes, dups)
    out = save_output(df)
    log.info(f"✅ Archivo generado: {out}")
    log.info(f"📊 Reporte: {os.path.join(CONFIG['BASE_DIR'], CONFIG['REPORT_FILE'])}")
    if pendientes:
        log.info(f"🟡 Pendientes: {os.path.join(CONFIG['BASE_DIR'], CONFIG['REVIEW_FILE'])}")
    if not dups.empty:
        log.info(f"🔎 Duplicados: {os.path.join(CONFIG['BASE_DIR'], CONFIG['DUPLICATES_FILE'])}")
    if CONFIG["EXPORT_JSON_METRICS"]:
        log.info(f"📈 Métricas JSON: {os.path.join(CONFIG['BASE_DIR'], CONFIG['METRICS_JSON_FILE'])}")
    log.info("=== Proceso completado exitosamente ===")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log.error(f"Error fatal: {e}")
        sys.exit(1)
