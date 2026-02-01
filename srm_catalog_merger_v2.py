import os
import pandas as pd
import json
from pathlib import Path
import re

# ==========================================================
#         SRM — CATALOG MERGER v2
# ==========================================================

BASE_DIR = r"C:\SRM_ADSI"

# Entradas
SOURCE_DIR = os.path.join(BASE_DIR, "02_cleaned_normalized")
FITMENT_FILE = os.path.join(BASE_DIR, "03_knowledge_base", "fitment", "fitment_srm_v2.csv")
OEM_FILE = os.path.join(BASE_DIR, "03_knowledge_base", "oem", "oem_cross_reference_v1.csv")
MODELS_FILE = os.path.join(BASE_DIR, "03_knowledge_base", "modelos", "modelos_srm.csv")
RULES_FILE = os.path.join(BASE_DIR, "03_knowledge_base", "rules", "srm_fitment_rules_v1.json")
LEARNING_FILE = os.path.join(BASE_DIR, "03_knowledge_base", "learning", "fitment_learning_memory.json")

# Salida
OUTPUT_DIR = os.path.join(BASE_DIR, "03_knowledge_base", "catalogo")
os.makedirs(OUTPUT_DIR, exist_ok=True)

OUTPUT_FILE = os.path.join(OUTPUT_DIR, "catalogo_unificado_v2.csv")


# ==========================================================
# Helper — Normalizar texto
# ==========================================================
def norm(text):
    if pd.isna(text):
        return ""
    t = str(text).upper()
    t = re.sub(r"[^A-Z0-9 ]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


# ==========================================================
# Carga de catálogos
# ==========================================================
def load_all_sources():
    registros = []
    for file in os.listdir(SOURCE_DIR):
        if file.lower().endswith((".csv", ".xlsx")):
            path = os.path.join(SOURCE_DIR, file)
            try:
                if file.endswith(".csv"):
                    df = pd.read_csv(path, encoding="utf-8", low_memory=False)
                else:
                    df = pd.read_excel(path)
            except:
                print(f"[ADVERTENCIA] No se pudo procesar {file}")
                continue

            # Campos candidatos a descripción
            posibles_desc = ["descripcion", "detalle", "nombre", "producto"]
            campo_desc = None
            for c in df.columns:
                if c.lower() in posibles_desc:
                    campo_desc = c
                    break

            if campo_desc:
                for _, row in df.iterrows():
                    registros.append({
                        "fuente": file,
                        "descripcion": str(row[campo_desc]),
                    })

    return pd.DataFrame(registros)


# ==========================================================
# Fusionar Fitment + OEM + Reglas + Modelos + Aprendizaje
# ==========================================================
def merge_all():
    print("→ Cargando Fitment SRM...")
    try:
        fit = pd.read_csv(FITMENT_FILE, encoding="utf-8")
    except:
        print("[ERROR] fitment_srm_v2.csv no encontrado.")
        fit = pd.DataFrame()

    print("→ Cargando OEM...")
    try:
        oem = pd.read_csv(OEM_FILE, encoding="utf-8")
    except:
        oem = pd.DataFrame(columns=["oem_codigo", "equivalentes"])

    print("→ Cargando modelos...")
    try:
        modelos = pd.read_csv(MODELS_FILE, encoding="utf-8")
    except:
        modelos = pd.DataFrame(columns=["modelo_srm"])

    print("→ Cargando reglas...")
    with open(RULES_FILE, "r", encoding="utf-8") as f:
        rules = json.load(f)

    print("→ Cargando aprendizaje...")
    try:
        with open(LEARNING_FILE, "r", encoding="utf-8") as f:
            learning = json.load(f)
    except:
        learning = {
            "modelos_frecuentes": {},
            "oem_frecuentes": {},
            "clusters_modelos": {},
        }

    print("→ Cargando catálogos originales...")
    cat = load_all_sources()
    cat["desc_norm"] = cat["descripcion"].apply(norm)

    # Integrar Fitment
    print("→ Integrando Fitment SRM...")
    catalogo = cat.merge(fit, how="left", on=["descripcion", "fuente"])

    # Integrar OEM
    print("→ Integrando OEM equivalentes...")
    catalogo = catalogo.merge(oem, how="left", left_on="oem_detectado", right_on="oem_codigo")

    # Aplicar aprendizaje empírico
    def apply_learning(model_list):
        if pd.isna(model_list):
            return ""
        models = [m for m in model_list.split(";") if m]
        enhanced = []
        for m in models:
            enhanced.extend(learning.get("clusters_modelos", {}).get(m, [m]))
        return ";".join(sorted(set(enhanced)))

    print("→ Aplicando aprendizaje...")
    if "modelos_detectados" in catalogo.columns:
        catalogo["modelos_srm"] = catalogo["modelos_detectados"].apply(apply_learning)
    else:
        catalogo["modelos_srm"] = ""

    # Asignar SKU SRM
    print("→ Generando SKU SRM...")
    catalogo["sku_srm"] = [
        f"SRM-{str(i).zfill(7)}" for i in range(1, len(catalogo) + 1)
    ]

    # Rango de cilindraje detectado
    catalogo["rango_cilindraje"] = catalogo.get("rango_detectado", "")

    # Descripción SRM
    catalogo["descripcion_srm"] = catalogo["descripcion"].apply(
        lambda x: norm(x).capitalize()
    )

    # Categoría SRM basada en reglas
    def detect_category(desc):
        d = norm(desc)
        for key in rules["reglas_no_universales"]:
            if key in d:
                return "ESPECIFICO MOTOR"
        for key in rules["reglas_universales"]:
            if key in d:
                return "UNIVERSAL"
        return "GENERAL"

    catalogo["categoria_srm"] = catalogo["descripcion"].apply(detect_category)

    return catalogo


# ==========================================================
# Guardar catálogo final
# ==========================================================
def run():
    print("===============================================")
    print("       SRM — CATALOG MERGER v2")
    print("===============================================")

    df = merge_all()

    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

    print(f"✔ Catálogo Unificado SRM generado: {OUTPUT_FILE}")
    print(f"✔ Registros totales: {len(df)}")
    print("===============================================")
    print("    ✔ CATALOG MASTER SRM v2 COMPLETADO")
    print("===============================================")


if __name__ == "__main__":
    run()
