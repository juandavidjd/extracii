import os
import json
import pandas as pd
import re
from collections import Counter, defaultdict

# ==========================================================
#        SRM — FITMENT LEARNING ENGINE v1
# ==========================================================

BASE_DIR = r"C:\SRM_ADSI"

FITTMENT_FILE = os.path.join(BASE_DIR, "03_knowledge_base", "fitment", "fitment_srm_v2.csv")

OUTPUT_DIR = os.path.join(BASE_DIR, "03_knowledge_base", "learning")
os.makedirs(OUTPUT_DIR, exist_ok=True)

OUTPUT_FILE = os.path.join(OUTPUT_DIR, "fitment_learning_memory.json")


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
# Detectar palabras que parecen modelos pero no están en reglas
# ==========================================================
def detect_empirical_patterns(descriptions):
    patterns = Counter()
    
    for desc in descriptions:
        words = desc.split()
        for w in words:
            if len(w) > 3 and any(c.isdigit() for c in w):
                patterns[w] += 1
    
    return dict(patterns)


# ==========================================================
# Detectar equivalencias empíricas por co-ocurrencia
# ==========================================================
def build_clusters(model_lists):
    clusters = defaultdict(set)
    for models in model_lists:
        items = [m for m in models if m.strip()]
        for m in items:
            clusters[m].update(items)
    return {k: list(v) for k, v in clusters.items()}


# ==========================================================
# Motor principal
# ==========================================================
def run():
    print("===============================================")
    print("       SRM — FITMENT LEARNING ENGINE v1")
    print("===============================================")

    try:
        df = pd.read_csv(FITTMENT_FILE, encoding="utf-8", low_memory=False)
    except Exception as e:
        print("[ERROR] No se pudo cargar fitment_srm_v2.csv:", e)
        return

    # Normalizar descripciones
    df["desc_norm"] = df["descripcion"].apply(norm)

    # Frecuencia de modelos detectados
    all_models = []
    for mlist in df["modelos_detectados"]:
        if isinstance(mlist, str):
            models = [m for m in mlist.split(";") if m.strip()]
            all_models.extend(models)

    model_freq = dict(Counter(all_models))

    # Frecuencia de OEM detectados
    oems = df["oem_detectado"].dropna().tolist()
    oem_freq = dict(Counter(oems))

    # Pseudo-modelos empíricos
    empirical_patterns = detect_empirical_patterns(df["desc_norm"])

    # Clusters empíricos
    clusters = build_clusters(df["modelos_detectados"].fillna("").str.split(";"))

    # Reglas mejoradas automáticas
    improved_rules = {
        "modelos_frecuentes": model_freq,
        "oem_frecuentes": oem_freq,
        "patrones_empiricos": empirical_patterns,
        "clusters_modelos": clusters
    }

    # Guardar memoria
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(improved_rules, f, indent=4, ensure_ascii=False)

    print(f"✔ Memoria técnica generada: {OUTPUT_FILE}")
    print(f"✔ Modelos aprendidos: {len(model_freq)}")
    print(f"✔ OEM aprendidos: {len(oem_freq)}")
    print(f"✔ Clusters generados: {len(clusters)}")
    print("===============================================")
    print("       ✔ LEARNING ENGINE COMPLETADO")
    print("===============================================")


if __name__ == "__main__":
    run()
