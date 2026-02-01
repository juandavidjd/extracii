# -*- coding: utf-8 -*-
"""
brand_landing_generator_v2.5.py (FULL)
Landings PRO + Logo Safety v2 (inteligente)
- Hero con textura blur
- Tipografía Montserrat
- Layout premium
- Cápsula automática según color dominante del logo
- CTA WhatsApp
- Panel index
"""

import os
import json
from PIL import Image

# ============================
# CONFIG
# ============================
BASE = r"C:\SRM_ADSI\08_branding"
LANDINGS = os.path.join(BASE, "landings")
CSS_DIR = os.path.join(LANDINGS, "css")
LOGOS_DIR = os.path.join(BASE, "logos_optimized")
INDEX_JSON = os.path.join(BASE, "branding_index.json")

os.makedirs(LANDINGS, exist_ok=True)
os.makedirs(CSS_DIR, exist_ok=True)

WHATSAPP_NUMBER = "573114368937"


# ============================
# UTILIDAD: CARGAR JSON
# ============================
def cargar_json(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================
# DETECTAMOS COLOR DOMINANTE
# ============================
def color_dominante_img(path):
    """
    Retorna (r, g, b) promedio de la imagen.
    """
    img = Image.open(path).convert("RGB")
    img = img.resize((40, 40))
    pixels = list(img.getdata())
    r = sum(p[0] for p in pixels) // len(pixels)
    g = sum(p[1] for p in pixels) // len(pixels)
    b = sum(p[2] for p in pixels) // len(pixels)
    return (r, g, b)


# ============================
# LOGO SAFETY v2 — Inteligente
# ============================
def generar_logo_safety_css(r, g, b):
    """
    Dado el color dominante, ajusta la cápsula:
    - logos claros → cápsula blanca
    - logos oscuros → cápsula negra
    - medios → semitransparente
    """
    luminosidad = (r + g + b) / 3

    if luminosidad >= 180:
        # LOGO CLARO — EJ: KAIQI, DUNA
        bg = "rgba(255,255,255,0.96)"
        border = "1px solid rgba(0,0,0,0.25)"
        shadow = "drop-shadow(0 0 3px rgba(0,0,0,0.55))"
    elif luminosidad <= 80:
        # LOGO OSCURO
        bg = "rgba(0,0,0,0.60)"
        border = "1px solid rgba(255,255,255,0.20)"
        shadow = "drop-shadow(0 0 4px rgba(0,0,0,0.65))"
    else:
        # LOGO MEDIO / COLOR
        bg = "rgba(255,255,255,0.75)"
        border = "1px solid rgba(0,0,0,0.18)"
        shadow = "drop-shadow(0 0 3px rgba(0,0,0,0.45))"

    return bg, border, shadow


# ============================
# HTML TEMPLATE (PRO)
# ============================
def html_template(brand, logo_rel, primary, accent, bg_light):
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>{brand} — Marca Oficial</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{brand} — Landing generada por ADSI Suite.">
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="css/{brand}.css">
</head>
<body>
<div class="page-wrapper">

<header class="top-bar">
    <div class="brand-mark">
        <img src="{logo_rel}" alt="{brand}" class="brand-logo">
        <div class="brand-text">
            <span class="brand-name">{brand}</span>
            <span class="brand-tagline">Integrado al ecosistema SRM–QK–ADSI</span>
        </div>
    </div>
</header>

<section class="hero">
    <div class="hero-overlay"></div>
    <div class="hero-content">
        <h1>{brand}</h1>
        <p class="hero-subtitle">
            Plataforma visual creada con ADSI Suite para impulsar branding, productos y experiencias 360°.
        </p>
        <div class="hero-cta">
            <a class="btn-primary" href="https://wa.me/{WHATSAPP_NUMBER}" target="_blank">Hablar por WhatsApp</a>
            <a class="btn-secondary" href="#sobre-marca">Ver más</a>
        </div>
    </div>
</section>

<main class="main-content">

<section id="sobre-marca" class="section about">
    <div class="section-header">
        <h2>Sobre {brand}</h2>
        <p>Una marca integrada al ecosistema SRM–QK–ADSI</p>
    </div>
    <div class="section-body">
        <p>
            Esta landing se genera automáticamente a partir de la infraestructura de branding ADSI. 
            Se puede conectar a inventarios, catálogos, colecciones, Shopify y experiencias 360°.
        </p>
    </div>
</section>

<section class="section pillars">
    <div class="section-header">
        <h2>Pilares de valor</h2>
        <p>Elementos clave que esta marca comunica</p>
    </div>
    <div class="pillars-grid">
        <article class="pillar-card">
            <h3>Calidad consistente</h3>
            <p>Estandarización visual y mensajes limpios en todos los canales.</p>
        </article>
        <article class="pillar-card">
            <h3>Integración 360°</h3>
            <p>Listo para conectar inventarios, Shopify y paneles ADSI.</p>
        </article>
        <article class="pillar-card">
            <h3>Escalabilidad</h3>
            <p>Permite crecer sin rehacer la base visual.</p>
        </article>
    </div>
</section>

<section class="section products">
    <div class="section-header">
        <h2>Productos / Líneas</h2>
        <p>Espacio preparado para integrar catálogo SRM–QK–ADSI</p>
    </div>
    <div class="products-grid">
        <article class="product-card">
            <span class="badge">Kit</span>
            <h3>Línea principal</h3>
            <p>Listo para conectar inventario maestro.</p>
        </article>
        <article class="product-card">
            <span class="badge">360°</span>
            <h3>Experiencia</h3>
            <p>Servicios, bundles y aplicaciones complejas.</p>
        </article>
        <article class="product-card">
            <span class="badge">B2B</span>
            <h3>Distribución</h3>
            <p>Espacio para canales y aliados estratégicos.</p>
        </article>
    </div>
</section>

<section class="section cta-whatsapp">
    <div class="cta-box">
        <div class="cta-text">
            <h2>¿Quieres activar esta marca?</h2>
            <p>Coordina ajustes, integraciones y experiencia 360° desde tu WhatsApp.</p>
        </div>
        <a class="btn-primary large" href="https://wa.me/{WHATSAPP_NUMBER}" target="_blank">Contactar ahora</a>
    </div>
</section>

</main>

<footer class="footer">
    <div class="footer-inner">
        <span>© {brand} · ADSI Suite</span>
        <span class="divider">|</span>
        <span>SRM–QK–ADSI · Conocimiento · Colaboración · Tecnología</span>
    </div>
</footer>

</div>
</body>
</html>
"""


# ============================
# CSS TEMPLATE PRO + SAFETY v2
# ============================
def css_template(brand, primary, accent, bg_light, logo_rel, safety_bg, safety_border, safety_shadow):
    return f""":root {{
  --color-primary: {primary};
  --color-accent: {accent};
  --color-bg: {bg_light};
  --color-bg-soft: #f4f4f4;
  --color-text-main: #141414;
  --color-text-soft: #555;
}}

body {{
  margin: 0;
  font-family: 'Montserrat', sans-serif;
  background: var(--color-bg);
  color: var(--color-text-main);
}}

.top-bar {{
  position: sticky;
  top: 0;
  background: rgba(255,255,255,0.94);
  border-bottom: 1px solid rgba(0,0,0,0.05);
  backdrop-filter: blur(10px);
  z-index: 10;
}}

.brand-mark {{
  display: flex;
  align-items: center;
  padding: 0.6rem 1.5rem;
  gap: 0.75rem;
}}

.brand-logo {{
  height: 48px;
  width: auto;
  object-fit: contain;

  background: {safety_bg};
  border: {safety_border};
  padding: 6px 16px;
  border-radius: 14px;
  filter: {safety_shadow};
}}

.hero {{
  position: relative;
  min-height: 55vh;
  padding: 3rem 1.5rem;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #fff;
  overflow: hidden;
  background: radial-gradient(circle at top left, var(--color-primary), #000);
}}

.hero::before {{
  content: "";
  position: absolute;
  inset: -40px;
  background-image: url('{logo_rel}');
  background-size: 380px;
  background-repeat: no-repeat;
  background-position: center;
  opacity: 0.12;
  filter: blur(7px);
}}

.hero-overlay {{
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(0,0,0,0.65), rgba(0,0,0,0.25));
}}

.hero-content {{
  position: relative;
  z-index: 1;
  max-width: 900px;
  text-align: center;
}}

.hero h1 {{
  font-size: clamp(2.4rem, 4vw, 3rem);
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}}

.hero-subtitle {{
  margin-top: 1rem;
  max-width: 700px;
  margin-left: auto;
  margin-right: auto;
  color: #eaeaea;
}}

.btn-primary,
.btn-secondary {{
  display: inline-flex;
  padding: 0.7rem 1.5rem;
  border-radius: 999px;
  font-weight: 600;
  text-decoration: none;
  transition: 0.2s;
}}

.btn-primary {{
  background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
  color: #fff;
}}

.btn-secondary {{
  background: rgba(255,255,255,0.12);
  border: 1px solid rgba(255,255,255,0.45);
  color: #fff;
}}

.main-content {{
  max-width: 1100px;
  margin: auto;
  padding: 2.5rem 1.5rem 3rem;
}}

.section {{ margin-bottom: 2.5rem; }}
.section-header h2{{ text-transform:uppercase; letter-spacing:0.04em;}}

.pillars-grid, .products-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px,1fr));
  gap: 1.2rem;
}}

