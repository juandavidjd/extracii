import os
import re
import json
import pandas as pd
from collections import defaultdict, Counter

# ==========================================================
#           SRM — MODEL UNIFIER v2 (PRO)
# ==========================================================

BASE = r"C:\SRM_ADSI"

IN_RAW = os.path.join(BASE, "03_knowledge_base", "modelos", "modelos_detectados_clean.csv")
IN_CANDIDATES = os.path.join(BASE, "03_knowledge_base", "modelos", "modelos_srm_candidates.csv")

OUT_DIR = os.path.join(BASE, "03_knowledge_base", "modelos")
os.makedirs(OUT_DIR, exist_ok=True)

OUT_SRM = os.path.join(OUT_DIR, "modelos_srm.csv")
OUT_CLUSTERS = os.path.join(OUT_DIR, "modelos_srm_clusters.json")
OUT_DICT = os.path.join(OUT_DIR, "modelos_srm_dictionary.json")


# ==========================================================
# MARCAS LATAM + REGEX DE MODELOS
# ==========================================================
MARCAS = [
    "AKT", "HONDA", "YAMAHA", "BAJAJ", "TVS", "HERO", "SUZUKI", "KYMCO",
    "BENELLI", "KAWASAKI", "HUSQVARNA", "KTM", "UM", "LONCIN", "HAOJUE",
    "VICTORY", "ITALIKA", "ZONTES", "ROYALENFIELD", "ROYAL", "ENFIELD"
]

PATRON_MODELO = re.compile(r"([A-Z]{2,5}\s?\d{2,4})")  # NS125, NKD125, CT100, FZ16, RS200
PATRON_CC = re.compile(r"(\d{2,4})")


def norm(text):
    if pd.isna(text):
        return ""
    t = str(text).upper()
    t = re.sub(r"[^A-Z0-9 ]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


# ==========================================================
# Detección de marca
# ==========================================================
def detectar_marca(text):
    for marca in MARCAS:
        if marca in text:
            return marca
    return ""


# ==========================================================
# Detección de modelo y cc
# ==========================================================
def detectar_modelo(text):
    modelos = PATRON_MODELO.findall(text)
    if modelos:
        return modelos[0]
    return ""


def detectar_cc(text):
    cc_found = PATRON_CC.findall(text)
    if not cc_found:
        return ""
    for cc in cc_found:
        if 80 <= int(cc) <= 300:
            return cc
    return ""


# ==========================================================
# Unificador principal
# ==========================================================
def unificar_modelos(df):
    registros = []

    for _, row in df.iterrows():

        m = str(row["modelo_norm"]).replace(" ", "")
        texto = m

        marca = detectar_marca(texto)
        modelo = detectar_modelo(texto)
        cc = detectar_cc(texto)

        # Reconstrucción SRM
        if marca and modelo:
            modelo_srm = f"{marca} {modelo}"
        elif marca and cc:
            modelo_srm = f"{marca} {cc}"
        else:
            modelo_srm = modelo if modelo else texto

        registros.append([m, marca, modelo, cc, modelo_srm])

    srm_df = pd.DataFrame(registros, columns=[
        "modelo_detectado",
        "marca_srm",
        "modelo_base",
        "cilindraje",
        "modelo_srm"
    ])

    return srm_df


# ==========================================================
# Crear clusters
# ==========================================================
def generar_clusters(df):
    clusters = defaultdict(set)

    for _, row in df.iterrows():
        modelo_srm = row["modelo_srm"]
        detectado = row["modelo_detectado"]
        clusters[modelo_srm].add(detectado)

    return {k: list(v) for k, v in clusters.items()}


# ==========================================================
# Diccionario SRM
# ==========================================================
def generar_diccionario(df):
    dicc = {}

    for _, row in df.iterrows():
        modelo_srm = row["modelo_srm"]
        marca = row["marca_srm"]
        cc = row["cilindraje"]

        if modelo_srm not in dicc:
            dicc[modelo_srm] = {
                "marca": marca,
                "cilindraje": cc,
                "variantes": []
            }

        dicc[modelo_srm]["variantes"].append(row["modelo_detectado"])

    return dicc


# ==========================================================
# Ejecución
# ==========================================================
def run():
    print("===============================================")
    print("        SRM — MODEL UNIFIER v2 (PRO)")
    print("===============================================")

    try:
        df = pd.read_csv(IN_CANDIDATES, encoding="utf-8")
    except:
        print("[ERROR] No se pudo cargar modelos_srm_candidates.csv")
        return

    print(f"→ Candidatos cargados: {len(df)}")

    df["modelo_norm"] = df["modelo_norm"].astype(str).apply(norm)

    srm_df = unificar_modelos(df)

    # Guardar tabla SRM
    srm_df.to_csv(OUT_SRM, index=False, encoding="utf-8-sig")

    # Clusters
    clusters = generar_clusters(srm_df)

    with open(OUT_CLUSTERS, "w", encoding="utf-8") as f:
        json.dump(clusters, f, indent=4, ensure_ascii=False)

    # Diccionario SRM
    dic = generar_diccionario(srm_df)

    with open(OUT_DICT, "w", encoding="utf-8") as f:
        json.dump(dic, f, indent=4, ensure_ascii=False)

    print(f"✔ Modelos SRM generados: {OUT_SRM}")
    print(f"✔ Clusters SRM generados: {OUT_CLUSTERS}")
    print(f"✔ Diccionario SRM generado: {OUT_DICT}")

    print("===============================================")
    print("       ✔ MODEL UNIFIER v2 COMPLETADO")
    print("===============================================")


if __name__ == "__main__":
    run()
