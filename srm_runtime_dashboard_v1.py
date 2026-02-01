# ======================================================================
#  srm_runtime_dashboard_v1.py — SRM-QK-ADSI Runtime Dashboard Generator
# ======================================================================
#  Propósito:
#     - Generar un dashboard HTML profesional que muestre
#       el estado en tiempo real del SRM Runtime Engine.
#     - Integrar logs, diagnósticos, estado del monitor,
#       actualizaciones, eventos y estado general del sistema.
#
#  Salida:
#     C:\SRM_ADSI\05_pipeline\runtime_dashboard\index.html
#
# ======================================================================

import os
import json
from datetime import datetime

BASE = r"C:\SRM_ADSI\05_pipeline"
DASHBOARD_DIR = os.path.join(BASE, "runtime_dashboard")
os.makedirs(DASHBOARD_DIR, exist_ok=True)

OUTPUT_HTML = os.path.join(DASHBOARD_DIR, "index.html")

FILES = {
    "state": os.path.join(BASE, "runtime_state.json"),
    "log": os.path.join(BASE, "runtime_log.json"),
    "health": os.path.join(BASE, "health", "health_status.json"),
    "events": os.path.join(BASE, "health", "events_log.json"),
    "versions": os.path.join(BASE, "updates", "version_manifest.json"),
}


# ----------------------------------------------------------------------
# UTILIDADES
# ----------------------------------------------------------------------
def load_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"error": "invalid_json"}


def prettify(obj):
    return json.dumps(obj, indent=4, ensure_ascii=False)


# ----------------------------------------------------------------------
# GENERADOR HTML
# ----------------------------------------------------------------------
def generate_dashboard():

    state = load_json(FILES["state"])
    log = load_json(FILES["log"])
    health = load_json(FILES["health"])
    events = load_json(FILES["events"])
    versions = load_json(FILES["versions"])

    last_events = events[-10:] if isinstance(events, list) else []

    html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>SRM Runtime Dashboard v1</title>
<style>

body {{
    font-family: Arial, sans-serif;
    background: #0e1117;
    color: #e2e2e2;
    margin: 0;
    padding: 0;
}}

header {{
    background: #1f2430;
    padding: 20px;
    text-align: center;
    border-bottom: 3px solid #4fa3ff;
}}

h1 {{
    margin: 0;
    font-size: 26px;
}}

.section {{
    margin: 20px;
    padding: 20px;
    background: #1a1f27;
    border-radius: 10px;
    border: 1px solid #333;
}}

.section h2 {{
    margin-top: 0;
    color: #4fa3ff;
}}

.box {{
    background: #202631;
    padding: 10px;
    border-radius: 8px;
    margin-bottom: 15px;
    border: 1px solid #333;
    white-space: pre-wrap;
}}

.status-ok {{ color: #5bff7b; font-weight: bold; }}
.status-warning {{ color: #ffdd57; font-weight: bold; }}
.status-error {{ color: #ff5c5c; font-weight: bold; }}

.btn {{
    display: inline-block;
    padding: 10px 15px;
    background: #4fa3ff;
    color: #000;
    border-radius: 6px;
    margin-right: 10px;
    text-decoration: none;
    font-weight: bold;
}}

.btn:hover {{
    background: #70b5ff;
}}

</style>
</head>
<body>

<header>
    <h1>SRM Runtime Dashboard v1</h1>
    <p>Última actualización: {datetime.now().isoformat()}</p>
</header>

<div class="section">
    <h2>Estado general del Runtime</h2>
    <div class="box">{prettify(state)}</div>
</div>

<div class="section">
    <h2>Estado de Salud del Sistema</h2>
    <div class="box">{prettify(health)}</div>
</div>

<div class="section">
    <h2>Últimos Eventos (Health Monitor)</h2>
    <div class="box">{prettify(last_events)}</div>
</div>

<div class="section">
    <h2>Historial de Runtime / Logs</h2>
    <div class="box">{prettify(log[-20:] if isinstance(log, list) else log)}</div>
</div>

<div class="section">
    <h2>Versiones / Actualizaciones</h2>
    <div class="box">{prettify(versions)}</div>
</div>

<div class="section">
    <h2>Acciones rápidas</h2>

    <a class="btn" href="../run_diagnostics.bat">Ejecutar Diagnóstico</a>
    <a class="btn" href="../run_updates.bat">Buscar Updates</a>
    <a class="btn" href="../run_frontend_sync.bat">Sync Frontend</a>
    <a class="btn" href="../run_integrator.bat">Ejecutar Integrador</a>
    <a class="btn" href="../restart_runtime.bat" style="background:#ff5c5c;color:#fff;">
        Reiniciar Runtime
    </a>

</div>

</body>
</html>
"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    print("\n===============================================")
    print(" ✔ SRM Runtime Dashboard generado correctamente")
    print(" ✔ Archivo:", OUTPUT_HTML)
    print("===============================================\n")


# ----------------------------------------------------------------------
# RUN
# ----------------------------------------------------------------------
if __name__ == "__main__":
    generate_dashboard()
