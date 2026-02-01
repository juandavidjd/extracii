# ================================================================
#   SRM TAXONOMY EXPANDER v2 — INDUSTRIAL EDITION (BLOQUE 1/12)
#   Configuración Global + Logger + Rutas SRM + Utilidades Base
# ================================================================

import os
import json
import pandas as pd
from datetime import datetime

# ---------------------------------------------------------------
# LOG SEGURO (COLORES AUTOMÁTICOS)
# ---------------------------------------------------------------
def log(msg, color="white"):
    colors = {
        "white": "\033[97m",
        "blue": "\033[94m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "red": "\033[91m"
    }
    ts = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    c = colors.get(color, "\033[97m")
    print(f"{c}{ts} {msg}\033[0m")


log("=== SRM TAXONOMY EXPANDER v2 — INICIO ===", "blue")

# ---------------------------------------------------------------
# RUTAS SRM — ESTÁNDAR INDUSTRIAL
# ---------------------------------------------------------------
BASE = r"C:\SRM_ADSI"

PATH_TAXO = os.path.join(BASE, r"03_knowledge_base\taxonomia\Taxonomia_SRM_QK_ADSI_v1.csv")
PATH_MODELOS = os.path.join(BASE, r"03_knowledge_base\modelos\modelos_srm_v3.csv")
PATH_OEM = os.path.join(BASE, r"03_knowledge_base\oem\oem_cross_reference_v1.csv")
PATH_FITMENT = os.path.join(BASE, r"03_knowledge_base\fitment\fitment_srm_v3.csv")
PATH_LEARNING = os.path.join(BASE, r"03_knowledge_base\learning\fitment_learning_memory.json")

PATH_VOCAB = os.path.join(BASE, r"03_knowledge_base\vocabulario_srm.json")
PATH_EMP = os.path.join(BASE, r"03_knowledge_base\terminologia_empirica.json")
PATH_SYN = os.path.join(BASE, r"03_knowledge_base\mapa_sinonimos.json")
PATH_STRUCT = os.path.join(BASE, r"03_knowledge_base\estructura_mecanica.json")

# Salida final
PATH_OUT = os.path.join(BASE, r"03_knowledge_base\taxonomia\taxonomia_expandida_v2.csv")
PATH_META = os.path.join(BASE, r"03_knowledge_base\taxonomia\taxonomia_expandida_metadata.json")
PATH_PATTERNS = os.path.join(BASE, r"03_knowledge_base\taxonomia\global_patterns.json")

# ---------------------------------------------------------------
# VALIDACIÓN INICIAL DE CARPETAS
# ---------------------------------------------------------------
REQUIRED_DIRS = [
    os.path.dirname(PATH_OUT),
    os.path.dirname(PATH_MODELOS),
    os.path.dirname(PATH_OEM),
    os.path.dirname(PATH_FITMENT)
]

for d in REQUIRED_DIRS:
    if not os.path.exists(d):
        os.makedirs(d, exist_ok=True)
        log(f"[CREADO] Directorio faltante: {d}", "yellow")

log("Rutas SRM validadas correctamente.", "green")

# ---------------------------------------------------------------
# CARGADOR SEGURO DE CSV
# ---------------------------------------------------------------
def load_csv(path, name):
    if not os.path.exists(path):
        log(f"[ERROR] No existe archivo {name}: {path}", "red")
        return pd.DataFrame()

    try:
        df = pd.read_csv(path, encoding="utf-8", dtype=str)
        log(f"[OK] {name} cargado → {path}", "green")
        return df
    except Exception as e:
        log(f"[ERROR] Fallo leyendo {name}: {e}", "red")
        return pd.DataFrame()

# ---------------------------------------------------------------
# CARGADOR SEGURO DE JSON
# ---------------------------------------------------------------
def load_json(path, name):
    if not os.path.exists(path):
        log(f"[ERROR] No existe JSON {name}: {path}", "red")
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        log(f"[OK] JSON cargado → {path}", "green")
        return data
    except Exception as e:
        log(f"[ERROR] Fallo JSON {name}: {e}", "red")
        return {}
# ================================================================
#   SRM TAXONOMY EXPANDER v2 — INDUSTRIAL EDITION (BLOQUE 2/12)
#   Loaders SRM: Taxonomía, Modelos, OEM, Fitment, Learning,
#   Motor Lingüístico SRM PRO
# ================================================================

# ---------------------------------------------------------------
# LOADER PRINCIPAL SRM
# ---------------------------------------------------------------
def load_all_inputs():
    log("=== MÓDULO 1/12 — Cargando insumos SRM INDUSTRIALES ===", "blue")

    # ---------------------------
    # 1. Taxonomía SRM Base
    # ---------------------------
    taxo_df = load_csv(PATH_TAXO, "Taxonomía SRM Base")
    if taxo_df.empty:
        raise Exception("❌ ERROR CRÍTICO: La taxonomía SRM base está vacía o no existe.")

    # Normalizar columnas esperadas
    expected_tax_cols = ["categoria", "subcategoria", "sistema", "subsistema", "componente", "keyword"]
    for col in expected_tax_cols:
        if col not in taxo_df.columns:
            taxo_df[col] = ""

    log(f"Taxonomía SRM cargada con {len(taxo_df)} filas.", "green")

    # ---------------------------
    # 2. Modelos SRM v3
    # ---------------------------
    modelos_df = load_csv(PATH_MODELOS, "Modelos SRM v3")
    if modelos_df.empty:
        raise Exception("❌ ERROR CRÍTICO: No se pudieron cargar los modelos SRM v3.")

    # Normalizar columnas
    if "modelo_srm" not in modelos_df.columns:
        modelos_df.rename(columns={modelos_df.columns[0]: "modelo_srm"}, inplace=True)

    if "familia" not in modelos_df.columns:
        modelos_df["familia"] = ""

    log(f"Modelos SRM detectados: {len(modelos_df)}", "green")

    # ---------------------------
    # 3. OEM Cross Reference
    # ---------------------------
    oem_df = load_csv(PATH_OEM, "OEM Cross Reference")
    if oem_df.empty:
        raise Exception("❌ ERROR CRÍTICO: No se pudo cargar OEM Cross Reference.")

    if "oem" not in oem_df.columns:
        oem_df.rename(columns={oem_df.columns[0]: "oem"}, inplace=True)

    log(f"OEM equivalentes detectados: {len(oem_df)}", "green")

    # ---------------------------
    # 4. Fitment SRM v3
    # ---------------------------
    fit_df = load_csv(PATH_FITMENT, "Fitment SRM v3")
    if fit_df.empty:
        raise Exception("❌ ERROR CRÍTICO: No se pudo cargar Fitment SRM v3.")

    # Detectar columna SKU
    sku_col = None
    for c in fit_df.columns:
        if c.lower() in ["sku", "codigo", "id_producto", "srm_sku"]:
            sku_col = c
            break
    if sku_col is None:
        raise Exception("❌ ERROR CRÍTICO: Fitment SRM no contiene columna SKU.")

    fit_df.rename(columns={sku_col: "sku"}, inplace=True)

    # Detectar columna de fitment
    fit_col = None
    for c in fit_df.columns:
        if "fitment" in c.lower():
            fit_col = c
            break
    if fit_col is None:
        fit_df["fitment_clean"] = ""
    else:
        fit_df.rename(columns={fit_col: "fitment_clean"}, inplace=True)

    log(f"Fitment SRM filas: {len(fit_df)}", "green")

    # ---------------------------
    # 5. Learning Engine
    # ---------------------------
    learning = load_json(PATH_LEARNING, "Fitment Learning Memory")
    if not learning:
        learning = {"modelos": {}, "oem": {}, "clusters": {}}
        log("Learning Engine vacío → Se utilizará estructura base.", "yellow")
    else:
        log("Learning Engine cargado correctamente.", "green")

    # ---------------------------
    # 6. Motor Lingüístico SRM PRO
    # ---------------------------
    vocab = load_json(PATH_VOCAB, "Vocabulario Técnico SRM")
    emp = load_json(PATH_EMP, "Terminología Empírica")
    syn = load_json(PATH_SYN, "Mapa de Sinónimos SRM")
    struct = load_json(PATH_STRUCT, "Estructura Mecánica SRM")

    if not vocab or not emp or not syn or not struct:
        raise Exception("❌ ERROR CRÍTICO: Motor lingüístico SRM incompleto.")

    log("Motor Lingüístico SRM PRO cargado correctamente.", "green")

    # ----------------------------------------------------------
    # RETORNO GLOBAL
    # ----------------------------------------------------------
    log("=== MÓDULO 2/12 — Loaders SRM INDUSTRIALES cargados ===", "blue")
    return {
        "taxo": taxo_df,
        "modelos": modelos_df,
        "oem": oem_df,
        "fitment": fit_df,
        "learning": learning,
        "vocab": vocab,
        "emp": emp,
        "syn": syn,
        "struct": struct
    }
# ================================================================
#   SRM TAXONOMY EXPANDER v2 — BLOQUE 3/12
#   Normalización lingüística SRM + Expansor técnico industrial
# ================================================================

import re
import unicodedata
from collections import defaultdict

# ---------------------------------------------------------------
# UTILIDAD CENTRAL: NORMALIZAR TEXTO
# ---------------------------------------------------------------
def normalize_text(text: str) -> str:
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)

    # Bajar a minúsculas
    text = text.lower().strip()

    # Quitar acentos
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()

    # Caracteres permitidos
    text = re.sub(r"[^a-z0-9\s\-\_/\.]", " ", text)

    # Normalizar espacios
    text = re.sub(r"\s+", " ", text).strip()

    return text


