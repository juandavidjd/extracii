# ======================================================================
# brand_narrative_generator_v2.py — SRM-QK-ADSI BRAND CORE v2
# ======================================================================
# Autor: SRM Engine
#
# Propósito:
#   - Tomar el Knowledge Pack generado por brand_knowledge_loader_v1.py.
#   - Construir la narrativa completa de cada marca:
#       * Historia
#       * Identidad verbal
#       * ADN técnico
#       * ADN comercial
#       * Filosofía
#       * Misión / Visión
#       * Promesa de valor
#       * Diferenciadores
#       * Historia SRM de integración
#   - Exportar un JSON narrativo.
# ======================================================================

import os
import json
from datetime import datetime

# ---------------------------------------------------------------
# Rutas principales
# ---------------------------------------------------------------
KNOWLEDGE_PATH = r"C:\SRM_ADSI\03_knowledge_base\brands"
OUTPUT_PATH    = os.path.join(KNOWLEDGE_PATH, "narratives")

os.makedirs(OUTPUT_PATH, exist_ok=True)


# ---------------------------------------------------------------
# Cargar Knowledge Pack
# ---------------------------------------------------------------
def load_knowledge_pack(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------
# Generar narrativa estructurada
# ---------------------------------------------------------------
def construir_narrativa(pack):

    brand = pack["brand"]

    raw_text = pack["raw_text"]
    tech = pack["technical_adn"]
    comm = pack["commercial_adn"]
    sem = pack["semantic_signature"]

    # -----------------------------------------------------------
    # Crear narrativa con estilo SRM-QK-ADSI
    # -----------------------------------------------------------

    historia = (
        f"{brand} es una marca con presencia destacada dentro del ecosistema "
        f"motopartista. Su trayectoria está construida sobre un enfoque técnico "
        f"que combina experiencia, conocimiento mecánico y entendimiento real "
        f"de las necesidades de los usuarios, talleres, distribuidores y flotas. "
        f"Cada pieza, catálogo y solución refleja una historia donde la "
        f"ingeniería, la confiabilidad y la disponibilidad son principios esenciales."
    )

    mision = (
        f"La misión de {brand} es ofrecer soluciones confiables, técnicas y "
        f"de alta calidad que mantengan el desempeño, durabilidad y seguridad "
        f"de las motocicletas en el día a día. La marca busca ser un aliado "
        f"estratégico para importadores, distribuidores, talleres y motociclistas."
    )

    vision = (
        f"La visión de {brand} es consolidarse como un referente técnico en "
        f"la industria motopartista, integrándose plenamente al estándar "
        f"multimarca desarrollado por SRM-QK-ADSI, garantizando compatibilidad, "
        f"integridad y trazabilidad total."
    )

    valores = [
        "Enfoque técnico",
        "Transparencia en la información",
        "Compromiso con la calidad",
        "Disponibilidad real en inventarios",
        "Alineación con el estándar SRM"
    ]

    promesa = (
        f"{brand} se compromete a entregar repuestos confiables, con "
        f"descripciones claras, fitment preciso y especificaciones técnicas "
        f"alineadas a la Enciclopedia de la Motocicleta — Ediciones Mundo. "
        f"Cada SKU avanza hacia un lenguaje estándar dentro del SRM Taxonomy v28."
    )

    diferenciadores = [
        f"ADN técnico característico: {', '.join(tech) if tech else 'Pendiente de expansión.'}",
        f"Enfoque comercial basado en: {', '.join(comm) if comm else 'Valores comerciales básicos.'}",
        f"Personalidad verbal: {', '.join(sem)}",
        "Integración completa con el estándar SRM-QK-ADSI",
        "Descripciones enriquecidas y normalizadas"
    ]

    narrativa_srm = (
        f"Con su incorporación al ecosistema SRM-QK-ADSI, {brand} evoluciona "
        f"de ser una marca aislada a convertirse en un componente integrado "
        f"de un sistema multimarca que comparte taxonomía, estándares técnicos "
        f"y procesos de inventario 360°. Ahora forma parte de un lenguaje "
        f"semántico unificado que permitirá mejorar integraciones, pedidos, "
        f"flujos operativos, stock predictor y agentes SRM."
    )

    return {
        "brand": brand,
        "generated_at": datetime.now().isoformat(),
        "historia": historia,
        "mision": mision,
        "vision": vision,
        "valores": valores,
        "promesa_de_valor": promesa,
        "adn_tecnico": tech,
        "adn_comercial": comm,
        "identidad_verbal": sem,
        "diferenciadores": diferenciadores,
        "integracion_srm": narrativa_srm,
        "raw_extract": raw_text
    }


# ---------------------------------------------------------------
# MAIN: Generar narrativa para cada marca
# ---------------------------------------------------------------
def generar_narrativas():

    print("\n===================================================")
    print("  SRM BRAND NARRATIVE GENERATOR v2 — INICIO")
    print("===================================================\n")

    for file in os.listdir(KNOWLEDGE_PATH):

        if not file.endswith("_knowledge.json"):
            continue

        brand_name = file.replace("_knowledge.json", "")
        path = os.path.join(KNOWLEDGE_PATH, file)

        print(f"→ Generando narrativa para: {brand_name}")

        pack = load_knowledge_pack(path)
        narrativa = construir_narrativa(pack)

        out_path = os.path.join(OUTPUT_PATH, f"{brand_name}_narrative.json")

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(narrativa, f, indent=4, ensure_ascii=False)

        print(f"   ✔ Narrativa generada → {out_path}\n")

    print("===================================================")
    print(" ✔ SRM BRAND NARRATIVE GENERATOR v2 — COMPLETADO")
    print(f" ✔ Output: {OUTPUT_PATH}")
    print("===================================================\n")



# ---------------------------------------------------------------
# RUN
# ---------------------------------------------------------------
if __name__ == "__main__":
    generar_narrativas()
