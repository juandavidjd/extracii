# ======================================================================
# srm_ui_generator_v1.py — SRM-QK-ADSI USER INTERFACE PANEL v1
# ======================================================================
# Autor: SRM Engine
#
# Propósito:
#   - Construir un panel HTML para visualizar el estado del ecosistema SRM.
#   - Mostrar módulos, logs, marcas, agentes, academia y pipeline.
#   - Base para futura SRM Desktop App / Control Panel.
#
# Salida:
#   C:\SRM_ADSI\05_pipeline\ui\srm_panel.html
# ======================================================================

import os
import json
from datetime import datetime

# ----------------------------------------------------------------------
# RUTAS
# ----------------------------------------------------------------------
ROOT_BRANDS = r"C:\SRM_ADSI\03_knowledge_base\brands"
FRONTEND_BUNDLE = os.path.join(ROOT_BRANDS, "frontend", "frontend_bundle.json")

PIPELINE_LOG = r"C:\SRM_ADSI\05_pipeline\logs\pipeline_v28_log.json"

UI_DIR = r"C:\SRM_ADSI\05_pipeline\ui"
os.makedirs(UI_DIR, exist_ok=True)

OUTPUT_HTML = os.path.join(UI_DIR, "srm_panel.html")


# ----------------------------------------------------------------------
# UTILIDADES
# ----------------------------------------------------------------------
def load_json(path, allow_empty=True):
    if not os.path.exists(path):
        if allow_empty:
            return {}
        else:
            raise FileNotFoundError(path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ----------------------------------------------------------------------
# Construcción del Panel
# ----------------------------------------------------------------------
def generar_html(bundle, log):

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ===============================================================
    # SECCIÓN MARCAS
    # ===============================================================
    marcas_html = ""
    for brand, info in bundle.get("brands", {}).items():

        logo = info.get("logo", "")
        palette = info.get("palette", {}).get("colors", {})

        primary = palette.get("primary", "#0046FF")
        accent = palette.get("accent", "#FFC300")

        marcas_html += f"""
        <div class="brand-card" style="border-left: 5px solid {primary};">
            <img src="{logo}" class="brand-logo"/>
            <h3>{brand}</h3>
            <p><strong>Tagline:</strong> {info.get("lovable", {}).get("metadata", {}).get("tagline", "")}</p>
            <div class="color-pill" style="background:{primary};"></div>
            <div class="color-pill" style="background:{accent};"></div>
        </div>
        """

    # ===============================================================
    # SECCIÓN LOG DEL PIPELINE
    # ===============================================================
    modules_html = ""
    for entry in log.get("modules", []):
        color = "#00cc88" if entry["status"] == "OK" else "#ff4444"
        modules_html += f"""
        <tr>
            <td>{entry['module']}</td>
            <td style="color:{color};font-weight:bold;">{entry['status']}</td>
        </tr>
        """

    # ===============================================================
    # GENERAMOS HTML FINAL
    # ===============================================================
    html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<title>SRM Control Panel v1</title>

<style>

body {{
    background: #f2f4f8;
    font-family: Arial, sans-serif;
    padding: 20px;
}}

h1 {{
    color: #222;
    text-align:center;
}}

.section {{
    background:white;
    padding:20px;
    margin-bottom:30px;
    border-radius:10px;
    box-shadow:0 4px 10px rgba(0,0,0,0.08);
}}

.section h2 {{
    margin-top:0;
    color:#333;
}}

.brand-container {{
    display:flex;
    flex-wrap:wrap;
    gap:20px;
}}

.brand-card {{
    width:220px;
    background:#fff;
    padding:15px;
    border-radius:10px;
    box-shadow:0 3px 8px rgba(0,0,0,0.1);
    text-align:center;
}}

.brand-logo {{
    width:100%;
    max-height:90px;
    object-fit:contain;
    margin-bottom:10px;
}}

.color-pill {{
    width:25px;
    height:12px;
    border-radius:4px;
    display:inline-block;
    margin:3px;
}}

table {{
    width:100%;
    border-collapse:collapse;
}}

td, th {{
    padding:10px;
    border-bottom:1px solid #ddd;
}}

.status-ok {{ color:#00cc88; }}
.status-error {{ color:#ff4444; }}

.footer {{
    text-align:center;
    margin-top:40px;
    color:#777;
    font-size:12px;
}}

</style>

</head>

<body>

<h1>SRM Control Panel PRO — v1</h1>
<p style="text-align:center;">Generado el {fecha}</p>


<div class="section">
    <h2>Marcas conectadas al SRM Frontend Bundle</h2>
    <div class="brand-container">
        {marcas_html}
    </div>
</div>


<div class="section">
    <h2>Estado del Pipeline v28</h2>
    <table>
        <tr><th>Módulo</th><th>Estado</th></tr>
        {modules_html}
    </table>
</div>


<div class="footer">
    SRM-QK-ADSI | Ecosistema Técnico Comercial para Repuestos de Motocicletas | 2025
</div>

</body>
</html>
"""

    return html


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------
def generar_ui():

    print("\n=====================================================")
    print("          SRM — UI GENERATOR v1")
    print("=====================================================\n")

    bundle = load_json(FRONTEND_BUNDLE)
    log    = load_json(PIPELINE_LOG)

    html = generar_html(bundle, log)

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    print("✔ UI generada correctamente")
    print(f"✔ Archivo: {OUTPUT_HTML}")
    print("\n=====================================================")


# ----------------------------------------------------------------------
# RUN
# ----------------------------------------------------------------------
if __name__ == "__main__":
    generar_ui()