# ---------------------------------------------------------------
# Sinónimos SRM (cliente → SRM → lenguaje técnico)
# ---------------------------------------------------------------
def apply_synonyms(text: str, syn_map: dict) -> str:
    if not syn_map:
        return text
    out = text
    for canonical, variations in syn_map.items():
        for v in variations:
            out = re.sub(rf"\b{re.escape(v)}\b", canonical, out)
    return out


# ---------------------------------------------------------------
# Vocabulario técnico SRM (términos expertos)
# ---------------------------------------------------------------
def apply_vocab(text: str, vocab: dict) -> str:
    if not vocab:
        return text
    out = text
    for term, canonical in vocab.items():
        out = re.sub(rf"\b{re.escape(term)}\b", canonical, out)
    return out


# ---------------------------------------------------------------
# Terminología empírica (lenguaje real de mecánicos)
# ---------------------------------------------------------------
def apply_empiric(text: str, empiric_dict: dict) -> str:
    if not empiric_dict:
        return text
    out = text
    for canonical, words in empiric_dict.items():
        for w in words:
            out = re.sub(rf"\b{re.escape(w)}\b", canonical, out)
    return out


# ---------------------------------------------------------------
# PIPELINE LINGÜÍSTICO COMPLETO — SRM v28 INDUSTRIAL
# ---------------------------------------------------------------
def linguistic_pipeline(text: str, syns, vocab, empiric):
    # Normalizar base
    t = normalize_text(text)

    # Aplicar sinónimos cliente → SRM
    t = apply_synonyms(t, syns)

    # Aplicar lenguaje empírico
    t = apply_empiric(t, empiric)

    # Aplicar vocabulario técnico SRM
    t = apply_vocab(t, vocab)

    # Normalizar final
    return normalize_text(t)


