#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
====================================================================================
 v26_360.py — GENERADOR 360° SRM–QK–ADSI
====================================================================================

Objetivo:
- Convertir knowledge_base_unificada.csv en perfiles completos 360°
- Generar:
    ✔ json_360_por_cliente/
    ✔ json_360_master.json
    ✔ csv_360_por_cliente/
- Producir título, SEO, tags, fitment preliminar, atributos, descripción comercial
- Normalizar datos para Shopify, Motor SRM–ADSI y Lovely.dev

Este archivo constituye el CEREBRO DE PRODUCTO de la plataforma.
====================================================================================
"""

import os
import re
import json
import pandas as pd
from pathlib import Path

BASE_DIR = Path(r"C:\img")
INPUT_FILE = BASE_DIR / "knowledge_base_unificada.csv"

OUT_JSON_DIR = BASE_DIR / "json_360_por_cliente"
OUT_CSV_DIR = BASE_DIR / "csv_360_por_cliente"
MASTER_JSON = BASE_DIR / "json_360_master.json"

os.makedirs(OUT_JSON_DIR, exist_ok=True)
os.makedirs(OUT_CSV_DIR, exist_ok=True)

# =================================================================================
# UTILIDADES
# =================================================================================

def generar_titulo(nombre_rico):
    """Genera título comercial tipo catálogo premium"""
    nombre_rico = nombre_rico.title()
    nombre_rico = nombre_rico.replace("Cdi", "CDI").replace("Bob ", "Bob ")
    return nombre_rico

def generar_tags(desc):
    words = re.sub(r"[^\w\s]", " ", desc.lower()).split()
    filtered = [w for w in words if len(w) > 3]
    tags = list(dict.fromkeys(filtered))  # dedupe
    return ", ".join(tags[:15])

def infer_fitment(desc):
    """
    Fitment preliminar basado en texto.
    El 360° final lo enriquecerá Lovely.dev con IA y modelos externos.
    """
    d = desc.lower()
    models = []

    # Honda
    if "cb" in d or "c70" in d or "xl" in d:
        models.append("Honda (varios modelos)")

    # Bajaj / Pulsar
    if "pulsar" in d or "bajaj" in d:
        models.append("Bajaj – Pulsar Series")

    # Akt
    if "akt" in d or "cr4" in d or "tt" in d:
        models.append("AKT (varios modelos)")

    # TVS
    if "tvs" in d:
        models.append("TVS (varios modelos)")

    # Suzuki
    if "gixxer" in d or "gn" in d or "gs" in d:
        models.append("Suzuki (varios modelos)")

    # Motocarro
    if "re" in d or "175" in d or "205" in d:
        models.append("Motocarro Bajaj RE 175 / 205")

    return models

def generar_descripcion_larga(nombre, sistema, subsistema, componente):
    return (
        f"{nombre}. Pertenece al sistema {sistema}, subsistema {subsistema}, "
        f"dentro del componente {componente}. Producto optimizado para alto desempeño "
        f"dentro del ecosistema SRM–QK–ADSI, apto para procesos de distribución, "
        f"venta minorista y servicio técnico certificado."
    )

# =================================================================================
# GENERADOR 360°
# =================================================================================

def generar_perfil_360(row):
    """Construye el perfil completo del producto"""

    desc = row["descripcion"]
    nombre = row["nombre_rico_final"]
    sistema = row["sistema"]
    subsistema = row["subsistema"]
    componente = row["componente"]

    fitment = infer_fitment(desc)
    tags = generar_tags(desc)
    titulo = generar_titulo(nombre)
    descripcion_larga = generar_descripcion_larga(titulo, sistema, subsistema, componente)

    return {
        "cliente": row["cliente"],
        "titulo": titulo,
        "nombre_rico": nombre,
        "descripcion_corta": nombre,
        "descripcion_larga": descripcion_larga,
        "sistema": sistema,
        "subsistema": subsistema,
        "componente": componente,
        "precio": row["precio"],

        "fitment": fitment,
        "tags": tags,

        "imagen_original": row["imagen_original"],
        "imagenes_detectadas": row["fotos_detectadas"],

        "sku_origen": "",
        "estado": "activo",

        "meta_seo_titulo": titulo,
        "meta_seo_descripcion": f"{titulo} – {sistema} / {subsistema}",

        "atributos": {
            "sistema": sistema,
            "subsistema": subsistema,
            "componente": componente,
            "fitment_modelos": fitment,
            "cliente_origen": row["cliente"]
        }
    }

# =================================================================================
# PROCESO PRINCIPAL
# =================================================================================

def main():
    print("\n=== GENERADOR 360° v26 SRM–QK–ADSI ===\n")

    if not INPUT_FILE.exists():
        print("❌ ERROR: No existe knowledge_base_unificada.csv")
        return

    df = pd.read_csv(INPUT_FILE)

    master_json_list = []
    clientes = df["cliente"].unique()

    for cli in clientes:
        df_cli = df[df["cliente"] == cli]
        out_rows = []

        print(f"[✔] Procesando cliente: {cli}")

        for _, row in df_cli.iterrows():
            perfil = generar_perfil_360(row)
            out_rows.append(perfil)
            master_json_list.append(perfil)

        # Guardar JSON del cliente
        out_json = OUT_JSON_DIR / f"{cli}_360.json"
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(out_rows, f, indent=4, ensure_ascii=False)

        # Guardar CSV del cliente
        out_csv = OUT_CSV_DIR / f"{cli}_360.csv"
        pd.DataFrame(out_rows).to_csv(out_csv, index=False, encoding="utf-8")

        print(f"   → JSON: {out_json}")
        print(f"   → CSV:  {out_csv}")

    # MASTER JSON 360° (todos los clientes)
    with open(MASTER_JSON, "w", encoding="utf-8") as f:
        json.dump(master_json_list, f, indent=4, ensure_ascii=False)

    print("\n=== PROCESO COMPLETO ===")
    print(f"[✔] json_360_por_cliente/")
    print(f"[✔] csv_360_por_cliente/")
    print(f"[✔] json_360_master.json")
    print("\nListo para FASE 4.\n")


# =================================================================================
# MAIN RUN
# =================================================================================

if __name__ == "__main__":
    main()
