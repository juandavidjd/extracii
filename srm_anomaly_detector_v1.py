# ======================================================================
#   srm_anomaly_detector_v1.py — SRM Predictive Anomaly Engine v1
# ======================================================================
#  Detecta patrones sospechosos en:
#     - Health Monitor events
#     - Runtime logs
#     - File structure
#     - Update patterns
#
#  Genera:
#     anomaly_report.json
#
#  Método:
#     - Reglas basadas en patrones (Rule-based)
#     - Estadísticas básicas
#     - Detección de frecuencia
#     - Conteo de eventos y anomalías estructurales
# ======================================================================

import os
import json
from datetime import datetime, timedelta

BASE = r"C:\SRM_ADSI\05_pipeline"
HEALTH_DIR = os.path.join(BASE, "health")
UPDATES_DIR = os.path.join(BASE, "updates")

FILES = {
    "events": os.path.join(HEALTH_DIR, "events_log.json"),
    "runtime_log": os.path.join(BASE, "runtime_log.json"),
    "health_status": os.path.join(HEALTH_DIR, "health_status.json"),
    "version_manifest": os.path.join(UPDATES_DIR, "version_manifest.json"),
}

OUTPUT = os.path.join(HEALTH_DIR, "anomaly_report.json")


# ----------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------
def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default


def save_report(report):
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)


def parse_timestamp(ts):
    try:
        return datetime.fromisoformat(ts)
    except:
        return None


# ----------------------------------------------------------------------
# ANÁLISIS DE EVENTOS
# ----------------------------------------------------------------------
def analyze_events(events):
    anomalies = []
    summary = {
        "total_events": len(events),
        "created": 0,
        "deleted": 0,
        "modified": 0,
        "by_folder": {}
    }

    timestamps = []

    for ev in events:
        event_type = ev.get("type", "")
        folder = ev.get("folder", "unknown")

        summary[event_type.lower()] += 1

        summary["by_folder"].setdefault(folder, 0)
        summary["by_folder"][folder] += 1

        ts = parse_timestamp(ev.get("timestamp", ""))
        if ts:
            timestamps.append(ts)

    # 1. Detectar demasiados eventos en corto tiempo
    if len(timestamps) >= 10:
        timestamps_sorted = sorted(timestamps)
        window_start = timestamps_sorted[-10]
        window_end = timestamps_sorted[-1]
        delta = (window_end - window_start).total_seconds()

        if delta < 20:
            anomalies.append({
                "type": "EVENT_SPIKE",
                "message": "Más de 10 eventos en menos de 20 segundos."
            })

    # 2. Cambios frecuentes en mismo archivo
    path_counter = {}
    for ev in events:
        p = ev.get("path")
        if p:
            path_counter[p] = path_counter.get(p, 0) + 1

    for path, count in path_counter.items():
        if count >= 15:
            anomalies.append({
                "type": "REPEATED_FILE_CHANGE",
                "message": f"El archivo {path} ha cambiado {count} veces.",
                "path": path
            })

    return summary, anomalies


# ----------------------------------------------------------------------
# ANALISIS DE LOGS
# ----------------------------------------------------------------------
def analyze_runtime_logs(logs):
    anomalies = []
    error_count = 0
    warning_count = 0

    for entry in logs[-50:]:  # analizar últimos 50 eventos
        msg = entry.get("message", "").lower()
        if "error" in msg:
            error_count += 1
        if "warning" in msg or "advertencia" in msg:
            warning_count += 1

    if error_count >= 10:
        anomalies.append({
            "type": "RUNTIME_ERRORS_SPIKE",
            "message": f"Más de 10 errores en los últimos 50 logs."
        })

    if warning_count >= 20:
        anomalies.append({
            "type": "RUNTIME_WARNINGS_SPIKE",
            "message": f"Más de 20 advertencias en los últimos 50 logs."
        })

    return error_count, warning_count, anomalies


# ----------------------------------------------------------------------
# ANALISIS DE ESTRUCTURA
# ----------------------------------------------------------------------
def analyze_structure(health_status):
    anomalies = []

    folders = health_status.get("folders", {})
    for name, info in folders.items():
        if info.get("exists") and info.get("files") == 0:
            anomalies.append({
                "type": "EMPTY_FOLDER",
                "message": f"La carpeta {name} existe pero está vacía."
            })

        if not info.get("exists"):
            anomalies.append({
                "type": "MISSING_FOLDER",
                "message": f"La carpeta {name} no existe."
            })

    return anomalies


# ----------------------------------------------------------------------
# ANALISIS DE VERSIONES
# ----------------------------------------------------------------------
def analyze_versions(manifest):
    anomalies = []

    history = manifest.get("history", [])
    if len(history) >= 5:
        last = history[-1]
        ts = parse_timestamp(last.get("timestamp", ""))

        if ts:
            if datetime.now() - ts < timedelta(minutes=2):
                anomalies.append({
                    "type": "FREQUENT_UPDATES",
                    "message": "Se detectaron actualizaciones demasiado frecuentes (posible loop)."
                })

    return anomalies


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------
def run_anomaly_detector():

    print("\n=====================================================")
    print("         SRM — ANOMALY DETECTOR v1")
    print("=====================================================\n")

    events = load_json(FILES["events"], [])
    logs = load_json(FILES["runtime_log"], [])
    health = load_json(FILES["health_status"], {})
    versions = load_json(FILES["version_manifest"], {})

    report = {
        "timestamp": datetime.now().isoformat(),
        "events_summary": {},
        "event_anomalies": [],
        "runtime_errors": 0,
        "runtime_warnings": 0,
        "runtime_anomalies": [],
        "health_anomalies": [],
        "version_anomalies": [],
        "all_anomalies": []
    }

    # Eventos
    event_summary, event_anomalies = analyze_events(events)
    report["events_summary"] = event_summary
    report["event_anomalies"] = event_anomalies

    # Logs
    err, warn, runtime_an = analyze_runtime_logs(logs)
    report["runtime_errors"] = err
    report["runtime_warnings"] = warn
    report["runtime_anomalies"] = runtime_an

    # Estructura
    health_an = analyze_structure(health)
    report["health_anomalies"] = health_an

    # Versiones
    version_an = analyze_versions(versions)
    report["version_anomalies"] = version_an

    # Unificar anomalías
    report["all_anomalies"] = (
        event_anomalies + runtime_an + health_an + version_an
    )

    save_report(report)

    print("✔ Análisis completado.")
    print("✔ Reporte generado en:", OUTPUT)
    print("\n=====================================================\n")


if __name__ == "__main__":
    run_anomaly_detector()
