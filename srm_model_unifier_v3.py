import os
import re
import json
import pandas as pd
from collections import defaultdict, Counter

# ==========================================================
#           SRM — MODEL UNIFIER v3 (DEEP INTELLIGENCE)
# ==========================================================

BASE = r"C:\SRM_ADSI"

FITMENT_FILE = os.path.join(BASE, "03_knowledge_base", "fitment", "fitment_srm_v2.csv")
CANDIDATES_FILE = os.path.join(BASE, "03_knowledge_base", "modelos", "modelos_srm_candidates.csv")

OUT_DIR = os.path.join(BASE, "03_knowledge_base", "modelos")
os.makedirs(OUT_DIR, exist_ok=True)

OUT_MODELS = os.path.join(OUT_DIR, "modelos_srm_v3.csv")
OUT_CLUSTERS = os.path.join(OUT_DIR, "modelos_srm_clusters_v3.json")
OUT_DICT = os.path.join(OUT_DIR, "modelos_srm_dictionary_v3.json")
OUT_FAMILY = os.path.join(OUT_DIR, "modelos_srm_family_map.json")

# ==========================================================
# Base de marcas industriales LATAM
# ==========================================================
MARCAS = [
    "AKT","HONDA","YAMAHA","BAJAJ","TVS","HERO","SUZUKI","KYMCO","BENELLI",
    "KAWASAKI","HUSQVARNA","KTM","UM","LONCIN","HAOJUE","VICTORY","ITALIKA",
    "ZONTES","ROYALENFIELD","ROYAL","ENFIELD"
]

# ==========================================================
# Patrones de modelos
# ==========================================================
PATRON_MODELO = re.compile(r"([A-Z]{2,5}\s?\d{2,4})")  # NS125, CT100, FZ16
PATRON_CC = re.compile(r"\b(\d{2,4})\b")

# Normalizar texto
def norm(t):
    t = str(t).upper()
    t = re.sub(r"[^A-Z0-9 ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()

# ==========================================================
# Detectar marca
# ==========================================================
def detectar_marca(text):
    for marca in MARCAS:
        if marca in text:
            return marca
    return ""

# ==========================================================
# Detectar modelo base
# ==========================================================
def detectar_modelo(text):
    found = PATRON_MODELO.findall(text)
    if found:
        return found[0]
    return ""

# ==========================================================
# Detectar cilindrada
# ==========================================================
def detectar_cc(text):
    found = PATRON_CC.findall(text)
    for cc in found:
        val = int(cc)
        if 80 <= val <= 300:
            return cc
    return ""

# ==========================================================
# Crear familia de modelos
# ==========================================================
def crear_familia(modelo_srm):
    parts = modelo_srm.split()
    if len(parts) >= 2:
        return f"{parts[0]} {parts[1]}"
    return modelo_srm

# ==========================================================
# Motor principal de unificación
# ==========================================================
def run():
    print("===============================================")
    print("      SRM — MODEL UNIFIER v3 (DEEP INTELLIGENCE)")
    print("===============================================")

    try:
        df = pd.read_csv(CANDIDATES_FILE, encoding="utf-8")
    except Exception as e:
        print("[ERROR] No se pudo cargar candidatos:", e)
        return

    print(f"→ Candidatos cargados: {len(df)}")

    registros = []
    familias = defaultdict(set)

    for _, row in df.iterrows():
        raw = norm(row["modelo_norm"])

        marca = detectar_marca(raw)
        modelo = detectar_modelo(raw)
        cc = detectar_cc(raw)

        # Reconstrucción profunda
        if marca and modelo:
            modelo_srm = f"{marca} {modelo}"
        elif marca and cc:
            modelo_srm = f"{marca} {cc}"
        elif modelo:
            modelo_srm = modelo
        else:
            modelo_srm = raw  # fallback

        familia = crear_familia(modelo_srm)
        familias[familia].add(modelo_srm)

        registros.append([
            raw, marca, modelo, cc, modelo_srm, familia
        ])

    df_srm = pd.DataFrame(registros, columns=[
        "modelo_detectado",
        "marca_srm",
        "modelo_base",
        "cilindraje",
        "modelo_srm",
        "familia_srm"
    ])

    df_srm.to_csv(OUT_MODELS, index=False, encoding="utf-8-sig")

    # Crear clusters
    clusters = defaultdict(set)
    for _, row in df_srm.iterrows():
        clusters[row["modelo_srm"]].add(row["modelo_detectado"])

    clusters = {k: list(v) for k, v in clusters.items()}
    with open(OUT_CLUSTERS, "w", encoding="utf-8") as f:
        json.dump(clusters, f, indent=4, ensure_ascii=False)

    # Diccionario SRM
    diccionario = {}
    for _, row in df_srm.iterrows():
        modelo = row["modelo_srm"]
        if modelo not in diccionario:
            diccionario[modelo] = {
                "marca": row["marca_srm"],
                "cilindraje": row["cilindraje"],
                "variantes": []
            }
        diccionario[modelo]["variantes"].append(row["modelo_detectado"])

    with open(OUT_DICT, "w", encoding="utf-8") as f:
        json.dump(diccionario, f, indent=4, ensure_ascii=False)

    # Familias
    familia_dict = {k: list(v) for k, v in familias.items()}
    with open(OUT_FAMILY, "w", encoding="utf-8") as f:
        json.dump(familia_dict, f, indent=4, ensure_ascii=False)

    print(f"✔ Modelos SRM v3: {OUT_MODELS}")
    print(f"✔ Clusters SRM v3: {OUT_CLUSTERS}")
    print(f"✔ Diccionario SRM v3: {OUT_DICT}")
    print(f"✔ Familias SRM: {OUT_FAMILY}")

    print("===============================================")
    print("        ✔ MODEL UNIFIER v3 COMPLETADO")
    print("===============================================")


if __name__ == "__main__":
    run()
