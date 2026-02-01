# ======================================================================
#  SRM Runtime Controller v1
#  El cerebro maestro del ecosistema SRM-QK-ADSI
# ======================================================================
#  Funciones:
#     - Mantener estado global del sistema.
#     - Orquestar pipeline, monitor, diagnóstico y updates.
#     - Controlar encendido y apagado de servicios.
#     - Ejecutar verificaciones periódicas.
#     - Servir como punto de entrada principal de SRM.
#
#  Módulos coordinados:
#     ✔ Health Monitor
#     ✔ Diagnostics Engine
#     ✔ Update Manager
#     ✔ Integrator Engine
#     ✔ UI Sync Engine
#     ✔ Shopify Sync / Inventory Sync
# ======================================================================

import os
import json
import time
import threading
from datetime import datetime
import subprocess


# ----------------------------------------------------------------------
# RUTAS BASE
# ----------------------------------------------------------------------
BASE = r"C:\SRM_ADSI\05_pipeline"
STATE_FILE = os.path.join(BASE, "runtime_state.json")
LOG_FILE = os.path.join(BASE, "runtime_log.json")

MODULES = {
    "health_monitor": os.path.join(BASE, "srm_health_monitor_v1.py"),
    "diagnostics": os.path.join(BASE, "srm_diagnostics_v1.py"),
    "update_manager": os.path.join(BASE, "srm_update_manager_v1.py"),
    "frontend_sync": os.path.join(BASE, "srm_frontend_sync_v1.py"),
    "integrator": os.path.join(BASE, "srm_integrator_v1.py"),
}


# ----------------------------------------------------------------------
# STATE MANAGEMENT
# ----------------------------------------------------------------------
def load_state():
    if not os.path.exists(STATE_FILE):
        state = {
            "status": "IDLE",
            "last_update": None,
            "last_diagnostics": None,
            "services_running": {
                "health_monitor": False
            }
        }
        save_state(state)
        return state

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4, ensure_ascii=False)


def log_event(event_type, message):
    log_data = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            log_data = json.load(f)

    log_data.append({
        "timestamp": datetime.now().isoformat(),
        "event": event_type,
        "message": message
    })

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=4, ensure_ascii=False)


# ----------------------------------------------------------------------
# SERVICE CONTROL
# ----------------------------------------------------------------------
def start_health_monitor():
    """Ejecuta el monitor en un hilo independiente."""
    def run_monitor():
        subprocess.call(["python", MODULES["health_monitor"]])

    thread = threading.Thread(target=run_monitor, daemon=True)
    thread.start()

    state = load_state()
    state["services_running"]["health_monitor"] = True
    save_state(state)

    log_event("SERVICE_START", "Health Monitor iniciado.")
    print("✔ Health Monitor iniciado correctamente.")


def run_diagnostics():
    log_event("DIAGNOSTICS", "Ejecutando diagnóstico general...")
    subprocess.call(["python", MODULES["diagnostics"]])

    state = load_state()
    state["last_diagnostics"] = datetime.now().isoformat()
    save_state(state)

    print("✔ Diagnóstico completado.")


def run_updates():
    log_event("UPDATE_CHECK", "Buscando actualizaciones...")
    subprocess.call(["python", MODULES["update_manager"]])

    state = load_state()
    state["last_update"] = datetime.now().isoformat()
    save_state(state)

    print("✔ Verificación de actualizaciones completada.")


def run_frontend_sync():
    log_event("FRONTEND_SYNC", "Sincronizando frontend SRM...")
    subprocess.call(["python", MODULES["frontend_sync"]])
    print("✔ Frontend sincronizado.")


def run_integrator():
    log_event("INTEGRATOR", "Ejecutando integrador de sistemas SRM...")
    subprocess.call(["python", MODULES["integrator"]])
    print("✔ Integrador completado.")


# ----------------------------------------------------------------------
# RUNTIME LOOP
# ----------------------------------------------------------------------
def start_runtime_loop():
    print("\n=====================================================")
    print("            SRM RUNTIME CONTROLLER v1")
    print("=====================================================\n")

    state = load_state()
    state["status"] = "RUNNING"
    save_state(state)

    print("→ Iniciando servicios esenciales...\n")

    # Health Monitor se mantiene activo en un thread
    start_health_monitor()

    print("\n→ Entrando al bucle de supervisión continua...\n")

    while True:

        # 1. Health Monitor ya corre independentemente

        # 2. Ejecutar diagnósticos cada 2 minutos
        run_diagnostics()

        # 3. Buscar updates cada 5 minutos
        run_updates()

        # 4. Sincronizar UI cada 3 minutos
        run_frontend_sync()

        # 5. Ejecutar integrador cada ciclo
        run_integrator()

        print("\n✔ Ciclo SRM completado. Esperando próximo ciclo...\n")

        # Tiempo entre ciclos (puede ajustarse)
        time.sleep(90)


# ----------------------------------------------------------------------
# RUN
# ----------------------------------------------------------------------
if __name__ == "__main__":
    start_runtime_loop()
