# ======================================================================
#               SRM_Catalog_Builder_v1.py
#     CONSTRUCTOR OFICIAL DEL CATÁLOGO UNIFICADO SRM v1
# ======================================================================
# Genera:
#   ✔ catalogo_unificado.csv
#   ✔ inventarios_unificados.csv
#   ✔ sku_srm_master.csv
#   ✔ fitment_srm.csv
#   ✔ taxonomia_srm_aplicada.csv
#   ✔ descripcion_srm.csv
#   ✔ reportes de calidad
#
# Usa:
#   - taxonomía SRM
#   - motor lingüístico técnico
#   - fuentes originales por cliente
# ======================================================================

import os
import pandas as pd
import json
from datetime import datetime

BASE = r"C:\SRM_ADSI"
SRC1 = os.path.join(BASE, "01_sources_originales")
SRC2 = os.path.join(BASE, "02_cleaned_normalized")

KB = os.path.join(BASE, "03_knowledge_base")
PIPE = os.path.join(BASE, "05_pipeline")

OUT = os.path.join(BASE, "02_cleaned_normalized")

# Paths knowledge
TAX_PATH = os.path.join(KB, "taxonomia", "Taxonomia_SRM_QK_ADSI_v1.csv")
LING_EMP = os.path.join(KB, "linguistico", "terminologia_empirica.json")
LING_MAP = os.path.join(KB, "linguistico", "mapa_sinonimos.json")
LING_MEC = os.path.join(KB, "linguistico", "estructura_mecanica.json")

# Output files
CATALOGO_OUT = os.path.join(OUT, "catalogo_unificado.csv")
INVENTARIO_OUT = os.path.join(OUT, "inventarios_unificados.csv")
SKU_OUT = os.path.join(OUT, "sku_srm_master.csv")
TAXO_OUT = os.path.join(OUT, "taxonomia_srm_aplicada.csv")
FITMENT_OUT = os.path.join(OUT, "fitment_srm.csv")
DESC_OUT = os.path.join(OUT, "descripcion_srm.csv")
REPORT = os.path.join(PIPE, "sql", "seeds", "catalog_report.json")


# ----------------------------------------------------------------------
# UTILIDADES
# ----------------------------------------------------------------------
def safe_read_csv(path):
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        return pd.read_csv(path, encoding="utf-8", dtype=str)
    except:
        return pd.DataFrame()


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default


def normalize_text(text):
    if not isinstance(text, str):
        return ""
    t = text.lower()
    t = t.replace("  ", " ").replace("\n", " ").strip()
    return t


def apply_synonyms(text, synonyms):
    if not isinstance(text, str): 
        return ""
    for k, v in synonyms.items():
        text = text.replace(k.lower(), v.lower())
    return text


def classify_taxonomy(desc, taxo_df):
    for _, row in taxo_df.iterrows():
        if row["keyword"] in desc:
            return row["categoria"], row["subcategoria"], row["sistema"], row["componente"]
    return "", "", "", ""


def build_sku_srm(marca, codigo, index):
    marca = marca.upper()[0:3]
    codigo = str(codigo).zfill(5)[-5:]
    return f"SRM-{marca}-{codigo}-{str(index).zfill(6)}"


# ----------------------------------------------------------------------
# ETAPA 1 — CARGA Y UNIFICACIÓN DE FUENTES
# ----------------------------------------------------------------------
def collect_all_sources():

    print("→ Cargando fuentes originales...")
    all_rows = []

    for root, _, files in os.walk(SRC2):
        for f in files:
            if f.endswith(".csv"):
                df = safe_read_csv(os.path.join(root, f))
                if not df.empty:
                    df["source_file"] = f
                    all_rows.append(df)

    if not all_rows:
        print("⚠ No hay archivos CSV en 02_cleaned_normalized")
        return pd.DataFrame()

    return pd.concat(all_rows, ignore_index=True)


# ----------------------------------------------------------------------
# ETAPA 2 — APLICAR MOTOR LINGÜÍSTICO
# ----------------------------------------------------------------------
def linguistic_processing(df):

    print("→ Procesando lenguaje técnico...")

    emp = load_json(LING_EMP, {})
    synonyms = load_json(LING_MAP, {})
    mec = load_json(LING_MEC, {})

    processed_desc = []

    for desc in df["descripcion"].fillna(""):
        d = normalize_text(desc)
        d = apply_synonyms(d, synonyms)
        processed_desc.append(d)

    df["descripcion_limpia"] = processed_desc

    return df


