import os
import json
from pathlib import Path

# ==========================================================
#       SRM — FITMENT RULES BUILDER v1
#       Genera reglas maestras para Fitment Universal SRM
# ==========================================================

BASE_DIR = r"C:\SRM_ADSI"
OUTPUT_DIR = os.path.join(BASE_DIR, "03_knowledge_base", "rules")
os.makedirs(OUTPUT_DIR, exist_ok=True)

OUTPUT_FILE = os.path.join(OUTPUT_DIR, "srm_fitment_rules_v1.json")


def build_rules():
    rules = {
        "version": "1.0",
        "descripcion": "Reglas maestras para el Fitment Universal SRM v2",
        
        # ----------------------------------------------------
        # 1. Reglas de piezas realmente universales
        # ----------------------------------------------------
        "reglas_universales": [
            "ESPEJO UNIVERSAL",
            "MANIGUETA UNIVERSAL",
            "TORNILLO",
            "TUERCA",
            "ARANDELA",
            "ACEITE",
            "GRASA",
            "ILUMINACION UNIVERSAL",
            "FILTRO UNIVERSAL",
            "GUAYA UNIVERSAL",
            "PUÑO UNIVERSAL",
        ],

        # ----------------------------------------------------
        # 2. Piezas que NUNCA deben ser universales
        # ----------------------------------------------------
        "reglas_no_universales": [
            "CILINDRO",
            "PISTON",
            "CIGUEÑAL",
            "CULATA",
            "BLOCK",
            "TRANSMISION",
            "CAJA DE CAMBIOS",
            "CARBURADOR ESPECIFICO",
            "INYECTOR",
            "COMPUTADOR",
            "ECU",
            "CHASIS",
            "TENCIONADOR",
        ],

        # ----------------------------------------------------
        # 3. Reglas basadas en rango de cilindraje
        # ----------------------------------------------------
        "reglas_cilindraje": {
            "100-125": [
                "FILTRO DE AIRE",
                "ZAPATA",
                "PASTILLA",
                "CORONA",
                "PIÑON",
            ],
            "125-150": [
                "FILTRO DE AIRE",
                "CARBURADOR",
                "BOBINA",
                "LLANTA",
            ],
            "150-200": [
                "DISCO DE FRENO",
                "CADENA",
            ]
        },

        # ----------------------------------------------------
        # 4. Reglas por modelo explícito
        # ----------------------------------------------------
        "reglas_modelo_estricto": [
            "AMORTIGUADOR",
            "TENSOR DE CADENA",
            "TAPA LATERAL",
            "GUARDABARRO ESPECIFICO",
            "CONECTOR OEM",
            "CARCAZA",
        ],

        # ----------------------------------------------------
        # 5. Reglas OEM (si aparece un código OEM, fitment debe ser estricto)
        # ----------------------------------------------------
        "reglas_oem": {
            "activar_modo_oem_estricto": True,
            "patrones_oem": [
                r"\d{3,5}-[A-Z]{2,4}-\d{2,4}",
                r"[A-Z0-9]{3,7}-[A-Z0-9]{2,4}-\d{2,4}",
                r"\d{5,11}[A-Z]?",
            ]
        },

        # ----------------------------------------------------
        # 6. Reglas empíricas (interpretación del mercado)
        # ----------------------------------------------------
        "reglas_empiricas": {
            "correcciones": {
                "BOZER": "BOXER",
                "BOXTER": "BOXER",
                "BOKSER": "BOXER",
                "AK100": "AX100",
            },
            "modelos_familia": {
                "BOXER": ["CT100", "BOXER 100", "BOXER 150"],
                "PULSAR": ["NS125", "135LS", "180", "200"],
                "NKD": ["NKD 125", "NKD 150"],
                "AKT": ["EVO", "SL", "TT", "CR4"]
            }
        },

        # ----------------------------------------------------
        # 7. Reglas anti-falsos positivos
        # ----------------------------------------------------
        "reglas_anti_ruido": {
            "evitar_si_contiene": [
                "GENERICA",
                "TIPO",
                "SIMILAR",
                "REEMPLAZO",
                "UNIVERSAL MAL DEFINIDO",
            ],
            "evitar_sin_medidas_para": [
                "AMORTIGUADOR",
                "BUJIA",
                "CARBURADOR",
                "LLANTA",
                "DISCO",
            ]
        }
    }

    return rules


def run():
    print("===============================================")
    print("     SRM — FITMENT RULES BUILDER v1")
    print("===============================================")

    rules = build_rules()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(rules, f, indent=4, ensure_ascii=False)

    print(f"✔ Reglas SRM generadas: {OUTPUT_FILE}")
    print("===============================================")
    print("       ✔ RULES ENGINE v1 COMPLETADO")
    print("===============================================")


if __name__ == "__main__":
    run()
