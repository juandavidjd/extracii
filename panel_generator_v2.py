# -*- coding: utf-8 -*-
"""
panel_generator_v2.py
Branding Control Panel PRO v2.0 — ADSI Suite
Incluye:
- Previews automáticos (tile, banner)
- Hover gallery
- Diagnóstico visual
- UI profesional con tipografía Montserrat
"""

import os
import json

BASE = r"C:\SRM_ADSI\08_branding"
LANDINGS = os.path.join(BASE, "landings")
CSS_DIR = os.path.join(LANDINGS, "css")
PREVIEWS = os.path.join(BASE, "previews")
INDEX_JSON = os.path.join(BASE, "branding_index.json")

OUT_FILE = os.path.join(BASE, "branding_panel.html")


# -----------------------------
# Helpers
# -----------------------------
def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def file_exists(path):
    return os.path.exists(path)


# -----------------------------
# Main Panel Generation
# -----------------------------
def generate_panel(brands):

    html = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Branding Control Panel PRO — v2.0</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;800&display=swap" rel="stylesheet">

<style>

body {
    margin: 0;
    padding: 2rem;
    background: #f5f6f8;
    font-family: 'Montserrat', sans-serif;
    color: #222;
}

h1 {
    margin: 0 0 0.5rem 0;
    font-size: 2rem;
    font-weight: 800;
}

.sub {
    margin-top: 0;
    color: #555;
    font-size: 1rem;
    margin-bottom: 1.8rem;
}

.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(290px, 1fr));
    gap: 1.4rem;
}

/* CARD */
.card {
    background: #ffffff;
    border-radius: 16px;
    padding: 1.2rem 1.2rem;
    border: 1px solid #e1e1e1;
    box-shadow: 0 4px 15px rgba(0,0,0,0.04);
    transition: 0.25s ease;
    position: relative;
}

.card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 22px rgba(0,0,0,0.08);
}

.card-logo {
    background: #fafafa;
    border-radius: 12px;
    padding: 0.8rem;
    border: 1px solid #ddd;
    text-align: center;
}

.card-logo img {
    max-width: 140px;
    max-height: 70px;
    object-fit: contain;
}

/* Preview tile */
.preview-tile-container {
    position: relative;
    margin-top: 0.7rem;
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid #ddd;
    cursor: pointer;
}

.preview-tile-container img {
    width: 100%;
    display: block;
}

/* Hover gallery — preview banner */
.preview-hover {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 0;
    overflow: hidden;
    transition: height 0.3s ease;
    border-radius: 12px;
    box-shadow: 0 6px 20px rgba(0,0,0,0.2);
    z-index: 50;
}

.preview-hover img {
    width: 100%;
    display: block;
}

/* Show hover gallery on tile hover */
.preview-tile-container:hover .preview-hover {
    height: 180px; /* Banner height */
}

.brand-name {
    margin-top: 0.9rem;
    font-weight: 700;
    font-size: 1.25rem;
}

.palette-row {
    margin-top: 0.35rem;
    display: flex;
    gap: 6px;
}

.swatch {
    width: 28px;
    height: 28px;
    border-radius: 6px;
    border: 1px solid #d4d4d4;
}

/* Buttons */
.btn-row {
    margin-top: 1rem;
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
}

.btn {
    padding: 0.45rem 0.9rem;
    font-size: 0.78rem;
    font-weight: 600;
    text-decoration: none;
    border-radius: 999px;
    display: inline-flex;
    align-items: center;
    border: 1px solid transparent;
    transition: 0.2s;
}

