# ======================================================================
#   srm_runtime_supervisor_v1.py — SRM RUNTIME SUPERVISOR v1
# ======================================================================
#  Este módulo coordina y supervisa todos los engines del SRM Runtime:
#
#      - Health Monitor
#      - Diagnostics Engine
#      - Anomaly Detector
#      - Maintenance Engine
#      - Recovery Engine
#      - Self Optimizer
#      - Update Manager
#      - Runtime Controller
#
#  El Supervisor interpreta los reportes y toma decisiones:
#      ✔ Reparar si hay fallas
#      ✔ Optimizar si el sistema está pesado
#      ✔ Acelerar monitoreo si hay riesgos
#      ✔ Solicitar mantenimiento si hay señales de degradación
#      ✔ Ordenar recuperación si hay corrupción
#
#  Produce:
#      - supervisor_report.json
#      - supervisor_summary.md
#
# ======================================================================

import os
import json
from datetime import datetime

BASE = r"C:\SRM_ADSI\05_pipeline"
HEALTH = os.path.join(BASE, "health")
UPDATES = os.path.join(BASE, "updates")

OUT_JSON = os.path.join(HEALTH, "supervisor_report.json")
OUT_MD = os.path.join(HEALTH, "supervisor_summary.md")

FILES = {
    "health": os.path.join(HEALTH, "health_status.json"),
    "diagnostics": os.path.join(HEALTH, "diagnostics_report.json"),
    "anomaly": os.path.join(HEALTH, "anomaly_report.json"),
    "maintenance": os.path.join(HEALTH, "maintenance_report.json"),
    "recovery": os.path.join(BASE, "recovery", "recovery_report.json"),
    "optimizer": os.path.join(HEALTH, "self_optimizer_report.json"),
    "updates": os.path.join(UPDATES, "version_manifest.json"),
    "runtime_state": os.path.join(BASE, "runtime_state.json"),
}


# ----------------------------------------------------------------------
# UTILIDADES
# ----------------------------------------------------------------------
def load(path, default=None):
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
# SUPERVISOR CORE DECISION ENGINE
# ----------------------------------------------------------------------
def evaluate_supervision(
    health, diagnostics, anomalies, maintenance, recovery, optimizer, updates
):

    decisions = {
        "needs_recovery": False,
        "needs_maintenance": False,
        "needs_optimization": False,
        "needs_update": False,
        "increase_monitor_frequency": False,
        "decrease_monitor_frequency": False,
        "accelerate_runtime": False,
        "slow_runtime": False,
        "notes": [],
    }

    # -------------------------------------------
    # 1. HEALTH STATUS
    # -------------------------------------------
    if health and "system_status" in health:
        status = health["system_status"].lower()

        if status == "critical":
            decisions["needs_recovery"] = True
            decisions["increase_monitor_frequency"] = True
            decisions["accelerate_runtime"] = True
            decisions["notes"].append("Estado CRÍTICO detectado por Health Monitor.")

        elif status == "degraded":
            decisions["needs_maintenance"] = True
            decisions["increase_monitor_frequency"] = True
            decisions["notes"].append("Sistema degradado: requiere mantenimiento.")

    # -------------------------------------------
    # 2. DIAGNOSTICS ENGINE
    # -------------------------------------------
    if diagnostics:
        critical_errors = diagnostics.get("critical_errors", 0)
        warnings = diagnostics.get("warnings", 0)

        if critical_errors > 0:
            decisions["needs_recovery"] = True
            decisions["notes"].append(f"{critical_errors} errores críticos detectados.")

        if warnings > 10:
            decisions["needs_maintenance"] = True

    # -------------------------------------------
    # 3. ANOMALY ENGINE
    # -------------------------------------------
    if anomalies:
        anomaly_count = len(anomalies.get("all_anomalies", []))

        if anomaly_count > 10:
            decisions["increase_monitor_frequency"] = True
            decisions["accelerate_runtime"] = True
            decisions["needs_maintenance"] = True
            decisions["notes"].append("Muchísimas anomalías detectadas > 10.")

        elif anomaly_count > 3:
            decisions["increase_monitor_frequency"] = True

    # -------------------------------------------
    # 4. OPTIMIZER ENGINE
    # -------------------------------------------
    if optimizer:
        cpu = optimizer.get("cpu_usage", 0)
        mem = optimizer.get("memory_usage", 0)

        if cpu > 80 or mem > 80:
            decisions["needs_optimization"] = True
            decisions["slow_runtime"] = True
            decisions["notes"].append("Carga elevada → se requiere optimización.")

    # -------------------------------------------
    # 5. MAINTENANCE ENGINE
    # -------------------------------------------
    if maintenance:
        if maintenance.get("requires_action", False):
            decisions["needs_maintenance"] = True
            decisions["notes"].append("Maintenance Engine solicitó intervención.")

    # -------------------------------------------
    # 6. UPDATE MANAGER
    # -------------------------------------------
    if updates:
        needs_update = updates.get("update_available", False)
        if needs_update:
            decisions["needs_update"] = True
            decisions["notes"].append("Actualización pendiente detectada.")

    return decisions


# ----------------------------------------------------------------------
# MAIN SUPERVISOR EXECUTION
# ----------------------------------------------------------------------
def run_supervisor():

    print("\n=====================================================")
    print("            SRM — RUNTIME SUPERVISOR v1")
    print("=====================================================\n")

    # Cargar información
    health = load(FILES["health"], {})
    diagnostics = load(FILES["diagnostics"], {})
    anomalies = load(FILES["anomaly"], {})
    maintenance = load(FILES["maintenance"], {})
    recovery = load(FILES["recovery"], {})
    optimizer = load(FILES["optimizer"], {})
    updates = load(FILES["updates"], {})
    runtime_state = load(FILES["runtime_state"], {})

    # Evaluar decisiones
    decisions = evaluate_supervision(
        health, diagnostics, anomalies, maintenance, recovery, optimizer, updates
    )

    # Construir reporte
    report = {
        "timestamp": datetime.now().isoformat(),
        "health_status": health,
        "diagnostics": diagnostics,
        "anomalies": anomalies,
        "maintenance": maintenance,
        "last_recovery": recovery,
        "optimizer": optimizer,
        "updates": updates,
        "runtime_state": runtime_state,
        "decisions": decisions,
    }

    # Guardar JSON
    save_json(report, OUT_JSON)

    # Generar MD
    md = f"""
# 🧠 SRM Runtime Supervisor — Reporte v1
Generado: **{report['timestamp']}**

---

## 🔎 Decisiones del Supervisor
