# ======================================================================
#   srm_self_optimizer_v1.py — SRM SELF OPTIMIZER ENGINE v1
# ======================================================================
#  Este módulo genera optimización autónoma del SRM Runtime:
#
#   ✔ Ajuste del ciclo de monitoreo
#   ✔ Ajuste del ciclo del runtime controller
#   ✔ Reducción de carga cuando el sistema está estable
#   ✔ Incremento de vigilancia ante anomalías
#   ✔ Optimización del tamaño de logs
#   ✔ Recomendaciones de mantenimiento
#   ✔ Aprendizaje simple basado en promedios históricos
#
#  Salidas:
#     /health/self_optimizer_report.json
#     /health/self_optimizer_summary.md
# ======================================================================

import os
import json
import psutil
from datetime import datetime

BASE = r"C:\SRM_ADSI\05_pipeline"
HEALTH_DIR = os.path.join(BASE, "health")
OUTPUT_JSON = os.path.join(HEALTH_DIR, "self_optimizer_report.json")
OUTPUT_MD = os.path.join(HEALTH_DIR, "self_optimizer_summary.md")

FILES = {
    "runtime_state": os.path.join(BASE, "runtime_state.json"),
    "runtime_log": os.path.join(BASE, "runtime_log.json"),
    "anomalies": os.path.join(HEALTH_DIR, "anomaly_report.json"),
    "health_status": os.path.join(HEALTH_DIR, "health_status.json"),
}


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


# ----------------------------------------------------------------------
# OPTIMIZACIÓN DINÁMICA
# ----------------------------------------------------------------------
def compute_recommended_runtime_cycle(cpu, errors, anomalies_count):
    """
    Devuelve el ciclo recomendado en segundos para el Runtime Controller.
    Base: 90 segundos
    """
    cycle = 90

    # CPU alta -> ciclo más largo
    if cpu > 70:
        cycle += 30
    
    if cpu > 85:
        cycle += 60

    # Errores -> ciclo más corto
    cycle -= errors * 1.5

    # Anomalías -> ciclo más corto
    cycle -= anomalies_count * 2

    # Rango seguro
    return max(30, min(300, int(cycle)))


def compute_recommended_health_monitor_interval(events_count, anomalies_count):
    """
    Base: 5 segundos
    Ajusta el intervalo del monitor según actividad.
    """

    interval = 5

    # Mucha actividad → más rápido
    if events_count > 20:
        interval = 2
    if events_count > 100:
        interval = 1

    # Si no hay actividad → ralentizar
    if events_count < 5:
        interval = 10

    # Anomalías elevadas → más rápido
    if anomalies_count > 5:
        interval = 2

    return max(1, min(20, interval))


# ----------------------------------------------------------------------
# MAIN OPTIMIZATION ENGINE
# ----------------------------------------------------------------------
def run_self_optimizer():

    print("\n=====================================================")
    print("            SRM — SELF OPTIMIZER ENGINE v1")
    print("=====================================================\n")

    # ------------------------------------------------------------------
    # Cargar datos del sistema
    # ------------------------------------------------------------------
    runtime_state = load_json(FILES["runtime_state"], {})
    logs = load_json(FILES["runtime_log"], [])
    anomalies = load_json(FILES["anomalies"], {}).get("all_anomalies", [])
    health = load_json(FILES["health_status"], {})

    # ------------------------------------------------------------------
    # Métricas clave
    # ------------------------------------------------------------------
    cpu_usage = psutil.cpu_percent(interval=1)
    mem_usage = psutil.virtual_memory().percent

    errors = sum("error" in e.get("message", "").lower() for e in logs[-50:])
    warnings = sum(
        ("warning" in e.get("message", "").lower() or "advertencia" in e.get("message", "").lower())
        for e in logs[-50:]
    )
    events_count = len(load_json(FILES["anomalies"], {}).get("events_summary", {}).get("total_events", []))

    anomalies_count = len(anomalies)

    # ------------------------------------------------------------------
    # Recomendaciones
    # ------------------------------------------------------------------
    recommended_runtime_cycle = compute_recommended_runtime_cycle(cpu_usage, errors, anomalies_count)
    recommended_monitor_interval = compute_recommended_health_monitor_interval(events_count, anomalies_count)

    # ------------------------------------------------------------------
    # Construir reporte
    # ------------------------------------------------------------------
    report = {
        "timestamp": datetime.now().isoformat(),
        "cpu_usage": cpu_usage,
        "memory_usage": mem_usage,
        "errors_last_50": errors,
        "warnings_last_50": warnings,
        "anomalies_count": anomalies_count,
        "recommended_runtime_cycle": recommended_runtime_cycle,
        "recommended_health_monitor_interval": recommended_monitor_interval,
        "notes": []
    }

    # Sugerencias adicionales
    if cpu_usage > 85:
        report["notes"].append("CPU muy alta: considerar reducir procesos secundarios.")
    if mem_usage > 85:
        report["notes"].append("Memoria crítica: sugerir compactación de logs.")
    if anomalies_count > 10:
        report["notes"].append("Alto número de anomalías: ejecutar diagnóstico profundo.")
    if errors > 15:
        report["notes"].append("Errores recurrentes: verificar módulos afectados.")

    # ------------------------------------------------------------------
    # Guardar reporte
    # ------------------------------------------------------------------
    save_json(report, OUTPUT_JSON)

    md = f"""
# ⚙️ SRM — Self Optimizer Report v1

Generado: **{report['timestamp']}**

---

## 🔋 Uso del Sistema
- CPU: **{cpu_usage}%**
- Memoria RAM: **{mem_usage}%**

---

## 📝 Logs (últimos 50)
- Errores: **{errors}**
- Advertencias: **{warnings}**

---

## 🔥 Anomalías
Total detectadas: **{anomalies_count}**

---

## 🔧 Recomendaciones automáticas

### ⏱ Ciclo recomendado para el Runtime Controller:
**{recommended_runtime_cycle} segundos**

### 📡 Intervalo recomendado para el Health Monitor:
**{recommended_monitor_interval} segundos**

---

## 🧠 Notas automatizadas
