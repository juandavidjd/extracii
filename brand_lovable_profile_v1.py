# ======================================================================
# brand_lovable_profile_v1.py — SRM-QK-ADSI BRAND CORE → LOVABLE
# ======================================================================
# Autor: SRM Engine
#
# Propósito:
#   - Convertir narrativa + voz + paleta + logos → perfil de marca Lovable.
#   - Unificar lenguaje visual, técnico y narrativo.
#   - Preparar estructura UI/UX para la auto-generación de interfaces SRM.
#
# Produce:
#   C:\SRM_ADSI\03_knowledge_base\brands\lovable_profiles\<marca>_lovable.json
# ======================================================================

import os
import json
from datetime import datetime

# ----------------------------------------------------------------------
# Directorios principales
# ----------------------------------------------------------------------
ROOT = r"C:\SRM_ADSI\03_knowledge_base\brands"

NARRATIVE_DIR = os.path.join(ROOT, "narratives")
VOICE_DIR     = os.path.join(ROOT, "voices")
PALETTE_DIR   = r"C:\SRM_ADSI\08_branding\palettes"
LOGO_DIR      = r"C:\SRM_ADSI\08_branding\logos_optimized"

OUTPUT_DIR    = os.path.join(ROOT, "lovable_profiles")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ----------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_palette(brand):
    """Busca la paleta automáticamente usando el nombre normalizado."""
    file = f"{brand}_palette.json"
    path = os.path.join(PALETTE_DIR, file)
    if not os.path.exists(path):
        print(f"[ADVERTENCIA] Paleta no encontrada para {brand}, usando fallback.")
        return {
            "primary": "#0046FF",
            "secondary": "#1A1A1A",
            "accent": "#FFCC00",
            "neutral": "#FFFFFF",
            "dark": "#000000"
        }
    return load_json(path)["colors"]


def find_logo(brand):
    """Detecta el PNG o SVG de la marca."""
    candidates = [
        f"{brand}.png",
        f"{brand}.svg",
        f"{brand.capitalize()}.png",
        f"{brand.capitalize()}.svg"
    ]
    for c in candidates:
        p = os.path.join(LOGO_DIR, c)
        if os.path.exists(p):
            return p
    return None


# ----------------------------------------------------------------------
# Construir perfil Lovable
# ----------------------------------------------------------------------
def construir_lovable_profile(brand, narrativa, voice_profile, palette, logo_path):

    descripcion_corta = f"{brand}: desempeño, confiabilidad y estándar multimarca SRM-QK-ADSI."
    tagline = f"{brand} · Ingeniería, confiabilidad y disponibilidad."

    ui_config = {
        "theme_colors": {
            "primary": palette.get("primary", "#0046FF"),
            "secondary": palette.get("secondary", "#1A1A1A"),
            "accent": palette.get("accent", "#FFC300"),
            "neutral": palette.get("neutral", "#FFFFFF"),
            "dark": palette.get("dark", "#000000")
        },
        "logo_path": logo_path,
        "recommended_components": [
            "hero_banner",
            "brand_story_block",
            "product_highlights",
            "technical_differentiators",
            "call_to_action_primary",
            "cta_whatsapp",
            "footer_minimal"
        ]
    }

    profile = {
        "brand": brand,
        "generated_at": datetime.now().isoformat(),

        "metadata": {
            "tagline": tagline,
            "descripcion_corta": descripcion_corta,
            "voz_principal": voice_profile["voice_profile"]["style"],
            "tono": ", ".join(narrativa["identidad_verbal"]),
        },

        "narrativa": narrativa,
        "voice_profile": voice_profile,
        "ui_config": ui_config
    }

    return profile


# ----------------------------------------------------------------------
# MAIN: Generar los perfiles Lovable para todas las marcas
# ----------------------------------------------------------------------
def generar_perfiles():

    print("\n========================================================")
    print("      SRM — BRAND LOVABLE PROFILE GENERATOR v1")
    print("========================================================\n")

    for file in os.listdir(NARRATIVE_DIR):

        if not file.endswith("_narrative.json"):
            continue

        brand = file.replace("_narrative.json", "")
        narrative_path = os.path.join(NARRATIVE_DIR, file)

        print(f"→ Generando perfil Lovable para marca: {brand}")

        # Cargar narrativa
        narrativa = load_json(narrative_path)

        # Cargar perfil de voz
        voice_path = os.path.join(VOICE_DIR, f"{brand}_voice_profile.json")
        if not os.path.exists(voice_path):
            print(f"[ERROR] No existe perfil de voz para {brand}. Genera primero brand_voice_elevenlabs_generator_v1.py.")
            continue

        voice = load_json(voice_path)

        # Cargar paleta
        palette = load_palette(brand)

        # Detectar logo
        logo_path = find_logo(brand)

        # Build profile
        lovable = construir_lovable_profile(brand, narrativa, voice, palette, logo_path)

        out = os.path.join(OUTPUT_DIR, f"{brand}_lovable.json")

        with open(out, "w", encoding="utf-8") as f:
            json.dump(lovable, f, indent=4, ensure_ascii=False)

        print(f"   ✔ Perfil Lovable generado → {out}\n")

    print("========================================================")
    print(" ✔ BRAND LOVABLE PROFILE GENERATOR v1 — COMPLETADO")
    print(f" ✔ Output: {OUTPUT_DIR}")
    print("========================================================\n")


# ----------------------------------------------------------------------
# RUN
# ----------------------------------------------------------------------
if __name__ == "__main__":
    generar_perfiles()
