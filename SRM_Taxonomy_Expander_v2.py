# ============================================================
#   SRM — TAXONOMY EXPANDER v2 (MÓDULO 1)
#   Configuración, Loaders y Funciones Base
# ============================================================

import os
import json
import pandas as pd
from datetime import datetime

# ------------------------------------------------------------
# COLORES CONSOLA
# ------------------------------------------------------------
class C:
    G = "\033[92m"  # Verde
    Y = "\033[93m"  # Amarillo
    R = "\033[91m"  # Rojo
    B = "\033[94m"  # Azul
    W = "\033[97m"  # Blanco
    E = "\033[0m"   # End / Reset


# ------------------------------------------------------------
# LOGGER
# ------------------------------------------------------------
def log(msg, color="G"):
    c = getattr(C, color, C.G)
    print(f"{c}[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}{C.E}")


# ------------------------------------------------------------
# RUTAS OFICIALES SRM
# ------------------------------------------------------------
BASE = r"C:\SRM_ADSI"
KB = os.path.join(BASE, "03_knowledge_base")
TAXO_DIR = os.path.join(KB, "taxonomia")
LING_DIR = KB
OEM_DIR = os.path.join(KB, "oem")
MODEL_DIR = os.path.join(KB, "modelos")
FIT_DIR = os.path.join(KB, "fitment")

OUT_TAXO_CSV = os.path.join(TAXO_DIR, "Taxonomia_SRM_QK_ADSI_v2.csv")
OUT_TAXO_JSON = os.path.join(TAXO_DIR, "Taxonomia_SRM_QK_ADSI_v2.json")
OUT_REPORT = os.path.join(TAXO_DIR, "taxo_report_v2.json")
OUT_KEYWORDS = os.path.join(TAXO_DIR, "taxo_keywords.json")
OUT_SYNONYMS = os.path.join(TAXO_DIR, "taxo_synonyms.json")
OUT_PATTERNS = os.path.join(TAXO_DIR, "taxo_patterns.json")

os.makedirs(TAXO_DIR, exist_ok=True)


# ------------------------------------------------------------
# CARGADORES UNIVERSALES
# ------------------------------------------------------------
def load_csv(path):
    if not os.path.exists(path):
        log(f"[ERROR] No se encontró el archivo CSV: {path}", "R")
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, dtype=str, encoding="utf-8", errors="ignore")
        df = df.fillna("").astype(str)
        log(f"[OK] CSV cargado → {path}", "G")
        return df
    except Exception as e:
        log(f"[ERROR] Fallo al leer CSV {path}: {e}", "R")
        return pd.DataFrame()


def load_json(path):
    if not os.path.exists(path):
        log(f"[ERROR] No se encontró el archivo JSON: {path}", "R")
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        log(f"[OK] JSON cargado → {path}", "G")
        return data
    except Exception as e:
        log(f"[ERROR] Fallo leyendo JSON {path}: {e}", "R")
        return {}


def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log(f"[OK] JSON guardado → {path}", "G")
    except Exception as e:
        log(f"[ERROR] No se pudo guardar JSON {path}: {e}", "R")


def save_csv(path, df):
    try:
        df.to_csv(path, index=False, encoding="utf-8")
        log(f"[OK] CSV generado → {path}", "G")
    except Exception as e:
        log(f"[ERROR] No se pudo guardar CSV {path}: {e}", "R")


# ------------------------------------------------------------
# UTILIDADES BASE
# ------------------------------------------------------------
def sanitize_text(t):
    """Limpia texto técnico para procesamiento semántico."""
    if not isinstance(t, str):
        return ""
    t = t.lower()
    t = t.replace("–", "-")
    t = t.replace("_", " ").replace("/", " ").replace("|", " ")
    while "  " in t:
        t = t.replace("  ", " ")
    return t.strip()


def ensure_columns(df, cols):
    """Garantiza que existan columnas requeridas."""
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    return df


def detect_main_keyword(row, candidates):
    """Detecta automáticamente columna de keyword."""
    for c in candidates:
        if c in row.index:
            return row[c]
    return ""


