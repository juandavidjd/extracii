import os
import json
import pandas as pd
import re
from collections import Counter

# ==========================================================
#        SRM — FITMENT QUALITY REPORT ENGINE v1
# ==========================================================

BASE_DIR = r"C:\SRM_ADSI"

FITTMENT_FILE = os.path.join(BASE_DIR, "03_knowledge_base", "fitment", "fitment_srm_v2.csv")
MODELS_FILE = os.path.join(BASE_DIR, "03_knowledge_base", "modelos", "modelos_srm.csv")
RULES_FILE = os.path.join(BASE_DIR, "03_knowledge_base", "rules", "srm_fitment_rules_v1.json")
LEARNING_FILE = os.path.join(BASE_DIR, "03_knowledge_base", "learning", "fitment_learning_memory.json")

OUTPUT_DIR = os.path.join(BASE_DIR, "03_knowledge_base", "fitment")
os.makedirs(OUTPUT_DIR, exist_ok=True)

OUTPUT_FILE = os.path.join(OUTPUT_DIR, "fitment_quality_report.json")


# ==========================================================
# Normalizar texto
# ==========================================================
def norm(text):
    if pd.isna(text):
        return ""
    t = str(text).upper()
    t = re.sub(r"[^A-Z0-9 ]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


# ==========================================================
# Cargar bases necesarias
# ==========================================================
def load_sources():
    try:
        fit = pd.read_csv(FITTMENT_FILE, encoding="utf-8", low_memory=False)
    except:
        print("[ERROR] No se pudo cargar fitment_srm_v2.csv")
        return None, None, None, None

    try:
        modelos = pd.read_csv(MODELS_FILE, encoding="utf-8")
        modelos_list = modelos["modelo_srm"].dropna().unique().tolist()
    except:
        modelos_list = []

    with open(RULES_FILE, "r", encoding="utf-8") as f:
        rules = json.load(f)

    try:
        with open(LEARNING_FILE, "r", encoding="utf-8") as f:
            learning = json.load(f)
    except:
        learning = {
            "modelos_frecuentes": {},
            "clusters_modelos": {},
        }

    return fit, modelos_list, rules, learning


# ==========================================================
# Analizador principal
# ==========================================================
def analyze_quality(fit, modelos_list, rules, learning):
    issues = []
    outliers = []
    counts = Counter()

    for _, row in fit.iterrows():
        desc = row["descripcion"]
        tipo = row["tipo_compatibilidad"]
        modelos = row["modelos_detectados"] if isinstance(row["modelos_detectados"], str) else ""
        oem = row["oem_detectado"]
        score = row["score_confianza"]

        counts[tipo] += 1

        # -------------------------------------------
        # 1. Score demasiado bajo
        # -------------------------------------------
        if score < 0.25:
            issues.append({
                "tipo": "low_confidence",
                "descripcion": desc,
                "score": score,
                "detalle": "Confianza demasiado baja"
            })

        # -------------------------------------------
        # 2. Modelo-específico pero sin modelos detectados
        # -------------------------------------------
        if tipo == "modelo_especifico" and modelos == "":
            issues.append({
                "tipo": "missing_models",
                "descripcion": desc,
                "detalle": "Clasificado como específico pero sin modelos detectados"
            })

        # -------------------------------------------
        # 3. Universal mal clasificado (ej: tiene OEM)
        # -------------------------------------------
        if tipo == "universal" and oem:
            issues.append({
                "tipo": "universal_invalido",
                "descripcion": desc,
                "oem": oem,
                "detalle": "Universal no válido — tiene OEM"
            })

        # -------------------------------------------
        # 4. Modelos desconocidos (no están en Model Unifier)
        # -------------------------------------------
        if modelos:
            for m in modelos.split(";"):
                if m not in modelos_list:
                    outliers.append({
                        "modelo": m,
                        "descripcion": desc,
                        "detalle": "Modelo no reconocido en Model Unifier"
                    })

        # -------------------------------------------
        # 5. Detectar descripciones empíricas dudosas
        # -------------------------------------------
        if any(x in norm(desc) for x in ["TIPO", "GENERICA", "SIMILAR"]):
            issues.append({
                "tipo": "empirico_dudoso",
                "descripcion": desc,
                "detalle": "Descripción empírica genera riesgo"
            })

    # -------------------------------------------------
    # Resumen general
    # -------------------------------------------------
    resumen = {
        "total_registros": len(fit),
        "conteo_por_tipo": dict(counts),
        "porcentaje_universales": counts["universal"] / len(fit) if len(fit) else 0,
        "porcentaje_especificos": counts["modelo_especifico"] / len(fit) if len(fit) else 0,
        "porcentaje_rango": counts["rango_cilindraje"] / len(fit) if len(fit) else 0,
        "porcentaje_bajo_score": counts["ambiguo"] / len(fit) if len(fit) else 0,
    }

    return resumen, issues, outliers


# ==========================================================
# Guardar reporte final
# ==========================================================
def run():
    print("===============================================")
    print("   SRM — FITMENT QUALITY REPORT ENGINE v1")
    print("===============================================")

    fit, modelos_list, rules, learning = load_sources()

    if fit is None:
        print("[ERROR] No se pudo ejecutar el reporte.")
        return

    resumen, issues, outliers = analyze_quality(fit, modelos_list, rules, learning)

    report = {
        "resumen": resumen,
        "issues_detectados": issues,
        "modelos_outliers": outliers
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)

    print(f"✔ Reporte de calidad generado: {OUTPUT_FILE}")
    print(f"✔ Issues detectados: {len(issues)}")
    print(f"✔ Modelos fuera de estándar: {len(outliers)}")
    print("===============================================")
    print("     ✔ FITMENT QUALITY REPORT COMPLETADO")
    print("===============================================")


if __name__ == "__main__":
    run()
