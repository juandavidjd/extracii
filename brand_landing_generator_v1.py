#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SRM–QK–ADSI — BRAND LANDING GENERATOR v1
Generador automático de landings HTML por cliente.

Flujo:
1) Leer logos optimizados en 08_branding/logos_optimizados/
2) Leer paletas JSON en 08_branding/paletas/
3) Detectar estilo → industrial | minimalista | moto-performance
4) Crear landing completa (HTML + CSS) por cliente
5) Guardar en 08_branding/landings/

Requisitos:
- Pillow
- json
- os
"""

import os
import json

BASE = r"C:/SRM_ADSI"
LOGOS_DIR = os.path.join(BASE, "08_branding", "logos_optimizados")
PALETAS_DIR = os.path.join(BASE, "08_branding", "paletas")
BACKGROUNDS_DIR = os.path.join(BASE, "08_branding", "backgrounds")
LANDINGS_DIR = os.path.join(BASE, "08_branding", "landings")
CSS_DIR = os.path.join(LANDINGS_DIR, "css")

os.makedirs(LANDINGS_DIR, exist_ok=True)
os.makedirs(CSS_DIR, exist_ok=True)

# --------------------------
# Detectar estilo por paleta
# --------------------------
def detectar_template(colores):
    # Colores como lista [(r,g,b)]
    if len(colores) == 1:
        return "minimalista"

    # Dominantes en rojo o diagonales (ej Japan)
    r,g,b = colores[0]
    if r > 150 and g < 100:
        return "moto-performance"

    # Amarillos + azules → industrial (ej Leo)
    if (colores[0][0] < 120 and colores[0][2] > 100):  # azul fuerte
        return "industrial"

    # Default
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
    <p>Tu inventario 100% optimizado, unificado y listo para e-commerce y puntos de venta.</p>
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
    r,g,b = primary
    primary_hex = '#%02x%02x%02x' % (r, g, b)

    if estilo == "industrial":
        css = f"""
body {{
    margin:0; padding:0;
    background:#111;
    color:white;
    font-family: 'Arial Black', sans-serif;
}}
.hero {{
    padding:80px 20px;
    text-align:center;
    background-size:cover;
}}
.logo {{
    width:250px;
}}
"""
    elif estilo == "minimalista":
        css = f"""
body {{
    margin:0; padding:0;
    background:white;
    color:#222;
    font-family: Arial, sans-serif;
}}
.contenedor {{
    padding:80px 20px;
    text-align:center;
}}
.logo-min {{
    width:200px;
    margin-bottom:30px;
}}
.tagline {{
    font-size:20px;
    color:{primary_hex};
}}
"""
    else:  # moto-performance
        css = f"""
body {{
    margin:0;
    background:#000;
    color:white;
}}
.hero {{
    position:relative;
    padding:100px 20px;
    text-align:center;
    background-size:cover;
}}
.overlay {{
    position:absolute;
    top:0; left:0;
    width:100%; height:100%;
    background:rgba(0,0,0,0.5);
}}
.logo-moto {{
    width:260px;
    position:relative;
    z-index:2;
}}
.speed {{
    font-size:28px;
    margin-top:20px;
}}
"""

    with open(os.path.join(CSS_DIR, f"{cliente}.css"), "w", encoding="utf-8") as f:
        f.write(css)


# --------------------------
# GENERAR LANDINGS
# --------------------------
def main():
    print("\n==============================================")
    print("   SRM–QK–ADSI — LANDING GENERATOR v1")
    print("==============================================\n")

    for logo_file in os.listdir(LOGOS_DIR):
        if not logo_file.lower().endswith(".png"):
            continue

        cliente = logo_file.replace("_logo.png", "")
        print(f"→ Generando landing para {cliente}...")

        # Cargar paleta
        paleta_file = os.path.join(PALETAS_DIR, f"{cliente}_palette.json")
        if not os.path.isfile(paleta_file):
            print(f"  ⚠ No hay paleta para {cliente}, saltando...")
            continue

        with open(paleta_file, "r") as f:
            paleta = json.load(f)

        colores = paleta["colors"]
        primary = colores[0]

        # Seleccionar background (si existe)
        bg_candidates = [f for f in os.listdir(BACKGROUNDS_DIR) if cliente.lower() in f.lower()]
        bg = bg_candidates[0] if bg_candidates else ""

        # Detectar template
        estilo = detectar_template(colores)

        # Crear HTML
        if estilo == "industrial":
            html = plantilla_industrial(cliente, logo_file, bg, primary)
        elif estilo == "minimalista":
            html = plantilla_minimalista(cliente, logo_file, bg, primary)
        else:
            html = plantilla_moto(cliente, logo_file, bg, primary)

        # Guardar HTML
        with open(os.path.join(LANDINGS_DIR, f"{cliente}_landing.html"), "w", encoding="utf-8") as f:
            f.write(html)

        # CSS
        generar_css(cliente, estilo, primary)

        print(f"  ✔ Landing creada → {cliente}_landing.html")

    print("\n==============================================")
    print(" ✔ LANDINGS GENERADAS COMPLETAMENTE")
    print(f" Directorio: {LANDINGS_DIR}")
    print("==============================================\n")


if __name__ == "__main__":
    main()
