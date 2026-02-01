#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
====================================================================================
  SRM–QK–ADSI — GENERADOR DE TAXONOMÍA v1
  Genera la taxonomía oficial SRM–QK–ADSI en CSV + JSON
====================================================================================
"""

import os
import csv
import json

BASE_OUT = r"C:\SRM_ADSI\03_knowledge_base"
os.makedirs(BASE_OUT, exist_ok=True)

CSV_OUT = os.path.join(BASE_OUT, "srm_taxonomia_v1.csv")
JSON_OUT = os.path.join(BASE_OUT, "srm_taxonomia_v1.json")

# ----------------------------------------------------------------------------------
# TAXONOMÍA MECÁNICA OFICIAL SRM–QK–ADSI v1
# (Basada en Enciclopedia Visual + Industria Colombia + Catálogos Importadores)
# ----------------------------------------------------------------------------------

TAXONOMIA = [
    # --------------------------------------------------------
    # SISTEMA DE MOTOR
    # --------------------------------------------------------
    {
        "SISTEMA": "MOTOR",
        "SUBSISTEMA": "CIGÜEÑAL",
        "COMPONENTE": "Balinera Cigüeñal",
        "DEFINICION": "Rodamiento encargado de soportar el giro del cigüeñal bajo alta carga.",
        "TAGS": "rodamiento, cigueñal, motor",
        "APLICA_A": "Ambos"
    },
    {
        "SISTEMA": "MOTOR",
        "SUBSISTEMA": "PISTON / CAMARA",
        "COMPONENTE": "Anillos Pistón",
        "DEFINICION": "Aros que sellan la compresión del pistón en el cilindro.",
        "TAGS": "piston, anillos, compresion",
        "APLICA_A": "Ambos"
    },
    {
        "SISTEMA": "MOTOR",
        "SUBSISTEMA": "ÁRBOL DE LEVAS",
        "COMPONENTE": "Balancín Superior",
        "DEFINICION": "Brazo que transmite el empuje del árbol de levas hacia la válvula.",
        "TAGS": "balancin, leva, motor",
        "APLICA_A": "Moto"
    },
    {
        "SISTEMA": "MOTOR",
        "SUBSISTEMA": "ÁRBOL DE LEVAS",
        "COMPONENTE": "Balancín Inferior",
        "DEFINICION": "Apoya la transmisión del movimiento del árbol hacia las válvulas.",
        "TAGS": "balancin, leva, motor",
        "APLICA_A": "Moto"
    },
    {
        "SISTEMA": "MOTOR",
        "SUBSISTEMA": "ARRANQUE",
        "COMPONENTE": "Relay / Automático Arranque",
        "DEFINICION": "Interruptor electromagnético que permite activar el arranque eléctrico.",
        "TAGS": "arranque, relay, electrico",
        "APLICA_A": "Ambos"
    },
    {
        "SISTEMA": "MOTOR",
        "SUBSISTEMA": "CARBURACION / INYECCION",
        "COMPONENTE": "Bendix Arranque",
        "DEFINICION": "Engranaje unidireccional que acopla el arranque eléctrico al motor.",
        "TAGS": "bendix, arranque, motor",
        "APLICA_A": "Ambos"
    },

    # --------------------------------------------------------
    # SISTEMA DE FRENOS
    # --------------------------------------------------------
    {
        "SISTEMA": "FRENOS",
        "SUBSISTEMA": "FRENO DE DISCO",
        "COMPONENTE": "Pastillas Delanteras",
        "DEFINICION": "Superficie de fricción que presiona el disco para frenar la moto.",
        "TAGS": "pastillas, freno disco, delantero",
        "APLICA_A": "Ambos"
    },
    {
        "SISTEMA": "FRENOS",
        "SUBSISTEMA": "FRENO DE DISCO",
        "COMPONENTE": "Pastillas Traseras",
        "DEFINICION": "Elemento de fricción encargado de la frenada posterior.",
        "TAGS": "pastillas, freno disco, trasero",
        "APLICA_A": "Ambos"
    },
    {
        "SISTEMA": "FRENOS",
        "SUBSISTEMA": "FRENO DE TAMBOR",
        "COMPONENTE": "Bandas de Freno",
        "DEFINICION": "Zapatas internas que presionan el tambor para frenar.",
        "TAGS": "bandas, freno, tambor",
        "APLICA_A": "Ambos"
    },

    # --------------------------------------------------------
    # SISTEMA ELECTRICO
    # --------------------------------------------------------
    {
        "SISTEMA": "ELECTRICO",
        "SUBSISTEMA": "ENCENDIDO",
        "COMPONENTE": "Bobina Encendido",
        "DEFINICION": "Genera el alto voltaje necesario para la chispa de encendido.",
        "TAGS": "bobina, encendido, chispa",
        "APLICA_A": "Moto"
    },
    {
        "SISTEMA": "ELECTRICO",
        "SUBSISTEMA": "LUCES Y CARGA",
        "COMPONENTE": "Bobina Luces y Carga",
        "DEFINICION": "Alimenta el sistema de iluminación y carga de batería.",
        "TAGS": "bobina, carga, luces",
        "APLICA_A": "Moto"
    },

    # --------------------------------------------------------
    # SUSPENSIÓN
    # --------------------------------------------------------
    {
        "SISTEMA": "SUSPENSION",
        "SUBSISTEMA": "DELANTERA",
        "COMPONENTE": "Tijera / Barra suspensión",
        "DEFINICION": "Elemento que une la rueda delantera con el chasis y absorbe impactos.",
        "TAGS": "suspension, delantera, tijera",
        "APLICA_A": "Moto"
    },
    {
        "SISTEMA": "SUSPENSION",
        "SUBSISTEMA": "TRASERA",
        "COMPONENTE": "Amortiguador",
        "DEFINICION": "Disipa energía y estabiliza la conducción.",
        "TAGS": "amortiguador, suspension, trasera",
        "APLICA_A": "Ambos"
    },

    # --------------------------------------------------------
    # MOTOCARRO — COMPONENTES EXCLUSIVOS
    # --------------------------------------------------------
    {
        "SISTEMA": "MOTOCARRO",
        "SUBSISTEMA": "DIFERENCIAL",
        "COMPONENTE": "Corona y Piñón",
        "DEFINICION": "Transfiere potencia a las ruedas traseras del motocarro.",
        "TAGS": "motocarro, diferencial",
        "APLICA_A": "Motocarro"
    },
    {
        "SISTEMA": "MOTOCARRO",
        "SUBSISTEMA": "ELECTRICO",
        "COMPONENTE": "Alternador Carguero",
        "DEFINICION": "Genera corriente para el sistema eléctrico del motocarro.",
        "TAGS": "alternador, carguero, electrico",
        "APLICA_A": "Motocarro"
    },
]

# ----------------------------------------------------------------------------------
# GUARDAR CSV
# ----------------------------------------------------------------------------------

with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=TAXONOMIA[0].keys())
    writer.writeheader()
    writer.writerows(TAXONOMIA)

# ----------------------------------------------------------------------------------
# GUARDAR JSON
# ----------------------------------------------------------------------------------

with open(JSON_OUT, "w", encoding="utf-8") as f:
    json.dump(TAXONOMIA, f, indent=2, ensure_ascii=False)

print("\n===========================================")
print("  ✔ Taxonomía SRM–QK–ADSI v1 Generada")
print("  Archivos:")
print(f"   → {CSV_OUT}")
print(f"   → {JSON_OUT}")
print("===========================================\n")
