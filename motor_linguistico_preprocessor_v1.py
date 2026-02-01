import os
import json
import re

# Rutas base
BASE_DOCS = r"C:\SRM_ADSI\00_docs"
INDEX_PATH = os.path.join(BASE_DOCS, "docs_index.json")
KNOWLEDGE_BASE = r"C:\SRM_ADSI\03_knowledge_base"

# Crear KB si no existe
os.makedirs(KNOWLEDGE_BASE, exist_ok=True)

# Archivos de salida
VOCAB_FILE      = os.path.join(KNOWLEDGE_BASE, "vocabulario_srm.json")
EMPIRIC_FILE    = os.path.join(KNOWLEDGE_BASE, "terminologia_empirica.json")
SINONIMOS_FILE  = os.path.join(KNOWLEDGE_BASE, "mapa_sinonimos.json")
ESTRUCTURA_FILE = os.path.join(KNOWLEDGE_BASE, "estructura_mecanica.json")
OEM_FILE        = os.path.join(KNOWLEDGE_BASE, "indice_oem.json")
TAXO_FILE       = os.path.join(KNOWLEDGE_BASE, "matriz_taxonomica_base.json")

# Palabras clave para detectar contextos mecánicos
SISTEMAS = {
    "motor": ["piston", "cilindro", "culata", "válvula", "árbol de levas", "biela"],
    "transmision": ["cadena", "sprocket", "piñón", "engranaje", "embrague"],
    "frenos": ["disco", "pastillas", "caliper", "bomba de freno", "mordaza"],
    "suspension": ["amortiguador", "tijera", "botella", "resorte"],
    "electrico": ["bobina", "arranque", "cdI", "rectificador", "alternador"],
    "carroceria": ["guardabarro", "tapa", "carenaje"],
}

# Empírico → técnico (base inicial; se expandirá con el PDF)
EMPIRICO_BASE = {
    "pacha": "sprocket",
    "piñon": "pinion",
    "trompo": "switch luz neutra",
    "pistera": "deportiva",
    "cadenilla": "cadena de distribución",
}

def load_index():
    """Cargar docs_index.json"""
    if not os.path.exists(INDEX_PATH):
        print("❌ No existe docs_index.json")
        return []
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def extract_text_stub(pdf_path):
    """
    EXTRACCIÓN SIMPLE
    Por ahora solo lee nombres y patrones de texto de filename.
    (OCR se activará en v2)
    """
    text = os.path.basename(pdf_path).lower()

    # Reemplazar guiones/puntos por espacios
    text = re.sub(r"[_\-\.]", " ", text)

    return text

def process_docs(docs):
    vocabulario = set()
    empirico = dict(EMPIRICO_BASE)
    sinonimos = {}
    estructura = {s: set() for s in SISTEMAS.keys()}
    oem_index = {}
    taxonomia = {}

    for item in docs:
        categoria = item.get("category", "otros")
        path = item.get("new_path")

        if not os.path.exists(path):
            continue

        contenido = extract_text_stub(path)

        palabras = contenido.split()

        # Construir vocabulario total
        for p in palabras:
            if len(p) > 2:
                vocabulario.add(p)

        # Clasificar palabras por sistemas mecánicos
        for sistema, kws in SISTEMAS.items():
            for kw in kws:
                if kw in contenido:
                    estructura[sistema].add(path)

        # Detección simple de OEM
        if "oem" in contenido or "part" in contenido:
            oem_index[path] = palabras

        # Mapear palabras empíricas si aparecen
        for emp, tec in EMPIRICO_BASE.items():
            if emp in contenido:
                empirico[emp] = tec

        # Construcción de taxonomía básica por categoría
        taxonomia.setdefault(categoria, []).append(path)

    # Convertir sets a listas
    estructura = {k: list(v) for k, v in estructura.items()}
    vocabulario = sorted(list(vocabulario))

    return vocabulario, empirico, sinonimos, estructura, oem_index, taxonomia

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def run_preprocessor():
    print("===============================================")
    print("  SRM – Motor Lingüístico Técnico v1 (Preprocesador)")
    print("===============================================")

    docs = load_index()
    if not docs:
        print("❌ No hay documentos para procesar.")
        return

    vocabulario, empirico, sinonimos, estructura, oem, taxonomia = process_docs(docs)

    save_json(VOCAB_FILE, vocabulario)
    save_json(EMPIRIC_FILE, empirico)
    save_json(SINONIMOS_FILE, sinonimos)
    save_json(ESTRUCTURA_FILE, estructura)
    save_json(OEM_FILE, oem)
    save_json(TAXO_FILE, taxonomia)

    print("✔ vocabulario_srm.json generado")
    print("✔ terminologia_empirica.json generado")
    print("✔ mapa_sinonimos.json generado")
    print("✔ estructura_mecanica.json generado")
    print("✔ indice_oem.json generado")
    print("✔ matriz_taxonomica_base.json generado")

    print("\n===============================================")
    print("  ✔ Motor Lingüístico Técnico SRM – COMPLETADO")
    print(f"  ✔ Knowledge Base: {KNOWLEDGE_BASE}")
    print("===============================================")

if __name__ == "__main__":
    run_preprocessor()
