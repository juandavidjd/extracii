# -*- coding: utf-8 -*-
"""
branding_index_rebuilder_v1.py
Reconstruye branding_index.json detectando marcas, logos y paletas.
"""

import os
import json

BASE_DIR = r"C:\SRM_ADSI\08_branding"
LOGOS_DIR = os.path.join(BASE_DIR, "logos_optimized")
PALETTES_DIR = os.path.join(BASE_DIR, "palettes")
OUTPUT = os.path.join(BASE_DIR, "branding_index.json")

def main():
    print("\n==============================================")
    print("   RECONSTRUCTOR DE BRANDING INDEX v1")
    print("==============================================\n")

    logos = {os.path.splitext(f)[0] for f in os.listdir(LOGOS_DIR) if f.lower().endswith(".png")}
    paletas = {os.path.splitext(f)[0].replace("_palette", "") for f in os.listdir(PALETTES_DIR)}

    marcas = sorted(logos.union(paletas))

    data = []
    for m in marcas:
        entry = {
            "brand": m,
            "logo": os.path.join(LOGOS_DIR, f"{m}.png"),
            "palette": os.path.join(PALETTES_DIR, f"{m}_palette.json")
        }
        data.append(entry)

        print(f"✔ {m}")

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump({"brands": data}, f, indent=4)

    print("\n✔ Archivo creado:")
    print(OUTPUT)

if __name__ == "__main__":
    main()
