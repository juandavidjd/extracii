import os
import json
from PIL import Image, ImageDraw, ImageFilter

PALETTE_DIR = r"C:\SRM_ADSI\08_branding\palettes"
OUT_DIR = r"C:\SRM_ADSI\08_branding\backgrounds"

os.makedirs(OUT_DIR, exist_ok=True)

def load_palette(cliente):
    pfile = os.path.join(PALETTE_DIR, f"{cliente}_palette.json")
    if not os.path.exists(pfile):
        return None

    data = json.load(open(pfile, "r", encoding="utf-8"))
    return [c["hex"] for c in data["colors"]]

def generate_gradient(colors, size=(1920, 1080)):
    img = Image.new("RGB", size, colors[0])
    draw = ImageDraw.Draw(img)
    w, h = size

    for i, col in enumerate(colors):
        draw.rectangle([0, int(i*h/len(colors)), w, int((i+1)*h/len(colors))], fill=col)

    return img.filter(ImageFilter.GaussianBlur(30))

def main():
    print("\n==============================================")
    print("   SRM–QK–ADSI — BACKGROUND GENERATOR v1")
    print("==============================================\n")

    for file in os.listdir(PALETTE_DIR):
        if not file.endswith("_palette.json"):
            continue

        cliente = file.replace("_palette.json", "")
        colors = load_palette(cliente)
        if not colors:
            print(f"  ⚠ No colors for {cliente}, skipping")
            continue

        bg = generate_gradient(colors)
        out_path = os.path.join(OUT_DIR, f"{cliente}_bg.png")
        bg.save(out_path)

        print(f"  ✔ Background generado → {out_path}")

    print("\n==============================================")
    print("   ✔ BACKGROUNDS COMPLETADOS")
    print("==============================================")

if __name__ == "__main__":
    main()
