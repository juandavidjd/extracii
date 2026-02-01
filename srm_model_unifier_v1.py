import os
import pandas as pd
import re
from pathlib import Path

# ==========================================================
#   SRM MODEL UNIFIER v1
#   Unifica modelos de todas las marcas y clientes
#   Autor: SRM-QK-ADSI Engine
# ==========================================================

BASE_DIR = r"C:\SRM_ADSI"
SOURCE_DIR = os.path.join(BASE_DIR, "02_cleaned_normalized")
OUTPUT_DIR = os.path.join(BASE_DIR, "03_knowledge_base", "modelos")
os.makedirs(OUTPUT_DIR, exist_ok=True)

OUTPUT_FILE = os.path.join(OUTPUT_DIR, "modelos_srm.csv")

# ==========================================================
# 1. Palabras claves y alias empíricos
# ==========================================================

ALIASES = {
    "AX100": ["ax-100", "ax 100", "suzuki ax100", "ax100 suzuki"],
    "DT125": ["dt-125", "dt 125", "yamaha dt"],
    "NKD125": ["nkd", "nkd 125", "boxer nkd"],
    "BOXER": ["boxer ct", "boxer 100", "boxer 150"],
    "DISCOVER": ["discover 125", "discover 135", "discover 150"],
    "PULSAR NS": ["ns125", "ns 125", "pulsar ns125", "pulsar ns 125"],
    "PULSAR": ["pulsar 135", "pulsar 150", "pulsar 180", "pulsar 200"],
    "AKT125": ["akt 125", "akt125", "akt evo", "akt sl"],
    "HONDA ECO": ["eco deluxe", "eco deluxe 100"],
    "YBR125": ["ybr", "ybr 125", "ybr125"],
}

# ==========================================================
# 2. Función para normalizar nombres de modelos
# ==========================================================

def normalize_model(text):
    if pd.isna(text):
        return None
    
    t = text.lower()
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()

    for base, alias_list in ALIASES.items():
        for alias in alias_list:
            if alias.lower() in t:
                return base

    # Detecta modelos estándar (ej: "CB125", "XR150", "Gixxer 150")
    match = re.findall(r"[a-zA-Z]{1,3}\s?\d{2,3}", text)
    if match:
        return match[0].upper().replace(" ", "")

    return text.strip().upper()


# ==========================================================
# 3. Carga TODAS las bases posibles dentro de 02_cleaned_normalized
# ==========================================================

def load_all_sources():
    modelos = []

    for file in os.listdir(SOURCE_DIR):
        if file.lower().endswith((".csv", ".xlsx")):
            try:
                path = os.path.join(SOURCE_DIR, file)

                if file.endswith(".csv"):
                    df = pd.read_csv(path, encoding="utf-8", low_memory=False)
                else:
                    df = pd.read_excel(path)

                # Detecta columnas potenciales
                for col in df.columns:
                    if col.lower() in ["modelo", "modelo moto", "fitment", "compatibilidad", "vehiculo", "aplica"]:
                        modelos.extend(df[col].dropna().astype(str).tolist())

            except Exception as e:
                print(f"[ADVERTENCIA] No se pudo leer {file}: {e}")

    return modelos


# ==========================================================
# 4. Construcción del dataset unificado
# ==========================================================

def build_model_universe():
    modelos_raw = load_all_sources()
    modelos_norm = []

    for m in modelos_raw:
        clean = normalize_model(m)
        if clean:
            modelos_norm.append(clean)

    df = pd.DataFrame({"modelo_srm": modelos_norm})
    df = df.drop_duplicates().sort_values("modelo_srm").reset_index(drop=True)

    # Añadir columnas estructurales para futuros módulos
    df["alias_empiricos"] = ""
    df["cilindraje_aprox"] = ""
    df["fabricante"] = ""
    df["rango_anios"] = ""

    return df


# ==========================================================
# 5. Guardado final
# ==========================================================

def run():
    print("===============================================")
    print("      SRM — MODEL UNIFIER v1")
    print("===============================================")

    df = build_model_universe()

    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

    print(f"✔ Modelos unificados generados: {OUTPUT_FILE}")
    print(f"✔ Total modelos detectados: {len(df)}")
    print("===============================================")
    print("        ✔ MODELOS SRM COMPLETADOS")
    print("===============================================")


if __name__ == "__main__":
    run()