# ------------------------------------------------------------
# VALIDACIÓN PREVIA
# ------------------------------------------------------------
def load_inputs():
    log("Validando archivos de entrada SRM Taxonomy Expander...", "B")

    taxo_base = load_csv(os.path.join(TAXO_DIR, "Taxonomia_SRM_QK_ADSI_v1.csv"))
    vocab = load_json(os.path.join(KB, "vocabulario_srm.json"))
    empirico = load_json(os.path.join(KB, "terminologia_empirica.json"))
    sinonimos = load_json(os.path.join(KB, "mapa_sinonimos.json"))
    estructura = load_json(os.path.join(KB, "estructura_mecanica.json"))
    modelos = load_csv(os.path.join(MODEL_DIR, "modelos_srm_v3.csv"))
    oem = load_csv(os.path.join(OEM_DIR, "oem_cross_reference_v1.csv"))
    fit = load_csv(os.path.join(FIT_DIR, "fitment_srm_v3.csv"))

    if taxo_base.empty:
        raise Exception("❌ La taxonomía base SRM v1 está vacía o no existe.")

    log("✓ Validación completada.", "G")

    return {
        "taxo": taxo_base,
        "vocab": vocab,
        "empirico": empirico,
        "sinonimos": sinonimos,
        "estructura": estructura,
        "modelos": modelos,
        "oem": oem,
        "fit": fit,
    }


# ------------------------------------------------------------
# HEADER MÓDULO 1 FINALIZADO
# ------------------------------------------------------------
log("=== MÓDULO 1/6 — Configuración y Loaders cargados correctamente ===", "B")
# ============================================================
#   SRM — TAXONOMY EXPANDER v2 (MÓDULO 2)
#   Motor Lingüístico SRM PRO
# ============================================================

import re

# ------------------------------------------------------------
# TOKENIZADOR TÉCNICO
# ------------------------------------------------------------
def tokenize(text):
    """Tokenizador avanzado para términos técnicos SRM."""
    if not isinstance(text, str):
        return []

    text = sanitize_text(text)

    # Separar por espacios y símbolos mecánicos
    tokens = re.split(r"[ \-\.,;:/]+", text)

    # Eliminar vacíos y duplicados
    tokens = [t.strip() for t in tokens if t.strip()]

    return list(dict.fromkeys(tokens))


# ------------------------------------------------------------
# EXPANSIÓN SEMÁNTICA (SINÓNIMOS)
# ------------------------------------------------------------
def expand_synonyms(tokens, sinonimos):
    """Expande tokens con sinónimos técnicos SRM."""
    expanded = set(tokens)

    for t in tokens:
        if t in sinonimos:
            for s in sinonimos[t]:
                expanded.add(s.lower())

    return list(expanded)


# ------------------------------------------------------------
# EXPANSIÓN EMPÍRICA
# ------------------------------------------------------------
def expand_empirical(tokens, empirico):
    """Integra lenguaje real usado por talleres, mecánicos y clientes."""
    expanded = set(tokens)

    for t in tokens:
        if t in empirico:
            for alt in empirico[t]:
                expanded.add(alt.lower())

    return list(expanded)


# ------------------------------------------------------------
# INTEGRACIÓN ESTRUCTURAL
# ------------------------------------------------------------
def expand_structural(row, estructura):
    """
    Usa la estructura mecánica (sistema, subsistema, componente)
    para generar tokens adicionales.
    """
    structural_tokens = []

    for field in ["sistema", "sub_sistema", "categoria", "componente"]:
        if field in row and isinstance(row[field], str):
            t = sanitize_text(row[field])
            if t:
                structural_tokens.extend(tokenize(t))

    # Tokens basados en jerarquía mecánica
    mec_group = []

    if "sistema" in row:
        mec_group.append(row["sistema"].lower())

    if "sub_sistema" in row:
        mec_group.append(row["sub_sistema"].lower())

    if "categoria" in row:
        mec_group.append(row["categoria"].lower())

    if "componente" in row:
        mec_group.append(row["componente"].lower())

    # Expandir con mapeo estructural si existe
    for key in mec_group:
        if key in estructura:
            structural_tokens.extend(estructura[key])

    return list(dict.fromkeys(structural_tokens))


