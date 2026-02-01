# ======================================================================
# srm_integrator_v1.py — SRM-QK-ADSI PIPELINE ORCHESTRATOR v1
# ======================================================================
# Autor: SRM Engine
#
# Propósito general:
#   - Ejecutar los módulos principales del Pipeline SRM v28.
#   - Orquestar Branding, Narrativa, Audio, Academy, Agents y Shopify.
#   - Validar dependencias y rutas.
#   - Generar LOG maestro del Pipeline.
#
# Este integrador NO ejecuta procesos destructivos.
# Solo orquesta módulos que ya conocemos como seguros.
# ======================================================================

import os
import subprocess
from datetime import datetime
import json

# ----------------------------------------------------------------------
# RUTAS
# ----------------------------------------------------------------------
PIPELINE_DIR = r"C:\SRM_ADSI\05_pipeline"
LOG_DIR = os.path.join(PIPELINE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "pipeline_v28_log.json")


# ----------------------------------------------------------------------
# UTILIDADES
# ----------------------------------------------------------------------
def run_module(name, script):
    """Ejecuta un módulo del pipeline y captura su salida."""
    script_path = os.path.join(PIPELINE_DIR, script)

    if not os.path.exists(script_path):
        return {
            "module": name,
            "status": "ERROR",
            "details": f"Script no encontrado: {script_path}"
        }

    print(f"\n▶ Ejecutando módulo: {name}")

    try:
        output = subprocess.check_output(
            ["python", script_path],
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )

        print(output)

        return {
            "module": name,
            "status": "OK",
            "details": output
        }

    except subprocess.CalledProcessError as e:
        return {
            "module": name,
            "status": "ERROR",
            "details": e.output
        }


# ----------------------------------------------------------------------
# DEFINICIÓN DEL PIPELINE (ORDEN CANÓNICO SRM v28)
# ----------------------------------------------------------------------
PIPELINE_ORDER = [
    # 1 — BRANDING CORE SYSTEM
    ("Brand Knowledge Loader",          "brand_knowledge_loader_v1.py"),
    ("Brand Narrative Generator",       "brand_narrative_generator_v2.py"),
    ("Brand ElevenLabs Voice",          "brand_voice_elevenlabs_generator_v1.py"),
    ("Brand Lovable Profile",           "brand_lovable_profile_v1.py"),

    # 2 — AGENTS CORE
    ("SRM Agent Builder",               "srm_agent_builder_v1.py"),

    # 3 — ACADEMY CORE
    ("SRM Academy Generator",           "srm_academy_generator_v1.py"),

    # 4 — AUDIO CORE
    ("SRM Audio Packager",              "srm_audio_packager_v1.py"),

    # 5 — FRONTEND CORE
    ("SRM Frontend Sync",               "srm_frontend_sync_v1.py"),

    # 6 — PRODUCT / INVENTORY CORE
    ("Shopify Exporter",                "srm_shopify_exporter_v1.py"),
    ("Inventory Sync Engine",           "srm_inventory_sync_v1.py"),

    # 7 — SHOPIFY LIVE API (SAFE MODE)
    ("Shopify API Sync",                "srm_shopify_api_sync_v1.py"),
]


# ----------------------------------------------------------------------
# MAIN ORCHESTRATION
# ----------------------------------------------------------------------
def ejecutar_pipeline():

    print("\n=====================================================")
    print("          SRM — PIPELINE ORCHESTRATOR v1")
    print("=====================================================\n")

    log_data = {
        "pipeline": "SRM v28",
        "executed_at": datetime.now().isoformat(),
        "modules": []
    }

    for name, script in PIPELINE_ORDER:
        result = run_module(name, script)
        log_data["modules"].append(result)

    # Guardar log maestro
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=4, ensure_ascii=False)

    print("\n=====================================================")
    print(" ✔ PIPELINE SRM v28 — EJECUCIÓN COMPLETADA")
    print(f" ✔ Log guardado en: {LOG_FILE}")
    print("=====================================================\n")


# ----------------------------------------------------------------------
# RUN
# ----------------------------------------------------------------------
if __name__ == "__main__":
    ejecutar_pipeline()
