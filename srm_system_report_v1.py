# ======================================================================
# srm_system_report_v1.py — SRM MASTER SYSTEM REPORT v1
# ======================================================================
# Objetivo:
#   - Consolidar en un único reporte:
#       * Estado del Runtime
#       * Estado del Health Monitor
#       * Estado de Logs
#       * Estado de Versiones
#       * Anomalías detectadas
#   - Calcular métricas de salud y riesgo
#   - Generar reporte JSON + Markdown
#
# Salidas:
#   /health/system_report.json
#   /health/SRM_STATUS.md
# ======================================================================

import os
import json
from datetime import datetime

BASE = r"C:\SRM_ADSI\05_pipeline"
HEALTH_DIR = os.path.join(BASE, "health")
UPDATES_DIR = os.path.join(BASE, "updates")

os.makedirs(HEALTH_DIR, exist_ok=True)

FILES = {
    "runtime_state": os.path.join(BASE, "runtime_state.json"),
    "runtime_log": os.path.join(BASE, "runtime_log.json"),
    "health_status": os.path.join(HEALTH_DIR, "health_status.json"),
    "events": os.path.join(HEALTH_DIR, "events_log.json"),
    "anomalies": os.path.join(HEALTH_DIR, "anomaly_report.json"),
    "versions": os.path.join(UPDATES_DIR, "version_manifest.json"),
}

OUT_JSON = os.path.join(HEALTH_DIR, "system_report.json")
OUT_MD = os.path.join(HEALTH_DIR, "SRM_STATUS.md")


# ----------------------------------------------------------------------
# UTILIDADES
# ----------------------------------------------------------------------
def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default


def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def save_md(text, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# ----------------------------------------------------------------------
# MÉTRICAS DE SALUD Y RIESGO
# ----------------------------------------------------------------------
def calculate_health_score(report):
    """
    Calcula un score global de salud SRM basado en:
        - errores en logs
        - warnings
        - anomalías
        - carpetas faltantes
        - versión estable
    """

    score = 100

    anomalies = report.get("anomalies", [])
    logs = report.get("runtime_logs", {})
    health = report.get("health_status", {})

    # Penalizar errores de runtime
    err = logs.get("errors", 0)
    score -= err * 3

    # Penalizar warnings
    warn = logs.get("warnings", 0)
    score -= warn * 1

    # Penalizar anomalías
    score -= len(anomalies) * 5

    # Penalizar carpetas rotas
    for name, info in health.get("folders", {}).items():
        if not info.get("exists"):
            score -= 15
        elif info.get("files", 1) == 0:
            score -= 8

    # Rango mínimo
    if score < 0:
        score = 0

    return score


# ----------------------------------------------------------------------
# GENERAR REPORTE MAESTRO
# ----------------------------------------------------------------------
def generate_report():

    print("\n=====================================================")
    print("          SRM — MASTER SYSTEM REPORT v1")
    print("=====================================================\n")

    runtime_state = load_json(FILES["runtime_state"], {})
    runtime_log = load_json(FILES["runtime_log"], [])
    health_status = load_json(FILES["health_status"], {})
    events = load_json(FILES["events"], [])
    anomalies = load_json(FILES["anomalies"], {})
    versions = load_json(FILES["versions"], {})

    # Estructurar datos
    report = {
        "generated_at": datetime.now().isoformat(),
        "runtime_state": runtime_state,
        "runtime_logs": {
            "entries": runtime_log[-50:] if isinstance(runtime_log, list) else [],
            "errors": sum("error" in e.get("message", "").lower() for e in runtime_log[-50:]),
            "warnings": sum(
                ("warning" in e.get("message", "").lower() or "advertencia" in e.get("message", "").lower())
                for e in runtime_log[-50:]
            )
        },
        "health_status": health_status,
        "recent_events": events[-20:] if isinstance(events, list) else [],
        "anomalies": anomalies.get("all_anomalies", []),
        "version_info": versions,
    }

    # Score de salud
    report["system_health_score"] = calculate_health_score(report)

    # Guardar JSON
    save_json(report, OUT_JSON)

    print("✔ Reporte JSON generado:", OUT_JSON)

    # ------------------------------------------------------------------
    # Generar Markdown
    # ------------------------------------------------------------------
    md = f"""
# 📊 SRM STATUS — System Report v1
Generado: **{report['generated_at']}**

---

## 🧠 Estado General del Runtime
