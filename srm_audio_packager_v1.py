# ======================================================================
# srm_audio_packager_v1.py — SRM-QK-ADSI AUDIO CORE v1
# ======================================================================
# Autor: SRM Engine
#
# Propósito:
#   - Preparar paquetes de audio para ElevenLabs, Lovable y SRM.
#   - Empaquetar scripts, perfiles de voz, narrativa visual y datos SRM.
#   - Crear "production-ready packs" por marca.
# ======================================================================

import os
import json
from datetime import datetime

# ----------------------------------------------------------------------
# DIRECTORIOS
# ----------------------------------------------------------------------
ROOT = r"C:\SRM_ADSI\03_knowledge_base\brands"

VOICE_DIR     = os.path.join(ROOT, "voices")
NARRATIVE_DIR = os.path.join(ROOT, "narratives")
LOVABLE_DIR   = os.path.join(ROOT, "lovable_profiles")

AUDIO_OUTPUT = os.path.join(ROOT, "audio_packs")
os.makedirs(AUDIO_OUTPUT, exist_ok=True)


# ----------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ----------------------------------------------------------------------
# Construir metadata para producción
# ----------------------------------------------------------------------
def construir_audio_metadata(brand, narrativa, voice_profile, lovable_profile):

    script_path = os.path.join(VOICE_DIR, f"{brand}_voice_script.txt")

    with open(script_path, "r", encoding="utf-8") as f:
        script_text = f.read().strip()

    voice_cfg = voice_profile["voice_profile"]

    metadata = {
        "brand": brand,
        "generated_at": datetime.now().isoformat(),

        "script": script_text,
        "voice_settings": {
            "style": voice_cfg["style"],
            "emotion": voice_cfg["emotion"],
            "pitch": voice_cfg["pitch"],
            "rate": voice_cfg["rate"],
            "model_params": voice_cfg["model_params"]
        },

        "narrativa_resumida": {
            "historia": narrativa.get("historia", ""),
            "promesa": narrativa.get("promesa_de_valor", ""),
            "diferenciadores": narrativa.get("diferenciadores", [])
        },

        "visual_support": {
            "logo": lovable_profile["ui_config"]["logo_path"],
            "colors": lovable_profile["ui_config"]["theme_colors"],
            "tagline": lovable_profile["metadata"]["tagline"]
        },

        "editorial_notes": {
            "timing_sugerido_seg": {
                "intro": 3,
                "historia": 12,
                "promesa": 8,
                "cierre": 4
            },
            "tono_general": ", ".join(narrativa["identidad_verbal"]),
            "recomendacion_edicion": "Usar música ambiente leve industrial-tecnológica. Mantener claridad vocal.",
            "recomendacion_audio_master": "-2.5 dB peak, normalización -14 LUFS."
        }
    }

    return metadata


# ----------------------------------------------------------------------
# Construir instrucciones de producción
# ----------------------------------------------------------------------
def construir_production_notes(brand, audio_metadata):

    texto = f"""
Producción de Audio Oficial SRM-QK-ADSI — Marca: {brand}

Instrucciones:

1) Voz y estilo:
   - Estilo: {audio_metadata['voice_settings']['style']}
   - Emoción: {audio_metadata['voice_settings']['emotion']}
   - Pitch: {audio_metadata['voice_settings']['pitch']}
   - Cadencia: {audio_metadata['voice_settings']['rate']}

2) Estructura recomendada:
   - Introducción (3s)
   - Historia de la marca (10–12s)
   - Promesa y diferenciadores (8s)
   - Cierre (4s)

3) Notas de edición:
   - Música ambiente suave, industrial o tecnológica.
   - Mantener inteligibilidad total.
   - No usar efectos exagerados.
   - Nivel final: -14 LUFS, pico -2.5dB.

4) Uso sugerido:
   - Onboarding SRM
   - Web institucional Lovable
   - Vídeos de marca
   - Material de entrenamiento
   - Presentaciones SRM

5) Script oficial:
{audio_metadata['script']}

    """

    return "\n".join([l.strip() for l in texto.split("\n")])


# ----------------------------------------------------------------------
# Construir configuración para reproductores UI
# ----------------------------------------------------------------------
def construir_player_config(brand, lovable_profile):

    return {
        "brand": brand,
        "player_theme": lovable_profile["ui_config"]["theme_colors"],
        "waveform_style": "rounded",
        "show_timestamp": True,
        "auto_play": False,
        "display_logo": True
    }


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------
def generar_audio_packs():

    print("\n=====================================================")
    print("          SRM — AUDIO PACKAGER v1 (OFICIAL)")
    print("=====================================================\n")

    for file in os.listdir(VOICE_DIR):

        if not file.endswith("_voice_profile.json"):
            continue

        brand = file.replace("_voice_profile.json", "")

        print(f"→ Empaquetando audio para marca: {brand}")

        # Cargar data
        voice_profile = load_json(os.path.join(VOICE_DIR, file))
        narrativa     = load_json(os.path.join(NARRATIVE_DIR, f"{brand}_narrative.json"))
        lovable       = load_json(os.path.join(LOVABLE_DIR, f"{brand}_lovable.json"))

        # Construir packs
        metadata  = construir_audio_metadata(brand, narrativa, voice_profile, lovable)
        notes     = construir_production_notes(brand, metadata)
        player    = construir_player_config(brand, lovable)

        # Guardar archivos
        out_meta  = os.path.join(AUDIO_OUTPUT, f"{brand}_audio_pack.json")
        out_notes = os.path.join(AUDIO_OUTPUT, f"{brand}_production_notes.txt")
        out_player = os.path.join(AUDIO_OUTPUT, f"{brand}_player_config.json")

        with open(out_meta, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4, ensure_ascii=False)

        with open(out_notes, "w", encoding="utf-8") as f:
            f.write(notes)

        with open(out_player, "w", encoding="utf-8") as f:
            json.dump(player, f, indent=4, ensure_ascii=False)

        print(f"   ✔ Audio Pack → {out_meta}")
        print(f"   ✔ Production Notes → {out_notes}")
        print(f"   ✔ Player Config → {out_player}\n")

    print("=====================================================")
    print(" ✔ AUDIO PACKAGER v1 — COMPLETADO")
    print(f" ✔ Output: {AUDIO_OUTPUT}")
    print("=====================================================\n")


# ----------------------------------------------------------------------
# RUN
# ----------------------------------------------------------------------
if __name__ == "__main__":
    generar_audio_packs()
