import os
import re
import pandas as pd
from pathlib import Path

# ==========================================================
#       SRM — OEM CROSS REFERENCE ENGINE v1
#       Crea equivalencias entre OEM, Aftermarket y SRM SKU
# ==========================================================

BASE_DIR = r"C:\SRM_ADSI"
SOURCE_DIR = os.path.join(BASE_DIR, "02_cleaned_normalized")
OUTPUT_DIR = os.path.join(BASE_DIR, "03_knowledge_base", "oem")
os.makedirs(OUTPUT_DIR, exist_ok=True)

OUTPUT_FILE = os.path.join(OUTPUT_DIR, "oem_cross_reference_v1.csv")

# ==========================================================
# Helper para detectar códigos OEM reales
# Formatos comunes:
# - 45105-KPH-900
# - 5TA-E4450-00
# - 13200B09F00
# ==========================================================

OEM_PATTERNS = [
    r"\b\d{3,5}-[A-Z]{2,4}-\d{2,4}\b",
    r"\b[A-Z0-9]{3,7}-[A-Z0-9]{2,4}-\d{2,4}\b",
    r"\b\d{5,11}[A-Z]?\b",
]

def detect_oem_code(text):
    if pd.isna(text):
        return None
    t = str(text).upper().strip()
    for pat in OEM_PATTERNS:
        match = re.findall(pat, t)
        if match:
            return match[0]
    return None


# ==========================================================
# Cargar todas las fuentes de datos desde 02_cleaned_normalized
# ==========================================================

def load_all_sources():
    records = []

    for file in os.listdir(SOURCE_DIR):
        if not file.lower().endswith((".csv", ".xlsx")):
            continue
        
        path = os.path.join(SOURCE_DIR, file)
        try:
            if file.endswith(".csv"):
                df = pd.read_csv(path, encoding="utf-8", low_memory=False)
            else:
                df = pd.read_excel(path)
        except:
            print(f"[ADVERTENCIA] No se pudo leer {file}")
            continue

        for col in df.columns:
            col_low = col.lower()

            # Detectar columnas típicas de OEM
            if any(k in col_low for k in ["oem", "codigo", "ref", "reference", "equiv"]):
                for val in df[col].dropna().astype(str):
                    oem = detect_oem_code(val)
                    if oem:
                        records.append({"fuente": file, "oem_detectado": oem, "valor_original": val})

    return pd.DataFrame(records)


# ==========================================================
# Crear equivalencias OEM - lógica simple v1
# ==========================================================

def build_equivalences(df):
    if df.empty:
        return pd.DataFrame(columns=["oem_codigo", "equivalentes", "fuentes"])

    # Agrupar por OEM detectado
    grupo = df.groupby("oem_detectado")

    rows = []
    for oem, group in grupo:
        equivalentes = list(group["valor_original"].unique())
        fuentes = list(group["fuente"].unique())

        rows.append({
            "oem_codigo": oem,
            "equivalentes": "; ".join(equivalentes),
            "fuentes": "; ".join(fuentes)
        })

    result = pd.DataFrame(rows).sort_values("oem_codigo")
    return result


# ==========================================================
# Guardar archivo final
# ==========================================================

def run():
    print("===============================================")
    print("      SRM — OEM CROSS REFERENCE ENGINE v1")
    print("===============================================")

    df_raw = load_all_sources()
    print(f"→ OEM detectados: {len(df_raw)} registros crudos")

    df_equiv = build_equivalences(df_raw)

    df_equiv.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

    print(f"✔ Archivo generado: {OUTPUT_FILE}")
    print(f"✔ OEM únicos detectados: {df_equiv.shape[0]}")
    print("===============================================")
    print("         ✔ OEM CROSS REF COMPLETADO")
    print("===============================================")


if __name__ == "__main__":
    run()
