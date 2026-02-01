import os
import json

PALETTE_DIR = r"C:\SRM_ADSI\08_branding\palettes"
LOGO_DIR = r"C:\SRM_ADSI\08_branding\logos_optimized"
BG_DIR = r"C:\SRM_ADSI\08_branding\backgrounds"
OUT_DIR = r"C:\SRM_ADSI\08_branding\landings"

os.makedirs(OUT_DIR, exist_ok=True)

TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>{cliente} — SRM–QK–ADSI Landing</title>
<style>
body {{
    margin:0;
    padding:0;
    background: url('../backgrounds/{cliente}_bg.png');
    background-size: cover;
    font-family: Arial, sans-serif;
    color: var(--primary-color);
}}
:root {{
    --primary-color: {p};
    --secondary-color: {s};
    --accent-color: {a};
    --dark-color: {d};
    --light-color: {l};
}}
header {{
    padding:40px;
    text-align:center;
}}
header img {{
    max-width:300px;
}}
.cta {{
    margin-top:80px;
    text-align:center;
}}
.cta a {{
    padding:15px 40px;
    background: var(--primary-color);
    color:white;
    border-radius:8px;
    text-decoration:none;
    font-size:22px;
}}
</style>
</head>
<body>
<header>
    <img src="../logos_optimized/{cliente}_logo_512.png">
</header>

<div class="cta">
    <a href="#">Ingresar a la Tienda</a>
</div>

</body>
</html>
"""

def load_palette(cliente):
    pfile = os.path.join(PALETTE_DIR, f"{cliente}_palette.json")
    if not os.path.exists(pfile):
        return None

    data = json.load(open(pfile, "r", encoding="utf-8"))
    return [c["hex"] for c in data["colors"]]

def main():
    print("\n==============================================")
    print("   SRM–QK–ADSI — LANDING GENERATOR v2.2")
    print("==============================================\n")

    for file in os.listdir(PALETTE_DIR):
        if not file.endswith("_palette.json"):
            continue

        cliente = file.replace("_palette.json", "")
        colors = load_palette(cliente)

        if not colors:
            print(f"  ⚠ Sin paleta: {cliente}")
            continue

        p, s, a, d, l = colors[:5]

        out_path = os.path.join(OUT_DIR, cliente)
        os.makedirs(out_path, exist_ok=True)

        html = TEMPLATE.format(cliente=cliente, p=p, s=s, a=a, d=d, l=l)

        with open(os.path.join(out_path, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)

        print(f"  ✔ Landing generada para {cliente}")

    print("\n==============================================")
    print("   ✔ LANDINGS COMPLETADAS")
    print("==============================================")

if __name__ == "__main__":
    main()