# ------------------------------------------------------------
# INGENIERÍA TEXTUAL: COMBINACIÓN DE TOKENS
# ------------------------------------------------------------
def engineering_tokens(tokens):
    """Genera tokens compuestos y variantes técnicas."""
    combos = set(tokens)

    # combinaciones de 2
    for i in range(len(tokens)):
        for j in range(i + 1, len(tokens)):
            combo = f"{tokens[i]} {tokens[j]}".strip()
            combos.add(combo)

    # variantes unidas
    for t in tokens:
        combos.add(t.replace(" ", ""))

    return list(combos)


# ------------------------------------------------------------
# PROCESADOR SEMÁNTICO COMPLETO
# ------------------------------------------------------------
def process_row_linguistics(row, vocab, empirico, sinonimos, estructura):
    """
    Fusiona todas las capas lingüísticas para generar
    un conjunto semántico avanzado para cada fila taxonómica.
    """
    base_text = ""

    for col in ["categoria", "sistema", "sub_sistema", "componente"]:
        if col in row:
            base_text += f" {row[col]}"

    tokens = tokenize(base_text)

    # 1) Expansión técnica
    tokens = expand_synonyms(tokens, sinonimos)

    # 2) Lenguaje empírico
    tokens = expand_empirical(tokens, empirico)

    # 3) Estructura mecánica
    tokens.extend(expand_structural(row, estructura))

    # 4) Ingeniería textual
    tokens = engineering_tokens(tokens)

    # 5) Integración con vocabulario SRM oficial
    tokens.extend(vocab.keys())

    tokens = [sanitize_text(t) for t in tokens if t.strip()]
    tokens = list(dict.fromkeys(tokens))

    return tokens


# ------------------------------------------------------------
# HEADER MÓDULO 2 FINALIZADO
# ------------------------------------------------------------
log("=== MÓDULO 2/6 — Motor Lingüístico SRM PRO cargado ===", "B")
# ============================================================
#   SRM — TAXONOMY EXPANDER v2 (MÓDULO 3)
#   Generación de Keywords + Patrones Técnicos
# ============================================================

import math


# ------------------------------------------------------------
# DETECTOR AUTOMÁTICO DE KEYWORD PRINCIPAL
# ------------------------------------------------------------
def choose_main_keyword(tokens):
    """
    Selecciona la palabra clave principal basada en:
    - frecuencia mecánica
    - relevancia técnica (longitud, estructura)
    - tokens sinónimos empíricos
    - ausencia de palabras muy genéricas
    """
    if not tokens:
        return ""

    # palabras demasiado genéricas que NO deben ser keyword principal
    blacklist = ["de", "para", "del", "la", "el", "y", "con", "por", "sin"]

    candidates = [t for t in tokens if t not in blacklist and len(t) > 2]

    if not candidates:
        return tokens[0]

    # el token más largo suele ser el término mecánico más descriptivo
    longest = max(candidates, key=len)

    return longest


# ------------------------------------------------------------
# GENERACIÓN DE KEYWORDS SECUNDARIOS
# ------------------------------------------------------------
def generate_secondary_keywords(tokens, main_kw):
    """Retorna tokens secundarios relevantes."""
    return [t for t in tokens if t != main_kw and len(t) > 2][:12]


# ------------------------------------------------------------
# GENERACIÓN DE PATRONES TÉCNICOS
# ------------------------------------------------------------
def generate_patterns(tokens):
    """
    Genera patrones mecánicos SRM:
    - tokens unidos
    - combinaciones
    - formas abreviadas
    """
    patterns = set()

    for t in tokens:
        patterns.add(t)
        patterns.add(t.replace(" ", ""))
        patterns.add(t.replace(" ", "-"))

    # combinaciones de dos tokens clave
    for i in range(len(tokens)):
        for j in range(i + 1, len(tokens)):
            combo = f"{tokens[i]} {tokens[j]}"
            patterns.add(combo)
            patterns.add(combo.replace(" ", "-"))

    return list(patterns)


