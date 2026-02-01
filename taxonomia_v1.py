#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
taxonomia_v1.py
Genera la Taxonomía SRM–QK–ADSI v1 (estática, estándar)
"""

import os
import json
import pandas as pd

ROOT = r"C:/SRM_ADSI"
OUT_DIR = os.path.join(ROOT, "03_knowledge_base")
os.makedirs(OUT_DIR, exist_ok=True)

# === TAXONOMÍA ESTÁNDAR SRM–ADSI v1 ===
TAXONOMIA = [
    {"SISTEMA": "MOTOR", "SUBSISTEMA": "Culata", "COMPONENTE": "Balancines"},
    {"SISTEMA": "MOTOR", "SUBSISTEMA": "Culata", "COMPONENTE": "Arbol de levas"},
    {"SISTEMA": "MOTOR", "SUBSISTEMA": "Encendido", "COMPONENTE": "Bujías"},
    {"SISTEMA": "MOTOR", "SUBSISTEMA": "Encendido", "COMPONENTE": "Bobinas"},
    {"SISTEMA": "MOTOR", "SUBSISTEMA": "Alimentación", "COMPONENTE": "Carburador"},
    {"SISTEMA": "MOTOR", "SUBSISTEMA": "Alimentación", "COMPONENTE": "Filtro aire"},

    {"SISTEMA": "TRANSMISIÓN", "SUBSISTEMA": "Cadena", "COMPONENTE": "Kit arrastre"},
    {"SISTEMA": "TRANSMISIÓN", "SUBSISTEMA": "Caja", "COMPONENTE": "Piñones"},
    {"SISTEMA": "TRANSMISIÓN", "SUBSISTEMA": "Embrague", "COMPONENTE": "Clutch"},

    {"SISTEMA": "FRENOS", "SUBSISTEMA": "Disco", "COMPONENTE": "Pastillas"},
    {"SISTEMA": "FRENOS", "SUBSISTEMA": "Tambor", "COMPONENTE": "Bandas"},
    {"SISTEMA": "FRENOS", "SUBSISTEMA": "Hidráulico", "COMPONENTE": "Bomba freno"},

    {"SISTEMA": "SUSPENSIÓN", "SUBSISTEMA": "Delantera", "COMPONENTE": "Tijera"},
    {"SISTEMA": "SUSPENSIÓN", "SUBSISTEMA": "Trasera", "COMPONENTE": "Amortiguador"},

    {"SISTEMA": "ELECTRICIDAD", "SUBSISTEMA": "Iluminación", "COMPONENTE": "Stop"},
    {"SISTEMA": "ELECTRICIDAD", "SUBSISTEMA": "Iluminación", "COMPONENTE": "Direccionales"},
    {"SISTEMA": "ELECTRICIDAD", "SUBSISTEMA": "Arranque", "COMPONENTE": "Motor arranque"},

    {"SISTEMA": "CHASIS", "SUBSISTEMA": "Carrocería", "COMPONENTE": "Guardabarros"},
    {"SISTEMA": "CHASIS", "SUBSISTEMA": "Carrocería", "COMPONENTE": "Tapa lateral"},
]

def main():
    df = pd.DataFrame(TAXONOMIA)

    csv_out = os.path.join(OUT_DIR, "srm_taxonomia_v1.csv")
    json_out = os.path.join(OUT_DIR, "srm_taxonomia_v1.json")

    df.to_csv(csv_out, index=False)
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(TAXONOMIA, f, indent=2, ensure_ascii=False)

    print("\n===========================================")
    print("  ✔ Taxonomía SRM–QK–ADSI v1 Generada")
    print("  Archivos:")
    print(f"   → {csv_out}")
    print(f"   → {json_out}")
    print("===========================================\n")


if __name__ == "__main__":
    main()
