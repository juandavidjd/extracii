import os
import json

BASE = r"C:\SRM_ADSI\08_branding"
OUT = os.path.join(BASE, "brand_index.json")

def main():
    palettes = os.path.join(BASE, "palettes")
    logos = os.path.join(BASE, "logos_optimized")
    landings = os.path.join(BASE, "landings")
    backgrounds = os.path.join(BASE, "backgrounds")

    index = {}

    for p in os.listdir(palettes):
        if not p.endswith("_palette.json"):
            continue

        cliente = p.replace("_palette.json", "")
        palette_file = os.path.join(palettes, p)

        index[cliente] = {
            "palette": palette_file,
            "logo_512": os.path.join(logos, f"{cliente}_logo_512.png"),
            "logo_1024": os.path.join(logos, f"{cliente}_logo_1024.png"),
            "favicon": os.path.join(logos, f"{cliente}_favicon_64.png"),
            "landing": os.path.join(landings, cliente, "index.html"),
            "background": os.path.join(backgrounds, f"{cliente}_bg.png")
        }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=4)

    print("\n==============================================")
    print("   ✔ BRANDING INDEX GENERADO")
    print(f"   Archivo: {OUT}")
    print("==============================================")

if __name__ == "__main__":
    main()
