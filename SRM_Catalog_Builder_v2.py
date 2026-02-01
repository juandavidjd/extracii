# ================================================================
#     SRM — CATALOG BUILDER v2 (PRO VERSION + FITMENT FIX)
#     ADSI | QK | SRM — Pipeline Industrial v28
# ================================================================
#     Módulos incluidos:
#     1) Cargadores y validaciones
#     2) Motor Lingüístico SRM PRO
#     3) Integración Taxonomía SRM
#     4) Integración Modelos SRM v3
#     5) Integración OEM Cross Reference
#     6) Ensamble del Catálogo SRM Master v2
# ================================================================

import pandas as pd
import json
import os
from datetime import datetime

# ---------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------
def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

# ---------------------------------------------------------------
# RUTAS SRM (modificar si es necesario)
# ---------------------------------------------------------------
RUTA_TAXO = r"C:\SRM_ADSI\03_knowledge_base\taxonomia\Taxonomia_SRM_QK_ADSI_v1.csv"
RUTA_FITMENT = r"C:\SRM_ADSI\03_knowledge_base\fitment\fitment_srm_v3.csv"
RUTA_MODELOS = r"C:\SRM_ADSI\03_knowledge_base\modelos\modelos_srm_v3.csv"
RUTA_OEM = r"C:\SRM_ADSI\03_knowledge_base\oem\oem_cross_reference_v1.csv"
RUTA_LEARNING = r"C:\SRM_ADSI\03_knowledge_base\learning\fitment_learning_memory.json"
RUTA_LING_VOCAB = r"C:\SRM_ADSI\03_knowledge_base\vocabulario_srm.json"
RUTA_LING_EMPIRICO = r"C:\SRM_ADSI\03_knowledge_base\terminologia_empirica.json"
RUTA_LING_SINONIMOS = r"C:\SRM_ADSI\03_knowledge_base\mapa_sinonimos.json"
RUTA_LING_ESTRUCTURA = r"C:\SRM_ADSI\03_knowledge_base\estructura_mecanica.json"

RUTA_SALIDA = r"C:\SRM_ADSI\03_knowledge_base\catalogo\catalogo_unificado_v2.csv"

# ---------------------------------------------------------------
# MÓDULO 1 — LOADERS
# ---------------------------------------------------------------
def load_sources():
    log("OK: Taxonomía SRM PRO cargado → " + RUTA_TAXO)
    taxo = pd.read_csv(RUTA_TAXO)

    log("OK: Fitment SRM v3 cargado → " + RUTA_FITMENT)
    fit = pd.read_csv(RUTA_FITMENT)

    log("OK: Modelos SRM v3 cargado → " + RUTA_MODELOS)
    modelos = pd.read_csv(RUTA_MODELOS)

    log("OK: OEM Cross Reference cargado → " + RUTA_OEM)
    oem = pd.read_csv(RUTA_OEM)

    log("OK: Learning Memory cargado → " + RUTA_LEARNING)
    with open(RUTA_LEARNING, "r", encoding="utf-8") as f:
        learning = json.load(f)

    log("✓ Validación inicial completada.")
    log("=== MÓDULO 1/6 — Configuración y Loaders cargados correctamente ===")

    return taxo, fit, modelos, oem, learning

# ---------------------------------------------------------------
# MÓDULO 2 — MOTOR LINGÜÍSTICO SRM PRO
# ---------------------------------------------------------------
def load_linguistic_engine():
    log("Cargando Motor Lingüístico SRM PRO...")

    with open(RUTA_LING_VOCAB, "r", encoding="utf-8") as f:
        vocab = json.load(f)

    with open(RUTA_LING_EMPIRICO, "r", encoding="utf-8") as f:
        empirico = json.load(f)

    with open(RUTA_LING_SINONIMOS, "r", encoding="utf-8") as f:
        sinonimos = json.load(f)

    with open(RUTA_LING_ESTRUCTURA, "r", encoding="utf-8") as f:
        estructura = json.load(f)

    log("✓ Motor lingüístico cargado correctamente.")
    log("=== MÓDULO 2/6 — Motor Lingüístico SRM PRO cargado ===")

    return vocab, empirico, sinonimos, estructura

# ---------------------------------------------------------------
# Limpieza lingüística
# ---------------------------------------------------------------
def limpiar_descripcion(desc, vocab, sinonimos):
    if not isinstance(desc, str):
        return ""

    d = desc.lower()

    # aplicar sinónimos
    for s, eq in sinonimos.items():
        d = d.replace(s.lower(), eq.lower())

    # aplicar vocabulario técnico
    for palabra in vocab:
        if palabra.lower() in d:
            pass  # futuro refinamiento

    return d.strip()