# ------------------------------------------------------------
# PATRONES EMPÍRICOS (SRM TALLER)
# ------------------------------------------------------------
def generate_empirical_patterns(tokens, empirico):
    emp = set()

    for t in tokens:
        if t in empirico:
            for alt in empirico[t]:
                emp.add(alt.lower())
                emp.add(alt.replace(" ", ""))

    return list(emp)


# ------------------------------------------------------------
# PESO SEMÁNTICO SRM
# ------------------------------------------------------------
def compute_semantic_weight(main_kw, tokens):
    """
    Asigna un peso de relevancia:
    - Longitud del keyword principal
    - Cantidad de tokens técnicos
    - Presencia de términos estructurales
    """
    if not main_kw:
        return 0.1

    weight = len(main_kw) / 10

    weight += min(len(tokens) / 20, 1.0)

    # Palabras claves muy técnicas aumentan peso
    technical_words = ["sensor", "carburador", "embrague", "bujía", "cilindro", "torque", "cojinete"]
    if any(t in tokens for t in technical_words):
        weight += 0.5

    return round(min(weight, 2.0), 3)


# ------------------------------------------------------------
# PROCESO COMPLETO DE GENERACIÓN DE KEYWORDS
# ------------------------------------------------------------
def generate_keywords_for_row(row, vocab, empirico, sinonimos, estructura):
    """
    Combina:
    - tokenización técnica
    - sinónimos
    - empírico
    - estructura mecánica
    - ingeniería textual
    Y produce:
    - keyword principal
    - secundarios
    - patrones
    - pesos
    """

    tokens = process_row_linguistics(row, vocab, empirico, sinonimos, estructura)

    # keyword principal
    main_kw = choose_main_keyword(tokens)

    # keywords secundarios
    secondary = generate_secondary_keywords(tokens, main_kw)

    # patrones técnicos
    patterns = generate_patterns(tokens)

    # patrones empíricos
    empirical = generate_empirical_patterns(tokens, empirico)

    # peso semántico
    weight = compute_semantic_weight(main_kw, tokens)

    return {
        "keyword": main_kw,
        "keywords_sec": secondary,
        "patterns": patterns,
        "patterns_empirical": empirical,
        "weight": weight,
        "tokens_all": tokens
    }


# ------------------------------------------------------------
# HEADER MÓDULO 3 FINALIZADO
# ------------------------------------------------------------
log("=== MÓDULO 3/6 — Keywords & Patrones Técnicos generados ===", "B")
# ============================================================
#   SRM — TAXONOMY EXPANDER v2 (MÓDULO 4)
#   Integración OEM + Modelos SRM + Familias Mecánicas
# ============================================================


# ------------------------------------------------------------
# AGRUPADOR DE MODELOS SRM
# ------------------------------------------------------------
def infer_model_group(modelos_df, row):
    """
    Crea un grupo de modelos SRM basado en:
    - coincidencias semánticas entre tokens de la taxonomía
    - nombres equivalentes en modelos_srm_v3
    """
    if modelos_df.empty:
        return []

    tokens = []
    for col in ["categoria", "sistema", "sub_sistema", "componente"]:
        if col in row:
            tokens.extend(tokenize(str(row[col])))

    tokens = list(set(tokens))

    group = []

    for _, m in modelos_df.iterrows():
        name = sanitize_text(m.get("modelo", ""))
        if any(t in name for t in tokens):
            group.append(name)

    return list(dict.fromkeys(group))


# ------------------------------------------------------------
# AGRUPADOR OEM SRM
# ------------------------------------------------------------
def infer_oem_group(oem_df, row):
    """
    Genera grupo de OEM equivalentes basado en:
    - tokens técnicos
    - coincidencias por categoría/part family
    - equivalencias ya detectadas en OEM engine
    """
    if oem_df.empty:
        return []

    tokens = []
    for col in ["categoria", "sistema", "sub_sistema", "componente"]:
        if col in row:
            tokens.extend(tokenize(str(row[col])))

    tokens = list(set(tokens))

    oem_group = []

    for _, r in oem_df.iterrows():
        desc = sanitize_text(r.get("descripcion", ""))
        if any(t in desc for t in tokens):
            ref = r.get("oem", "")
            if ref:
                oem_group.append(ref)

    return list(dict.fromkeys(oem_group))


