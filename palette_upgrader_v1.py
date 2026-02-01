import os
import json

BASE = r"C:\SRM_ADSI\08_branding\palettes"

def ensure_hex(c):
    if not c:
        return "#000000"
    c = c.strip()
    if not c.startswith("#"):
        c = "#" + c
    if len(c) == 4:  # formato #abc
        c = "#" + "".join([x*2 for x in c[1:]])
    return c.lower()

def upgrade_palette(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cliente = data.get("cliente") or os.path.basename(path).replace("_palette.json", "")

    # Detectar formato viejo
    if "palette" in data:
        raw_colors = [ensure_hex(c) for c in data["palette"]]
    elif "colors" in data:
        raw_colors = [ensure_hex(c["hex"]) for c in data["colors"]]
    else:
        raw_colors = ["#000000"]

    # Asegurar mínimo 5 colores
    while len(raw_colors) < 5:
        raw_colors.append(raw_colors[-1])

    upgraded = {
        "cliente": cliente,
        "colors": [
            {"role": "primary", "hex": raw_colors[0]},
            {"role": "secondary", "hex": raw_colors[1]},
            {"role": "accent", "hex": raw_colors[2]},
            {"role": "dark", "hex": raw_colors[3]},
            {"role": "light", "hex": raw_colors[4]}
        ]
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(upgraded, f, indent=4)

    print(f"  ✔ Paleta actualizada → {os.path.basename(path)}")

def main():
    print("\n==============================================")
    print("   SRM–QK–ADSI — PALETTE UPGRADER v1")
    print("==============================================\n")

    for file in os.listdir(BASE):
        if file.endswith("_palette.json"):
            upgrade_palette(os.path.join(BASE, file))

    print("\n==============================================")
    print("   ✔ PALETAS ACTUALIZADAS A v2.2")
    print("==============================================")

if __name__ == "__main__":
    main()
