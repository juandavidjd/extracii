# ======================================================================
#   srm_context_memory_engine_v1.py — SRM CONTEXT MEMORY ENGINE v1
# ======================================================================
#  Este módulo administra la memoria persistente del SRM Runtime en tres
#  niveles:
#
#   ✔ Short-Term Memory  (memoria operativa reciente)
#   ✔ Mid-Term Memory    (memoria contextual de tendencias)
#   ✔ Long-Term Memory   (memoria histórica compactada)
#
#  Produce:
#      - memory_short.json
#      - memory_context.json
#      - memory_long.json
#
#  Nota:
#    v1 utiliza métodos heurísticos robustos y simples.
#    v2 integrará ML liviano basado en patrones.
#
# ======================================================================

import os
import json
from datetime import datetime

BASE = r"C:\SRM_ADSI\05_pipeline"
HEALTH = os.path.join(BASE, "health")
REC = os.path.join(BASE, "recovery")
OUT_DIR = os.path.join(HEALTH, "memory")

os.makedirs(OUT_DIR, exist_ok=True)

FILES = {
    "short": os.path.join(OUT_DIR, "memory_short.json"),
    "context": os.path.join(OUT_DIR, "memory_context.json"),
    "long": os.path.join(OUT_DIR, "memory_long.json"),

    "runtime_state": os.path.join(BASE, "runtime_state.json"),
    "supervisor": os.path.join(HEALTH, "supervisor_report.json"),
    "autopilot": os.path.join(HEALTH, "autopilot_log.json"),
    "optimizer": os.path.join(HEALTH, "self_optimizer_report.json"),
    "anomalies": os.path.join(HEALTH, "anomaly_report.json"),
    "predictor": os.path.join(HEALTH, "ai_predictor_report.json"),
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


def save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def compact_list(values, max_size=200):
    """Evita crecimiento infinito de la memoria."""
    if not isinstance(values, list):
        return []
    if len(values) <= max_size:
        return values
    return values[-max_size:]


def increment_counter(obj, key):
    obj[key] = obj.get(key, 0) + 1


# ----------------------------------------------------------------------
# MEMORY ENGINE CORE
# ----------------------------------------------------------------------
def run_memory_engine():

    print("\n=====================================================")
    print("         SRM — CONTEXT MEMORY ENGINE v1")
    print("=====================================================\n")

    # ======================================================
    # 1) SHORT-TERM MEMORY
    # ======================================================
    memory_short = load(FILES["short"], {})

    runtime_state = load(FILES["runtime_state"], {})
    supervisor = load(FILES["supervisor"], {})
    autopilot = load(FILES["autopilot"], {})
    optimizer = load(FILES["optimizer"], {})

    memory_short.update({
        "last_updated": datetime.now().isoformat(),
        "last_runtime_state": runtime_state,
        "last_supervisor_decisions": supervisor.get("decisions", {}),
        "last_autopilot_actions": autopilot.get("actions_log", []),
        "last_optimizer_state": {
            "cpu": optimizer.get("cpu_usage", None),
            "ram": optimizer.get("memory_usage", None),
            "recomendations": optimizer.get("notes", []),
        }
    })

    save(FILES["short"], memory_short)

    print("✔ Memoria SHORT-TERM actualizada.")

    # ======================================================
    # 2) CONTEXT MEMORY (MID-TERM)
    # ======================================================
    memory_context = load(FILES["context"], {
        "error_trend": [],
        "anomaly_trend": [],
        "cpu_usage": [],
        "ram_usage": [],
        "predictive_risks": [],
    })

    anomalies = load(FILES["anomalies"], {}).get("all_anomalies", [])
    predictor = load(FILES["predictor"], {}).get("prediction", {})

    # Guardar tendencias
    memory_context["error_trend"] = compact_list(
        memory_context.get("error_trend", []) +
        [supervisor.get("diagnostics", {}).get("critical_errors", 0)]
    )

    memory_context["anomaly_trend"] = compact_list(
        memory_context.get("anomaly_trend", []) +
        [len(anomalies)]
    )

    memory_context["cpu_usage"] = compact_list(
        memory_context.get("cpu_usage", []) +
        [optimizer.get("cpu_usage", 0)]
    )

    memory_context["ram_usage"] = compact_list(
        memory_context.get("ram_usage", []) +
        [optimizer.get("memory_usage", 0)]
    )

    memory_context["predictive_risks"] = compact_list(
        memory_context.get("predictive_risks", []) +
        [predictor.get("risk_failure", 0)]
    )

    save(FILES["context"], memory_context)

    print("✔ Memoria CONTEXT actualizada.")

    # ======================================================
    # 3) LONG-TERM MEMORY (HISTÓRICA)
    # ======================================================
    memory_long = load(FILES["long"], {
        "module_failures": {},
        "module_repairs": {},
        "common_anomalies": {},
        "pattern_stats": {},
    })

    # ----- registrar patrones repetitivos -----
    for anomaly in anomalies:
        mod = anomaly.get("module", "unknown")
        increment_counter(memory_long["common_anomalies"], mod)

    # ----- registrar decisiones frecuentes -----
    decisions = supervisor.get("decisions", {})
    for key, value in decisions.items():
        if value is True:
            increment_counter(memory_long["pattern_stats"], key)

    # ----- registrar acciones del autopilot -----
    for action in autopilot.get("actions_log", []):
        if "Recovery Engine" in action:
            increment_counter(memory_long["module_repairs"], "recovery")
        if "Maintenance Engine" in action:
            increment_counter(memory_long["module_repairs"], "maintenance")

    save(FILES["long"], memory_long)

    print("✔ Memoria LONG-TERM actualizada.")
    print("\n=====================================================")
    print("✔ CONTEXT MEMORY ENGINE COMPLETADO")
    print("=====================================================\n")


if __name__ == "__main__":
    run_memory_engine()