# ======================================================================
#      GENERADOR DE PATRONES TÉCNICOS INDUSTRIALES SRM v2
# ======================================================================
def generate_patterns(ling_terms, modelos_df, oem_df, struct):
    patterns = defaultdict(list)

    # -----------------------------------------------------------
    # 1. Componentes mecánicos (enciclopedia + estructura)
    # -----------------------------------------------------------
    for c in struct.get("componentes", []):
        cc = normalize_text(c)
        if len(cc) > 2:
            patterns["componente"].append(cc)

    # -----------------------------------------------------------
    # 2. Sistemas principales
    # -----------------------------------------------------------
    for s in struct.get("sistemas", []):
        ss = normalize_text(s)
        if len(ss) > 2:
            patterns["sistema"].append(ss)

    # -----------------------------------------------------------
    # 3. Subsistemas
    # -----------------------------------------------------------
    for sub in struct.get("subsistemas", []):
        sb = normalize_text(sub)
        if len(sb) > 2:
            patterns["subsistema"].append(sb)

    # -----------------------------------------------------------
    # 4. Palabras núcleo SRM (términos técnicos industriales)
    # -----------------------------------------------------------
    for t in ling_terms:
        nt = normalize_text(t)
        if len(nt) > 2:
            patterns["termino"].append(nt)

    # -----------------------------------------------------------
    # 5. OEM patterns
    # -----------------------------------------------------------
    if "oem" in oem_df.columns:
        for o in oem_df["oem"].astype(str):
            oo = normalize_text(o)
            if len(oo) > 2:
                patterns["oem"].append(oo)

    # -----------------------------------------------------------
    # 6. Modelos SRM (v3)
    # -----------------------------------------------------------
    modelos = modelos_df["modelo_srm"].astype(str).unique()
    for m in modelos:
        mm = normalize_text(m)
        if len(mm) > 2:
            patterns["modelo"].append(mm)

    # Extraer cilindradas → "125cc", "200cc"
    for m in modelos:
        raw = normalize_text(m)
        cc_matches = re.findall(r"\b\d{2,4}cc\b", raw)
        for c in cc_matches:
            patterns["cilindrada"].append(c)

    # Años → "2008", "2015"
    for m in modelos:
        raw = normalize_text(m)
        yr_matches = re.findall(r"\b(19|20)\d{2}\b", raw)
        for y in yr_matches:
            patterns["anio"].append(y)

    # -----------------------------------------------------------
    # 7. Familias SRM
    # -----------------------------------------------------------
    if "familia" in modelos_df.columns:
        for fam in modelos_df["familia"].dropna().astype(str).unique():
            ff = normalize_text(fam)
            if len(ff) > 2:
                patterns["familia"].append(ff)

    # -----------------------------------------------------------
    # 8. Palabras industriales por estructura mecánica
    # -----------------------------------------------------------
    for block, values in struct.items():
        if isinstance(values, list):
            for v in values:
                patterns["estructura"].append(normalize_text(v))

    # -----------------------------------------------------------
    # 9. Léxico industrial general del catálogo
    # -----------------------------------------------------------
    patterns["lexico_catalogo"] = [
        "kit", "juego", "conjunto", "brazo", "caja", "base", "disco", "tapa",
        "eje", "cople", "aro", "cubierta", "tensor", "barra", "guia"
    ]

    # -----------------------------------------------------------
    # 10. Compatibilidad universal típica
    # -----------------------------------------------------------
    patterns["general"] = [
        "compatible con",
        "equivalente",
        "universal",
        "delantero",
        "trasero",
        "izquierdo",
        "derecho",
        "superior",
        "inferior"
    ]

    log("=== MÓDULO 3/12 — Patrones técnicos industriales generados ===", "blue")
    return dict(patterns)
# ================================================================
#   SRM TAXONOMY EXPANDER v2 — BLOQUE 4/12
#   Clasificador Técnico Industrial SRM PRO v28
# ================================================================

# ---------------------------------------------------------------
# COINCIDENCIA POR PATRONES (lingüístico + técnico + industrial)
# ---------------------------------------------------------------
def match_patterns(text: str, patterns: dict):
    scores = defaultdict(int)
    matched = defaultdict(list)

    for category, plist in patterns.items():
        for p in plist:
            if p in text:
                scores[category] += 1
                matched[category].append(p)

    return scores, matched


# ---------------------------------------------------------------
# COINCIDENCIA POR OEM
# ---------------------------------------------------------------
def match_oem(text: str, oem_df):
    oem_found = []
    for o in oem_df["oem"].astype(str):
        oo = normalize_text(o)
        if len(oo) > 1 and oo in text:
            oem_found.append(o)
    return oem_found


# ---------------------------------------------------------------
# COINCIDENCIA POR MODELOS SRM
# ---------------------------------------------------------------
def match_models(text: str, modelos_df):
    models_found = []

    modelos = modelos_df["modelo_srm"].astype(str).unique()
    for m in modelos:
        mm = normalize_text(m)
        if mm in text and len(mm) > 2:
            models_found.append(m)

    return models_found


# ---------------------------------------------------------------
# COINCIDENCIA POR FAMILIA
# ---------------------------------------------------------------
def match_families(text: str, modelos_df):
    families = []
    if "familia" not in modelos_df.columns:
        return families

    fams = modelos_df["familia"].dropna().astype(str).unique()
    for f in fams:
        ff = normalize_text(f)
        if ff in text:
            families.append(f)

    return families


# ---------------------------------------------------------------
# COINCIDENCIA POR ESTRUCTURA MECÁNICA SRM
# ---------------------------------------------------------------
def match_mechanical_structure(text: str, struct):
    hits = []
    for key, values in struct.items():
        if isinstance(values, list):
            for v in values:
                vv = normalize_text(v)
                if vv in text:
                    hits.append(v)
    return hits


# ---------------------------------------------------------------
# SISTEMA DE PUNTUACIÓN INDUSTRIAL SRM PRO
# ---------------------------------------------------------------
def compute_score(scores, models, oem, fams, mech):
    score = 0

    # Patrones técnicos
    for cat, val in scores.items():
        score += val * 2     # cada patrón técnico vale doble

    # Modelos
    score += len(models) * 4  # modelo detectado vale mucho más

    # OEM
    score += len(oem) * 3

    # Familias
    score += len(fams) * 2

    # Estructura mecánica
    score += len(mech) * 2

    return score


