#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SRM–QK–ADSI — BRANDING OPTIMIZER v1.1 (FIX)
Modo D — Conservación total del arte
Genera:
 - PNG optimizado 1024px (sin recorte, sin alterar)
 - SVG vectorizado (sin modificar arte)
Lee reglas desde brand_rules.json
"""

import os
import json
from PIL import Image
import shutil
import subprocess

BASE_LOGOS = r"C:/img"
OUT_DIR = r"C:/SRM_ADSI/08_branding/logos_optimized"
RULES_FILE = r"C:/SRM_ADSI/08_branding/brand_rules.json"


# ------------------------------------------------------------------------------------
# UTILIDADES
# ------------------------------------------------------------------------------------

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def load_rules():
    if os.path.exists(RULES_FILE):
        with open(RULES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    print("⚠ No se encontró brand_rules.json — usando reglas globales por defecto.")
    return {"global": {"safe_mode": True}}

def optimize_png(input_path, output_path, max_size=1024, preserve_alpha=True):
    """Optimiza PNG sin alterar arte, sin recortar, sin limpiar."""
    img = Image.open(input_path)

    # Convertimos a modo seguro
    if preserve_alpha:
        img = img.convert("RGBA")
    else:
        img = img.convert("RGB")

    # Reducción segura sin modificar arte
    w, h = img.size
    if max(w, h) > max_size:
        scale = max_size / float(max(w, h))
        new_size = (int(w * scale), int(h * scale))
        img = img.resize(new_size, Image.LANCZOS)

    # Guardar PNG optimizado
    img.save(output_path, optimize=True)


def convert_to_svg(input_path, output_path):
    """
    Intenta convertir PNG a SVG usando potrace.
    Si no existe potrace o convert, genera fallback.
    """
    try:
        temp_bmp = input_path.replace(".png", "_temp.bmp")
        temp_pbm = input_path.replace(".png", "_temp.pbm")

        img = Image.open(input_path).convert("L")
        img.save(temp_bmp)

        # Intentamos convertir BMP -> PBM
        subprocess.run(["convert", temp_bmp, temp_pbm], shell=True)

        # Intentamos vectorización con potrace
        subprocess.run(["potrace", temp_pbm, "-s", "-o", output_path], shell=True)

        # Limpiar basura
        for t in [temp_bmp, temp_pbm]:
            if os.path.exists(t):
                os.remove(t)

    except Exception:
        # Fallback SVG contenedor
        fallback_path = output_path.replace(".svg", "_fallback.png")
        shutil.copy(input_path, fallback_path)
        print(f"⚠ Potrace no disponible → SVG fallback generado: {fallback_path}")


# ------------------------------------------------------------------------------------
# PROCESAR LOGOS
# ------------------------------------------------------------------------------------

def process_logo(name, path, rules, global_rules):
    print(f"\n→ Procesando {name}...")

    try:
        brand_rules = rules.get(name, global_rules)

        max_size     = brand_rules.get("max_resize", 1024)
        preserve_alpha = brand_rules.get("preserve_transparency", True)
        vectorize    = brand_rules.get("vectorize_svg", True)
        png_export   = brand_rules.get("png_export", True)

        # ARCHIVOS DE SALIDA
        png_out = os.path.join(OUT_DIR, f"{name}.png")
        svg_out = os.path.join(OUT_DIR, f"{name}.svg")

        # PNG optimizado
        if png_export:
            optimize_png(path, png_out, max_size=max_size, preserve_alpha=preserve_alpha)

        # SVG vectorizado
        if vectorize:
            convert_to_svg(png_out, svg_out)

        print(f"  ✔ OK — {name}")

    except Exception as e:
        print(f"  ❌ Error procesando {name}: {e}")


def main():
    print("\n==========================================")
    print(" SRM–QK–ADSI — BRANDING OPTIMIZER v1.1 (FIX)")
    print("==========================================\n")

    ensure_dir(OUT_DIR)
    rules = load_rules()
    global_rules = rules.get("global", {})

    for file in os.listdir(BASE_LOGOS):
        if not file.lower().endswith((".png", ".jpg", ".jpeg")):
            continue

        path = os.path.join(BASE_LOGOS, file)
        name = os.path.splitext(file)[0]

        process_logo(name, path, rules, global_rules)

    print("\n==========================================")
    print(" ✔ BRANDING OPTIMIZADO COMPLETADO (v1.1)")
    print(" Archivos en:", OUT_DIR)
    print("==========================================\n")


if __name__ == "__main__":
    main()
