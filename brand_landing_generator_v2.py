#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SRM–QK–ADSI — BRAND LANDING GENERATOR v2.1 (FIX DEFINITIVO)
Corrección:
- Usa correctamente la carpeta real de paletas: palettes_detectadas
"""

import os
import json

BASE = r"C:/SRM_ADSI"
LOGOS_DIR = os.path.join(BASE, "08_branding", "logos_optimizados")

# 🔥 Carpeta corregida
PALETAS_DIR = os.path.join(BASE, "08_branding", "palettes_detectadas")

BACKGROUNDS_DIR = os.path.join(BASE, "08_branding", "backgrounds")
LANDINGS_DIR = os.path.join(BASE, "08_branding", "landings")
CSS_DIR = os.path.join(LANDINGS_DIR, "css")

os.makedirs(LANDINGS_DIR, exist_ok=True)
os.makedirs(CSS_DIR, exist_ok=True)


# ------------------------------------------------------------
# Limpia el nombre del cliente eliminando sufijos (_logo_512)
# ------------------------------------------------------------
def limpiar_nombre_cliente(filename):
    return filename.split("_")[0]  # Bara_logo_1024.png → Bara


# --------------------------
# Detectar template
# --------------------------
def detectar_template(colores):
    r, g, b = colores[0]

    if len(colores) == 1:
        return "minimalista"
    if r > 150 and g < 100:
        return "moto-performance"
    if r < 120 and b > 100:
        return "industrial"

    return "minimalista"


# --------------------------
# Plantillas HTML
# --------------------------
def plantilla_industrial(cliente, logo_file, bg, primary):
    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>{cliente} | Repuestos & Tecnología</title>
<link rel="stylesheet" href="css/{cliente}.css">
</head>
<body>

<header class="hero" style="background-image:url('../backgrounds/{bg}');">
    <img src="../logos_optimizados/{logo_file}" class="logo">
    <h1 class="titulo">{cliente}</h1>
    <h2 class="subtitulo">Calidad • Ingeniería • Desempeño</h2>
</header>

<section class="bloque">
    <h3>Catálogo Integrado SRM–QK–ADSI</h3>
    <p>Repuestos optimizados y clasificados automáticamente.</p>
</section>

</body>
</html>
"""


def plantilla_minimalista(cliente, logo_file, bg, primary):
    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>{cliente} | Official Store</title>
<link rel="stylesheet" href="css/{cliente}.css">
</head>
<body>

<div class="contenedor">
    <img src="../logos_optimizados/{logo_file}" class="logo-min">
    <h1>{cliente}</h1>
    <p class="tagline">Repuestos • Innovación • Precisión</p>
</div>

</body>
</html>
"""


def plantilla_moto(cliente, logo_file, bg, primary):
    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>{cliente} Moto Performance</title>
<link rel="stylesheet" href="css/{cliente}.css">
</head>
<body>

<header class="hero" style="background-image:url('../backgrounds/{bg}');">
    <div class="overlay"></div>
    <img src="../logos_optimizados/{logo_file}" class="logo-moto">
    <h1 class="speed">Velocidad • Confianza • Precisión</h1>
</header>

</body>
</html>
"""


# --------------------------
# CSS Generator
# --------------------------
def generar_css(cliente, estilo, primary):
    r, g, b = primary
    primary_hex = '#%02x%02x%02x' % (r, g, b)

    if estilo == "industrial":
        css = f"""
body {{
    background:#111;
    color:white;
}}
.logo {{ width:250px; }}
"""
    elif estilo == "minimalista":
        css = f"""
body {{
    background:white;
    color:#222;
}}
.logo-min {{ width:200px; }}
.tagline {{ color:{primary_hex}; }}
"""
    else:
        css = f"""
body {{
    background:#000;
    color:white;
}}
.logo-moto {{ width:260px; }}
"""

    with open(os.path.join(CSS_DIR, f"{cliente}.css"), "w", encoding="utf-8") as f:
        f.write(css)


# --------------------------
# MAIN
# --------------------------
def main():
    print("\n==============================================")
    print("   SRM–QK–ADSI — LANDING GENERATOR v2.1")
    print("==============================================\n")

    for logo_file in os.listdir(LOGOS_DIR):

        if not logo_file.lower().endswith(".png"):
            continue

        cliente = limpiar_nombre_cliente(logo_file)

        print(f"→ Generando landing para {cliente} ({logo_file})...")

        paleta_file = os.path.join(PALETAS_DIR, f"{cliente}_palette.json")

        if not os.path.isfile(paleta_file):
            print(f"  ⚠ Paleta NO encontrada: {paleta_file}")
            continue

        with open(paleta_file, "r") as f:
            paleta = json.load(f)

        colores = paleta["colors"]
        primary = colores[0]

        # background
        bg_candidates = [f for f in os.listdir(BACKGROUNDS_DIR) if cliente.lower() in f.lower()]
        bg = bg_candidates[0] if bg_candidates else ""

        estilo = detectar_template(colores)

        if estilo == "industrial":
            html = plantilla_industrial(cliente, logo_file, bg, primary)
        elif estilo == "minimalista":
            html = plantilla_minimalista(cliente, logo_file, bg, primary)
        else:
            html = plantilla_moto(cliente, logo_file, bg, primary)

        with open(os.path.join(LANDINGS_DIR, f"{cliente}_landing.html"), "w", encoding="utf-8") as f:
            f.write(html)

        generar_css(cliente, estilo, primary)

        print(f"  ✔ Landing creada → {cliente}_landing.html")

    print("\n==============================================")
    print(" ✔ LANDINGS GENERADAS CORRECTAMENTE (v2.1)")
    print("==============================================\n")


if __name__ == "__main__":
    main()