# ---------------------------------------------------------------
# CLASIFICADOR TAXONÓMICO INDUSTRIAL SRM PRO
# ---------------------------------------------------------------
def classify_item(text, taxo_df, patterns, modelos_df, oem_df, struct):

    desc = normalize_text(text)

    # 1. Patrones técnicos
    scores, hits = match_patterns(desc, patterns)

    # 2. OEM
    oem_found = match_oem(desc, oem_df)

    # 3. Modelos SRM
    models_found = match_models(desc, modelos_df)

    # 4. Familias SRM
    families_found = match_families(desc, modelos_df)

    # 5. Estructura mecánica
    mech_found = match_mechanical_structure(desc, struct)

    # 6. Puntuación industrial
    score = compute_score(scores, models_found, oem_found, families_found, mech_found)

    # 7. Determinar entrada mejor ajustada en la taxonomía base
    best_row = None
    best_hits = -1

    for idx, row in taxo_df.iterrows():
        row_kw = normalize_text(str(row["keyword"]))
        if row_kw and row_kw in desc:
            # Cuenta coincidencias fuertes
            local_hits = desc.count(row_kw)
            if local_hits > best_hits:
                best_hits = local_hits
                best_row = row

    # Si no hubo coincidencias con taxonomía base → fallback inteligente
    if best_row is None:
        return {
            "categoria": "otros",
            "subcategoria": "",
            "sistema": "",
            "subsistema": "",
            "componente": "",
            "score": score,
            "models": models_found,
            "oem": oem_found,
            "familias": families_found,
            "estructura": mech_found,
            "patterns_hits": hits
        }

    # Si encontró entrada taxonómica
    return {
        "categoria": best_row["categoria"],
        "subcategoria": best_row["subcategoria"],
        "sistema": best_row["sistema"],
        "subsistema": best_row["subsistema"],
        "componente": best_row["componente"],
        "score": score,
        "models": models_found,
        "oem": oem_found,
        "familias": families_found,
        "estructura": mech_found,
        "patterns_hits": hits
    }
# ================================================================
#   SRM TAXONOMY EXPANDER v2 — BLOQUE 5/12
#   Motor de Clasificación Masiva Industrial SRM v28
# ================================================================

def classify_catalog(df_catalogo, taxo, patterns, modelos_df, oem_df, struct, syns, vocab, emp):
    log("=== MÓDULO 9/12 — Motor de Clasificación Masiva SRM ===", "blue")

    # Columnas obligatorias
    COLUMNAS_VALIDAS = ["descripcion", "producto", "detalle", "nombre"]

    desc_col = None
    for c in df_catalogo.columns:
        if c.lower() in COLUMNAS_VALIDAS:
            desc_col = c
            break

    if desc_col is None:
        raise Exception("❌ ERROR: No existe columna de descripción en el catálogo.")

    # Preparamos listas para salida
    categorias = []
    subcategorias = []
    sistemas = []
    subsistemas = []
    componentes = []
    scores = []
    modelos_out = []
    oem_out = []
    familias_out = []
    estructura_out = []
    patrones_out = []
    descripcion_normalizada = []

    # Procesamiento fila por fila
    total = len(df_catalogo)
    log(f"Catálogo cargado: {total} registros.", "green")

    for idx, row in df_catalogo.iterrows():
        raw_desc = str(row[desc_col])

        # ------------------------------------------
        # 1. Normalización lingüística SRM PRO
        # ------------------------------------------
        desc_norm = linguistic_pipeline(raw_desc, syns, vocab, emp)
        descripcion_normalizada.append(desc_norm)

        # ------------------------------------------
        # 2. Clasificador técnico
        # ------------------------------------------
        result = classify_item(
            desc_norm,
            taxo,
            patterns,
            modelos_df,
            oem_df,
            struct
        )

        # Guardar campos resultantes
        categorias.append(result["categoria"])
        subcategorias.append(result["subcategoria"])
        sistemas.append(result["sistema"])
        subsistemas.append(result["subsistema"])
        componentes.append(result["componente"])

        scores.append(result["score"])
        modelos_out.append(";".join(result["models"]) if result["models"] else "")
        oem_out.append(";".join(result["oem"]) if result["oem"] else "")
        familias_out.append(";".join(result["familias"]) if result["familias"] else "")
        estructura_out.append(";".join(result["estructura"]) if result["estructura"] else "")

        # Patrones activados → lista de listas → texto
        patrones_str = []
        for cat, vals in result["patterns_hits"].items():
            if vals:
                patrones_str.append(f"{cat}:{','.join(vals)}")
        patrones_out.append(";".join(patrones_str))

        # Log de avance cada 2000 registros
        if idx % 2000 == 0 and idx > 0:
            log(f"Procesados {idx}/{total} items...", "yellow")

    # Construcción del DataFrame de salida
    df_out = df_catalogo.copy()
    df_out["descripcion_normalizada"] = descripcion_normalizada
    df_out["categoria"] = categorias
    df_out["subcategoria"] = subcategorias
    df_out["sistema"] = sistemas
    df_out["subsistema"] = subsistemas
    df_out["componente"] = componentes
    df_out["score_srm"] = scores
    df_out["modelos_detectados"] = modelos_out
    df_out["oem_detectados"] = oem_out
    df_out["familias_detectadas"] = familias_out
    df_out["estructura_detectada"] = estructura_out
    df_out["patrones_activados"] = patrones_out

    log("Clasificación masiva completada.", "green")
    return df_out
# ================================================================
#   SRM TAXONOMY EXPANDER v2 — BLOQUE 6/12
#   Integración Final + Exportadores + Metadata SRM
# ================================================================

