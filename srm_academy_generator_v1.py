# ======================================================================
# srm_academy_generator_v1.py — SRM-QK-ADSI — ACADEMIA SRM v1
# ======================================================================
# Autor: SRM Engine
#
# Propósito:
#   - Generar los módulos educativos SRM 360° basados en:
#       * Taxonomía SRM
#       * Enciclopedia de la Motocicleta
#       * Motor Lingüístico Técnico
#       * Perfiles de Marca
#       * Agentes SRM
#       * Narrativa técnica del ecosistema
# ======================================================================

import os
import json
from datetime import datetime

# ----------------------------------------------------------------------
# DIRECTORIOS
# ----------------------------------------------------------------------
ROOT_KB     = r"C:\SRM_ADSI\03_knowledge_base"
MOTOR_PATH  = ROOT_KB
BRANDS_PATH = os.path.join(ROOT_KB, "brands")
AGENTS_PATH = os.path.join(ROOT_KB, "agents")

OUTPUT_DIR  = os.path.join(ROOT_KB, "academy")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ----------------------------------------------------------------------
# Cargar archivos JSON genéricos
# ----------------------------------------------------------------------
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ----------------------------------------------------------------------
# Cargar núcleo técnico SRM
# ----------------------------------------------------------------------
def load_srm_technical_core():
    vocab      = load_json(os.path.join(MOTOR_PATH, "vocabulario_srm.json"))
    sinonimos  = load_json(os.path.join(MOTOR_PATH, "mapa_sinonimos.json"))
    estructura = load_json(os.path.join(MOTOR_PATH, "estructura_mecanica.json"))
    oem        = load_json(os.path.join(MOTOR_PATH, "indice_oem.json"))
    tax        = load_json(os.path.join(MOTOR_PATH, "matriz_taxonomica_base.json"))
    return vocab, sinonimos, estructura, oem, tax


# ----------------------------------------------------------------------
# Crear módulos educativos
# ----------------------------------------------------------------------
def crear_modulos_srm(vocab, sinonimos, estructura, oem, tax):

    # ===== NIVELES =====

    niveles = {
        "Nivel 1 — Fundamentos SRM": {
            "descripcion": "Conceptos básicos del ecosistema SRM-QK-ADSI.",
            "modulos": [
                "¿Qué es SRM?",
                "Entendiendo la estructura de catálogo multimarca",
                "Taxonomía SRM — Introducción",
                "Nomenclatura de repuestos: OEM vs Aftermarket",
                "Cómo se describe un repuesto correctamente",
                "Buenas prácticas de comunicación técnica"
            ]
        },

        "Nivel 2 — Módulo Técnico SRM": {
            "descripcion": "Fundamentos mecánicos y eléctricos del sistema motocicleta.",
            "modulos": [
                "Sistema motor — componentes y fallas frecuentes",
                "Sistema admisión / inyección",
                "Sistema encendido",
                "Sistema eléctrico general",
                "Transmisión primaria y secundaria",
                "Suspensión delantera y trasera",
                "Frenos — Disco, tambor y sistema hidráulico"
            ]
        },

        "Nivel 3 — Profesional SRM": {
            "descripcion": "Aplicación técnica + comercial del estándar SRM.",
            "modulos": [
                "Cómo identificar correctamente un repuesto",
                "Interpretación de catálogos multimarca",
                "Detección de equivalencias SRM",
                "Fitment avanzado",
                "Errores comunes del sector y cómo evitarlos",
                "Integración de marcas al estándar",
            ]
        },

        "Nivel 4 — Inventarios 360°": {
            "descripcion": "Gestión inteligente de inventarios y modelos predictivos.",
            "modulos": [
                "Concepto de Disponibilidad 360°",
                "Cómo interpretar un Inventario SRM",
                "Redundancia y equivalencias aplicadas al stock",
                "Clasificación ABC aplicada a motocicletas",
                "Stock Predictor — Introducción"
            ]
        },

        "Nivel 5 — Maestro SRM (Nivel Elite)": {
            "descripcion": "Dominio total de SRM para importadores, fabricantes y arquitectos técnicos.",
            "modulos": [
                "Estructura mecánica profunda SRM",
                "Optimización de catálogos multimarca",
                "Construcción de taxonomías personalizadas",
                "Integración SRM con ERP / WMS",
                "Diseño de arquitecturas omnicanal SRM"
            ]
        }
    }

    return niveles


# ----------------------------------------------------------------------
# Generar ejercicios, actividades y exámenes
# ----------------------------------------------------------------------
def generar_contenido_didactico(niveles, vocab, estructura):

    contenido = {}

    for nivel, data in niveles.items():
        actividades = []
        exam = []

        for modulo in data["modulos"]:

            actividades.append({
                "modulo": modulo,
                "actividad": f"Explica con tus palabras el concepto de '{modulo}'.",
                "practica": f"Crea un ejemplo real aplicado al ecosistema SRM del módulo '{modulo}'."
            })

            exam.append({
                "pregunta": f"¿Cuál es la definición correcta dentro del estándar SRM del tema '{modulo}'?",
                "tipo": "abierta",
                "dificultad": "media"
            })

        contenido[nivel] = {
            "actividades": actividades,
            "evaluacion": exam
        }

    return contenido


# ----------------------------------------------------------------------
# Generar Academia SRM completa
# ----------------------------------------------------------------------
def generar_academia():

    print("\n======================================================")
    print("        SRM — ACADEMY GENERATOR v1 (OFICIAL)")
    print("======================================================\n")

    vocab, sinonimos, estructura, oem, tax = load_srm_technical_core()

    print("→ Cargando núcleo técnico SRM… OK")

    niveles = crear_modulos_srm(vocab, sinonimos, estructura, oem, tax)
    print("→ Módulos académicos generados… OK")

    contenido = generar_contenido_didactico(niveles, vocab, estructura)
    print("→ Contenido didáctico estructurado… OK\n")

    # Output final
    academia = {
        "generated_at": datetime.now().isoformat(),
        "niveles": niveles,
        "contenido": contenido,
        "recursos_srm": {
            "vocabulario": vocab,
            "estructura_mecanica": estructura,
            "taxonomia": tax
        }
    }

    out_path = os.path.join(OUTPUT_DIR, "srm_academy_v1.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(academia, f, indent=4, ensure_ascii=False)

    print("======================================================")
    print(" ✔ ACADEMIA SRM v1 — GENERADA CORRECTAMENTE")
    print(f" ✔ Archivo: {out_path}")
    print("======================================================\n")


# ----------------------------------------------------------------------
# RUN
# ----------------------------------------------------------------------
if __name__ == "__main__":
    generar_academia()
