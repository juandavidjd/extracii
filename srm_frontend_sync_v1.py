# ======================================================================
# srm_frontend_sync_v1.py — SRM-QK-ADSI FRONTEND BUNDLE GENERATOR v1
# ======================================================================
# Autor: SRM Engine
#
# Propósito:
#   - Unificar branding, narrativa, audio, agentes, academy y UI config.
#   - Generar un único bundle para Lovable, Shopify UI y SRM Frontend.
#   - Estandarizar bloques visuales y de contenido.
#
# Resultado:
#   C:\SRM_ADSI\03_knowledge_base\frontend\frontend_bundle.json
# ======================================================================

import os
import json
from datetime import datetime

# ----------------------------------------------------------------------
# DIRECTORIOS PRINCIPALES
# ----------------------------------------------------------------------
ROOT_BRANDS = r"C:\SRM_ADSI\03_knowledge_base\brands"

NARRATIVES = os.path.join(ROOT_BRANDS, "narratives")
VOICES     = os.path.join(ROOT_BRANDS, "voices")
LOVABLE    = os.path.join(ROOT_BRANDS, "lovable_profiles")
AUDIO      = os.path.join(ROOT_BRANDS, "audio_packs")
ACADEMY    = os.path.join(ROOT_BRANDS, "academy_packs")
AGENTS     = r"C:\SRM_ADSI\03_knowledge_base\agents"

PALETTES   = r"C:\SRM_ADSI\08_branding\palettes"
LOGOS      = r"C:\SRM_ADSI\08_branding\logos_optimized"

# OUTPUT
FRONTEND = os.path.join(ROOT_BRANDS, "frontend")
os.makedirs(FRONTEND, exist_ok=True)


# ----------------------------------------------------------------------
# UTILIDADES
# ----------------------------------------------------------------------
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_load(path, tipo):
    if not os.path.exists(path):
        print(f"[ADVERTENCIA] No existe {tipo}: {path}")
        return None
    return load_json(path)


# ----------------------------------------------------------------------
# DEFINICIÓN DE UI BLOCKS SRM ESTÁNDAR
# ----------------------------------------------------------------------
UI_BLOCKS = {
    "hero_block": {
        "requires": ["logo", "primary_color", "tagline"],
        "layout": "centered",
        "max_width": 1200
    },
    "brand_story_block": {
        "requires": ["historia"],
        "layout": "two_column",
        "max_width": 1400
    },
    "technical_differentiators_block": {
        "requires": ["diferenciadores"],
        "layout": "cards_row",
        "max_width": 1400
    },
    "audio_presentation_block": {
        "requires": ["audio_pack", "player_config"],
        "layout": "audio_card",
        "max_width": 1000
    },
    "cta_whatsapp_block": {
        "requires": ["whatsapp_number"],
        "layout": "button_center",
        "max_width": 600
    },
    "product_showcase_block": {
        "requires": ["catalogue"],
        "layout": "grid_dynamic",
        "max_width": 1600
    }
}


# ----------------------------------------------------------------------
# CONSTRUIR PERFIL UNIFICADO DE MARCA PARA EL FRONTEND
# ----------------------------------------------------------------------
def construir_frontend_brand_profile(brand):

    narrativa_path = os.path.join(NARRATIVES, f"{brand}_narrative.json")
    voice_path     = os.path.join(VOICES, f"{brand}_voice_profile.json")
    lovable_path   = os.path.join(LOVABLE, f"{brand}_lovable.json")
    audio_pack     = os.path.join(AUDIO, f"{brand}_audio_pack.json")
    player_cfg     = os.path.join(AUDIO, f"{brand}_player_config.json")
    academy_pack   = os.path.join(ACADEMY, f"{brand}_academy_pack.json")

    narrativa = safe_load(narrativa_path, "narrativa")
    voice     = safe_load(voice_path, "voz")
    lovable   = safe_load(lovable_path, "lovable")
    audio     = safe_load(audio_pack, "audio pack")
    player    = safe_load(player_cfg, "player config")
    academy   = safe_load(academy_pack, "academy")

    # Logo + paleta
    palette_path = os.path.join(PALETTES, f"{brand}_palette.json")
    palette = safe_load(palette_path, "paleta")

    logo_png = os.path.join(LOGOS, f"{brand}.png")
    logo_svg = os.path.join(LOGOS, f"{brand}.svg")

    logo = None
    if os.path.exists(logo_png): logo = logo_png
    if os.path.exists(logo_svg): logo = logo_svg

    profile = {
        "brand": brand,
        "generated_at": datetime.now().isoformat(),
        "narrative": narrativa,
        "voice": voice,
        "lovable": lovable,
        "audio": audio,
        "player_config": player,
        "academy": academy,
        "palette": palette,
        "logo": logo,
        "ui_blocks_available": UI_BLOCKS
    }

    return profile


# ----------------------------------------------------------------------
# MAIN: Construir el bundle completo
# ----------------------------------------------------------------------
def generar_frontend_bundle():

    print("\n=====================================================")
    print("        SRM — FRONTEND SYNC ENGINE v1")
    print("=====================================================\n")

    bundle = {
        "generated_at": datetime.now().isoformat(),
        "brands": {},
        "agents_available": [],
        "ui_blocks": UI_BLOCKS,
        "whatsapp_number": "+57 3114368937",
        "srm_attitude": [
            "Claridad técnica",
            "Rigor industrial",
            "Lenguaje accesible",
            "Estándar SRM-QK-ADSI",
            "Profesionalismo visual"
        ]
    }

    # Cargar agentes existentes
    if os.path.exists(AGENTS):
        for file in os.listdir(AGENTS):
            if file.endswith(".json"):
                bundle["agents_available"].append(file.replace(".json", ""))

    # Construir perfiles por marca
    for file in os.listdir(NARRATIVES):
        if not file.endswith("_narrative.json"):
            continue

        brand = file.replace("_narrative.json", "")
        print(f"→ Sincronizando marca para Frontend: {brand}")

        brand_profile = construir_frontend_brand_profile(brand)
        bundle["brands"][brand] = brand_profile

    # Guardar bundle final
    out_path = os.path.join(FRONTEND, "frontend_bundle.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=4, ensure_ascii=False)

    print("\n=====================================================")
    print(" ✔ FRONTEND SYNC ENGINE — COMPLETADO")
    print(f" ✔ Archivo: {out_path}")
    print("=====================================================\n")


# ----------------------------------------------------------------------
# RUN
# ----------------------------------------------------------------------
if __name__ == "__main__":
    generar_frontend_bundle()
