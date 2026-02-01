# ======================================================================
#         srm_runtime_launcher_v1.py — SRM RUNTIME LAUNCHER v1
# ======================================================================
#
#  Este módulo es el ORQUESTADOR PRINCIPAL del SRM Runtime v30.
#  Ejecuta todos los engines en orden correcto:
#
#   1. Health Monitor
#   2. Diagnostics Engine
#   3. Anomaly Detector
#   4. Maintenance Engine
#   5. Recovery Engine (solo si aplica)
#   6. Self Optimizer
#   7. Supervisor
#   8. Autopilot
#   9. AI Predictor
#  10. Context Memory Engine
#
#  Produce:
#     - runtime_cycle_report.json
#     - runtime_cycle_summary.md
#
# ======================================================================

import os
import json
from datetime import datetime
import time

BASE = r"C:\SRM_ADSI\05_pipeline"
HEALTH = os.path.join(BASE, "health")

OUT_JSON = os.path.join(HEALTH, "runtime_cycle_report.json")
OUT_MD = os.path.join(HEALTH, "runtime_cycle_summary.md")

ENGINES = {
    "health_monitor": os.path.join(BASE, "srm_health_monitor_v1.py"),
    "diagnostics": os.path.join(BASE, "srm_diagnostics_v1.py"),
    "anomaly_detector": os.path.join(BASE, "srm_anomaly_detector_v1.py"),
    "maintenance": os.path.join(BASE, "srm_maintenance_engine_v1.py"),
    "recovery": os.path.join(BASE, "srm_recovery_engine_v1.py"),
    "optimizer": os.path.join(BASE, "srm_self_optimizer_v1.py"),
    "supervisor": os.path.join(BASE, "srm_runtime_supervisor_v1.py"),
    "autopilot": os.path.join(BASE, "srm_runtime_autopilot_v1.py"),
    "predictor": os.path.join(BASE, "srm_runtime_ai_predictor_v1.py"),
    "memory": os.path.join(BASE, "srm_context_memory_engine_v1.py"),
}

SUPERVISOR_REPORT = os.path.join(HEALTH, "supervisor_report.json")


# ----------------------------------------------------------------------
# UTILIDADES
# ----------------------------------------------------------------------
def run_engine(label, path, logs):
    start = time.time()
    logs.append(f"→ Ejecutando {label}...")
    try:
        os.system(f'python "{path}"')
        logs.append(f"✔ {label} completado en {round(time.time() - start, 2)}s")
        return True
    except Exception as e:
        logs.append(f"❌ Error ejecutando {label}: {str(e)}")
        return False


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def save_md(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# ----------------------------------------------------------------------
# RUNTIME LAUNCHER CORE
# ----------------------------------------------------------------------
def run_runtime_cycle():

    print("\n=====================================================")
    print("            SRM — RUNTIME LAUNCHER v1")
    print("=====================================================\n")

    cycle_start = datetime.now().isoformat()
    logs = [f"SRM Runtime Cycle iniciado: {cycle_start}"]

    # 1. Health Monitor
    run_engine("Health Monitor", ENGINES["health_monitor"], logs)

    # 2. Diagnostics
    run_engine("Diagnostics Engine", ENGINES["diagnostics"], logs)

    # 3. Anomaly Detector
    run_engine("Anomaly Detector", ENGINES["anomaly_detector"], logs)

    # 4. Maintenance Engine
    run_engine("Maintenance Engine", ENGINES["maintenance"], logs)

    # 5. Optimizer
    run_engine("Self Optimizer", ENGINES["optimizer"], logs)

    # 6. Supervisor
    run_engine("Runtime Supervisor", ENGINES["supervisor"], logs)

    # Cargar decisiones del Supervisor para saber si Recovery se necesita
    supervisor = load_json(SUPERVISOR_REPORT, {})
    needs_recovery = supervisor.get("decisions", {}).get("needs_recovery", False)

    # 7. Recovery Engine (si aplica)
    if needs_recovery:
        logs.append("⚠ Supervisor solicita RECOVERY ENGINE.")
        run_engine("Recovery Engine", ENGINES["recovery"], logs)
    else:
        logs.append("✔ No se requiere Recovery Engine.")

    # 8. Autopilot
    run_engine("Autopilot", ENGINES["autopilot"], logs)

    # 9. AI Predictor
    run_engine("AI Predictor", ENGINES["predictor"], logs)

    # 10. Context Memory Engine
    run_engine("Context Memory Engine", ENGINES["memory"], logs)

    cycle_end = datetime.now().isoformat()

    logs.append(f"SRM Runtime Cycle finalizado: {cycle_end}")

    # Construir reporte
    report = {
        "cycle_start": cycle_start,
        "cycle_end": cycle_end,
        "logs": logs,
        "supervisor_decisions": supervisor.get("decisions", {}),
    }

    save_json(OUT_JSON, report)

    # Markdown
    md = f"""
# ⚙️ SRM Runtime — Cycle Report v1

### Inicio del ciclo:
**{cycle_start}**

### Fin del ciclo:
**{cycle_end}**

---

## 📜 Logs del ciclo
