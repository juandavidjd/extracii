# ======================================================================
# srm_diagnostics_v1.py — SRM-QK-ADSI DIAGNOSTIC ENGINE v1
# ======================================================================
# Autor: SRM Engine
#
# Propósito:
#   - Escanear todo el ecosistema SRM y generar un diagnóstico técnico.
#   - Verificar existencia, consistencia y salud de archivos y carpetas.
#   - Detectar faltantes en Branding, Narrativas, Voces, Academy, Agents,
#     Shopify Export, Inventario, Bundles y Logs.
#   - Generar un informe técnico + panel visual HTML.
#
# Resultados:
#   diagnostics_report.json
#   diagnostics_panel.html
# ======================================================================

import os
import json
from datetime import datetime

# ----------------------------------------------------------------------
# RUTAS BASE
# ----------------------------------------------------------------------
ROOT = r"C:\SRM_ADSI"

BRANDS = os.path.join(ROOT, "03_knowledge_base", "brands")
PIPELINE = os.path.join(ROOT, "05_pipeline")
NORMALIZED = os.path.join(ROOT, "02_cleaned_normalized")
SHOPIFY = os.path.join(ROOT, "06_shopify")

BRANDING = os.path.join(ROOT, "08_branding")
FRONTEND_BUNDLE = os.path.join(BRANDS, "frontend", "frontend_bundle.json")

DIAG_DIR = os.path.join(PIPELINE, "diagnostics")
os.makedirs(DIAG_DIR, exist_ok=True)

REPORT_PATH = os.path.join(DIAG_DIR, "diagnostics_report.json")
PANEL_PATH = os.path.join(DIAG_DIR, "diagnostics_panel.html")


# ----------------------------------------------------------------------
# UTILIDADES
# ----------------------------------------------------------------------
def safe_exists(path):
    return os.path.exists(path)


def safe_json(path):
    if not os.path.exists(path):
        return None, "Archivo no encontrado"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f), None
    except Exception as e:
        return None, f"Error JSON: {str(e)}"


# ----------------------------------------------------------------------
# ANALIZADORES
# ----------------------------------------------------------------------
def analizar_branding():
    logos = os.path.join(BRANDING, "logos_optimized")
    palettes = os.path.join(BRANDING, "palettes")

    return {
        "logos_ok": safe_exists(logos),
        "palettes_ok": safe_exists(palettes),
        "logos_count": len(os.listdir(logos)) if safe_exists(logos) else 0,
        "palettes_count": len(os.listdir(palettes)) if safe_exists(palettes) else 0
    }


def analizar_narrativas():
    folder = os.path.join(BRANDS, "narratives")
    return {
        "exists": safe_exists(folder),
        "count": len(os.listdir(folder)) if safe_exists(folder) else 0
    }


def analizar_voices():
    folder = os.path.join(BRANDS, "voices")
    return {
        "exists": safe_exists(folder),
        "count": len(os.listdir(folder)) if safe_exists(folder) else 0
    }


def analizar_agents():
    folder = os.path.join(BRANDS, "..", "agents")
    folder = os.path.abspath(folder)
    return {
        "exists": safe_exists(folder),
        "count": len(os.listdir(folder)) if safe_exists(folder) else 0
    }


def analizar_academy():
    folder = os.path.join(BRANDS, "academy_packs")
    return {
        "exists": safe_exists(folder),
        "count": len(os.listdir(folder)) if safe_exists(folder) else 0
    }


def analizar_catalogo():
    file = os.path.join(NORMALIZED, "catalogo_unificado.csv")
    return {
        "exists": safe_exists(file),
        "path": file
    }


def analizar_shopify_export():
    file = os.path.join(SHOPIFY, "shopify_export.csv")
    return {
        "exists": safe_exists(file),
        "path": file
    }


def analizar_frontend_bundle():
    data, error = safe_json(FRONTEND_BUNDLE)
    return {
        "exists": safe_exists(FRONTEND_BUNDLE),
        "error": error,
        "brands_detected": list(data["brands"].keys()) if data and "brands" in data else []
    }


def analizar_pipeline_logs():
    log_path = os.path.join(PIPELINE, "logs", "pipeline_v28_log.json")
    data, error = safe_json(log_path)
    return {
        "exists": safe_exists(log_path),
        "error": error,
        "modules_count": len(data["modules"]) if data and "modules" in data else 0
    }


# ----------------------------------------------------------------------
# Construcción del panel HTML
# ----------------------------------------------------------------------
def generar_panel_html(report):

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def color(v):
        return "#00cc88" if v else "#ff4444"

    html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<title>SRM Diagnostics Panel v1</title>

<style>
body {{
    background:#f5f6fa;
    font-family:Arial;
    padding:20px;
}}

h1 {{
    text-align:center;
    color:#222;
}}

.section {{
    background:white;
    padding:20px;
    margin-bottom:25px;
    border-radius:10px;
    box-shadow:0 4px 10px rgba(0,0,0,0.08);
}}

.row {{
    display:flex;
    justify-content:space-between;
}}
.status {{
    font-weight:bold;
}}
</style>

</head>

<body>

<h1>SRM Diagnostics Panel v1</h1>
<p style="text-align:center;">Generado el {fecha}</p>

"""

    for section, data in report.items():
        html += f"<div class='section'><h2>{section.replace('_',' ').upper()}</h2>"
        for key, value in data.items():
            if isinstance(value, bool):
                html += f"<p><span class='status' style='color:{color(value)}'>{key}:</span> {value}</p>"
            else:
                html += f"<p><strong>{key}:</strong> {value}</p>"
        html += "</div>"

    html += """
</body>
</html>
"""

    return html


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------
def ejecutar_diagnostics():

    print("\n=====================================================")
    print("          SRM — DIAGNOSTICS ENGINE v1")
    print("=====================================================\n")

    report = {
        "branding": analizar_branding(),
        "narrativas": analizar_narrativas(),
        "voces": analizar_voices(),
        "agents": analizar_agents(),
        "academy": analizar_academy(),
        "catalogo": analizar_catalogo(),
        "shopify_export": analizar_shopify_export(),
        "frontend_bundle": analizar_frontend_bundle(),
        "pipeline_logs": analizar_pipeline_logs(),
    }

    # Guardar JSON
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)

    print(f"✔ Reporte generado: {REPORT_PATH}")

    # Panel HTML
    html = generar_panel_html(report)
    with open(PANEL_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✔ Panel generado: {PANEL_PATH}")
    print("\n=====================================================\n")


# ----------------------------------------------------------------------
# RUN
# ----------------------------------------------------------------------
if __name__ == "__main__":
    ejecutar_diagnostics()
