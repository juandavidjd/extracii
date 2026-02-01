import os
import json

BASE_DIR = r"C:\SRM_ADSI\00_docs"
INDEX_PATH = os.path.join(BASE_DIR, "docs_index.json")
REPORT_PATH = os.path.join(BASE_DIR, "docs_report.json")

def load_index():
    if not os.path.exists(INDEX_PATH):
        print("❌ No existe docs_index.json")
        return []

    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def analyze(docs):
    report = {
        "total": len(docs),
        "duplicados": [],
        "por_categoria": {},
        "archivos_grandes": [],
        "categorias_dudosas": [],
        "rutas_invalidas": []
    }

    seen = {}
    for item in docs:
        f = item["file"].lower()

        # Detectar duplicados
        if f in seen:
            report["duplicados"].append([seen[f], item])
        else:
            seen[f] = item

        # Categorías
        cat = item["category"]
        report["por_categoria"].setdefault(cat, 0)
        report["por_categoria"][cat] += 1

        # PDFs muy grandes > 60MB
        try:
            size = os.path.getsize(item["new_path"])
            if size > 60 * 1024 * 1024:
                report["archivos_grandes"].append(item)
        except:
            report["rutas_invalidas"].append(item)

        # Categorías sospechosas
        if cat == "otros":
            report["categorias_dudosas"].append(item)

    return report

def save_report(report):
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)

    print("=============================================")
    print(" ✔ ANÁLISIS COMPLETADO")
    print(f" ✔ Reporte: {REPORT_PATH}")
    print("=============================================")

if __name__ == "__main__":
    docs = load_index()
    if docs:
        report = analyze(docs)
        save_report(report)
