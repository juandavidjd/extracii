# -*- coding: utf-8 -*-
"""
preview_generator_v1.py
Genera capturas automáticas de TODAS las landings SRM–QK–ADSI.
Usa Playwright + Chromium (headless).
Produce:
- banner   (1600x500)
- full     (1366xFullScroll)
- mobile   (430xFullScroll)
- tile     (400x300 crop)
"""

import os
import json
from playwright.sync_api import sync_playwright
from PIL import Image

# ============================
# CONFIGURACIÓN
# ============================

BRANDING_BASE = r"C:\SRM_ADSI\08_branding"
LANDINGS_DIR = os.path.join(BRANDING_BASE, "landings")
INDEX_JSON = os.path.join(BRANDING_BASE, "branding_index.json")

PREVIEWS_DIR = os.path.join(BRANDING_BASE, "previews")
os.makedirs(PREVIEWS_DIR, exist_ok=True)


# ============================
# UTILIDADES
# ============================

def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def crop_tile(input_path, output_path, width=400, height=300):
    """
    Crea un recorte 400×300 desde el centro.
    """
    img = Image.open(input_path)
    w, h = img.size

    left = max(0, (w - width) // 2)
    upper = max(0, (h - height) // 2)
    right = left + width
    lower = upper + height

    cropped = img.crop((left, upper, right, lower))
    cropped.save(output_path)


# ============================
# CAPTURA DE LANDING
# ============================

def generar_previews(play, marca, html_path):
    """
    html_path = ruta absoluta al archivo HTML de la landing.
    """
    print(f"→ Generando previews para {marca}...")

    banner_out = os.path.join(PREVIEWS_DIR, f"{marca}_banner.png")
    full_out = os.path.join(PREVIEWS_DIR, f"{marca}_full.png")
    mobile_out = os.path.join(PREVIEWS_DIR, f"{marca}_mobile.png")
    tile_out = os.path.join(PREVIEWS_DIR, f"{marca}_tile.png")

    # Convertir ruta local a URL file:///
    html_url = "file:///" + html_path.replace("\\", "/")

    # ------------------------------------------
    # BANNER (1600×500)
    # ------------------------------------------
    browser = play.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 500})
    page.goto(html_url)
    page.wait_for_timeout(1200)
    page.screenshot(path=banner_out, full_page=False)
    browser.close()

    # ------------------------------------------
    # FULL PAGE (1366×full scroll)
    # ------------------------------------------
    browser = play.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1366, "height": 800})
    page.goto(html_url)
    page.wait_for_timeout(1200)

    # Capturar scroll completo
    full_scroll_height = page.evaluate("document.body.scrollHeight")
    page.set_viewport_size({"width": 1366, "height": full_scroll_height})
    page.wait_for_timeout(600)
    page.screenshot(path=full_out, full_page=True)
    browser.close()

    # ------------------------------------------
    # MOBILE (430×full scroll)
    # ------------------------------------------
    browser = play.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 430, "height": 800})
    page.goto(html_url)
    page.wait_for_timeout(1200)

    full_scroll_height = page.evaluate("document.body.scrollHeight")
    page.set_viewport_size({"width": 430, "height": full_scroll_height})
    page.wait_for_timeout(600)
    page.screenshot(path=mobile_out, full_page=True)
    browser.close()

    # ------------------------------------------
    # TILE (400×300 crop desde FULL)
    # ------------------------------------------
    crop_tile(full_out, tile_out)

    print(f"   ✔ banner    → {banner_out}")
    print(f"   ✔ full      → {full_out}")
    print(f"   ✔ mobile    → {mobile_out}")
    print(f"   ✔ tile      → {tile_out}")


# ============================
# MAIN
# ============================

def main():
    print("\n==============================================")
    print("      PREVIEW GENERATOR v1 — ADSI Suite")
    print("==============================================\n")

    index = load_json(INDEX_JSON)
    if not index:
        print("❌ ERROR: No existe branding_index.json")
        return

    brands = index.get("brands", [])
    if not brands:
        print("❌ No hay marcas en branding_index.json")
        return

    with sync_playwright() as play:
        for b in brands:
            marca = b["brand"]
            html_path = os.path.join(LANDINGS_DIR, f"{marca}.html")

            if not os.path.exists(html_path):
                print(f"⚠ Landing no encontrada: {html_path}")
                continue

            generar_previews(play, marca, html_path)

    print("\n==============================================")
    print("   ✔ PREVIEWS GENERADOS PARA TODAS LAS MARCAS")
    print(f"   Carpeta: {PREVIEWS_DIR}")
    print("==============================================\n")


if __name__ == "__main__":
    main()