def export_results(df_final, patterns):
    log("=== MÓDULO 10/12 — Exportadores Industriales SRM ===", "blue")

    # 1. Guardar Taxonomía Expandida
    try:
        df_final.to_csv(PATH_OUT, index=False, encoding="utf-8")
        log(f"✔ Taxonomía Expandida v2 guardada → {PATH_OUT}", "green")
    except Exception as e:
        log(f"❌ ERROR guardando taxonomía expandida: {e}", "red")

    # 2. Guardar Patrones Industriales
    try:
        with open(PATH_PATTERNS, "w", encoding="utf-8") as f:
            json.dump(patterns, f, indent=4, ensure_ascii=False)
        log(f"✔ Patrones industriales guardados → {PATH_PATTERNS}", "green")
    except Exception as e:
        log(f"❌ ERROR guardando patrones industriales: {e}", "red")

    # 3. Metadata Industrial SRM
    metadata = {
        "registros_totales": len(df_final),
        "columnas_generadas": list(df_final.columns),
        "timestamp": datetime.now().isoformat(),
        "fuente_taxonomia": PATH_TAXO,
        "fuente_modelos": PATH_MODELOS,
        "fuente_oem": PATH_OEM,
        "fuente_fitment": PATH_FITMENT,
        "motor_version": "SRM Taxonomy Expander v2 - Industrial"
    }

    try:
        with open(PATH_META, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4, ensure_ascii=False)
        log(f"✔ Metadata industrial guardada → {PATH_META}", "green")
    except Exception as e:
        log(f"❌ ERROR guardando metadata: {e}", "red")

    log("Exportación completada.", "green")


# ================================================================
#   MÓDULO CENTRAL — EJECUCIÓN COMPLETA DEL EXPANSOR
# ================================================================
def run():
    log("=== MÓDULO 11/12 — Ensamblando SRM Taxonomy Expander Industrial ===", "blue")

    # ------------------------------------------------------------
    # 1. Cargar insumos SRM
    # ------------------------------------------------------------
    inputs = load_all_inputs()

    taxo = inputs["taxo"]
    modelos = inputs["modelos"]
    oem = inputs["oem"]
    fitment = inputs["fitment"]
    learning = inputs["learning"]
    vocab = inputs["vocab"]
    emp = inputs["emp"]
    syn = inputs["syn"]
    struct = inputs["struct"]

    # ------------------------------------------------------------
    # 2. Generar patrones técnicos industriales
    # ------------------------------------------------------------
    ling_terms = list(vocab.keys()) + list(emp.keys()) + list(syn.keys())
    patterns = generate_patterns(ling_terms, modelos, oem, struct)

    # ------------------------------------------------------------
    # 3. Preparar catálogo unificado para clasificación
    # ------------------------------------------------------------
    catalog_path = os.path.join(
        BASE,
        r"03_knowledge_base\catalogo\catalogo_unificado_v2.csv"
    )

    if not os.path.exists(catalog_path):
        raise Exception("❌ ERROR: No existe el catálogo unificado SRM v2.")

    df_catalogo = pd.read_csv(catalog_path, dtype=str, encoding="utf-8")

    # ------------------------------------------------------------
    # 4. Clasificación masiva industrial
    # ------------------------------------------------------------
    df_final = classify_catalog(
        df_catalogo,
        taxo,
        patterns,
        modelos,
        oem,
        struct,
        syn,
        vocab,
        emp
    )

    # ------------------------------------------------------------
    # 5. Exportación final
    # ------------------------------------------------------------
    export_results(df_final, patterns)

    # ------------------------------------------------------------
    # 6. Cierre del sistema
    # ------------------------------------------------------------
    log("=== MÓDULO 12/12 — SRM TAXONOMY EXPANDER COMPLETADO ===", "green")


# ==================================================================
#   EJECUCIÓN PRINCIPAL
# ==================================================================
if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        log(f"❌ ERROR CRÍTICO DURANTE LA EJECUCIÓN: {e}", "red")
# ================================================================
#   SRM TAXONOMY EXPANDER v2 — BLOQUE 7/12
#   Validadores Industriales SRM v28
# ================================================================

def validate_columns(df, required_cols, name="DATAFRAME"):
    """Valida que el dataframe contenga las columnas requeridas."""
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise Exception(f"❌ {name} carece de columnas obligatorias: {missing}")
    return True


def sanitize_dataframe(df):
    """Limpieza industrial previa a clasificación."""
    df = df.copy()

    # Remover espacios basura
    df.columns = [c.strip() for c in df.columns]

    # Convertir todo a string
    for col in df.columns:
        df[col] = df[col].astype(str).fillna("")

    # Normalización rápida de texto
    for col in df.columns:
        df[col] = df[col].apply(lambda x: normalize_text(x))

    return df


def validate_taxonomy_structure(df_tax):
    """Valida que la taxonomía tenga los ejes mínimos industriales."""
    required = ["categoria", "subcategoria", "componente", "keyword"]
    validate_columns(df_tax, required, name="TAXONOMÍA SRM")
    log("✔ Validación estructura taxonomía: OK", "green")


def validate_model_structure(df_mod):
    """Validación industrial de modelos SRM."""
    if "modelo_srm" not in df_mod.columns:
        log("⚠ Modelos SRM sin columna modelo_srm: intentando recuperar...", "yellow")

        # fallback industrial
        df_mod["modelo_srm"] = df_mod.iloc[:, 0].astype(str)

    df_mod["modelo_srm"] = df_mod["modelo_srm"].apply(normalize_text)
    log("✔ Validación estructura modelos: OK", "green")
    return df_mod


def validate_oem_structure(df_oem):
    """Validación industrial para OEM."""
    if "oem" not in df_oem.columns:
        col = df_oem.columns[0]
        df_oem["oem"] = df_oem[col]

    df_oem["oem"] = df_oem["oem"].apply(normalize_text)
    log("✔ Validación estructura OEM: OK", "green")
    return df_oem


def validate_fitment_structure(df_fit):
    """Validación industrial para Fitment SRM."""
    if "sku" not in df_fit.columns:
        raise Exception("❌ Fitment SRM no contiene columna SKU.")

    if "fitment_clean" not in df_fit.columns:
        raise Exception("❌ Fitment SRM requiere campo fitment_clean.")

    df_fit["fitment_clean"] = df_fit["fitment_clean"].apply(normalize_text)

    log("✔ Validación estructura Fitment SRM: OK", "green")
    return df_fit


def validate_catalog_input(df):
    """Verifica que el catálogo SRM tenga columnas mínimas antes de expandir."""
    required = ["descripcion", "sku_cliente", "oem_detectado"]
    validate_columns(df, required, name="CATÁLOGO UNIFICADO SRM v2")

    for c in required:
        df[c] = df[c].astype(str).apply(normalize_text)

    log("✔ Validación catálogo SRM unificado: OK", "green")
    return df


