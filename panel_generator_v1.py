# -*- coding: utf-8 -*-
"""
panel_generator_v1.py
Branding Control Panel PRO v1.0
Genera un panel visual para todas las marcas, leyendo:
- branding_index.json
- paletas
- landings
- logos
"""

import os
import json

BASE = r"C:\SRM_ADSI\08_branding"
LANDINGS = os.path.join(BASE, "landings")
CSS_DIR = os.path.join(LANDINGS, "css")
INDEX_JSON = os.path.join(BASE, "branding_index.json")

PANEL_OUT = os.path.join(BASE, "branding_panel.html")


def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_panel(brands):
    html = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Branding Control Panel PRO — ADSI</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;800&display=swap" rel="stylesheet">

<style>
body {
    margin: 0;
    padding: 1.8rem;
    font-family: 'Montserrat', sans-serif;
    background: #f4f5f7;
    color: #222;
}

h1 {
    margin-top: 0;
    font-size: 1.8rem;
    font-weight: 800;
    letter-spacing: 0.03em;
}

.panel-sub {
    color: #555;
    margin-bottom: 1.8rem;
    font-size: 0.95rem;
}

.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 1.2rem;
}

/* CARD */
.card {
    background: #fff;
    border-radius: 14px;
    padding: 1.2rem;
    box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    border: 1px solid #e5e5e5;
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.card-logo {
    background: #fafafa;
    border-radius: 12px;
    padding: 0.8rem 0.8rem;
    text-align: center;
    border: 1px solid #e0e0e0;
}

.card-logo img {
    max-width: 120px;
    max-height: 60px;
    object-fit: contain;
}

.brand-name {
    font-weight: 700;
    font-size: 1.2rem;
}

.palette-row {
    display: flex;
    gap: 6px;
}

.swatch {
    width: 26px;
    height: 26px;
    border-radius: 6px;
    border: 1px solid #dcdcdc;
}

.btn-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
}

.btn {
    display: inline-flex;
    padding: 0.45rem 0.9rem;
    text-decoration: none;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    border: 1px solid transparent;
    transition: 0.18s;
}

.btn-view {
    background: #111;
    color: #fff;
}

.btn-view:hover {
    background: #333;
}

.btn-css {
    background: #005eff;
    color: #fff;
}

.btn-css:hover {
    background: #0045c9;
}

.btn-json {
    background: #00a65a;
    color: #fff;
}

.btn-json:hover {
    background: #00894a;
}

.btn-folder {
    background: #e8e8e8;
    color: #333;
}

.btn-folder:hover {
    background: #d5d5d5;
}

.footer {
    margin-top: 2.5rem;
    font-size: 0.8rem;
    color: #777;
    text-align: center;
}

</style>
</head>
<body>

<h1>Branding Control Panel PRO</h1>
<p class="panel-sub">Vista centralizada de todas las marcas del ecosistema SRM–QK–ADSI.</p>

<div class="grid">
"""

    # -------------------------------------------------------
    # GENERATE CARDS
    # -------------------------------------------------------
    for b in brands:
        brand = b["brand"]
        logo = os.path.relpath(b["logo"], BASE).replace("\\", "/")
        palette_path = b["palette"]
        palette = load_json(palette_path)

        primary = palette["colors"]["primary"]
        secondary = palette["colors"]["secondary"]
        accent = palette["colors"]["accent"]
        neutral = palette["colors"]["neutral"]
        dark = palette["colors"]["dark"]

        html += f"""
<div class="card">

    <div class="card-logo">
        <img src="{logo}" alt="{brand}">
    </div>

    <div class="brand-name">{brand}</div>

    <div class="palette-row">
        <div class="swatch" style="background:{primary};"></div>
        <div class="swatch" style="background:{secondary};"></div>
        <div class="swatch" style="background:{accent};"></div>
        <div class="swatch" style="background:{neutral};"></div>
        <div class="swatch" style="background:{dark};"></div>
    </div>

    <div class="btn-row">
        <a class="btn btn-view" href="landings/{brand}.html" target="_blank">Landing</a>
        <a class="btn btn-css" href="landings/css/{brand}.css" target="_blank">CSS</a>
        <a class="btn btn-json" href="{palette_path}" target="_blank">Paleta JSON</a>
        <a class="btn btn-folder" href="#" onclick="alert('Abra la carpeta manualmente en C:\\\\SRM_ADSI\\\\08_branding\\\\')">Carpeta</a>
    </div>

</div>
"""

    # -------------------------------------------------------
    # FOOTER
    # -------------------------------------------------------
    html += """
</div>

<div class="footer">
    ADSI Suite — SRM–QK–ADSI · Conocimiento · Colaboración · Tecnología
</div>

</body>
</html>
"""

    return html


def main():
    index = load_json(INDEX_JSON)
    if not index:
        print("❌ ERROR: No existe branding_index.json")
        return

    brands = index.get("brands", [])
    if not brands:
        print("❌ No hay marcas en branding_index.json")
        return

    html = generate_panel(brands)

    with open(PANEL_OUT, "w", encoding="utf-8") as f:
        f.write(html)

    print("\n==============================================")
    print("  ✔ Branding Control Panel PRO generado")
    print(f"  ✔ Archivo: {PANEL_OUT}")
    print("==============================================\n")


if __name__ == "__main__":
    main()
