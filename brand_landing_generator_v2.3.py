#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
brand_landing_generator_v2.3.py
SRM–QK–ADSI — LANDING GENERATOR (Auto-detected branding)
"""

import os
import json
from PIL import Image
import base64

BASE = r"C:/SRM_ADSI/08_branding"
LOGOS = os.path.join(BASE, "logos_optimized")
PALETTES = os.path.join(BASE, "palettes")
BACKGROUNDS = os.path.join(BASE, "backgrounds")
LANDINGS = os.path.join(BASE, "landings")


# =====================================================
#   UTILIDADES
# =====================================================
def load_palette(client):
    f = os.path.join(PALETTES, f"{client}_palette.json")
    if not os.path.exists(f):
        print(f"  ⚠ No existe paleta → {f}")
        return None
    with open(f, "r", encoding="utf-8") as fp:
        return json.load(fp)


def select_template_type(palette):
    """
    Auto-detección basada en paleta:
      - Rojo dominante → Racing/Energía
      - Negro + Amarillo → Industrial
      - Azul → Técnico/Profesional
      - Blanco/Gris → Minimalista
    """

    colors = palette.get("colors", [])
    if not colors:
        return "minimal"

    first = colors[0]["hex"].lower()

    if any(c in first for c in ["ff0000", "d40000", "c10000"]):
        return "energy"

    if any(c in first for c in ["000000", "111111", "222222"]):
        return "industrial"

    if any(c in first for c in ["0046ff", "0050ff", "0a3cff"]):
        return "technical"

    if any(c in first for c in ["f0f0f0", "fafafa", "ffffff"]):
        return "minimal"

    return "technical"


def img_to_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


# =====================================================
#   TEMPLATES HTML
# =====================================================
def render_html(client, palette, logo_path, bg_path, mode):
    primary = palette["colors"][0]["hex"] if palette["colors"] else "#222"
    secondary = palette["colors"][1]["hex"] if len(palette["colors"]) > 1 else "#666"

    logo_b64 = img_to_base64(logo_path)
    bg_b64 = img_to_base64(bg_path)

    if mode == "energy":
        grad = f"linear-gradient(135deg, {primary}, #000000)"
        font = "font-weight:800; letter-spacing:1px;"
    elif mode == "industrial":
        grad = f"linear-gradient(135deg, #111111, {primary})"
        font = "font-weight:700;"
    elif mode == "minimal":
        grad = f"linear-gradient(135deg, #ffffff, {primary})"
        font = "font-weight:300;"
    else:  # technical
        grad = f"linear-gradient(135deg, {primary}, {secondary})"
        font = "font-weight:600;"

    html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8" />
<title>{client} — Landing Oficial</title>
<style>
body {{
    margin: 0;
    padding: 0;
    background: {grad}, url('data:image/png;base64,{bg_b64}');
    background-size: cover;
    font-family: Arial, sans-serif;
    color: #fff;
}}
.container {{
    width: 100%;
    height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    backdrop-filter: blur(6px);
}}
.logo {{
    width: 260px;
    margin-bottom: 35px;
}}
h1 {{
    font-size: 42px;
    {font}
}}
p {{
    font-size: 20px;
    opacity: 0.85;
}}
.btn {{
    margin-top: 40px;
    padding: 14px 32px;
    background: #ffffff;
    color: #000;
    text-decoration: none;
    border-radius: 6px;
    font-size: 18px;
    font-weight: 700;
}}
</style>
</head>
<body>
<div class="container">
    <img src="data:image/png;base64,{logo_b64}" class="logo"/>
    <h1>Bienvenido a {client}</h1>
    <p>Calidad, confianza y tecnología para tu motocicleta.</p>
    <a class="btn" href="#">Entrar a la tienda</a>
</div>
</body>
</html>
"""
    return html


# =====================================================
#   MAIN PROCESS
# =====================================================
def main():
    print("\n==============================================")
    print("   SRM–QK–ADSI — LANDING GENERATOR v2.3")
    print("==============================================\n")

    for file in os.listdir(LOGOS):
        if not file.endswith("_logo_1024.png"):
            continue

        client = file.replace("_logo_1024.png", "")
        print(f"→ Generando landing para {client}...")

        palette = load_palette(client)
        if not palette:
            print("  ⚠ Paleta inexistente, saltando...\n")
            continue

        mode = select_template_type(palette)
        logo_path = os.path.join(LOGOS, file)

        # Buscar un background del cliente
        bg_file = os.path.join(BACKGROUNDS, f"{client}_bg.jpg")
        if not os.path.exists(bg_file):
            # fallback genérico
            bg_file = os.path.join(BACKGROUNDS, "default_bg.jpg")

        html = render_html(client, palette, logo_path, bg_file, mode)

        out_folder = os.path.join(LANDINGS, client)
        os.makedirs(out_folder, exist_ok=True)
        out_file = os.path.join(out_folder, "index.html")

        with open(out_file, "w", encoding="utf-8") as fp:
            fp.write(html)

        print(f"  ✔ Landing generada → {out_file}\n")

    print("==============================================")
    print("   ✔ LANDINGS COMPLETADAS (v2.3)")
    print("==============================================\n")


if __name__ == "__main__":
    main()