# ================================================================
#      MÓDULO INVOCADO DESDE RUN() PARA VALIDACIÓN TOTAL
# ================================================================
def run_validators(taxo, modelos, oem, fitment, df_catalogo):
    log("=== MÓDULO 7/12 — Validadores Industriales SRM ===", "blue")

    validate_taxonomy_structure(taxo)
    modelos = validate_model_structure(modelos)
    oem = validate_oem_structure(oem)
    fitment = validate_fitment_structure(fitment)
    df_catalogo = validate_catalog_input(df_catalogo)

    return taxo, modelos, oem, fitment, df_catalogo
# ================================================================
#   SRM TAXONOMY EXPANDER v2 — BLOQUE 8/12
#   Motor de Clasificación Taxonómica SRM v28
# ================================================================

def match_pattern(text, patterns):
    """Retorna el primer patrón encontrado dentro del texto."""
    for p in patterns:
        if p in text:
            return p
    return ""


def classify_row(desc, patterns, learning_memory):
    """Clasificador industrial SRM basado en patrones + aprendizaje técnico."""

    result = {
        "categoria": "",
        "subcategoria": "",
        "componente": "",
        "sistema": "",
        "subsistema": "",
        "familia": "",
        "tags": [],
        "inferencias": [],
    }

    # ---------------------------------------------------------
    # 1. Normalización lingüística previa
    # ---------------------------------------------------------
    d = normalize_text(desc)

    # ---------------------------------------------------------
    # 2. Detección por patrones SRM
    # ---------------------------------------------------------
    for eje in ["categoria", "subcategoria", "componente",
                "sistema", "subsistema", "familia"]:

        if eje in patterns:
            match = match_pattern(d, patterns[eje])
            if match:
                result[eje] = match

    # ---------------------------------------------------------
    # 3. Tags técnicos
    # ---------------------------------------------------------
    tags_found = []
    for eje, pats in patterns.items():
        for p in pats:
            if p in d:
                tags_found.append(p)
    result["tags"] = list(set(tags_found))

    # ---------------------------------------------------------
    # 4. Aprendizaje SRM (memoria técnica)
    # ---------------------------------------------------------
    for key, learned in learning_memory.items():
        if key in d:
            result["inferencias"].append(learned)

    return result


def apply_classification(df, patterns, learning_memory):
    """
    Clasifica masivamente todo el catálogo SRM.
    Este módulo nunca se detiene aunque un registro falle.
    Se reporta individualmente cada línea fallida.
    """

    classified = {
        "categoria": [],
        "subcategoria": [],
        "componente": [],
        "sistema": [],
        "subsistema": [],
        "familia": [],
        "tags": [],
        "inferencias": [],
    }

    errores = 0

    log("=== MÓDULO 8/12 — Iniciando clasificación industrial SRM ===", "blue")

    for i, row in df.iterrows():
        try:
            desc = str(row.get("descripcion", ""))

            out = classify_row(desc, patterns, learning_memory)

            classified["categoria"].append(out["categoria"])
            classified["subcategoria"].append(out["subcategoria"])
            classified["componente"].append(out["componente"])
            classified["sistema"].append(out["sistema"])
            classified["subsistema"].append(out["subsistema"])
            classified["familia"].append(out["familia"])
            classified["tags"].append(";".join(out["tags"]))
            classified["inferencias"].append(";".join(out["inferencias"]))

        except Exception as e:
            errores += 1
            classified["categoria"].append("")
            classified["subcategoria"].append("")
            classified["componente"].append("")
            classified["sistema"].append("")
            classified["subsistema"].append("")
            classified["familia"].append("")
            classified["tags"].append("")
            classified["inferencias"].append("")
            log(f"[WARN] Fila {i} no pudo ser clasificada: {e}", "yellow")

    log(f"✔ Clasificación SRM completada — Errores detectados: {errores}", 
        "green" if errores == 0 else "yellow")

    return classified
# ================================================================
#   SRM TAXONOMY EXPANDER v2 — BLOQUE 9/12
#   Motor de Integración Técnica SRM (POST-CLASIFICACIÓN)
# ================================================================

def integrate_fitment(row, fitment_dict):
    """Retorna fitment SRM v3 si existe para el SKU o descripción."""
    sku = str(row.get("sku", "")).strip()
    desc = normalize_text(str(row.get("descripcion", "")))

    # Prioridad 1: SKU exacto
    if sku in fitment_dict:
        return fitment_dict[sku]

    # Prioridad 2: Buscar por patrones en descripción
    for k, v in fitment_dict.items():
        if k in desc:
            return v

    return ""


def integrate_oem(row, oem_df):
    """Integra OEM detectados para un producto."""
    desc = normalize_text(str(row.get("descripcion", "")))

    encontrados = []

    for oem in oem_df["oem"].astype(str):
        if oem.lower() in desc:
            encontrados.append(oem)

    return ";".join(sorted(set(encontrados))) if encontrados else ""


def integrate_modelos(row, modelos_df):
    """Integra modelos SRM v3 detectados o inferidos."""
    desc = normalize_text(str(row.get("descripcion", "")))

    modelos = []

    if "modelo_srm" in modelos_df.columns:
        col = "modelo_srm"
    else:
        col = modelos_df.columns[0]

    for m in modelos_df[col].astype(str):
        mm = normalize_text(m)
        if mm in desc:
            modelos.append(m)

    return ";".join(sorted(set(modelos))) if modelos else ""


def integrate_learning(row, learning_memory):
    """Integra inferencias del motor de aprendizaje SRM."""
    desc = normalize_text(str(row.get("descripcion", "")))

    found = []

    for key, learned in learning_memory.items():
        if key in desc:
            found.append(learned)

    return ";".join(found)


