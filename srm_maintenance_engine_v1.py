# ======================================================================
#  srm_maintenance_engine_v1.py — SRM Maintenance Engine v1
# ======================================================================
#  Funciones:
#   - Limpieza de logs
#   - Rotación de archivos grandes
#   - Eliminación / cuarentena de archivos huérfanos
#   - Validación de integridad mínima del sistema
#   - Compactación de historiales
#   - Generación de reporte
#
#  Salidas:
#   /maintenance/maintenance_report.json
#   /maintenance/maintenance_summary.md
# ======================================================================

import os
import json
from datetime import datetime

BASE = r"C:\SRM_ADSI\05_pipeline"
HEALTH_DIR = os.path.join(BASE, "health")
UPDATES_DIR = os.path.join(BASE, "updates")

MAINT_DIR = os.path.join(BASE, "maintenance")
ARCHIVE_DIR = os.path.join(MAINT_DIR, "archive")
QUARANTINE_DIR = os.path.join(MAINT_DIR, "quarantine")

os.makedirs(MAINT_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)
os.makedirs(QUARANTINE_DIR, exist_ok=True)

FILES = {
    "runtime_log": os.path.join(BASE, "runtime_log.json"),
    "events_log": os.path.join(HEALTH_DIR, "events_log.json"),
    "anomaly_log": os.path.join(HEALTH_DIR, "anomaly_report.json"),
    "version_manifest": os.path.join(UPDATES_DIR, "version_manifest.json"),
}

OUTPUT_JSON = os.path.join(MAINT_DIR, "maintenance_report.json")
OUTPUT_MD = os.path.join(MAINT_DIR, "maintenance_summary.md")

MAX_LOG_SIZE = 2 * 1024 * 1024  # 2 MB
MAX_ENTRIES = 50                # conservación de historiales


# ----------------------------------------------------------------------
# UTILIDADES
# ----------------------------------------------------------------------
def load_json(path, default):
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


def rotate_if_large(path):
    if not os.path.exists(path):
        return None

    size = os.path.getsize(path)
    if size < MAX_LOG_SIZE:
        return None

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_name = os.path.join(ARCHIVE_DIR, f"{os.path.basename(path)}.{ts}.bak")
    os.replace(path, new_name)
    return new_name


def quarantine_file(path):
    if not os.path.exists(path):
        return None

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(QUARANTINE_DIR, f"{os.path.basename(path)}.{ts}.q")
    os.replace(path, dest)
    return dest


def compact_log(path):
    data = load_json(path, [])
    if not isinstance(data, list):
        return data

    if len(data) > MAX_ENTRIES:
        return data[-MAX_ENTRIES:]
    return data


# ----------------------------------------------------------------------
# DETECTAR ARCHIVOS HUÉRFANOS
# ----------------------------------------------------------------------
def scan_for_orphans():
    orphan_extensions = [".tmp", ".bak", ".old", ".corrupt"]
    quarantined = []

    for root, _, files in os.walk(BASE):
        for name in files:
            path = os.path.join(root, name)
            if any(name.endswith(ext) for ext in orphan_extensions):
                q = quarantine_file(path)
                if q:
                    quarantined.append(q)

    return quarantined


# ----------------------------------------------------------------------
# VALIDAR INTEGRIDAD DEL SISTEMA
# ----------------------------------------------------------------------
def validate_integrity():
    required_files = [
        "srm_runtime_controller_v1.py",
        "srm_diagnostics_v1.py",
        "srm_update_manager_v1.py",
        "srm_health_monitor_v1.py",
        "srm_system_report_v1.py",
    ]

    missing = []

    for f in required_files:
        path = os.path.join(BASE, f)
        if not os.path.exists(path):
            missing.append(path)

    return missing


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------
def run_maintenance():

    print("\n=====================================================")
    print("             SRM — MAINTENANCE ENGINE v1")
    print("=====================================================\n")

    report = {
        "timestamp": datetime.now().isoformat(),
        "log_rotations": [],
        "log_compactions": [],
        "quarantined_files": [],
        "missing_critical_files": [],
    }

    # 1. Rotación de logs grandes
    for key, path in FILES.items():
        rotated = rotate_if_large(path)
        if rotated:
            report["log_rotations"].append({
                "file": path,
                "rotated_to": rotated
            })

    # 2. Compactación de historiales (últimos 50 eventos)
    for key, path in FILES.items():
        data = load_json(path, [])
        if isinstance(data, list) and len(data) > MAX_ENTRIES:
            compacted = data[-MAX_ENTRIES:]
            save_json(compacted, path)
            report["log_compactions"].append(path)

    # 3. Archivos huérfanos → cuarentena
    orphaned = scan_for_orphans()
    report["quarantined_files"] = orphaned

    # 4. Validación de integridad mínima
    missing = validate_integrity()
    report["missing_critical_files"] = missing

    # 5. Guardar reporte JSON
    save_json(report, OUTPUT_JSON)

    print("✔ maintenance_report.json generado")

    # 6. Resumen en Markdown
    md = f"""
# 🧹 SRM — Maintenance Report v1

Generado: **{report['timestamp']}**

---

## 🔧 Archivos rotados por tamaño
{json.dumps(report['log_rotations'], indent=4, ensure_ascii=False)}

---

## ✂️ Logs compactados
{json.dumps(report['log_compactions'], indent=4, ensure_ascii=False)}

---

## 🚫 Archivos sospechosos movidos a cuarentena
{json.dumps(report['quarantined_files'], indent=4, ensure_ascii=False)}

---

## ⚠ Archivos críticos faltantes
{json.dumps(report['missing_critical_files'], indent=4, ensure_ascii=False)}

---

## ✔ Fin del reporte
"""

    save_md(md, OUTPUT_MD)
    print("✔ maintenance_summary.md generado")

    print("\n=====================================================")
    print("✔ MAINTENANCE ENGINE COMPLETADO")
    print("=====================================================\n")


if __name__ == "__main__":
    run_maintenance()
