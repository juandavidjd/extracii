import os
import re
import json
import ast
import pandas as pd
from collections import defaultdict

# ==========================================================
#     SRM — FITMENT ENGINE v2.1 (PRECISION MODE - FIX FINAL)
# ==========================================================

BASE = r"C:\SRM_ADSI"

FITMENT_IN = os.path.join(BASE, "03_knowledge_base", "fitment", "fitment_srm_v2.csv")
MODELOS_SRM = os.path.join(BASE, "03_knowledge_base", "modelos", "modelos_srm_v3.csv")
DICT_SRM = os.path.join(BASE, "03_knowledge_base", "modelos", "modelos_srm_dictionary_v3.json")
FAMILY_SRM = os.path.join(BASE, "03_knowledge_base", "modelos", "modelos_srm_family_map.json")

OUT_FITMENT = os.path.join(BASE, "03_knowledge_base", "fitment", "fitment_srm_v3.csv")
OUT_ISSUES = os.path.join(BASE, "03_knowledge_base", "fitment", "fitment_srm_v3_issues.json")


# ==========================================================
# Helpers
# ==========================================================
def norm(t):
    if pd.isna(t):
        return ""
    t = str(t).upper()
    t = re.sub(r"[^A-Z0-9 ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def parse_modelos_detectados(value):
    """
    Acepta textos como:
        "BOXER CT 100;DISCOVER 125"
        "['BOXER CT 100', 'DISCOVER 125']"
        "BOXER CT 100"
    Y siempre retorna lista de modelos normalizados.
    """
    if pd.isna(value):
        return []

    txt = str(value).strip()

    # Caso lista Python
    if txt.startswith("[") and txt.endswith("]"):
        try:
            lst = ast.literal_eval(txt)
            return [norm(x) for x in lst if isinstance(x, str)]
        except:
            pass

    # Caso modelos separados por ;
    if ";" in txt:
        return [norm(x) for x in txt.split(";") if x.strip()]

    # Caso un solo valor
    return [norm(txt)]


# ==========================================================
# Engine principal
# ==========================================================
def run():

    print("===============================================")
    print("   SRM — FITMENT ENGINE v2.1 (PRECISION MODE)")
    print("===============================================")

    # --------------------------------------------
    # Cargar fitment v2
    # --------------------------------------------
    df = pd.read_csv(FITMENT_IN, encoding="utf-8")

    if "modelos_detectados" not in df.columns:
        raise Exception(
            f"❌ ERROR: La columna 'modelos_detectados' NO existe.\n"
            f"Columnas disponibles: {df.columns}"
        )

    # --------------------------------------------
    # Cargar modelos SRM
    # --------------------------------------------
    df_modelos = pd.read_csv(MODELOS_SRM, encoding="utf-8")

    with open(DICT_SRM, "r", encoding="utf-8") as f:
        diccionario_modelos = json.load(f)

    modelos_validos = set(diccionario_modelos.keys())

    issues = defaultdict(list)

    # ======================================================
    # Procesar cada registro de fitment
    # ======================================================
    result_fitment = []

    for idx, row in df.iterrows():

        detected = parse_modelos_detectados(row["modelos_detectados"])
        modelos_corregidos = []

        for m in detected:
            if m in modelos_validos:
                modelos_corregidos.append(m)
                continue

            # Coincidencias parciales
            encontrado = False
            for modelo_srm, info in diccionario_modelos.items():
                # Variantes
                for variante in info["variantes"]:
                    if m == variante or m in variante:
                        modelos_corregidos.append(modelo_srm)
                        encontrado = True
                        break
                if encontrado:
                    break

            if not encontrado:
                issues["modelos_no_identificados"].append({
                    "linea": idx,
                    "valor_original": m,
                    "detectados": detected
                })

        modelos_corregidos = sorted(list(set(modelos_corregidos)))

        df.at[idx, "fitment_srm_v3"] = ";".join(modelos_corregidos)

    df.to_csv(OUT_FITMENT, index=False, encoding="utf-8-sig")

    with open(OUT_ISSUES, "w", encoding="utf-8") as f:
        json.dump(issues, f, indent=4, ensure_ascii=False)

    print(f"✔ FITMENT SRM v3 generado: {OUT_FITMENT}")
    print(f"✔ Modelos NO identificados: {len(issues['modelos_no_identificados'])}")
    print("===============================================")
    print("   ✔ FITMENT ENGINE v2.1 COMPLETADO")
    print("===============================================")


if __name__ == "__main__":
    run()
