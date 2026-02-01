import os
import json
import pandas as pd
import re
from pathlib import Path

# ==========================================================
#        SRM — FITMENT INFERENCE ENGINE v1
#        El cerebro del Fitment Universal SRM
# ==========================================================

BASE_DIR = r"C:\SRM_ADSI"

# Rutas de entrada
MODEL_FILE = os.path.join(BASE_DIR, "03_knowledge_base", "modelos", "modelos_srm.csv")
OEM_FILE = os.path.join(BASE_DIR, "03_knowledge_base", "oem", "oem_cross_reference_v1.csv")
RULES_FILE = os.path.join(BASE_DIR, "03_knowledge_base", "rules", "srm_fitment_rules_v1.json")

# Fuentes de catálogo (todos los CSV del normalized)
SOURCE_DIR = os.path.join(BASE_DIR, "02_cleaned_normalized")

# Ruta de salida
OUTPUT_DIR = os.path.join(BASE_DIR, "03_knowledge_base", "fitment")
os.makedirs(OUTPUT_DIR, exist_ok=True)

OUTPUT_FILE = os.path.join(OUTPUT_DIR, "fitment_srm_v2.csv")


# ==========================================================
# Helper: Normalizar texto
# ==========================================================
def norm(text):
    if pd.isna(text):
        return ""
    t = str(text).upper()
    t = re.sub(r"[^A-Z0-9 ]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


# ==========================================================
# Cargar modelos SRM
# ==========================================================
def load_models():
    try:
        df = pd.read_csv(MODEL_FILE, encoding="utf-8")
        modelos = df["modelo_srm"].dropna().unique().tolist()
        return modelos
    except Exception as e:
        print("[ERROR] No se pudieron cargar modelos SRM:", e)
        return []


# ==========================================================
# Cargar equivalencias OEM
# ==========================================================
def load_oem():
    try:
        df = pd.read_csv(OEM_FILE, encoding="utf-8")
        return df
    except:
        return pd.DataFrame(columns=["oem_codigo", "equivalentes"])


# ==========================================================
# Cargar reglas SRM
# ==========================================================
def load_rules():
    with open(RULES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ==========================================================
# Detectar OEM en un texto
# ==========================================================
def detect_oem(text, rules):
    if pd.isna(text):
        return None
    t = str(text)
    for pat in rules["reglas_oem"]["patrones_oem"]:
        match = re.findall(pat, t, flags=re.IGNORECASE)
        if match:
            return match[0].upper()
    return None


# ==========================================================
# Extraer modelos desde descripciones
# ==========================================================
def detect_models(desc, modelos_srm):
    found = []
    for m in modelos_srm:
        if m in desc:
            found.append(m)
    return found


# ==========================================================
# Clasificar por reglas
# ==========================================================
def analyze_fitment(desc, rules, modelos_srm):
    desc_norm = norm(desc)

    # ---------------------------
    # 1. Universal verdadero
    # ---------------------------
    for u in rules["reglas_universales"]:
        if u in desc_norm:
            return {"tipo": "universal", "modelos": [], "score": 0.95}

    # ---------------------------
    # 2. Universal falso
    # ---------------------------
    for nu in rules["reglas_no_universales"]:
        if nu in desc_norm:
            return {"tipo": "modelo_especifico", "modelos": [], "score": 0.30}

    # ---------------------------
    # 3. Detectar modelos explícitos
    # ---------------------------
    mods = detect_models(desc_norm, modelos_srm)
    if mods:
        return {"tipo": "modelo_detectado", "modelos": mods, "score": 0.85}

    # ---------------------------
    # 4. Analizar por cilindrada (aunque no tengamos rango explícito)
    # ---------------------------
    for rango, piezas in rules["reglas_cilindraje"].items():
        for p in piezas:
            if p in desc_norm:
                return {"tipo": "rango_cilindraje", "rango": rango, "modelos": [], "score": 0.70}

    # ---------------------------
    # 5. Empírico corregido
    # ---------------------------
    for wrong, correct in rules["reglas_empiricas"]["correcciones"].items():
        if wrong in desc_norm:
            return {"tipo": "empirico_corregido", "modelos": [correct], "score": 0.60}

    # ---------------------------
    # 6. Anti-ruido
    # ---------------------------
    for bad in rules["reglas_anti_ruido"]["evitar_si_contiene"]:
        if bad in desc_norm:
            return {"tipo": "ambiguo", "modelos": [], "score": 0.10}

    # ---------------------------
    # Default
    # ---------------------------
    return {"tipo": "sin_datos", "modelos": [], "score": 0.20}


# ==========================================================
# Cargar todos los catálogos de clientes
# ==========================================================
def load_all_catalogs():
    registros = []
    for file in os.listdir(SOURCE_DIR):
        if file.lower().endswith((".csv", ".xlsx")):
            try:
                path = os.path.join(SOURCE_DIR, file)
                if file.endswith(".csv"):
                    df = pd.read_csv(path, encoding="utf-8", low_memory=False)
                else:
                    df = pd.read_excel(path)

                # Campos típicos para fitment
                posibles = [
                    "descripcion", "nombre", "producto", "detalle",
                    "compatibilidad", "fitment", "aplica"
                ]

                campo_desc = None
                for c in df.columns:
                    if c.lower() in posibles:
                        campo_desc = c
                        break

                if campo_desc:
                    for _, row in df.iterrows():
                        registros.append({
                            "fuente": file,
                            "descripcion": str(row[campo_desc]),
                        })
            except:
                print(f"[ADVERTENCIA] No se pudo procesar {file}")
    return pd.DataFrame(registros)


# ==========================================================
# Ejecución principal
# ==========================================================
def run():
    print("===============================================")
    print("   SRM — FITMENT INFERENCE ENGINE v1")
    print("===============================================")

    modelos_srm = load_models()
    oem_df = load_oem()
    rules = load_rules()
    catalog = load_all_catalogs()

    rows = []

    for _, row in catalog.iterrows():
        desc = row["descripcion"]
        oem = detect_oem(desc, rules)
        fit = analyze_fitment(desc, rules, modelos_srm)

        rows.append({
            "fuente": row["fuente"],
            "descripcion": desc,
            "oem_detectado": oem,
            "tipo_compatibilidad": fit["tipo"],
            "modelos_detectados": ";".join(fit.get("modelos", [])),
            "rango_detectado": fit.get("rango", ""),
            "score_confianza": fit["score"],
        })

    df_final = pd.DataFrame(rows)
    df_final.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

    print(f"✔ Fitment Universal generado: {OUTPUT_FILE}")
    print(f"✔ Registros procesados: {len(df_final)}")
    print("===============================================")
    print("     ✔ FITMENT ENGINE v1 COMPLETADO")
    print("===============================================")


if __name__ == "__main__":
    run()
