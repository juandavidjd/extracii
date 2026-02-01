# ======================================================================
# srm_agent_builder_v1.py — SRM-QK-ADSI AGENT CORE v1
# ======================================================================
# Autor: SRM Engine
#
# Propósito:
#   - Construir la base cognitiva de todos los agentes SRM.
#   - Integrar Brand Core + Narrativas + Voceo + Lovable + Taxonomía + Roles.
#   - Producir agentes listos para orquestación multimodelo (Lovable/ElevenLabs).
# ======================================================================

import os
import json
from datetime import datetime

# ----------------------------------------------------------------------
# RUTAS PRINCIPALES
# ----------------------------------------------------------------------
KB_BRANDS      = r"C:\SRM_ADSI\03_knowledge_base\brands"
BRAND_PROFILES = os.path.join(KB_BRANDS, "lovable_profiles")
NARRATIVES     = os.path.join(KB_BRANDS, "narratives")
VOICES          = os.path.join(KB_BRANDS, "voices")

KB_CONFIG      = r"C:\SRM_ADSI\03_knowledge_base\config"
KB_MOTOR       = r"C:\SRM_ADSI\03_knowledge_base"

OUTPUT_AGENTS  = r"C:\SRM_ADSI\03_knowledge_base\agents"
os.makedirs(OUTPUT_AGENTS, exist_ok=True)


# ----------------------------------------------------------------------
# Cargar utilidades
# ----------------------------------------------------------------------
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ----------------------------------------------------------------------
# Cargar conocimiento técnico SRM
# ----------------------------------------------------------------------
def load_srm_technical_knowledge():

    vocab      = load_json(os.path.join(KB_MOTOR, "vocabulario_srm.json"))
    sinonimos  = load_json(os.path.join(KB_MOTOR, "mapa_sinonimos.json"))
    estructura = load_json(os.path.join(KB_MOTOR, "estructura_mecanica.json"))
    oem        = load_json(os.path.join(KB_MOTOR, "indice_oem.json"))
    tax        = load_json(os.path.join(KB_MOTOR, "matriz_taxonomica_base.json"))

    return {
        "vocabulario_srm": vocab,
        "sinonimos": sinonimos,
        "estructura_mecanica": estructura,
        "indice_oem": oem,
        "taxonomia_srm": tax
    }


# ----------------------------------------------------------------------
# Construir agente genérico
# ----------------------------------------------------------------------
def build_agent(name, role_desc, system_instructions, brand_profiles, srm_tech, permisos):

    return {
        "agent_name": name,
        "generated_at": datetime.now().isoformat(),

        "role_description": role_desc,
        "system_instructions": system_instructions,

        "brand_profiles": brand_profiles,
        "technical_knowledge": srm_tech,
        "permissions": permisos
    }