# ------------------------------------------------------------
# GENERADOR DE FAMILIA MECÁNICA SRM
# ------------------------------------------------------------
def infer_family(row):
    """
    Construye un identificador de familia mecánica SRM:
    ejemplo: motor_alta_cilindro_guia
    """
    fields = ["sistema", "sub_sistema", "categoria", "componente"]
    parts = []

    for f in fields:
        if f in row and isinstance(row[f], str):
            parts.append(sanitize_text(row[f]).replace(" ", "_"))

    return "_".join(parts).strip("_")


# ------------------------------------------------------------
# GENERADOR DE CLÚSTER TÉCNICO
# ------------------------------------------------------------
def infer_cluster(row, keywords):
    """
    Construye un cluster técnico basado en:
    - keyword principal
    - familia mecánica
    - tokens estructurales
    """
    fam = infer_family(row)
    kw = sanitize_text(keywords.get("keyword", ""))

    if fam and kw:
        return f"{kw}_{fam}"
    elif fam:
        return fam
    else:
        return kw


# ------------------------------------------------------------
# PROCESO COMPLETO DE INTEGRACIÓN OEM + MODELOS + FAMILIAS
# ------------------------------------------------------------
def integrate_external_signals(row, modelos, oem, keywords):
    """
    Genera estructura técnica final que vincula:
    - keyword
    - modelos relacionados
    - OEM relacionados
    - familia mecánica
    - cluster técnico SRM
    """

    model_group = infer_model_group(modelos, row)
    oem_group = infer_oem_group(oem, row)
    family = infer_family(row)
    cluster = infer_cluster(row, keywords)

    return {
        "model_group": model_group,
        "oem_group": oem_group,
        "family": family,
        "cluster": cluster
    }


# ------------------------------------------------------------
# HEADER MÓDULO 4 FINALIZADO
# ------------------------------------------------------------
log("=== MÓDULO 4/6 — Integración OEM + Modelos + Familias completada ===", "B")
# ============================================================
#   SRM — TAXONOMY EXPANDER v2 (MÓDULO 5)
#   Reglas Técnicas + Patrones Semánticos + Matriz SRM
# ============================================================


# ------------------------------------------------------------
# REGLAS BASADAS EN SISTEMAS MECÁNICOS
# ------------------------------------------------------------
def rules_by_system(row):
    """
    Reglas generales basadas en el sistema mecánico:
    - Motor
    - Suspensión
    - Transmisión
    - Frenos
    - Eléctrico
    - Carrocería
    """

    system = sanitize_text(row.get("sistema", ""))

    rules = []

    if system == "motor":
        rules.append("requiere_precision_alta")
        rules.append("compatible_con_rangos_cilindraje")
        rules.append("puede_asociarse_oem")

    elif system == "suspension":
        rules.append("requiere_medida_milimetros")
        rules.append("depende_de_modelo_especifico")

    elif system == "frenos":
        rules.append("requiere_dimension_disco_tambores")
        rules.append("requiere_equivalencia_compuestos")

    elif system == "transmision":
        rules.append("requiere_paso_cadena")
        rules.append("requiere_relacion_corona_pinon")

    elif system == "electrico":
        rules.append("requiere_voltaje_especifico")
        rules.append("depende_de_compatibilidad_conector")

    else:
        rules.append("regla_generica_sistema")

    return rules


# ------------------------------------------------------------
# REGLAS OEM (cuando aplique)
# ------------------------------------------------------------
def rules_by_oem(oem_group):
    rules = []

    if len(oem_group) > 0:
        rules.append("oem_equivalente_detectado")
        if len(oem_group) > 1:
            rules.append("oem_multiple_equivalente")

    return rules


# ------------------------------------------------------------
# REGLAS POR FAMILIA MECÁNICA
# ------------------------------------------------------------
def rules_by_family(family):
    rules = []

    if "cilindro" in family:
        rules.append("requiere_diametro_cilindro")
        rules.append("requiere_altura_ensamble")

    if "embrague" in family:
        rules.append("requiere_numero_discos")
        rules.append("requiere_material_friccion")

    if "amortiguador" in family:
        rules.append("requiere_largo_total_mm")
        rules.append("requiere_tipo_resorte")

    if "bujia" in family:
        rules.append("requiere_calor_termico")
        rules.append("requiere_roscado_especifico")

    return rules


