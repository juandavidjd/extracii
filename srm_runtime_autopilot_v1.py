# ======================================================================
#   srm_runtime_autopilot_v1.py — SRM AUTOPILOT ENGINE v1
# ======================================================================
#  El Autopilot ejecuta ACCIONES basadas en las decisiones del Supervisor:
#
#   ✔ Reparación automática (Recovery Engine)
#   ✔ Mantenimiento automático (Maintenance Engine)
#   ✔ Optimización activa (Self Optimizer → Runtime Controller)
#   ✔ Aceleración / reducción del Health Monitor
#   ✔ Aplicación de actualizaciones
#   ✔ Modo SAFE STATE ante fallas graves
#
#  Produce:
#     - autopilot_log.json
#     - autopilot_summary.md
#
# ======================================================================

import os
import json
from datetime import datetime

BASE = r"C:\SRM_ADSI\05_pipeline"
HEALTH = os.path.join(BASE, "health")
REC = os.path.join(BASE, "recovery")

OUT_JSON = os.path.join(HEALTH, "autopilot_log.json")
OUT_MD = os.path.join(HEALTH, "autopilot_summary.md")

SUPERVISOR = os.path.join(HEALTH, "supervisor_report.json")

# Engines ejecutables
ENGINES = {
    "recovery": os.path.join(BASE, "srm_recovery_engine_v1.py"),
    "maintenance": os.path.join(BASE, "srm_maintenance_engine_v1.py"),
    "optimizer": os.path.join(BASE, "srm_self_optimizer_v1.py"),
    "updates": os.path.join(BASE, "srm_update_manager_v1.py"),
    "diagnostics": os.path.join(BASE, "srm_diagnostics_v1.py"),
}

RUNTIME_STATE = os.path.join(BASE, "runtime_state.json")


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


def run_engine(path):
    """Ejecuta un engine SRM de forma segura."""
    try:
        os.system(f'python "{path}"')
        return True
    except:
        return False


def update_runtime_state(changes):
    state = load(RUNTIME_STATE, {})
    state.update(changes)
    save_json(state, RUNTIME_STATE)


# ----------------------------------------------------------------------
# AUTO-PILOT CORE LOGIC
# ----------------------------------------------------------------------
def execute_autopilot_actions(decisions):

    logs = []
    def log(msg):
        logs.append(f"[{datetime.now().isoformat()}] {msg}")
        print(msg)

    # ============================================================
    # 1. SAFE MODE — ESTADO CRÍTICO
    # ============================================================
    if decisions.get("needs_recovery"):
        log("⚠ Estado crítico — Ejecutando Recovery Engine completo...")
        run_engine(ENGINES["recovery"])
        update_runtime_state({"safe_mode": True})
        log("✔ SAFE MODE activado.")
    
    # ============================================================
    # 2. MAINTENANCE ENGINE
    # ============================================================
    if decisions.get("needs_maintenance"):
        log("🛠 Requiere mantenimiento — Ejecutando Maintenance Engine...")
        run_engine(ENGINES["maintenance"])

    # ============================================================
    # 3. OPTIMIZACIÓN ACTIVA
    # ============================================================
    if decisions.get("needs_optimization"):
        log("⚙ Optimizando sistema — Ejecutando Self Optimizer...")
        run_engine(ENGINES["optimizer"])

    # ============================================================
    # 4. AJUSTES DEL HEALTH MONITOR
    # ============================================================
    if decisions.get("increase_monitor_frequency"):
        update_runtime_state({"health_monitor_interval": 2})
        log("📡 Aumentada frecuencia del Health Monitor → 2s")

    if decisions.get("decrease_monitor_frequency"):
        update_runtime_state({"health_monitor_interval": 15})
        log("📡 Reducida frecuencia del Health Monitor → 15s")

    # ============================================================
    # 5. AJUSTES DEL RUNTIME CONTROLLER
    # ============================================================
    if decisions.get("accelerate_runtime"):
        update_runtime_state({"runtime_cycle": 45})
        log("⏩ Runtime acelerado → ciclo 45s")

    if decisions.get("slow_runtime"):
        update_runtime_state({"runtime_cycle": 180})
        log("⏪ Runtime ralentizado → ciclo 180s")

    # ============================================================
    # 6. ACTUALIZACIONES AUTOMÁTICAS
    # ============================================================
    if decisions.get("needs_update"):
        log("⬆ Actualización disponible — Ejecutando Update Manager...")
        run_engine(ENGINES["updates"])
        log("✔ Actualización aplicada.")

    # ============================================================
    # 7. LOG FINAL
    # ============================================================
    return logs


# ----------------------------------------------------------------------
# MAIN AUTOPILOT EXECUTION
# ----------------------------------------------------------------------
def run_autopilot():

    print("\n=====================================================")
    print("               SRM — AUTOPILOT ENGINE v1")
    print("=====================================================\n")

    supervisor = load(SUPERVISOR, {})
    decisions = supervisor.get("decisions", {})

    if not decisions:
        print("❌ No hay decisiones del Supervisor — No se ejecuta Autopilot.")
        return

    logs = execute_autopilot_actions(decisions)

    autopilot_report = {
        "timestamp": datetime.now().isoformat(),
        "decisions": decisions,
        "actions_log": logs,
    }

    save_json(autopilot_report, OUT_JSON)

    md = f"""
# 🤖 SRM Autopilot — Resumen de acciones v1

Generado: **{autopilot_report['timestamp']}**

---

## 🧠 Decisiones ejecutadas