def build_srm_signal(row):
    """Crea una señal inteligente SRM: resumen técnico que viaja en todos los módulos."""
    parts = []

    for key in ["categoria", "subcategoria", "componente",
                "sistema", "subsistema", "familia"]:
        val = str(row.get(key, "")).strip()
        if val:
            parts.append(val)

    tags = str(row.get("tags", ""))
    if tags:
        parts.append(tags)

    inferencias = str(row.get("inferencias", ""))
    if inferencias:
        parts.append(inferencias)

    return " | ".join(parts)


def integrate_all(df, patterns, fitment_dict, oem_df, modelos_df, learning_memory):
    """
    Motor de integración industrial SRM.
    Aquí se unifica TODO lo aprendido y detectado.
    """

    log("=== MÓDULO 9/12 — Iniciando integración técnica SRM ===", "blue")

    df["oem_equivalentes"] = df.apply(lambda x: integrate_oem(x, oem_df), axis=1)
    df["modelos_srm"] = df.apply(lambda x: integrate_modelos(x, modelos_df), axis=1)
    df["fitment_srm"] = df.apply(lambda x: integrate_fitment(x, fitment_dict), axis=1)
    df["inferencias_aprendidas"] = df.apply(lambda x: integrate_learning(x, learning_memory), axis=1)

    # Construcción de señal SRM final
    df["srm_signal"] = df.apply(build_srm_signal, axis=1)

    log("✔ Integración técnica completada.", "green")
    return df
# ================================================================
#   SRM TAXONOMY EXPANDER v2 — BLOQUE 10/12
#   Ensamblaje Maestro del Catálogo SRM (OUTPUT BUILDER)
# ================================================================

def assemble_final_catalog(df):
    """
    Ordena, normaliza y estructura el catálogo SRM industrial.
    Este catálogo es el producto oficial del Taxonomy Expander v2.
    """

    log("=== MÓDULO 10/12 — Ensamblaje del Catálogo Maestro SRM ===", "blue")

    # -----------------------------------------------------------
    # ORDEN OFICIAL SRM — BASE INDUSTRIAL
    # -----------------------------------------------------------
    orden_columnas = [
        "sku", "sku_cliente", "sku_srm",
        "descripcion_original", "descripcion_srm",
        "categoria", "subcategoria", "sistema", "subsistema",
        "componente", "familia",
        "oem_equivalentes", "modelos_srm", "fitment_srm",
        "inferencias_aprendidas", "srm_signal",
        "tags", "fuente", "marca", "cliente",
        "precio", "unidad", "estado"
    ]

    # Verifica columnas existentes
    columnas_validas = [c for c in orden_columnas if c in df.columns]

    # Añade columnas faltantes vacías
    for col in orden_columnas:
        if col not in df.columns:
            df[col] = ""

    # Reordena
    df = df[columnas_validas]

    # -----------------------------------------------------------
    # CAMPOS DERIVADOS — Shopify, 360, LOVABLE
    # -----------------------------------------------------------
    df["title_shopify"] = df["descripcion_srm"].apply(lambda x: x.title())
    df["tags_shopify"] = df["srm_signal"]
    df["vendor"] = df["marca"]
    df["product_type"] = df["categoria"]
    df["status"] = "active"

    # -----------------------------------------------------------
    # VARIABLES DE CONTROL SRM
    # -----------------------------------------------------------
    df["srm_hash"] = df.apply(
        lambda x: hash(
            str(x["descripcion_srm"])
            + str(x["srm_signal"])
            + str(x["fitment_srm"])
        ),
        axis=1
    )

    df["srm_version"] = "SRM-TAXO-V2"

    log("✔ Catálogo SRM ensamblado correctamente.", "green")
    return df


def save_final_catalog(df, output_path):
    """Guarda el catálogo final y el reporte técnico asociado."""
    try:
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        log(f"✔ Catálogo SRM guardado → {output_path}", "green")
    except Exception as e:
        log(f"❌ ERROR al guardar catálogo final: {e}", "red")


def export_shopify_ready(df, output_path):
    """Exportación paralela lista para Shopify CSV."""
    shopify_cols = [
        "title_shopify", "descripcion_srm", "vendor",
        "product_type", "tags_shopify", "status",
        "sku_srm", "precio", "unidad"
    ]

    shopify = df[shopify_cols].copy()

    try:
        shopify.to_csv(output_path, index=False, encoding="utf-8-sig")
        log(f"✔ Export Shopify lista → {output_path}", "green")
    except Exception as e:
        log(f"❌ ERROR exportando Shopify: {e}", "red")
# ==================================================================
#   SRM TAXONOMY EXPANDER v2 — BLOQUE 11/12
#   Auditoría Técnica, Validación y Reporte Industrial SRM
# ==================================================================

