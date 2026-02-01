import os
import shutil
import json

BASE_DIR = r"C:\SRM_ADSI\00_docs"

TARGETS = {
    "enciclopedia": os.path.join(BASE_DIR, "Enciclopedia"),
    "manuales": os.path.join(BASE_DIR, "Manuales"),
    "catalogos": os.path.join(BASE_DIR, "Catalogos"),
    "pdfs_clientes": os.path.join(BASE_DIR, "PDFs_Clientes"),
    "taxonomia": os.path.join(BASE_DIR, "Taxonomia_Referencia"),
    "otros": os.path.join(BASE_DIR, "Otros"),
}

# Palabras clave para clasificación
KEYWORDS = {
    "enciclopedia": ["enciclopedia", "tomo", "ediciones mundo"],
    "manuales": ["manual", "service", "taller", "workshop", "repair", "mantenimiento"],
    "catalogos": ["catalogo", "repuestos", "parts catalog", "autopartes", "precios"],
    "taxonomia": ["oem", "part list", "exploded", "diagram", "fiche"],
    "pdfs_clientes": ["cliente", "kaiqi", "yokomar", "japan", "store", "importaciones"],
}

def classify_pdf(filename):
    """Clasifica un PDF según palabras clave."""
    name = filename.lower()

    for category, words in KEYWORDS.items():
        if any(word in name for word in words):
            return category

    return "otros"

def ensure_directories():
    """Crear carpetas si no existen"""
    for path in TARGETS.values():
        os.makedirs(path, exist_ok=True)

def move_pdf(src_path, dst_folder):
    """Mover archivo a carpeta destino evitando sobrescritura"""
    filename = os.path.basename(src_path)
    dst_path = os.path.join(dst_folder, filename)

    # Si ya está en su lugar → no mover
    if os.path.dirname(src_path).lower() == dst_folder.lower():
        return dst_path

    # Evitar duplicados agregando sufijo
    if os.path.exists(dst_path):
        base, ext = os.path.splitext(dst_path)
        counter = 1
        while os.path.exists(f"{base}_{counter}{ext}"):
            counter += 1
        dst_path = f"{base}_{counter}{ext}"

    shutil.move(src_path, dst_path)
    return dst_path

def scan_and_organize():
    """Escanear PDFs y organizarlos"""
    docs_index = []

    for root, _, files in os.walk(BASE_DIR):
        for file in files:
            if not file.lower().endswith(".pdf"):
                continue

            full_path = os.path.join(root, file)
            category = classify_pdf(file)
            dst_folder = TARGETS[category]
            new_path = move_pdf(full_path, dst_folder)

            docs_index.append({
                "file": file,
                "original_path": full_path,
                "new_path": new_path,
                "category": category
            })

            print(f"[{category.upper()}] {file}")

    # Guardar índice JSON
    index_path = os.path.join(BASE_DIR, "docs_index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(docs_index, f, indent=4, ensure_ascii=False)

    print("\n==============================================")
    print(" ✔ ORGANIZACIÓN COMPLETADA")
    print(f" ✔ Índice generado: {index_path}")
    print("==============================================")

if __name__ == "__main__":
    ensure_directories()
    scan_and_organize()
