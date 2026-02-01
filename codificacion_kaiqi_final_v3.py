# -*- coding: utf-8 -*-
"""
codificacion_kaiqi_final_v3.py
--------------------------------------------------
Genera una clasificación maestra unificada (PIM).
Resuelve PEND-000 y asigna CODIGO NEW, SISTEMA, SUBSISTEMA, etc.

Flujo:
1) Carga y normalización de columnas (tolerante a encabezados variantes).
2) Limpieza de texto y unificación de categorías (ALIAS_MAP).
3) Detección de vehículo (Moto / Motocarguero).
4) Asignación de Sistema / Sub-sistema / Componente por palabras clave + categoría.
5) Preservación de secuencia existente en "CODIGO NEW" y asignación secuencial por prefijo.
6) Reportes: validación, pendientes, duplicados, métricas.
7) Exporta Excel final y CSVs auxiliares.

Uso:
    python codificacion_kaiqi_final_v3.py
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
    "EXCEL_FILE": "Inventario Kaiqi.xlsx",  # Usar el archivo principal del usuario
    "SHEET_NAME": "Inventario",           # Asumiendo el nombre de la hoja, o dejar None
    
    "OUTPUT_FILE": "LISTADO_KAIQI_FINAL_CODIFICADO.xlsx",
    "REPORT_FILE": "LISTADO_KAIQI_VALIDACION.csv",
    "REVIEW_FILE": "LISTADO_KAIQI_PENDIENTES_REVISION.csv", # Items que no pudieron ser codificados (debería ser 0)
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
    # Asegura que las barras no tengan espacio al lado antes de normalizar
    s = str(x).upper()
    s = re.sub(r"\s*([/+-])\s*", r"\1", s)
    return re.sub(r"\s+", " ", s).strip()

def norm_header(h):
    """Normaliza nombres de columnas a un formato estable."""
    if h is None: return ""
    h = str(h)
    h = re.sub(r"[\s,;]+", " ", h).strip().upper()
    repl = {
        "CATEGORIA ORIGINAL": "CATEGORIA",
        "CATEGORIA NORM": "CATEGORIA_NORM",
        "SISTEMA PROPUESTO": "SISTEMA PRINCIPAL",
        "PRECIO SIN IVA RAW": "PRECIO SIN IVA RAW",
        "PRECIO": "PRECIO SIN IVA", # Para tomar el precio principal
        "CODIGO NEW": "CODIGO NEW",
    }
    return repl.get(h, h)

def safe_float(x):
    """Convierte a float tolerando formatos locales."""
    try:
        if pd.isna(x) or str(x).strip() == "":
            return math.nan
        s = re.sub(r"[^\d,.\-]", "", str(x))
        if s.count(",") == 1 and s.count(".") == 0: # Si hay coma pero no punto, es separador decimal
            s = s.replace(",", ".")
        s = s.replace(",", "") # Eliminar miles (si usa punto, no hacer nada)
        return float(s)
    except:
        return math.nan

def format_precio(x):
    """Formatea precio como $123.456 (puntos miles) para salida de texto."""
    val = safe_float(x)
    if pd.isna(val):
        return "$ - "
    return f"${int(round(val)):,}".replace(",", ".")

def next_seq(counter, prefix, start_from=1):
    """Genera secuencia incremental por prefijo."""
    if prefix not in counter:
        counter[prefix] = start_from - 1
    counter[prefix] += 1
    return f"{prefix}-{counter[prefix]:03d}"

def parse_existing_seq(df):
    """Detecta secuencias existentes en CODIGO NEW -> retorna {prefijo: max_n}."""
    existing = defaultdict(int)
    if "CODIGO NEW" not in df.columns: return existing
    for val in df["CODIGO NEW"].dropna().astype(str):
        m = re.match(r"^([A-Z0-9\-]+)-(\d{3,})$", val.strip())
        if m:
            pref, num = m.group(1), int(m.group(2))
            existing[pref] = max(existing[pref], num)
    return existing

# ==========================
# Diccionarios maestros (ACTUALIZADOS)
# ==========================

# Alias de categorías: unifica variaciones/typos a una categoría normalizada
ALIAS_MAP = {
    # Novedades y correcciones de tipografía
    "KIT COMPLETO DE EMPAQUES": "KIT EMPAQUES CTO", 
    "BLOQUE COMPLETO": "BLOQUE COMPLETO",
    "CIGÜEÑAL + BALINERA": "CIGÜEÑAL+BALINERA",
    "CHOQUE ELETRICO": "CHOQUE ELECTRICO",
    "CHOQUE ELECTRIC": "CHOQUE ELECTRICO",
    "PASTILLAS DE FRERENO DELANTERAS HLK": "PASTILLAS DE FRENO DELANTERAS HLK",
    "DISCOS DE EMBRAGE": "DISCOS CLUTCH",
    "PRENSA CLUTH CON DISCOS": "PRENSA CLUTCH CON DISCOS",
    "GUAYAS/VARIOS": "GUAYAS / VARIOS",
    "CADENILLAS ": "CADENILLAS",
    # Asegurar unificación
    "PRENSA CLUTCH CON DISCOS": "PRENSA CLUTCH CON DISCOS",
    "KIT VALVULAS": "KIT VALVULAS",
    "PARTES ELETRICAS COMANDOS": "PARTES ELETRICAS COMANDOS",
    # ... (el resto se maneja en mayúsculas)
}

def apply_alias(cat):
    cat = norm_text(cat)
    return ALIAS_MAP.get(cat, cat)

# Prefijos por categoría normalizada (ACTUALIZADOS)
PREFIJOS = {
    "BLOQUE COMPLETO": "MOT-BLO", # NUEVO: Motor Bloque Completo
    "KIT EMPAQUES CTO": "EMP-KIT", # Normalizado
    "CIGÜEÑAL+BALINERA": "MOT-CIG",
    "PASTILLAS DE FRENO DELANTERAS HLK": "FRE-PAS-DEL",
    "DISCOS CLUTCH": "CLU-DIS",
    "PRENSA CLUTCH CON DISCOS": "CLU-PRE",
    "CHOQUE ELECTRICO": "ELE-CHOQ",
    "PIÑON SALIDA": "TRA-PIN-SAL", # Piñón de salida
    
    # Resto de prefijos esenciales
    "ANTIVIBRANTES": "CHA-ANT", "ARBOL LEVAS": "MOT-LEV", "BALANCIN SUPERIOR": "MOT-BAL",
    "BALINERAS ESPECIALES": "TRA-BAL-ESP", "BANDAS FRENO TRASERO": "FRE-BAN-TRAS",
    "BENDIX-ONE WAY": "ARR-BEN", "BOBINA DE ALTA CON CAPUCHON": "ELE-BOB", "BUJIA": "BUJ",
    "CAJA DE CAMBIOS": "TRA-CAM", "CDI": "ELE-CDI", "CRUCETAS CARGUERO": "TRA-CRU",
    "CULATA COMPLETA CON VALVULAS": "MOT-CUL", "GUAYAS / VARIOS": "GUA", "MOTOR ARRANQUE": "ARR-MOT",
    "RADIADOR": "REF-RAD", "REGULADOR TRIFASICO": "ELE-REG-TRI", "VENTILADOR": "REF-VENT",
    "RIN": "RIN", "TREN DELANTERO CARGUERO": "CHA-TREN", "GUAYA CLUTCH": "GUA-CLU",
    "GUAYA ACEL": "GUA-ACE", "GUAYA VEL": "GUA-VEL", "GUAYA FRENO": "GUA-FRE",
    "GUAYA EMERGENCIA": "GUA-EME", "KIT CILINDRO EOM": "MOT-CIL", "FILTRO DE AIRE": "FIL-AIR",
    "ESPEJOS": "CHA-ESP", "KIT VALVULAS": "MOT-VAL", "MANIGUETA CON BASE COMPLETA": "CHA-MANIG",
    "CARBURADORES": "CAR-CAR", "LLAVE GASOLINA": "CAR-LLA", "FILTRO ACEITE": "LUB-FIL",
}

# Reglas: palabras clave para derivar sistema/prefijo (refinamiento)
KEYWORD_RULES = [
    # GUAYAS / VARIOS -> subtipos
    {"category": "GUAYAS / VARIOS", "pattern": r"\bCLUTCH\b|EMBRAG", "prefix": "GUA-CLU", "subsistema": "Guayas", "componente": "Clutch"},
    {"category": "GUAYAS / VARIOS", "pattern": r"\bACEL|ACELERADOR", "prefix": "GUA-ACE", "subsistema": "Guayas", "componente": "Acelerador"},
    {"category": "GUAYAS / VARIOS", "pattern": r"\bVEL|VELOCIM", "prefix": "GUA-VEL", "subsistema": "Guayas", "componente": "Velocímetro"},
    {"category": "GUAYAS / VARIOS", "pattern": r"\bFRENO", "prefix": "GUA-FRE", "subsistema": "Guayas", "componente": "Freno"},
    # Suspensión (mantenida por la lógica de base_system)
]

# Palabras clave para VEHÍCULO
VEHICLE_HINTS = {
    "Moto": [r"\bMOTO\b", r"\bAKT\b", r"\bAGILITY\b", r"\bBWS\b", r"\bPULSAR\b", r"\bFZ\b"],
    "Motocarguero": [r"\bCARGUERO\b", r"\b3W\b", r"\bAYCO\b", r"\bVAISAN(D)?\b", r"\bCERONTE\b", r"\bSIGMA\b"]
}

# ==========================
# Clasificación de Sistema/Subsistema/Componente
# ==========================
def base_system_from_category(cat_norm):
    """Devuelve sistema sugerido a partir de categoría normalizada."""
    if cat_norm in ["BLOQUE COMPLETO", "KIT CILINDRO EOM", "CULATA COMPLETA CON VALVULAS", "CIGÜEÑAL+BALINERA", "ARBOL LEVAS", "CADENILLAS"]:
        return "Motor"
    if cat_norm in ["BANDAS FRENO DELANTERO", "PASTILLAS DE FRENO DELANTERAS HLK", "BOMBA FRENO -CILINDRO FRENO"]:
        return "Frenos"
    if cat_norm in ["CDI", "CHOQUE ELECTRICO", "REGULADOR TRIFASICO", "STATOR -CORONA ENCENDIDO"]:
        return "Eléctrico"
    if cat_norm in ["PIÑON DELANTERO", "CRUCETAS CARGUERO", "CAJA DE CAMBIOS", "PIÑON SALIDA"]:
        return "Transmisión"
    if cat_norm in ["DISCOS CLUTCH", "PRENSA CLUTCH CON DISCOS"]:
        return "Embrague"
    if cat_norm in ["MOTOR ARRANQUE", "BENDIX-ONE WAY"]:
        return "Arranque"
    if cat_norm in ["KIT EMPAQUES CTO", "KIT RETENEDORES"]:
        return "Empaques / Retenedores"
    if cat_norm in ["RADIADOR", "VENTILADOR"]:
        return "Refrigeración"
    if cat_norm in ["FILTRO DE AIRE", "LLAVE GASOLINA", "CARBURADORES"]:
        return "Carburación"
    if cat_norm in ["ANTIVIBRANTES", "RIN", "GUARDA BARRO DELANTERO METALICO"]:
        return "Chasis / Controles"
    return ""

def derive_subsystem_and_component(cat_norm, desc):
    """Deriva subsistema/componente por heurística."""
    d = desc or ""
    
    if cat_norm == "BLOQUE COMPLETO":
        return "Motor Bloque", "Motor Completo"
    if cat_norm in ("KIT CILINDRO EOM", "CULATA COMPLETA CON VALVULAS"):
        return "Top-end", "Cilindro/Culata/Pistón/Anillos"
    if cat_norm in ("CIGÜEÑAL+BALINERA", "EJE CRANK COMPLETO"):
        return "Bottom-end", "Cigüeñal"
    if cat_norm in ("ARBOL LEVAS", "KIT VALVULAS", "CADENILLAS"):
        return "Distribución", "Levas/Valvulas/Balancines"
    if cat_norm in ("PASTILLAS DE FRENO DELANTERAS HLK", "PASTILLAS DE FRENO TRASERAS HLK"):
        return "Freno disco", "Pastillas"
    if cat_norm in ("CRUCETAS CARGUERO", "CAJA DE CAMBIOS", "PIÑON SALIDA"):
        return "Transmisión carguero/Caja", cat_norm.title().replace('-', ' ')
    if cat_norm in ("CHOQUE ELECTRICO", "CDI", "REGULADOR TRIFASICO"):
        return "Control eléctrico", cat_norm.title().replace('-', ' ')
    if cat_norm in ("DISCOS CLUTCH", "PRENSA CLUTCH CON DISCOS"):
        return "Embrague", cat_norm.title().replace('-', ' ')
    if cat_norm in ("KIT EMPAQUES CTO", "KIT RETENEDORES"):
        return "Empaques/Retenedores", cat_norm.title().replace('-', ' ')
    if cat_norm in ("LLAVE GASOLINA", "CARBURADORES", "FILTRO DE AIRE"):
        return "Alimentación/Admisión", cat_norm.title().replace('-', ' ')
    if cat_norm == "MOTOR ARRANQUE":
        return "Sistema de arranque", "Motor Arranque"
        
    return cat_norm.title(), cat_norm.title() # Default (se ajustará manualmente)

def detect_vehicle(desc):
    """Detecta tipo de vehículo por palabras clave en DESCRIPCION."""
    d = norm_text(desc)
    motocarguero_found = re.search(r"\b(CARGUERO|3W|AYCO|VAISAN(D)?|CERONTE|SIGMA|ZOLON|NATSUKY)\b", d)
    moto_found = re.search(r"\b(AKT|AGILITY|BWS|PULSAR|FZ)\b", d)
    
    if motocarguero_found:
        return "Motocarguero"
    if moto_found:
        return "Moto"
    
    return "Moto" # Default a Moto si no hay señal clara

def refine_category_by_keywords(cat_norm, desc):
    """Ajuste fino de categoría por palabras clave."""
    c = cat_norm
    d = norm_text(desc)
    for rule in KEYWORD_RULES:
        if rule.get("force_category") and c == rule["category"] and re.search(rule["pattern"], d, flags=re.IGNORECASE):
            c = rule["force_category"]
    return c

def resolve_prefix(cat_norm, desc):
    """Devuelve PREFIJO_BASE aplicando reglas y diccionario maestro."""
    d = norm_text(desc)
    # Reglas de refinamiento por keywords (Guayas)
    for rule in KEYWORD_RULES:
        if cat_norm == rule.get("category") and re.search(rule["pattern"], d, flags=re.IGNORECASE):
            return rule["prefix"]
    # Directo del diccionario
    return PREFIJOS.get(cat_norm, None)

# ==========================
# Carga y Procesamiento
# ==========================
def load_dataframe(inv_path, sheet_name):
    df = pd.read_excel(inv_path, sheet_name=sheet_name, dtype=str)
    df.columns = [norm_header(c) for c in df.columns]

    # Garantizar columnas que el usuario espera ver completadas
    opt_cols = [
        "CODIGO", "DESCRIPCION", "CATEGORIA", "CODIGO NEW", "CATEGORIA_NORM", 
        "SISTEMA PRINCIPAL", "SUBSISTEMA", "COMPONENTE", "PREFIJO_BASE", 
        "TIPO VEHICULO", "PRECIO SIN IVA", "PRECIO SIN IVA RAW"
    ]
    for col in opt_cols:
        if col not in df.columns:
            df[col] = ""

    # Normalizar valores y aplicar alias de categorías
    df["DESCRIPCION"] = df["DESCRIPCION"].apply(norm_text)
    df["CATEGORIA"] = df["CATEGORIA"].apply(norm_text)
    df["CATEGORIA_NORM"] = df["CATEGORIA"].apply(apply_alias)
    
    # Precio
    df["PRECIO SIN IVA RAW"] = df["PRECIO SIN IVA"].apply(safe_float)
    df["PRECIO SIN IVA"] = df["PRECIO SIN IVA RAW"].apply(format_precio)
    
    # Solo mantener una fila por CODIGO (SKU)
    df = df.drop_duplicates(subset=["CODIGO"], keep="first")
    
    return df

def classify_rows(df):
    
    df["CATEGORIA_REF"] = [refine_category_by_keywords(cat, desc) for cat, desc in zip(df["CATEGORIA_NORM"], df["DESCRIPCION"])]

    df["SISTEMA PRINCIPAL"] = df["CATEGORIA_REF"].apply(base_system_from_category)
    df["TIPO VEHICULO"] = df["DESCRIPCION"].apply(detect_vehicle)
    df["PREFIJO_BASE"] = [resolve_prefix(cat, desc) for cat, desc in zip(df["CATEGORIA_REF"], df["DESCRIPCION"])]

    # SUBSISTEMA / COMPONENTE
    subs, comps = [], []
    for cat, desc in zip(df["CATEGORIA_REF"], df["DESCRIPCION"]):
        sub, comp = derive_subsystem_and_component(cat, desc)
        subs.append(sub)
        comps.append(comp)
    df["SUBSISTEMA"] = subs
    df["COMPONENTE"] = comps
    
    df.drop(columns=["CATEGORIA_REF"], inplace=True)
    return df

def assign_codes(df):
    """Asigna CODIGO NEW, respetando los existentes y reportando PEND-000."""
    existing_seq = parse_existing_seq(df) if CONFIG["PRESERVAR_SECUENCIA_EXISTENTE"] else defaultdict(int)
    counters = defaultdict(int)
    for pref, maxn in existing_seq.items():
        counters[pref] = maxn

    codigos_new, pendientes = [], []

    for i, row in df.iterrows():
        # Preservar código existente si lo hay
        if row.get("CODIGO NEW", "").strip():
            codigos_new.append(row["CODIGO NEW"])
            continue

        pref = row.get("PREFIJO_BASE", "")
        desc = row.get("DESCRIPCION", "")
        
        if not pref:
            # Reportar como pendiente de codificación
            pendientes.append({
                "CODIGO": row.get("CODIGO", ""),
                "DESCRIPCION": desc,
                "CATEGORIA_NORM": row.get("CATEGORIA_NORM", ""),
                "SISTEMA SUGERIDO": row.get("SISTEMA PRINCIPAL", "")
            })
            codigos_new.append("PEND-000")
            continue

        # Asignar nuevo código secuencial
        code = next_seq(counters, pref, start_from=(existing_seq.get(pref, 0) + 1))
        codigos_new.append(code)

    df["CODIGO NEW"] = codigos_new
    return df, pendientes

# ==========================
# Exportadores y Main
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
    pd.DataFrame(pendientes).to_csv(os.path.join(base_dir, CONFIG["REVIEW_FILE"]), index=False, encoding="utf-8-sig")

    # Duplicados (por CODIGO)
    dups.to_csv(os.path.join(base_dir, CONFIG["DUPLICATES_FILE"]), index=False, encoding="utf-8-sig")

    # Métricas JSON
    metrics = {
        "total_rows": int(len(df)),
        "unique_categories_norm": sorted([c for c in df["CATEGORIA_NORM"].dropna().unique().tolist() if c]),
        "unique_prefixes": sorted([p for p in df["PREFIJO_BASE"].dropna().unique().tolist() if p]),
        "pendientes_count": int(len(pendientes)),
        "duplicates_count": int(len(dups)),
        "prefix_counts": {str(k): int(v) for k, v in df["PREFIJO_BASE"].value_counts().to_dict().items()},
    }
    with open(os.path.join(base_dir, CONFIG["METRICS_JSON_FILE"]), "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, ensure_ascii=False, indent=2)

def save_output(df):
    base_dir = CONFIG["BASE_DIR"]
    cols_order = [
        "CODIGO NEW", "CODIGO", "DESCRIPCION", "CATEGORIA", "CATEGORIA_NORM",
        "SISTEMA PRINCIPAL", "SUBSISTEMA", "COMPONENTE", "TIPO VEHICULO",
        "PREFIJO_BASE", "PRECIO SIN IVA", "PRECIO SIN IVA RAW",
    ]
    df = df.reindex(columns=cols_order)
    out_path = os.path.join(base_dir, CONFIG["OUTPUT_FILE"])
    
    # Sobrescribir el archivo de inventario final
    df.to_excel(out_path, index=False)

# ==========================
# MAIN
# ==========================
def main():
    log.info("=== Iniciando procesamiento de inventario KAIQI (v3) ===")

    # 1) Carga
    try:
        inv_path = os.path.join(CONFIG["BASE_DIR"], CONFIG["EXCEL_FILE"])
        df = load_dataframe(inv_path, CONFIG["SHEET_NAME"])
    except FileNotFoundError:
        log.error(f"❌ No se encontró el archivo de entrada: {inv_path}. Por favor, verifique la ruta y el nombre del archivo.")
        sys.exit(1)
    except Exception as e:
        log.error(f"❌ Error al cargar/normalizar el Excel: {e}")
        sys.exit(1)
        
    log.info(f"Filas cargadas: {len(df)}")

    # 2) Duplicados por CODIGO
    dups = df[df["CODIGO"].astype(str).str.strip().duplicated(keep=False)].copy()
    log.info(f"Registros duplicados por CODIGO: {len(dups)}")

    # 3) Clasificar sistema/subsistema/componente y tipo vehículo
    df = classify_rows(df)
    log.info("Clasificación de Sistema, Subsistema y Vehículo completada.")

    # 4) Asignar CODIGO NEW
    df, pendientes = assign_codes(df)
    log.warning(f"Filas pendientes de asignación de prefijo (PEND-000): {len(pendientes)}")

    # 5) Exportar reportes y métricas
    export_reports(df, pendientes, dups)

    # 6) Excel final
    save_output(df)

    log.info(f"✅ Archivo generado: {os.path.join(CONFIG['BASE_DIR'], CONFIG['OUTPUT_FILE'])}")
    log.info(f"📊 Reporte de clasificación: {os.path.join(CONFIG['BASE_DIR'], CONFIG['REPORT_FILE'])}")
    log.info(f"🔎 Reporte de pendientes (PEND-000): {os.path.join(CONFIG['BASE_DIR'], CONFIG['REVIEW_FILE'])}")
    log.info("=== Proceso completado exitosamente ===")

if __name__ == "__main__":
    main()