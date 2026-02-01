# -*- coding: utf-8 -*-
"""
brand_landing_generator_v2.4.py
Genera landings HTML + CSS por marca, con index.html y logs claros.
"""

import os
import json

BASE = r"C:\SRM_ADSI\08_branding"
LANDINGS = os.path.join(BASE, "landings")
CSS_DIR = os.path.join(LANDINGS, "css")
os.makedirs(LANDINGS, exist_ok=True)
os.makedirs(CSS_DIR, exist_ok=True)

INDEX_JSON = os.path.join(BASE, "branding_index.json")

TEMPLATE_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>{brand} — Landing</title>
<link rel="stylesheet" href="css/{brand}.css">
</head>
<body>
<header>
  <img src="{logo}" alt="{brand} logo" class="logo">
  <h1>{brand}</h1>
</header>
<section class="hero">
  <h2>{brand}</h2>
  <p>Landing generada automáticamente por ADSI.</p>
</section>
</body>
</html>
"""

TEMPLATE_CSS = """
body {{
  margin: 0;
  font-family: Arial, sans-serif;
  background-color: {bg};
}}
.logo {{
  width: 160px;
  margin: 20px;
}}
header {{
  background-color: {primary};
  padding: 10px;
  color: white;
}}
"""

def cargar_json(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    print("\n==============================================")
    print("   LANDING GENERATOR v2.4 (FIXED)")
    print("==============================================\n")

    index = cargar_json(INDEX_JSON)

    if not index:
        print("❌ ERROR: No existe branding_index.json")
        return

    marcas = index.get("brands", [])

    if not marcas:
        print("❌ No hay marcas dentro de branding_index.json")
        return

    for item in marcas:
        marca = item["brand"]
        logo = item["logo"]
        palette_path = item["palette"]

        print(f"\n→ Generando landing para: {marca}")

        paleta = cargar_json(palette_path)
        if not paleta:
            print(f"   ⚠ Paleta no encontrada, usando fallback neutro")
            primary = "#333333"
            bg = "#ffffff"
        else:
            primary = paleta["colors"]["primary"]
            bg = paleta["background"]["light"]

        # Generar HTML
        html_out = os.path.join(LANDINGS, f"{marca}.html")
        with open(html_out, "w", encoding="utf-8") as f:
            f.write(
                TEMPLATE_HTML.format(
                    brand=marca,
                    logo=os.path.relpath(logo, LANDINGS).replace("\\", "/")
                )
            )

        # Generar CSS
        css_out = os.path.join(CSS_DIR, f"{marca}.css")
        with open(css_out, "w", encoding="utf-8") as f:
            f.write(
                TEMPLATE_CSS.format(
                    primary=primary,
                    bg=bg
                )
            )

        print(f"   ✔ HTML generado → {html_out}")
        print(f"   ✔ CSS generado  → {css_out}")

    # Generar INDEX
    index_file = os.path.join(LANDINGS, "index.html")
    with open(index_file, "w", encoding="utf-8") as f:
        f.write("<h1>Landings Generadas</h1>\n<ul>\n")
        for item in marcas:
            m = item["brand"]
            f.write(f'<li><a href="{m}.html">{m}</a></li>\n')
        f.write("</ul>\n")

    print("\n==============================================")
    print("   ✔ TODAS LAS LANDINGS GENERADAS (v2.4)")
    print("   ✔ INDEX CREADO")
    print("==============================================\n")

if __name__ == "__main__":
    main()