def audit_catalog(df, patterns, model_dict, oem_df):
    """
    Analiza el catálogo SRM y genera un reporte técnico industrial:
    - Duplicados
    - Descripciones inconsistentes
    - Falta de categoría
    - Fitment vacío
    - OEM sin normalizar
    - Modelos desconocidos
    - Señal SRM débil
    """

    log("=== MÓDULO 11/12 — Auditoría Técnica del Catálogo SRM ===", "blue")

    report = {
        "total_registros": len(df),
        "sin_categoria": 0,
        "sin_componente": 0,
        "sin_fitment": 0,
        "oem_no_normalizado": 0,
        "modelos_no_estandar": 0,
        "descripcion_debil": 0,
        "duplicados_sku_srm": 0,
        "duplicados_descripcion": 0,
        "señal_debil": 0,
        "inconsistencias": []
    }

    # ----------------------------------------------------------
    # Validaciones campo por campo
    # ----------------------------------------------------------

    # 1. Categorías faltantes
    report["sin_categoria"] = df["categoria"].eq("").sum()

    # 2. Componentes faltantes
    report["sin_componente"] = df["componente"].eq("").sum()

    # 3. Fitment vacío
    report["sin_fitment"] = df["fitment_srm"].eq("").sum()

    # 4. OEM sin normalizar
    if "oem" in df.columns:
        known_oem = set(oem_df["oem_normalizado"].astype(str))
        report["oem_no_normalizado"] = df[~df["oem"].isin(known_oem)].shape[0]

    # 5. Modelos fuera del estándar SRM
    valid_models = set(model_dict.keys())
    modelos_invalidos = []

    for _, row in df.iterrows():
        if not row["modelos_srm"]:
            continue
        for m in row["modelos_srm"].split(";"):
            if m not in valid_models:
                modelos_invalidos.append(m)

    report["modelos_no_estandar"] = len(set(modelos_invalidos))

    # 6. Descripciones débiles
    report["descripcion_debil"] = df["descripcion_srm"].apply(lambda x: len(str(x)) < 12).sum()

    # 7. Señal SRM débil
    report["señal_debil"] = df["srm_signal"].apply(lambda x: len(str(x)) < 4).sum()

    # 8. Duplicados en SKU SRM
    if "sku_srm" in df.columns:
        report["duplicados_sku_srm"] = df["sku_srm"].duplicated().sum()

    # 9. Duplicados en descripción SRM
    report["duplicados_descripcion"] = df["descripcion_srm"].duplicated().sum()

    # ----------------------------------------------------------
    # Construcción de inconsistencias detalladas
    # ----------------------------------------------------------
    inconsistencias = []

    for idx, row in df.iterrows():
        issues = []

        if row["categoria"] == "":
            issues.append("Sin categoría")

        if row["componente"] == "":
            issues.append("Sin componente")

        if row["fitment_srm"] == "":
            issues.append("Fitment vacío")

        if len(str(row["descripcion_srm"])) < 12:
            issues.append("Descripción SRM débil")

        if len(str(row["srm_signal"])) < 4:
            issues.append("Señal SRM débil")

        if issues:
            inconsistencias.append({
                "sku_srm": row.get("sku_srm", ""),
                "descripcion_srm": row.get("descripcion_srm", ""),
                "issues": issues
            })

    report["inconsistencias"] = inconsistencias

    log("✔ Auditoría técnica completada.", "green")
    return report


def save_audit_report(report, output_path):
    """Guarda el reporte SRM en JSON."""
    import json
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4, ensure_ascii=False)
        log(f"✔ Reporte técnico SRM guardado → {output_path}", "green")
    except Exception as e:
        log(f"❌ ERROR guardando reporte SRM: {e}", "red")
# ==================================================================
#   SRM TAXONOMY EXPANDER v2 — BLOQUE 12/12
#   MAIN EXECUTION ENGINE — Orquestación completa SRM
# ==================================================================

def run():
    log("=== SRM TAXONOMY EXPANDER v2 — INICIO ===", "blue")

    # --------------------------------------
    # 1. Cargar insumos SRM
    # --------------------------------------
    taxo = read_csv_safe(INPUT_TAXONOMY)
    if taxo.empty:
        raise Exception("❌ La taxonomía base SRM está vacía o no existe.")
    log("Taxonomía base cargada correctamente.", "green")

    vocab = read_json_safe(INPUT_VOCAB_SRM)
    emp = read_json_safe(INPUT_TERMINOLOGIA)
    syns = read_json_safe(INPUT_SINONIMOS)
    struct = read_json_safe(INPUT_ESTRUCTURA)
    log("Motor lingüístico SRM cargado correctamente.", "green")

    modelos = read_csv_safe(INPUT_MODELOS)
    oem = read_csv_safe(INPUT_OEM)
    fitment = read_csv_safe(INPUT_FITMENT)
    learning = read_json_safe(INPUT_LEARNING)
    log("Modelos, OEM y Fitment cargados correctamente.", "green")
    log("Learning Engine cargado correctamente.", "green")

    # --------------------------------------
    # 2. Cargar catálogo unificado v2
    # --------------------------------------
    df = read_csv_safe(INPUT_CATALOGO)
    if df.empty:
        raise Exception("❌ El catálogo v2 está vacío o no existe.")

    log("Catálogo cargado: {} registros.".format(len(df)), "blue")

    # --------------------------------------
    # 3. Construir matriz técnica SRM
    # --------------------------------------
    global GLOBAL_PATTERNS
    linguistic_terms = set(list(vocab.keys()) + list(emp.keys()) + list(syns.keys()))
    GLOBAL_PATTERNS = generate_patterns(
        linguistic_terms,
        modelos,
        oem,
        struct
    )
    log("Matriz técnica SRM construida.", "green")

    # --------------------------------------
    # 4. Expansión de taxonomía
    # --------------------------------------
    df = expand_taxonomy(df, taxo, GLOBAL_PATTERNS)
    log("Expansión taxonómica aplicada.", "green")

    # --------------------------------------
    # 5. Integración full SRM (modelo, OEM, zonas)
    # --------------------------------------
    df = integrate_full_srm(df, modelos, oem, fitment, learning)
    log("Integración SRM completa aplicada.", "green")

    # --------------------------------------
    # 6. Generar señal SRM
    # --------------------------------------
    df = generate_srm_signal(df, GLOBAL_PATTERNS)
    log("Señal SRM generada.", "green")

    # --------------------------------------
    # 7. Auditoría técnica industrial
    # --------------------------------------
    audit_report = audit_catalog(df, GLOBAL_PATTERNS, modelos.set_index(modelos.columns[0]).to_dict()['modelo_srm'] if "modelo_srm" in modelos else {}, oem)
    save_audit_report(audit_report, OUTPUT_REPORT)

    # --------------------------------------
    # 8. Guardar catálogo final SRM
    # --------------------------------------
    try:
        df.to_csv(OUTPUT_CATALOG_FINAL, index=False, encoding="utf-8")
        log(f"✔ Catálogo SRM FINAL guardado → {OUTPUT_CATALOG_FINAL}", "green")
    except Exception as e:
        log(f"❌ ERROR guardando catálogo final: {e}", "red")

    log("=== SRM TAXONOMY EXPANDER v2 — COMPLETADO ===", "blue")


# --------------------------------------------------------------
# EJECUTAR SOLO SI ES LLAMADO DIRECTAMENTE
# --------------------------------------------------------------
if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        log(f"❌ ERROR CRÍTICO → {e}", "red")
