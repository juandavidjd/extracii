# ======================================================================
# brand_voice_elevenlabs_generator_v1.py — SRM-QK-ADSI — BRAND CORE v28
# ======================================================================
# Autor: SRM Engine
#
# Propósito:
#   - Convertir la narrativa de cada marca en un perfil de voz ElevenLabs.
#   - Definir tono, intención, cadencia, temperatura y estilo.
#   - Generar scripts base para locución corporativa multimarca.
#   - Preparar material para SRM Agents, Guided Tour, Academia y Onboarding.
# ======================================================================

import os
import json
from datetime import datetime

# ----------------------------------------------------------------------
# DIRECTORIOS
# ----------------------------------------------------------------------
NARRATIVE_DIR = r"C:\SRM_ADSI\03_knowledge_base\brands\narratives"
OUTPUT_DIR    = r"C:\SRM_ADSI\03_knowledge_base\brands\voices"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ----------------------------------------------------------------------
# Plantillas de voz por estilo SRM
# ----------------------------------------------------------------------

VOICE_TEMPLATES = {
    "voz confiable": {
        "stability": 0.58,
        "similarity_boost": 0.82,
        "style": "corporate",
        "pitch": "neutral",
        "rate": "medium",
        "emotion": "serenity"
    },
    "voz moderna": {
        "stability": 0.53,
        "similarity_boost": 0.88,
        "style": "dynamic",
        "pitch": "slightly_up",
        "rate": "medium_fast",
        "emotion": "confidence"
    },
    "voz práctica": {
        "stability": 0.62,
        "similarity_boost": 0.70,
        "style": "informative",
        "pitch": "neutral",
        "rate": "medium",
        "emotion": "clarity"
    },
    "voz deportiva": {
        "stability": 0.47,
        "similarity_boost": 0.90,
        "style": "energetic",
        "pitch": "slightly_up",
        "rate": "fast",
        "emotion": "intensity"
    },
    "voz neutra profesional": {
        "stability": 0.65,
        "similarity_boost": 0.75,
        "style": "neutral",
        "pitch": "neutral",
        "rate": "medium",
        "emotion": "objective"
    }
}

# ----------------------------------------------------------------------
# Construye un script de audio profesional para la marca
# ----------------------------------------------------------------------
def construir_script_audio(brand, narrativa):

    historia = narrativa["historia"]
    promesa  = narrativa["promesa_de_valor"]
    diferenciadores = narrativa["diferenciadores"]

    texto = f"""
Bienvenido. Esta es la voz oficial de {brand} dentro del ecosistema SRM-QK-ADSI.

{historia}

Nuestra promesa de valor es clara:
{promesa}

Algunos de nuestros diferenciadores clave son:
- {chr(10).join(['• ' + d for d in diferenciadores])}

Gracias por confiar en {brand}. Este contenido ha sido generado bajo el estándar técnico SRM v28.
    """

    return " ".join(texto.split())


# ----------------------------------------------------------------------
# Generar perfil de voz ElevenLabs para una marca
# ----------------------------------------------------------------------
def generar_voice_profile(brand, narrativa):

    estilo = narrativa["identidad_verbal"][0] if narrativa["identidad_verbal"] else "voz neutra profesional"

    plantilla = VOICE_TEMPLATES.get(estilo, VOICE_TEMPLATES["voz neutra profesional"])

    config = {
        "brand": brand,
        "generated_at": datetime.now().isoformat(),
        "voice_profile": {
            "style": plantilla["style"],
            "emotion": plantilla["emotion"],
            "pitch": plantilla["pitch"],
            "rate": plantilla["rate"],
            "model_params": {
                "stability": plantilla["stability"],
                "similarity_boost": plantilla["similarity_boost"]
            }
        }
    }

    return config


# ----------------------------------------------------------------------
# MAIN GENERATOR
# ----------------------------------------------------------------------
def generar_voz_marcas():

    print("\n=====================================================")
    print("     SRM — BRAND VOICE ELEVENLABS GENERATOR v1")
    print("=====================================================\n")

    for file in os.listdir(NARRATIVE_DIR):

        if not file.endswith("_narrative.json"):
            continue

        narrative_path = os.path.join(NARRATIVE_DIR, file)
        brand_name = file.replace("_narrative.json", "")

        print(f"→ Procesando voz para marca: {brand_name}")

        with open(narrative_path, "r", encoding="utf-8") as f:
            narrativa = json.load(f)

        # Crear perfil de voz
        profile = generar_voice_profile(brand_name, narrativa)

        # Crear script base profesional
        script_voice = construir_script_audio(brand_name, narrativa)

        # Guardar perfil
        out_profile = os.path.join(OUTPUT_DIR, f"{brand_name}_voice_profile.json")
        out_script  = os.path.join(OUTPUT_DIR, f"{brand_name}_voice_script.txt")

        with open(out_profile, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=4, ensure_ascii=False)

        with open(out_script, "w", encoding="utf-8") as f:
            f.write(script_voice)

        print(f"   ✔ Perfil de voz → {out_profile}")
        print(f"   ✔ Script base → {out_script}\n")

    print("=====================================================")
    print(" ✔ BRAND VOICE ELEVENLABS GENERATOR v1 — COMPLETADO")
    print(f" ✔ Output: {OUTPUT_DIR}")
    print("=====================================================\n")



# ----------------------------------------------------------------------
# RUN
# ----------------------------------------------------------------------
if __name__ == "__main__":
    generar_voz_marcas()
