# -*- coding: utf-8 -*-
"""
brand_palette_autogen_v1.py
Genera paletas de colores ADSI v2.2 basadas en el color dominante de cada logo PNG.
"""

import os
import json
from PIL import Image
from collections import Counter

BASE_DIR = r"C:\SRM_ADSI\08_branding"
LOGOS_DIR = os.path.join(BASE_DIR, "logos_optimized")
PALETTES_DIR = os.path.join(BASE_DIR, "palettes")

os.makedirs(PALETTES_DIR, exist_ok=True)

def color_dominante(path):
    img = Image.open(path).convert("RGB")
    img = img.resize((50, 50))
    pixels = list(img.getdata())
    contador = Counter(pixels).most_common(1)[0][0]
    return contador

def generar_paleta(hex_primary):
    r = int(hex_primary[1:3], 16)
    g = int(hex_primary[3:5], 16)
    b = int(hex_primary[5:7], 16)

    def clamp(x): return max(0, min(255, x))

    secondary = f"#{clamp(r-40):02x}{clamp(g-40):02x}{clamp(b-40):02x}"
    accent = f"#{clamp(r+40):02x}{clamp(g+40):02x}{clamp(b+40):02x}"
    neutral = "#f4f4f4"
    dark = "#111111"

    return {
        "colors": {
            "primary": hex_primary,
            "secondary": secondary,
            "accent": accent,
            "neutral": neutral,
            "dark": dark
        },
        "background": {
            "light": "#ffffff",
            "dark": "#000000"
        }
    }

def rgb_to_hex(r, g, b):
    return "#{:02x}{:02x}{:02x}".format(r, g, b)

def main():
    print("\n==============================================")
    print("   GENERADOR DE PALETAS — AUTO v1")
    print("==============================================\n")

    logos = [f for f in os.listdir(LOGOS_DIR) if f.lower().endswith(".png")]

    if not logos:
        print("❌ No se encontraron logos PNG en:", LOGOS_DIR)
        return

    for logo in logos:
        marca = os.path.splitext(logo)[0]
        ruta_logo = os.path.join(LOGOS_DIR, logo)
        ruta_paleta = os.path.join(PALETTES_DIR, f"{marca}_palette.json")

        print(f"→ Procesando marca: {marca}")

        dom = color_dominante(ruta_logo)
        hex_primary = rgb_to_hex(dom[0], dom[1], dom[2])
        paleta = generar_paleta(hex_primary)

        with open(ruta_paleta, "w", encoding="utf-8") as f:
            json.dump({"brand": marca, **paleta}, f, indent=4)

        print(f"   ✔ Paleta generada: {ruta_paleta}")

    print("\n✔ Finalizado. Paletas autogeneradas en:")
    print(PALETTES_DIR)

if __name__ == "__main__":
    main()
