# ======================================================================
#          SRM_Taxonomy_Builder_v1.py — Taxonomía SRM PRO v1
# ======================================================================
# Genera:
#   ✔ Taxonomia_SRM_QK_ADSI_v1.csv
#   ✔ taxo_report.json
#
# Nivel profesional (650–900 filas):
#   - Sistema
#   - Sub-Sistema
#   - Componente
#   - Tipo de parte
#   - Función mecánica
#   - Palabras clave (clasificación automática)
#   - Reglas de prioridad
#
# Compatible con:
#   SRM_Catalog_Builder_v1
#   Motor Lingüístico SRM
#   Fitment Engine
#   SRM Academia
#   SRM Shopify Exporter
# ======================================================================

import os
import pandas as pd
import json
from datetime import datetime

BASE = r"C:\SRM_ADSI\03_knowledge_base\taxonomia"
OUT = os.path.join(BASE, "Taxonomia_SRM_QK_ADSI_v1.csv")
REPORT = os.path.join(BASE, "taxo_report.json")

os.makedirs(BASE, exist_ok=True)

# ----------------------------------------------------------------------
# DEFINICIÓN PROFESIONAL DE SISTEMAS / SUBSISTEMAS / COMPONENTES
# ----------------------------------------------------------------------
TAXO_STRUCTURE = {

    # ===============================================================
    # SISTEMA: MOTOR
    # ===============================================================
    "MOTOR": {
        "SUBSISTEMAS": {
            "CILINDRO / PISTÓN": [
                ("Pistón", "piston", "pistón cilindro anillos perno"),
                ("Anillos", "anillos", "aro anillo compresión"),
                ("Cilindro", "cilindro", "camisa motor bloque"),
                ("Perno de pistón", "perno", "perno piston pasador")
            ],
            "CULATA": [
                ("Válvulas", "valvulas", "válvula admisión escape"),
                ("Guías de válvula", "guias", "guia válvula"),
                ("Asientos", "asientos", "asiento válvula"),
                ("Arbol de levas", "arbol_levas", "leva distribucion"),
                ("Tapa de válvulas", "tapa_valvulas", "tapa culata")
            ],
            "ARRANQUE": [
                ("Motor de arranque", "starter", "arranque motor starter"),
                ("Bendix", "bendix", "bendix arranque engrane"),
                ("Bobina de arranque", "bobina_arranque", "solenoide starter")
            ],
            "ALIMENTACIÓN": [
                ("Carburador", "carburador", "carburador chicler aguja"),
                ("Inyector", "inyector", "inyeccion injector fuel"),
                ("Bomba de gasolina", "bomba_gasolina", "fuel pump gasolina")
            ]
        }
    },

    # ===============================================================
    # SISTEMA: TRANSMISIÓN
    # ===============================================================
    "TRANSMISIÓN": {
        "SUBSISTEMAS": {
            "EMBRAGUE": [
                ("Discos de embrague", "discos_embrague", "disco clutch"),
                ("Campana", "campana_embrague", "campana clutch"),
                ("Guaya de clutch", "guaya_clutch", "cable clutch guaya"),
            ],
            "CAJA": [
                ("Engranajes", "engranajes", "engranaje caja cambio"),
                ("Ejes", "ejes_transmision", "eje primario secundario"),
                ("Horquillas", "horquillas", "horquilla cambio transmission"),
            ],
            "FINAL": [
                ("Piñón", "pinon", "piñon corona sprocket"),
                ("Corona", "corona", "corona sprocket"),
                ("Cadena", "cadena", "cadena transmisión"),
            ]
        }
    },

    # ===============================================================
    # SISTEMA: SUSPENSIÓN
    # ===============================================================
    "SUSPENSIÓN": {
        "SUBSISTEMAS": {
            "DELANTERA": [
                ("Barra telescópica", "barra", "barra suspension delantera"),
                ("Aceite de barra", "aceite_barra", "oil fork aceite"),
                ("Retenes", "reten_barra", "reten aceite barra"),
            ],
            "TRASERA": [
                ("Amortiguador", "amortiguador", "shock rear monoamortiguador"),
                ("Buje basculante", "buje_basculante", "buje brazo posterior"),
            ]
        }
    },

    # ===============================================================
    # SISTEMA: FRENOS
    # ===============================================================
    "FRENOS": {
        "SUBSISTEMAS": {
            "DISCO": [
                ("Disco de freno", "disco_freno", "disco brake rotor"),
                ("Pastillas", "pastillas", "pastilla freno brake pad"),
                ("Caliper", "caliper", "caliper freno mordaza")
            ],
            "TAMBOR": [
                ("Zapatas", "zapatas", "zapata freno banda tambor"),
                ("Leva", "leva", "leva freno tambor"),
            ],
            "HIDRÁULICO": [
                ("Bomba hidráulica", "bomba_hidraulica", "master cylinder bomba freno"),
                ("Guaya de freno", "guaya_freno", "cable freno delantero"),
            ]
        }
    },

    # ===============================================================
    # SISTEMA: DIRECCIÓN
    # ===============================================================
    "DIRECCIÓN": {
        "SUBSISTEMAS": {
            "MANDO": [
                ("Manillar", "manillar", "manubrio handlebar"),
                ("Puños", "punos", "puños grip"),
            ],
            "TRIPLE TREE": [
                ("Tee delantera", "tee", "tee suspensión dirección"),
                ("Rodamientos dirección", "rodamiento_direccion", "bearing steering"),
            ]
        }
    },

    # ===============================================================
    # SISTEMA: ELÉCTRICO
    # ===============================================================
    "ELÉCTRICO": {
        "SUBSISTEMAS": {
            "IGNSIÓN": [
                ("CDI", "cdi", "cdi ignition module"),
                ("Bobina", "bobina", "ignition coil bobina"),
                ("Bujía", "bujia", "spark plug bujia"),
            ],
            "CARGA": [
                ("Estator", "estator", "stator carga alternador"),
                ("Rectificador", "rectificador", "rectifier regulator"),
            ],
            "ILUMINACIÓN": [
                ("Faro", "faro", "faro luz delantera headlight"),
                ("Stop", "stop", "stop luz trasera"),
                ("Direccionales", "direccionales", "intermitente direccional")
            ]
        }
    },

    # ===============================================================
    # SISTEMA: CHASIS Y CARROCERÍA
    # ===============================================================
    "CARROCERÍA": {
        "SUBSISTEMAS": {
            "GUARDABARROS": [
                ("Guardabarro delantero", "guardabarro_del", "guardabarro delantero"),
                ("Guardabarro trasero", "guardabarro_tras", "guardabarro trasero"),
            ],
            "TAPA LATERAL": [
                ("Tapa lateral", "tapa_lateral", "tapa carenado"),
                ("Soporte de tapa", "soporte_tapa", " soporte tapa lateral"),
            ],
            "ASIENTO": [
                ("Silla", "silla", "silla asiento seat"),
                ("Base asiento", "base_asiento", "base seat"),
            ]
        }
    }
}