# ----------------------------------------------------------------------
# ETAPA 3 — APLICAR TAXONOMÍA SRM
# ----------------------------------------------------------------------
def apply_taxonomy(df):

    print("→ Aplicando taxonomía SRM...")

    tax = safe_read_csv(TAX_PATH)
    if tax.empty:
        print("⚠ No se encontró Taxonomía SRM.")
        df["categoria"] = ""
        df["subcategoria"] = ""
        df["sistema"] = ""
        df["componente"] = ""
        return df

    cats, subs, sist, comp = [], [], [], []

    for desc in df["descripcion_limpia"]:
        c, s, sy, co = classify_taxonomy(desc, tax)
        cats.append(c)
        subs.append(s)
        sist.append(sy)
        comp.append(co)

    df["categoria"] = cats
    df["subcategoria"] = subs
    df["sistema"] = sist
    df["componente"] = comp

    return df


# ----------------------------------------------------------------------
# ETAPA 4 — ASIGNAR SKU SRM
# ----------------------------------------------------------------------
def assign_sku(df):

    print("→ Generando SKU SRM universal...")

    sku_list = []

    for idx, row in df.iterrows():
        marca = row.get("marca", "GEN")
        codigo = row.get("codigo", "0")
        sku_list.append(build_sku_srm(marca, codigo, idx))

    df["sku_srm"] = sku_list

    sku_df = pd.DataFrame({"sku_srm": sku_list})
    sku_df.to_csv(SKU_OUT, index=False, encoding="utf-8")

    return df


# ----------------------------------------------------------------------
# ETAPA 5 — FITMENT BASE
# ----------------------------------------------------------------------
def build_fitment(df):

    print("→ Construyendo Fitment SRM...")

    fit_rows = []

    for _, row in df.iterrows():
        desc = row["descripcion_limpia"]

        modelo = ""
        cilindraje = ""

        # ejemplo simple — en v2 se integrará la magia de Fitment Japan
        if "125" in desc:
            cilindraje = "125"
        if "150" in desc:
            cilindraje = "150"

        fit_rows.append([row["sku_srm"], modelo, cilindraje])

    fit_df = pd.DataFrame(fit_rows, columns=["sku_srm", "modelo", "cilindraje"])
    fit_df.to_csv(FITMENT_OUT, index=False, encoding="utf-8")

    return fit_df


# ----------------------------------------------------------------------
# ETAPA 6 — GUARDAR SALIDAS FINALES
# ----------------------------------------------------------------------
def store_outputs(df):

    print("→ Guardando catálogo unificado SRM...")

    df.to_csv(CATALOGO_OUT, index=False, encoding="utf-8")

    inv = df[["sku_srm", "marca", "codigo", "stock"]].copy()
    inv.to_csv(INVENTARIO_OUT, index=False, encoding="utf-8")

    tax_df = df[
        ["sku_srm", "categoria", "subcategoria", "sistema", "componente"]
    ]
    tax_df.to_csv(TAXO_OUT, index=False, encoding="utf-8")

    desc_df = df[["sku_srm", "descripcion_limpia"]]
    desc_df.to_csv(DESC_OUT, index=False, encoding="utf-8")

    print("✔ Catálogo SRM guardado correctamente.")


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------
def run():

    print("\n===============================================")
    print("       SRM — CATALOG BUILDER v1")
    print("===============================================\n")

    df = collect_all_sources()
    if df.empty:
        print("❌ No se pudo generar catálogo — no hay fuentes.")
        return

    # normalizar columnas mínimas
    required_cols = ["descripcion", "marca", "codigo", "stock"]
    for c in required_cols:
        if c not in df.columns:
            df[c] = ""

    df = linguistic_processing(df)
    df = apply_taxonomy(df)
    df = assign_sku(df)

    fit_df = build_fitment(df)

    store_outputs(df)

    report = {
        "timestamp": datetime.now().isoformat(),
        "total_items": len(df),
        "fuentes_procesadas": df["source_file"].unique().tolist(),
        "categorias_detectadas": df["categoria"].unique().tolist(),
    }

    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)

    print("\n===============================================")
    print(" ✔ CATALOGO SRM v1 COMPLETADO")
    print("===============================================\n")


if __name__ == "__main__":
    run()