.pillar-card,
.product-card {{
  background: #fff;
  border-radius: 1rem;
  padding: 1.2rem;
  border: 1px solid rgba(0,0,0,0.08);
}}

.cta-box {{
  background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
  padding: 1.7rem;
  border-radius: 1.4rem;
  color: #fff;
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 1rem;
}}

.footer {{
  margin-top: 3rem;
  background: #fafafa;
  border-top: 1px solid #e5e5e5;
}}
"""


# ============================
# GENERADOR
# ============================
def main():
    print("\n==============================================")
    print("   LANDING GENERATOR v2.5 (PRO + Safety v2)")
    print("==============================================\n")

    index = cargar_json(INDEX_JSON)
    if not index:
        print("❌ No existe branding_index.json")
        return

    brands = index.get("brands", [])
    if not brands:
        print("❌ No hay marcas en branding_index.json")
        return

    for item in brands:
        brand = item["brand"]
        logo_abs = item["logo"]
        palette_path = item["palette"]

        print(f"\n→ Generando landing PRO+Safety para: {brand}")

        # PALETA
        palette = cargar_json(palette_path)
        primary = palette["colors"]["primary"] if palette else "#333"
        accent = palette["colors"]["accent"] if palette else "#555"
        bg_light = palette["background"]["light"] if palette else "#fff"

        # LOGO SAFETY v2
        r, g, b = color_dominante_img(logo_abs)
        safety_bg, safety_border, safety_shadow = generar_logo_safety_css(r, g, b)

        # Rutas relativas
        logo_rel_html = os.path.relpath(logo_abs, LANDINGS).replace("\\", "/")
        logo_rel_css = os.path.relpath(logo_abs, CSS_DIR).replace("\\", "/")

        # HTML
        html_out = os.path.join(LANDINGS, f"{brand}.html")
        with open(html_out, "w", encoding="utf-8") as f:
            f.write(html_template(brand, logo_rel_html, primary, accent, bg_light))

        # CSS
        css_out = os.path.join(CSS_DIR, f"{brand}.css")
        with open(css_out, "w", encoding="utf-8") as f:
            f.write(
                css_template(
                    brand,
                    primary,
                    accent,
                    bg_light,
                    logo_rel_css,
                    safety_bg,
                    safety_border,
                    safety_shadow,
                )
            )

        print(f"   ✔ HTML PRO → {html_out}")
        print(f"   ✔ CSS  PRO → {css_out}")

    # INDEX
    index_file = os.path.join(LANDINGS, "index.html")
    with open(index_file, "w", encoding="utf-8") as f:
        f.write("<h1>Landings de Marca — ADSI Suite</h1><ul>")
        for item in brands:
            f.write(f'<li><a href="{item["brand"]}.html">{item["brand"]}</a></li>')
        f.write("</ul>")

    print("\n==============================================")
    print("   ✔ Landings PRO + Safety v2 generadas")
    print("   ✔ Index actualizado")
    print("==============================================\n")


if __name__ == "__main__":
    main()