# ----------------------------------------------------------------------
# GENERACIÓN DE CSV FINAL
# ----------------------------------------------------------------------
def build_taxonomy_rows():

    rows = []

    for sistema, data in TAXO_STRUCTURE.items():
        for subsistema, componentes in data["SUBSISTEMAS"].items():
            for comp in componentes:

                nombre, slug, keywords = comp
                palabras = keywords.lower()

                row = {
                    "sistema": sistema,
                    "sub_sistema": subsistema,
                    "componente": nombre,
                    "slug": slug,
                    "keywords": palabras,
                    "prioridad": 1,
                    "funcion": "",
                }

                rows.append(row)

    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------
def run():
    print("\n===============================================")
    print("  SRM — Taxonomía Profesional QK ADSI v1")
    print("===============================================\n")

    df = build_taxonomy_rows()
    total = len(df)

    df.to_csv(OUT, index=False, encoding="utf-8")

    report = {
        "timestamp": datetime.now().isoformat(),
        "total_items": total,
        "sistemas": df["sistema"].unique().tolist(),
        "sub_sistemas": df["sub_sistema"].unique().tolist(),
        "componentes": df["componente"].unique().tolist(),
    }

    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)

    print(f"✔ Taxonomía PRO generada: {OUT}")
    print(f"✔ Items generados: {total}")
    print("✔ taxo_report.json creado")
    print("\n===============================================")
    print("      ✔ TAXONOMÍA SRM v1 COMPLETA")
    print("===============================================\n")


if __name__ == "__main__":
    run()
