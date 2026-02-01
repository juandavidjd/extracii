#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
====================================================================================
 v26_unifier.py — SRM–QK–ADSI
 UNIFICADOR MAESTRO DE DATOS (FASE 2)
====================================================================================

Objetivo:
- Consumir los extract_*.csv generados por v26_extract.py
- Unificar todos los clientes en un conocimiento común
- Normalizar campos, generar nombre_rico_final, corregir ruido comercial
- Generar knowledge_base_unificada.csv y knowledge_base_unificada.json

Este archivo será la base para:
 ✔ Renombrador v26
 ✔ Generador 360°
 ✔ Compilador Shopify
 ✔ Modelo Lovely.dev
 ✔ API SRM–ADSI
====================================================================================
"""

import os
import re
import json
import pandas as pd
from pathlib import Path

BASE_DIR = Path(r"C:\img")

CLIENTES = [
    "Bara", "DFG", "Duna", "Japan",
    "Kaiqi", "Leo", "Store", "Vaisand", "Yokomar"
]

# ==============================================================================
# UTILIDADES
# ==============================================================================

def normalize_text(t):
    if pd.isna(t): 
        return ""
    t = str(t).strip()
    t = re.sub(r"\s+", " ", t)
    return t

def clean_codes(t):
    """
    Elimina:
    - prefijos 1-11-131
    - sufijos 1010115
    - códigos 2, 3, 85
    - SKUs DALU017
    """
    if not isinstance(t, str):
        return ""
    t = t.upper()

    # Eliminar códigos tipo 1-11-131 / 1-2-300
    t = re.sub(r"\b\d{1,4}(-\d{1,4}){1,3}\b", "", t)

    # Eliminar códigos tipo 1010115
    t = re.sub(r"\b\d{5,10}\b", "", t)

    # Eliminar referencias cortas tipo 2 / 3 / 85
    t = re.sub(r"\b\d{1,3}\b", "", t)

    # Eliminar SKUs tipo DALU017
    t = re.sub(r"\b[A-Z]{2,6}\d{2,6}\b", "", t)

    # Limpieza final
    t = re.sub(r"\s+", " ", t).strip()
    return t

def enrich_nombre_rico(desc):
    """
    Genera un nombre rico final para usarse en:
    - Renombrado SEO
    - Shopify
    - Imagen final
    """
    d = normalize_text(desc)
    d = clean_codes(d)
    d = re.sub(r"[^\w\s\-\(\)]", "", d)
    d = d.replace("  ", " ").strip()
    return d.upper()

# ==============================================================================
# DETECCIÓN SEMÁNTICA (sistema / subsistema / componente)
# ==============================================================================

def detect_taxonomia(desc):
    d = desc.lower()

    # MOTOR
    if any(w in d for w in ["piston", "cilindro", "biela", "culata", "retenedor motor"]):
        return "MOTOR", "BLOQUE MOTOR", "COMPONENTE MOTOR"

    # CLUTCH / TRANSMISIÓN
    if any(w in d for w in ["clutch", "embrague", "arrastre", "cadena", "piñon", "sprocket"]):
        return "TRANSMISIÓN", "EMBRAGUE / ARRRASTRE", "COMPONENTE TRANSMISIÓN"

    # FRENOS
    if any(w in d for w in ["pastilla", "banda", "zapatas", "bomba de freno", "disco"]):
        return "FRENOS", "FRENADO", "COMPONENTE FRENO"

    # ELÉCTRICO
    if any(w in d for w in ["bobina", "cdi", "relay", "regulador", "rectificador", "estator", "bob luces"]):
        return "ELÉCTRICO", "ENCENDIDO / CARGA", "COMPONENTE ELÉCTRICO"

    # SUSPENSIÓN
    if any(w in d for w in ["amortiguador", "barra", "tijera", "suspensión"]):
        return "SUSPENSIÓN", "DELANTERA / TRASERA", "COMPONENTE SUSPENSIÓN"

    # DIRECCIÓN
    if "manillar" in d or "direccion" in d:
        return "DIRECCIÓN", "CONTROL", "COMPONENTE DIRECCIÓN"

    # RUEDAS
    if any(w in d for w in ["llanta", "rin", "balinera"]):
        return "RUEDAS", "EJE / RODAMIENTO", "COMPONENTE RUEDAS"

    # ILUMINACIÓN
    if any(w in d for w in ["faro", "stop", "direccional"]):
        return "ILUMINACIÓN", "SEÑALIZACIÓN", "COMPONENTE ILUMINACIÓN"

    # MOTOCARRO
    if any(w in d for w in ["175", "205", "re", "motocarro"]):
        return "MOTOCARRO", "PLANTA COMPLETA", "COMPONENTE MOTOCARRO"

    return "GENÉRICO", "UNIVERSAL", "UNIVERSAL"

# ==============================================================================
# UNIFICADOR
# ==============================================================================

def unify_all():
    print("\n=== UNIFICADOR v26 SRM–QK–ADSI ===\n")

    master_rows = []

    for cli in CLIENTES:
        print(f"[✔] Procesando cliente: {cli}")

        extract_file = BASE_DIR / f"extract_{cli}_raw.csv"
        if not extract_file.exists():
            print(f"   → ADVERTENCIA: No existe extract_{cli}_raw.csv, saltando…")
            continue

        df = pd.read_csv(extract_file, encoding="utf-8")

        # Normalizar columnas esperadas
        for col in ["descripcion", "precio", "imagen_original", "fotos_detectadas"]:
            if col not in df.columns:
                df[col] = ""

        # Procesar fila por fila
        for _, row in df.iterrows():

            desc = normalize_text(row["descripcion"])

            # Nombre rico final
            nombre_rico_final = enrich_nombre_rico(desc)

            # Taxonomía
            sistema, subsistema, componente = detect_taxonomia(desc)

            # Datos finales
            master_rows.append({
                "cliente": cli,
                "descripcion": desc,
                "nombre_rico_final": nombre_rico_final,
                "precio": row["precio"],
                "imagen_original": row["imagen_original"],
                "fotos_detectadas": row["fotos_detectadas"],
                "sistema": sistema,
                "subsistema": subsistema,
                "componente": componente
            })

    # Convertir a DataFrame
    df_out = pd.DataFrame(master_rows)

    # Exportar
    out_csv = BASE_DIR / "knowledge_base_unificada.csv"
    out_json = BASE_DIR / "knowledge_base_unificada.json"

    df_out.to_csv(out_csv, index=False, encoding="utf-8")

    with open(out_json, "w", encoding="utf-8") as f:
        f.write(df_out.to_json(orient="records", force_ascii=False, indent=4))

    print("\n=== PROCESO COMPLETO ===")
    print(f"[✔] knowledge_base_unificada.csv creado")
    print(f"[✔] knowledge_base_unificada.json creado\n")


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    unify_all()
