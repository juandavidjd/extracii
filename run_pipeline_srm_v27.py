#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SRM–QK–ADSI — ORQUESTADOR v27
Incluye:
    PASO 0 → normalizador_csv_v1.py
    PASO 1 → taxonomia_v1.py
    PASO 2 → extractor_v2.py
    PASO 3 → unificador_v1.py
    PASO 4 → renombrador_v26.py
    PASO 5 → generador_360_v1.py
    PASO 6 → compilador_shopify_v2.py
    PASO 7 → generador_json_lovely_v2.py
    PASO 8 → lovely_installer_v1.py
"""

import subprocess
import time

STEPS = [
    ("PASO 0 — Normalizador CSV", "normalizador_csv_v1.py"),
    ("PASO 1 — Taxonomía SRM–QK–ADSI", "taxonomia_v1.py"),
    ("PASO 2 — Extractor v2", "extractor_v2.py"),
    ("PASO 3 — Unificador v1", "unificador_v1.py"),
    ("PASO 4 — Renombrador v26", "renombrador_v26.py"),
    ("PASO 5 — Generador 360° v1", "generador_360_v1.py"),
    ("PASO 6 — Compilador Shopify v3", "compilador_shopify_v3.py"),
    ("PASO 7 — Generador JSON Lovely v2", "generador_json_lovely_v2.py"),
    ("PASO 8 — Lovely Installer v1", "lovely_installer_v1.py"),
]


def run_step(name, script):
    print("\n===================================================")
    print(f"▶ {name}")
    print("===================================================")

    start = time.time()
    try:
        subprocess.check_call(["python", script])
        print(f"✔ OK: {name} completado ({round(time.time()-start,2)}s)")
        return True
    except Exception as e:
        print(f"❌ ERROR ejecutando {script}: {e}")
        print("⚠ El pipeline continuará.")
        return False


def main():
    print("\n===================================================")
    print("        🚀 SRM–QK–ADSI PIPELINE ORQUESTADOR v27")
    print("===================================================\n")

    results = {}

    for name, script in STEPS:
        ok = run_step(name, script)
        results[name] = ok

    print("\n===================================================")
    print("                 RESUMEN FINAL PIPELINE")
    print("===================================================")
    for name, ok in results.items():
        status = "✔ COMPLETADO" if ok else "❌ ERROR"
        print(f"{name}: {status}")

    print("\n===================================================")
    print("        🏁 PIPELINE SRM–QK–ADSI v27 FINALIZADO")
    print("===================================================\n")


if __name__ == "__main__":
    main()
