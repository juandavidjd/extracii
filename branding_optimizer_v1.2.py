#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SRM–QK–ADSI — BRANDING OPTIMIZER v1.2
Windows-SAFE VERSION — NO potrace, NO convert
Modo D — Conservación total del arte

Genera:
 - PNG optimizado (sin alterar)
 - SVG WRAPPER (incrusta PNG sin vectorizar)
"""

import os
import json
from PIL import Image
import base64

BASE_LOGOS = r"C:/img"
OUT_DIR = r"C:/SRM_ADSI/08_branding/logos_optimized"
RULES_FILE = r"C:/SRM_ADSI/08_branding/brand_rules.json"


# -------------------------------------------------------------------
# UTILIDADES
# -------------------------------------------------------------------

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def load_rules():
    if os.path.exists(RULES_FILE):
        with open(RULES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    print("⚠ No existe brand_rules.json — usando reglas default")
    return {"global": {"max_resize": 1024, "preserve_transparency": True}}


def optimize_png(input_path, output_path, max_size=1024, preserve_alpha=True):
    """Optimiza PNG sin alterar arte original"""
    img = Image.open(input_path)

    if preserve_alpha:
        img = img.convert("RGBA")
    else:
        img = img.convert("RGB")

    w, h = img.size
    if max(w, h) > max_size:
        scale = max_size / float(max(w, h))
        new_size = (int(w * scale), int(h * scale))
        img = img.resize(new_size, Image.LANCZOS)

    img.save(output_path, optimize=True)


def create_svg_wrapper(png_path, svg_path):
    """Crea un SVG que contiene el PNG como <image> (sin vectorizar)"""
    with open(png_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    img = Image.open(png_path)
    w, h = img.size

    svg = f"""
<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <image href="data:image/png;base64,{b64}" width="{w}" height="{h}" />
</svg>
    """

    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg)


# -------------------------------------------------------------------
# PROCESADOR
# -------------------------------------------------------------------

def process_logo(name, path, rules, global_rules):
    print(f"\n→ Procesando {name}...")

    try:
        brand_rules = rules.get(name, global_rules)

        max_size = brand_rules.get("max_resize", 1024)
        preserve_alpha = brand_rules.get("preserve_transparency", True)

        png_out = os.path.join(OUT_DIR, f"{name}.png")
        svg_out = os.path.join(OUT_DIR, f"{name}.svg")

        # PNG optimizado
        optimize_png(path, png_out, max_size=max_size, preserve_alpha=preserve_alpha)

        # SVG wrapper (NO vectorización)
        create_svg_wrapper(png_out, svg_out)

        print(f"  ✔ OK — {name}")

    except Exception as e:
        print(f"  ❌ Error en {name}: {e}")


def main():
    print("\n========================================")
    print(" SRM–QK–ADSI — BRANDING OPTIMIZER v1.2")
    print("  Windows-SAFE — Sin potrace, sin convert")
    print("========================================\n")

    ensure_dir(OUT_DIR)
    rules = load_rules()
    global_rules = rules.get("global", {})

    for file in os.listdir(BASE_LOGOS):
        if file.lower().endswith((".png", ".jpg", ".jpeg")):
            path = os.path.join(BASE_LOGOS, file)
            name = os.path.splitext(file)[0]
            process_logo(name, path, rules, global_rules)

    print("\n========================================")
    print(" ✔ BRANDING COMPLETADO (v1.2)")
    print(" Out:", OUT_DIR)
    print("========================================\n")


if __name__ == "__main__":
    main()