.btn-view { background:#111; color:#fff; }
.btn-view:hover { background:#333; }

.btn-css { background:#005eff; color:#fff; }
.btn-css:hover { background:#0045c9; }

.btn-json { background:#00a65a; color:#fff; }
.btn-json:hover { background:#00894a; }

.btn-preview { background:#ff9800; color:#fff; }
.btn-preview:hover { background:#e37f00; }

.btn-folder { background:#e8e8e8; color:#333; }
.btn-folder:hover { background:#d5d5d5; }

.status {
    margin-top: 0.5rem;
    font-size: 0.78rem;
    color: #555;
}

.status-ok { color: #00a65a; font-weight: 600; }
.status-warn { color: #e67e22; font-weight: 600; }
.status-err { color: #e74c3c; font-weight: 600; }

.footer {
    margin-top: 3rem;
    text-align: center;
    font-size: 0.8rem;
    color: #777;
}

</style>
</head>
<body>

<h1>Branding Control Panel PRO — v2.0</h1>
<p class="sub">Interfaz visual de todas las marcas del ecosistema SRM–QK–ADSI.</p>

<div class="grid">
"""

    # ----------------------------------------------------
    # GENERATE CARDS
    # ----------------------------------------------------
    for b in brands:
        brand = b["brand"]
        logo_rel = os.path.relpath(b["logo"], BASE).replace("\\", "/")
        palette_path = b["palette"]

        # Previews
        tile = os.path.join(PREVIEWS, f"{brand}_tile.png")
        banner = os.path.join(PREVIEWS, f"{brand}_banner.png")

        tile_rel = os.path.relpath(tile, BASE).replace("\\","/") if file_exists(tile) else None
        banner_rel = os.path.relpath(banner, BASE).replace("\\","/") if file_exists(banner) else None

        # Paleta
        palette = load_json(palette_path)
        p = palette["colors"]["primary"]
        s = palette["colors"]["secondary"]
        a = palette["colors"]["accent"]
        n = palette["colors"]["neutral"]
        d = palette["colors"]["dark"]

        # Estado
        state = []
        state.append("Preview: OK" if tile_rel else "Previews: Pending")

        # ----------------------------
        # CARD HTML
        # ----------------------------
        html += f"""
<div class="card">

    <div class="card-logo">
        <img src="{logo_rel}">
    </div>

    <div class="brand-name">{brand}</div>

    <div class="palette-row">
        <div class="swatch" style="background:{p};"></div>
        <div class="swatch" style="background:{s};"></div>
        <div class="swatch" style="background:{a};"></div>
        <div class="swatch" style="background:{n};"></div>
        <div class="swatch" style="background:{d};"></div>
    </div>
"""

        # PREVIEW TILE + HOVER BANNER
        if tile_rel:
            html += f"""
    <div class="preview-tile-container">
        <img src="{tile_rel}">
        <div class="preview-hover">
            <img src="{banner_rel}">
        </div>
    </div>
"""
        else:
            html += """
    <div class="preview-tile-container" style="height:140px; background:#eee; display:flex; align-items:center; justify-content:center;">
        <span style="color:#888; font-size:0.85rem;">Sin previews</span>
    </div>
"""

        # BUTTONS
        html += f"""
    <div class="btn-row">
        <a class="btn btn-view" href="landings/{brand}.html" target="_blank">Landing</a>
        <a class="btn btn-css" href="landings/css/{brand}.css" target="_blank">CSS</a>
        <a class="btn btn-json" href="{palette_path}" target="_blank">Paleta JSON</a>
        <a class="btn btn-preview" href="previews/{brand}_full.png" target="_blank">Preview Full</a>
        <a class="btn btn-folder" href="file:///C:/SRM_ADSI/08_branding/">Carpeta</a>
    </div>

    <div class="status">
        Estado: <span class="{ 'status-ok' if tile_rel else 'status-warn'}">{', '.join(state)}</span>
    </div>

</div>
"""

    # ---------------------------------------
    # FOOTER
    # ---------------------------------------
    html += """
</div>

<div class="footer">
ADSI Suite — SRM–QK–ADSI · Conocimiento · Colaboración · Tecnología
</div>

</body>
</html>
"""

    return html


# -----------------------------
# MAIN
# -----------------------------
def main():
    index = load_json(INDEX_JSON)
    if not index:
        print("❌ ERROR: No se encontró branding_index.json")
        return

    brands = index.get("brands", [])
    if not brands:
        print("❌ No hay marcas registradas.")
        return

    html = generate_panel(brands)

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print("\n==============================================")
    print(" ✔ Branding Control Panel PRO v2.0 Generado")
    print(f" ✔ Archivo: {OUT_FILE}")
    print("==============================================\n")


if __name__ == "__main__":
    main()
