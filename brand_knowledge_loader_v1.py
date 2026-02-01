# ======================================================================
# brand_knowledge_loader_v1.py — SRM-QK-ADSI — BRAND CORE v1
# ======================================================================
# Autor: SRM Engine
#
# Propósito:
#   - Cargar y estructurar el conocimiento de cada marca.
#   - Extraer ADN técnico, ADN comercial y ADN semántico.
#   - Preparar un "Brand Knowledge Pack" para uso de:
#       * brand_narrative_generator_v2.py
#       * brand_voice_elevenlabs_generator_v1.py
#       * brand_lovable_profile_v1.py
#       * SRM Guided Tour
#       * SRM Agents
#       * SRM Legal Engine
# ======================================================================

import os
import json
import re
import fitz  # PyMuPDF para lectura PDF

# ----------------------------------------------------------------------
# Rutas principales
# ----------------------------------------------------------------------
DOCS_PATH = r"C:\SRM_ADSI\00_docs"
BRAND_DOCS_PATH = os.path.join(DOCS_PATH, "Perfiles")
OUTPUT_PATH = r"C:\SRM_ADSI\03_knowledge_base\brands"

os.makedirs(OUTPUT_PATH, exist_ok=True)

# ----------------------------------------------------------------------
# Función para leer PDF
# ----------------------------------------------------------------------
def extract_text_pdf(path):
    try:
        doc = fitz.open(path)
        text = "\n".join(page.get_text() for page in doc)
        return text
    except Exception as e:
        print(f"[ERROR] No se pudo leer PDF {path}: {e}")
        return ""


# ----------------------------------------------------------------------
# Limpieza básica de texto
# ----------------------------------------------------------------------
def clean_text(text):
    text = re.sub(r"\s+", " ", text)
    text = text.replace("◼", "").replace("•", "").replace("●", "")
    return text.strip()


# ----------------------------------------------------------------------
# Extraer ADN técnico (terminología mecánica, sistemas, subsistemas)
# ----------------------------------------------------------------------
def extract_technical_adn(text):
    patrones = [
        r"(motor.*?)\b",
        r"(carburador.*?)\b",
        r"(freno.*?)\b",
        r"(eléctrico.*?)\b",
        r"(transmisión.*?)\b",
        r"(suspensión.*?)\b",
        r"(inyector.*?)\b",
        r"(encendido.*?)\b",
        r"(admisión.*?)\b",
    ]
    resultados = []
    for p in patrones:
        matches = re.findall(p, text, flags=re.IGNORECASE)
        resultados.extend(matches)
    return list(set(resultados))


# ----------------------------------------------------------------------
# Extraer ADN comercial (promesas, valores, diferenciales)
# ----------------------------------------------------------------------
def extract_commercial_adn(text):
    claves = [
        "calidad", "garantía", "respaldo", "importador",
        "distribuidor", "durabilidad", "estándar", "OEM",
        "mejor rendimiento", "mayor vida útil", "certificación"
    ]
    encontrados = [c for c in claves if c.lower() in text.lower()]
    return list(set(encontrados))


# ----------------------------------------------------------------------
# Extraer identidad verbal (tono, estilo, personalidad)
# ----------------------------------------------------------------------
def extract_semantic_signature(text):
    tono = []

    if "calidad" in text.lower(): tono.append("enfoque técnico-premium")
    if "experiencia" in text.lower(): tono.append("voz confiable")
    if "innovación" in text.lower(): tono.append("voz moderna")
    if "economía" in text.lower(): tono.append("voz práctica")
    if "desempeño" in text.lower(): tono.append("voz deportiva")

    if not tono:
        tono.append("voz neutra profesional")

    return tono


# ----------------------------------------------------------------------
# Procesar un archivo de marca
# ----------------------------------------------------------------------
def process_brand_pdf(pdf_path, brand_name):
    raw_text = extract_text_pdf(pdf_path)
    cleaned = clean_text(raw_text)

    tech = extract_technical_adn(cleaned)
    commercial = extract_commercial_adn(cleaned)
    semantic = extract_semantic_signature(cleaned)

    return {
        "brand": brand_name,
        "raw_text": cleaned,
        "technical_adn": tech,
        "commercial_adn": commercial,
        "semantic_signature": semantic
    }


# ----------------------------------------------------------------------
# MAIN: Procesar todas las marcas del directorio /Perfiles
# ----------------------------------------------------------------------
def cargar_marcas():

    print("\n==============================================")
    print("      SRM BRAND KNOWLEDGE LOADER v1 — INICIO")
    print("==============================================\n")

    for file in os.listdir(BRAND_DOCS_PATH):

        if not file.lower().endswith(".pdf"):
            continue

        brand_name = os.path.splitext(file)[0].replace(" ", "_")

        pdf_path = os.path.join(BRAND_DOCS_PATH, file)

        print(f"→ Procesando marca: {brand_name}")

        pack = process_brand_pdf(pdf_path, brand_name)

        # Guardar Knowledge Pack
        out = os.path.join(OUTPUT_PATH, f"{brand_name}_knowledge.json")

        with open(out, "w", encoding="utf-8") as f:
            json.dump(pack, f, indent=4, ensure_ascii=False)

        print(f"   ✔ Knowledge Pack → {out}\n")

    print("==============================================")
    print(" ✔ SRM BRAND KNOWLEDGE LOADER v1 — COMPLETADO")
    print(f" ✔ Output: {OUTPUT_PATH}")
    print("==============================================\n")


# ----------------------------------------------------------------------
# RUN
# ----------------------------------------------------------------------
if __name__ == "__main__":
    cargar_marcas()
