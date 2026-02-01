import os
import re
import pandas as pd

# ==========================================================
#           SRM — MODEL DETECTOR v1
# ==========================================================

BASE = r"C:\SRM_ADSI"
OUT_DIR = os.path.join(BASE, "03_knowledge_base", "modelos")
os.makedirs(OUT_DIR, exist_ok=True)

FITMENT_FILE = os.path.join(BASE, "03_knowledge_base", "fitment", "fitment_srm_v2.csv")

RAW_OUT = os.path.join(OUT_DIR, "modelos_detectados_raw.csv")
CLEAN_OUT = os.path.join(OUT_DIR, "modelos_detectados_clean.csv")
CANDIDATES_OUT = os.path.join(OUT_DIR, "modelos_srm_candidates.csv")

# ==========================================================
# Diccionario base de marcas y patrones de modelos
# ==========================================================

MARCAS = [
    "AKT", "HONDA", "YAMAHA", "TVS", "BAJAJ", "HERO", "SUZUKI", "KYMCO",
    "VICTORY", "BENELLI", "KAWASAKI", "HAOJUE", "UM", "LONCIN",
    "ZONTES", "ROYAL", "ENFIELD"
]

# patrones típicos LATAM (NS125, CT100, NKD125, etc.)
PATRONES_MODELOS = [
    r"[A-Z]{2,4}\s?\d{2,4}",      # NS125 / CT100 / NKD125
    r"[A-Z]{2,4}",                # NKD, NS, CT, RS
    r"\d{3}",                     # 100 / 125 / 150
    r"[A-Z]+\s\d{3}",             # DIO 110
]


def norm(text):
    if pd.isna(text):
        return ""
    t = str(text).upper()
    t = re.sub(r"[^A-Z0-9 ]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


# ==========================================================
# Extraer patrones de modelos desde texto
# ==========================================================
def detect_modelos_from_text(text):
    modelos = set()
    t = norm(text)

    # Detectar marcas como prefijo
    for marca in MARCAS:
        if marca in t:
            modelos.add(marca)

    # Detectar patrones secundarios
    for pattern in PATRONES_MODELOS:
        found = re.findall(pattern, t)
        for f in found:
            modelos.add(f.strip())

    return list(modelos)


# ==========================================================
# Procesamiento principal
# ==========================================================
def run():
    print("===============================================")
    print("        SRM — MODEL DETECTOR v1")
    print("===============================================")

    try:
        df = pd.read_csv(FITMENT_FILE, encoding="utf-8")
    except:
        print("[ERROR] No se pudo cargar fitment_srm_v2.csv")
        return

    raw_models = []

    for idx, row in df.iterrows():
        desc = row.get("descripcion", "")
        fitm = row.get("fitment_final", "")
        oem = row.get("oem_detectado", "")

        modelos_desc = detect_modelos_from_text(desc)
        modelos_fitm = detect_modelos_from_text(fitm)
        modelos_oem = detect_modelos_from_text(oem)

        all_models = set(modelos_desc + modelos_fitm + modelos_oem)

        for m in all_models:
            raw_models.append([idx, m, desc])

    raw_df = pd.DataFrame(raw_models, columns=["row_id", "modelo_detectado", "fuente"])

    raw_df.to_csv(RAW_OUT, index=False, encoding="utf-8-sig")
    print(f"✔ RAW MODELS → {RAW_OUT} ({len(raw_df)} registros)")

    # Normalización inicial
    clean_df = raw_df.copy()
    clean_df["modelo_norm"] = clean_df["modelo_detectado"].apply(
        lambda x: re.sub(r"\s+", "", x).upper()
    )

    clean_df.to_csv(CLEAN_OUT, index=False, encoding="utf-8-sig")
    print(f"✔ CLEAN MODELS → {CLEAN_OUT}")

    # Agrupación por frecuencia
    freq = clean_df["modelo_norm"].value_counts().reset_index()
    freq.columns = ["modelo_norm", "frecuencia"]

    freq.to_csv(CANDIDATES_OUT, index=False, encoding="utf-8-sig")
    print(f"✔ CANDIDATE MODELS → {CANDIDATES_OUT}")

    print("===============================================")
    print("      ✔ MODEL DETECTOR COMPLETADO")
    print("===============================================")


if __name__ == "__main__":
    run()