# ----------------------------------------------------------------------
# Ensamblar agentes SRM
# ----------------------------------------------------------------------
def generar_agentes():

    print("\n====================================================")
    print("        SRM — AGENT BUILDER v1 (FASE CORE)")
    print("====================================================\n")

    # -----------------------------
    # Cargar perfiles de marca
    # -----------------------------
    perfiles = {}
    for file in os.listdir(BRAND_PROFILES):
        if file.endswith("_lovable.json"):
            brand = file.replace("_lovable.json", "")
            perfiles[brand] = load_json(os.path.join(BRAND_PROFILES, file))

    # -----------------------------
    # Conocimiento técnico SRM
    # -----------------------------
    srm_tech = load_srm_technical_knowledge()

    # -----------------------------
    # Roles y permisos SRM
    # -----------------------------
    permisos = load_json(os.path.join(KB_CONFIG, "roles_permisos_srm.json"))

    # ===================================================================
    # AGENTES DEFINIDOS
    # ===================================================================

    agentes = {

        "agente_comercial_srm": {
            "role": "Asesor Comercial SRM",
            "desc": "Agente especializado en ventas, disponibilidad, fitment, equivalencias y cierres comerciales.",
            "instructions": """
Eres el Agente Comercial SRM. Tu tarea es ayudar a resolver dudas comerciales,
consultar inventarios (cuando estén disponibles), sugerir equivalencias basadas 
en taxonomía SRM y construir mensajes profesionales alineados con el lenguaje 
técnico-comercial de cada marca del ecosistema SRM-QK-ADSI.
"""
        },

        "agente_tecnico_srm": {
            "role": "Especialista Técnico SRM",
            "desc": "Interpretación técnica, sistemas mecánicos, eléctricos, fitment y estructura OEM.",
            "instructions": """
Eres el Agente Técnico SRM. Tu enfoque es totalmente técnico. Explicas sistemas,
subsistemas, componentes, fitment, OEM, estructura mecánica, fallas frecuentes,
y lineamientos técnicos basados en la Enciclopedia de la Motocicleta y el estándar SRM.
"""
        },

        "agente_inventarios_360": {
            "role": "Coordinador de Inventarios 360°",
            "desc": "Interpreta, analiza y gestiona disponibilidad multicentro.",
            "instructions": """
Eres el Agente Inventarios 360°. Actúas sobre datos consolidados de stock, 
equivalencias, redundancias y disponibilidad. Eres preciso, cuantitativo y claro.
"""
        },

        "agente_pedidos_audio": {
            "role": "Agente Audio-Pedidos SRM",
            "desc": "Convierte voz → intención → pedido → mensaje estructurado.",
            "instructions": """
Eres el Agente Audio-Pedidos SRM. Recibes instrucciones habladas, las interpretas,
y devuelves pedidos estructurados, corregidos, normalizados y compatibles con SRM.
"""
        },

        "agente_onboarding_srm": {
            "role": "Guía de Onboarding SRM",
            "desc": "Explica cómo funciona SRM, sus módulos, procesos y beneficios.",
            "instructions": """
Eres el Agente de Onboarding SRM. Enseñas, guías, explicas y describes cada 
módulo del sistema SRM-QK-ADSI de manera clara para usuarios nuevos.
"""
        },

        "agente_guided_tour": {
            "role": "Agente Guided Tour",
            "desc": "Navega interfaces, paneles y opciones de Lovable y SRM.",
            "instructions": """
Eres el Agente Guided Tour SRM. Navegas paso a paso, explicas pantallas,
botones, paneles y flujos en interfaces Lovable, dashboards y paneles SRM.
"""
        },

        "agente_legal_srm": {
            "role": "Asesor Legal SRM",
            "desc": "Evalúa riesgos, contratos, disclaimers y blindajes.",
            "instructions": """
Eres el Agente Legal SRM. Mantienes consistencia con el SRM Legal Engine™.
Evalúas textos legales, sesión de marca, disclaimers y condiciones de uso.
"""
        },

        "agente_flotas_srm": {
            "role": "Agente Flotas & Motos Cliente",
            "desc": "Gestiona vehículos, historial, mantenimiento, predictivo y repuestos.",
            "instructions": """
Eres el Agente SRM para Flotas y Motos Cliente. Gestionas historial de mantenimiento,
recomendaciones técnicas, consumibles, predictivo y rutas recomendadas de piezas.
"""
        },

        "agente_academia_srm": {
            "role": "Instructor Academia SRM",
            "desc": "Genera material educativo técnico-comercial basado en SRM",
            "instructions": """
Eres el Instructor de la Academia SRM. Generas contenido didáctico, guías,
prácticas, explicaciones y evaluaciones basadas en contenido SRM Core.
"""
        }
    }

    # ===================================================================
    # Construcción de agentes
    # ===================================================================
    for agent_key, info in agentes.items():

        print(f"→ Construyendo {agent_key}...")

        agent = build_agent(
            name=info["role"],
            role_desc=info["desc"],
            system_instructions=info["instructions"],
            brand_profiles=perfiles,
            srm_tech=srm_tech,
            permisos=permisos
        )

        out_path = os.path.join(OUTPUT_AGENTS, f"{agent_key}.json")

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(agent, f, indent=4, ensure_ascii=False)

        print(f"   ✔ Creado → {out_path}\n")

    print("====================================================")
    print(" ✔ SRM AGENT BUILDER v1 — COMPLETADO")
    print(f" ✔ Output: {OUTPUT_AGENTS}")
    print("====================================================\n")


# ----------------------------------------------------------------------
# RUN
# ----------------------------------------------------------------------
if __name__ == "__main__":
    generar_agentes()