# ------------------------------------------------------------
# REGLAS POR KEYWORD
# ------------------------------------------------------------
def rules_by_keyword(main_kw):
    rules = []

    if any(term in main_kw for term in ["sensor", "switch"]):
        rules.append("requiere_version_electrica")

    if any(term in main_kw for term in ["rodamiento", "cojinete"]):
        rules.append("requiere_medidas_externas")

    if any(term in main_kw for term in ["cadena"]):
        rules.append("requiere_paso_cadena")

    if any(term in main_kw for term in ["carburador"]):
        rules.append("requiere_diametro_venturi")

    if len(main_kw) <= 3:
        rules.append("keyword_demasiado_corto")

    return rules


# ------------------------------------------------------------
# MATRIZ DE CLASIFICACIÓN SRM
# ------------------------------------------------------------
def build_classification_matrix(row, keywords, integration):
    """
    Combina:
    - reglas por sistema
    - reglas OEM
    - reglas familia mecánica
    - reglas keyword
    Y devuelve matriz SRM PRO lista.
    """

    system_rules = rules_by_system(row)
    oem_rules = rules_by_oem(integration.get("oem_group", []))
    family_rules = rules_by_family(integration.get("family", ""))
    keyword_rules = rules_by_keyword(keywords.get("keyword", ""))

    matrix = {
        "rules_system": system_rules,
        "rules_oem": oem_rules,
        "rules_family": family_rules,
        "rules_keyword": keyword_rules,
    }

    # Reglas totales
    total = system_rules + oem_rules + family_rules + keyword_rules
    matrix["rules_all"] = list(dict.fromkeys(total))

    return matrix


# ------------------------------------------------------------
# PROCESO COMPLETO PARA UNA FILA
# ------------------------------------------------------------
def build_full_taxo_row(row, vocab, empirico, sinonimos, estructura, modelos, oem):
    """
    Construye TODA la información expandida:
    - keywords
    - patrones
    - signals OEM
    - signals modelos
    - familia mecánica
    - cluster técnico
    - reglas completas SRM
    """

    # 1) Linguística avanzada
    keywords = generate_keywords_for_row(row, vocab, empirico, sinonimos, estructura)

    # 2) OEM + modelos + familia + cluster
    integration = integrate_external_signals(row, modelos, oem, keywords)

    # 3) Matriz de clasificación SRM
    rules = build_classification_matrix(row, keywords, integration)

    return {
        "keyword": keywords["keyword"],
        "keywords_sec": ", ".join(keywords["keywords_sec"]),
        "patterns": keywords["patterns"],
        "patterns_empirical": keywords["patterns_empirical"],
        "tokens_all": keywords["tokens_all"],
        "model_group": integration["model_group"],
        "oem_group": integration["oem_group"],
        "family": integration["family"],
        "cluster": integration["cluster"],
        "rules": rules["rules_all"],
        "weight": keywords["weight"],
    }


# ------------------------------------------------------------
# HEADER MÓDULO 5 FINALIZADO
# ------------------------------------------------------------
log("=== MÓDULO 5/6 — Reglas y Matriz SRM generadas ===", "B")
# ============================================================
#   SRM — TAXONOMY EXPANDER v2 (MÓDULO 6)
#   Ensamblador Final + Exportadores + Auditoría
# ============================================================


