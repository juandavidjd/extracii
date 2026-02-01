# ======================================================================
# srm_health_monitor_v1.py — SRM-QK-ADSI HEALTH MONITOR v1
# ======================================================================
# Autor: SRM Engine
#
# Propósito:
#   - Monitorear los directorios críticos del ecosistema SRM.
#   - Detectar cambios en tiempo real: creación, eliminación, modificación.
#   - Registrar eventos y anomalías.
#   - Verificar consistencia estructural de forma continua.
#
# Resultados:
#   events_log.json  → historial completo de monitoreo
#   health_status.json → último estado del sistema
#
# NOTA:
#   v1 opera solo como monitor pasivo (sin ejecutar pipeline).
# ======================================================================

import os
import json
import time
from datetime import datetime


# ----------------------------------------------------------------------
# CONFIGURACIÓN
# ----------------------------------------------------------------------
MONITORED_FOLDERS = {
    "docs": r"C:\SRM_ADSI\00_docs",
    "normalized": r"C:\SRM_ADSI\02_cleaned_normalized",
    "knowledge": r"C:\SRM_ADSI\03_knowledge_base",
    "pipeline": r"C:\SRM_ADSI\05_pipeline",
    "shopify": r"C:\SRM_ADSI\06_shopify",
    "branding": r"C:\SRM_ADSI\08_branding",
}

HEALTH_DIR = r"C:\SRM_ADSI\05_pipeline\health"
os.makedirs(HEALTH_DIR, exist_ok=True)

EVENTS_LOG = os.path.join(HEALTH_DIR, "events_log.json")
STATUS_FILE = os.path.join(HEALTH_DIR, "health_status.json")

SCAN_INTERVAL = 5   # segundos (puede subir a 15 o 30 si deseas menos carga)
FILE_HASH_CACHE = {}  # huellas digitales para detectar modificaciones


# ----------------------------------------------------------------------
# UTILIDADES
# ----------------------------------------------------------------------
def snapshot_folder(folder):
    """Devuelve un snapshot simple de archivos: tamaño, fecha, existencia."""
    files = {}
    for root, _, filenames in os.walk(folder):
        for name in filenames:
            path = os.path.join(root, name)
            try:
                stat = os.stat(path)
                files[path] = {
                    "size": stat.st_size,
                    "modified": stat.st_mtime
                }
            except:
                continue
    return files


def load_events():
    if not os.path.exists(EVENTS_LOG):
        return []
    with open(EVENTS_LOG, "r", encoding="utf-8") as f:
        return json.load(f)


def save_events(events):
    with open(EVENTS_LOG, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=4, ensure_ascii=False)


def save_status(status):
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=4, ensure_ascii=False)


def emit_event(event_type, folder, path):
    """Registra un nuevo evento detectado por el monitor."""
    events = load_events()

    events.append({
        "timestamp": datetime.now().isoformat(),
        "type": event_type,
        "folder": folder,
        "path": path
    })

    save_events(events)

    print(f"⚠ EVENTO [{event_type}] → {path}")


# ----------------------------------------------------------------------
# HEALTH CHECKS
# ----------------------------------------------------------------------
def health_check(snapshot):
    status = {
        "timestamp": datetime.now().isoformat(),
        "folders": {}
    }

    for name, folder in MONITORED_FOLDERS.items():
        exists = os.path.exists(folder)
        count = len(snapshot.get(name, {}))

        status["folders"][name] = {
            "exists": exists,
            "files": count,
            "status": "OK" if exists and count > 0 else "ALERTA"
        }

    save_status(status)


# ----------------------------------------------------------------------
# MAIN MONITOR LOOP
# ----------------------------------------------------------------------
def start_monitor():

    print("\n=====================================================")
    print("           SRM — HEALTH MONITOR v1 (ACTIVO)")
    print("=====================================================\n")
    print("Monitoreando carpetas críticas cada", SCAN_INTERVAL, "segundos...\n")

    # Snapshot inicial
    previous_snapshots = {
        name: snapshot_folder(folder)
        for name, folder in MONITORED_FOLDERS.items()
    }

    while True:

        current_snapshots = {
            name: snapshot_folder(folder)
            for name, folder in MONITORED_FOLDERS.items()
        }

        # Detectar cambios
        for name in MONITORED_FOLDERS.keys():
            prev = previous_snapshots.get(name, {})
            curr = current_snapshots.get(name, {})

            # Archivos nuevos
            for path in curr.keys():
                if path not in prev:
                    emit_event("CREATED", name, path)

            # Archivos eliminados
            for path in prev.keys():
                if path not in curr:
                    emit_event("DELETED", name, path)

            # Archivos modificados
            for path in curr.keys():
                if (
                    path in prev and
                    curr[path]["modified"] != prev[path]["modified"]
                ):
                    emit_event("MODIFIED", name, path)

        # Guardar snapshot actualizado
        previous_snapshots = current_snapshots

        # Actualizar health status
        health_check(current_snapshots)

        time.sleep(SCAN_INTERVAL)


# ----------------------------------------------------------------------
# RUN
# ----------------------------------------------------------------------
if __name__ == "__main__":
    start_monitor()