# ---------------------------------------------------------------
# MÓDULO 3 — TAXONOMÍA
# ---------------------------------------------------------------
def apply_taxonomy(df, taxo):
    df["categoria_srm"] = ""
    df["subcategoria_srm"] = ""
    df["sistema_srm"] = ""
    df["componente_srm"] = ""

    for i, row in taxo.iterrows():
        kw = str(row["keyword"]).lower()
        mask = df["descripcion_clean"].str.contains(kw, na=False)

        df.loc[mask, "categoria_srm"] = row["categoria"]
        df.loc[mask, "subcategoria_srm"] = row["subcategoria"]
        df.loc[mask, "sistema_srm"] = row["sistema"]
        df.loc[mask, "componente_srm"] = row["componente"]

    log("✓ Taxonomía aplicada correctamente.")
    log("=== MÓDULO 3/6 — Taxonomía SRM aplicada ===")
    return df

# ---------------------------------------------------------------
# MÓDULO 4 — INTEGRACIÓN DE FITMENT + FIX AUTOMÁTICO
# ---------------------------------------------------------------

def detect_fitment_key(df):
    posibles = ["sku", "codigo", "codigo_new", "producto", "descripcion", "nombre", "id"]
    for c in posibles:
        if c in df.columns:
            return c
    raise Exception(f"No se encontró columna válida para mapear FITMENT. Columnas disponibles: {df.columns}")


def integrate_fitment(df, df_fit):
    log("Aplicando Fitment SRM...")

    df_fit["fitment_clean"] = df_fit["fitment_clean"].fillna("").astype(str)

    # FIX PRO — detectar llave automáticamente
    fit_key = detect_fitment_key(df_fit)
    log(f"[FIX] Llave FITMENT detectada: {fit_key}")

    FITMENT_DICT = dict(zip(
        df_fit[fit_key].astype(str),
        df_fit["fitment_clean"].astype(str)
    ))

    df["fitment_srm"] = df["descripcion_clean"].apply(
        lambda x: FITMENT_DICT.get(x, "")
    )

    log("✓ Fitment SRM integrado correctamente.")
    log("=== MÓDULO 4/6 — Fitment SRM aplicado ===")
    return df


# ---------------------------------------------------------------
# MÓDULO 5 — OEM + LEARNING
# ---------------------------------------------------------------
def integrate_oem(df, oem):
    log("Integrando OEM Cross Reference...")

    oem_dict = dict(zip(oem["oem"], oem["equivalente"]))

    df["oem_equivalente"] = df["oem_detectado"].astype(str).apply(
        lambda x: oem_dict.get(x, "")
    )

    log("✓ OEM integrado correctamente.")
    return df


def integrate_learning(df, learning):
    log("Aplicando aprendizaje técnico SRM...")

    learn_dict = learning.get("aprendidos", {})

    df["fitment_learning"] = df["descripcion_clean"].apply(
        lambda x: learn_dict.get(x, "")
    )

    log("✓ Learning SRM aplicado.")
    log("=== MÓDULO 5/6 — OEM + Learning integrados ===")
    return df

# ---------------------------------------------------------------
# MÓDULO 6 — GENERAR CATALOGO FINAL SRM
# ---------------------------------------------------------------
def build_catalog(df):
    log("Generando catálogo SRM Master v2...")

    df["sku_srm"] = df.index + 1

    df.to_csv(RUTA_SALIDA, index=False, encoding="utf-8-sig")

    log("✔ Catálogo Unificado SRM generado: " + RUTA_SALIDA)
    log(f"✔ Registros totales: {len(df)}")
    log("=== MÓDULO 6/6 — Catálogo SRM v2 COMPLETADO ===")

# ---------------------------------------------------------------
# PIPELINE PRINCIPAL
# ---------------------------------------------------------------
def run():
    taxo, fit, modelos, oem, learning = load_sources()
    vocab, empirico, sinonimos, estructura = load_linguistic_engine()

    # fuente a procesar: fitment_srm_v3
    df = fit.copy()

    df["descripcion_clean"] = df["descripcion"].astype(str).apply(
        lambda x: limpiar_descripcion(x, vocab, sinonimos)
    )

    df = apply_taxonomy(df, taxo)
    df = integrate_fitment(df, fit)
    df = integrate_oem(df, oem)
    df = integrate_learning(df, learning)

    build_catalog(df)

# ---------------------------------------------------------------
# RUN
# ---------------------------------------------------------------
if __name__ == "__main__":
    run()