# ------------------------------------------------------------
# ENSAMBLADOR FINAL DE LA TAXONOMÍA EXPANDIDA
# ------------------------------------------------------------
def build_full_taxonomy(inputs):
    taxo = inputs["taxo"]
    vocab = inputs["vocab"]
    empirico = inputs["empirico"]
    sinonimos = inputs["sinonimos"]
    estructura = inputs["estructura"]
    modelos = inputs["modelos"]
    oem = inputs["oem"]

    log("Construyendo taxonomía industrial SRM v2...", "B")

    rows = []
    keywords_dict = {}
    synonyms_dict = {}
    patterns_dict = {}

    for idx, row in taxo.iterrows():

        expanded = build_full_taxo_row(
            row,
            vocab,
            empirico,
            sinonimos,
            estructura,
            modelos,
            oem
        )

        # guardar fila para DataFrame final
        rows.append({
            "categoria": row.get("categoria", ""),
            "sistema": row.get("sistema", ""),
            "sub_sistema": row.get("sub_sistema", ""),
            "componente": row.get("componente", ""),

            "keyword": expanded["keyword"],
            "keywords_sec": expanded["keywords_sec"],
            "patterns": "; ".join(expanded["patterns"]),
            "patterns_empirical": "; ".join(expanded["patterns_empirical"]),
            "tokens_all": "; ".join(expanded["tokens_all"]),

            "model_group": "; ".join(expanded["model_group"]),
            "oem_group": "; ".join(expanded["oem_group"]),
            "family": expanded["family"],
            "cluster": expanded["cluster"],

            "rules": "; ".join(expanded["rules"]),
            "weight": expanded["weight"]
        })

        # diccionarios auxiliares
        kw = expanded["keyword"]
        if kw:
            keywords_dict[kw] = expanded["tokens_all"]
            synonyms_dict[kw] = expanded["patterns_empirical"]
            patterns_dict[kw] = expanded["patterns"]

    df_out = pd.DataFrame(rows)

    return df_out, keywords_dict, synonyms_dict, patterns_dict


# ------------------------------------------------------------
# AUDITORÍA INDUSTRIAL SRM
# ------------------------------------------------------------
def build_taxo_report(df):
    report = {
        "total_items": len(df),
        "unique_keywords": df["keyword"].nunique() if "keyword" in df else 0,
        "unique_families": df["family"].nunique() if "family" in df else 0,
        "unique_clusters": df["cluster"].nunique() if "cluster" in df else 0,
        "avg_weight": float(df["weight"].astype(float).mean()) if "weight" in df else 0,
        "columns": list(df.columns),
        "warnings": []
    }

    # Advertencias típicas
    if df["keyword"].isnull().sum() > 0:
        report["warnings"].append("Existen elementos sin keyword principal.")

    if df["family"].isnull().sum() > 0:
        report["warnings"].append("Existen elementos sin familia mecánica.")

    if df["cluster"].isnull().sum() > 0:
        report["warnings"].append("Existen elementos sin cluster técnico.")

    return report


# ------------------------------------------------------------
# EXPORTADORES
# ------------------------------------------------------------
def export_outputs(df, keywords_dict, synonyms_dict, patterns_dict):

    # CSV industrial
    save_csv(OUT_TAXO_CSV, df)

    # JSON estructurado
    json_data = df.to_dict(orient="records")
    save_json(OUT_TAXO_JSON, json_data)

    # Diccionarios auxiliares
    save_json(OUT_KEYWORDS, keywords_dict)
    save_json(OUT_SYNONYMS, synonyms_dict)
    save_json(OUT_PATTERNS, patterns_dict)

    # Auditoría
    report = build_taxo_report(df)
    save_json(OUT_REPORT, report)


# ------------------------------------------------------------
# PUNTO DE ENTRADA PRINCIPAL
# ------------------------------------------------------------
def run():
    log("=== SRM TAXONOMY EXPANDER v2 — INICIO ===", "B")

    inputs = load_inputs()

    df_out, kw_dict, syn_dict, pat_dict = build_full_taxonomy(inputs)

    export_outputs(df_out, kw_dict, syn_dict, pat_dict)

    log("=== SRM TAXONOMY EXPANDER v2 — COMPLETADO ===", "G")
    log(f"→ CSV Industrial: {OUT_TAXO_CSV}", "G")
    log(f"→ JSON IA:        {OUT_TAXO_JSON}", "G")
    log(f"→ Keywords:        {OUT_KEYWORDS}", "G")
    log(f"→ Synonyms:        {OUT_SYNONYMS}", "G")
    log(f"→ Patterns:        {OUT_PATTERNS}", "G")
    log(f"→ Auditoría:       {OUT_REPORT}", "G")


# ------------------------------------------------------------
# EJECUCIÓN
# ------------------------------------------------------------
if __name__ == "__main__":
    run()
