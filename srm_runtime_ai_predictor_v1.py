# ======================================================================
#   srm_runtime_ai_predictor_v1.py — SRM AI PREDICTOR ENGINE v1
# ======================================================================
#  Este módulo analiza los logs históricos del SRM Runtime y extrae
#  tendencias para predecir:
#
#   ✔ Riesgo de fallo crítico
#   ✔ Riesgo de degradación futura
#   ✔ Carga futura del sistema
#   ✔ Probabilidad de anomalías próximas
#   ✔ Necesidad de mantenimiento
#   ✔ Necesidad de optimización
#
#  Produce:
#      /health/ai_predictor_report.json
#      /health/ai_predictor_summary.md
#
#  v1 utiliza heurísticas avanzadas NO basadas en ML:
#      → análisis de tendencias, regresión manual simple, patrones.
#
#  v2 podrá incluir ML local opcional (cuando SRM Cloud esté listo).
#
# ======================================================================

import os
import json
import numpy as np
from datetime import datetime

BASE = r"C:\SRM_ADSI\05_pipeline"
HEALTH = os.path.join(BASE, "health")

OUT_JSON = os.path.join(HEALTH, "ai_predictor_report.json")
OUT_MD = os.path.join(HEALTH, "ai_predictor_summary.md")

FILES = {
    "runtime_log": os.path.join(BASE, "runtime_log.json"),
    "anomalies": os.path.join(HEALTH, "anomaly_report.json"),
    "health_status": os.path.join(HEALTH, "health_status.json"),
    "optimizer": os.path.join(HEALTH, "self_optimizer_report.json"),
    "supervisor": os.path.join(HEALTH, "supervisor_report.json"),
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


def trend_score(values):
    """Evalúa tendencia creciente o decreciente."""
    if len(values) < 2:
        return 0

    x = np.arange(len(values))
    y = np.array(values)

    # Regresión lineal simple (sin librerías externas)
    A = np.vstack([x, np.ones(len(x))]).T
    slope, _ = np.linalg.lstsq(A, y, rcond=None)[0]

    return slope


# ----------------------------------------------------------------------
# MAIN AI PREDICTOR LOGIC
# ----------------------------------------------------------------------
def run_ai_predictor():

    print("\n=====================================================")
    print("            SRM — AI PREDICTOR ENGINE v1")
    print("=====================================================\n")

    # --------------------------------------------------
    # CARGAR DATOS
    # --------------------------------------------------
    runtime_log = load(FILES["runtime_log"], [])
    anomalies = load(FILES["anomalies"], {}).get("all_anomalies", [])
    health = load(FILES["health_status"], {})
    optimizer = load(FILES["optimizer"], {})
    supervisor = load(FILES["supervisor"], {})

    # --------------------------------------------------
    # EXTRAER MÉTRICAS
    # --------------------------------------------------
    error_trend = trend_score([
        1 if "error" in e.get("message", "").lower() else 0
        for e in runtime_log[-200:]
    ])

    anomaly_trend = trend_score([
        a.get("severity", 1)
        for a in anomalies[-200:]
    ])

    cpu_trend = trend_score([
        optimizer.get("cpu_usage", 0)
        for _ in range(5)
    ])

    ram_trend = trend_score([
        optimizer.get("memory_usage", 0)
        for _ in range(5)
    ])

    health_status = health.get("system_status", "unknown").lower()

    # --------------------------------------------------
    # RIESGOS PREDICTIVOS
    # --------------------------------------------------
    risk_failure = 0
    risk_degradation = 0
    risk_anomaly_future = 0

    # ------- Fallos críticos -------
    if error_trend > 0.2:
        risk_failure += 40
    if anomaly_trend > 0.3:
        risk_failure += 30
    if health_status == "critical":
        risk_failure += 50
    if supervisor.get("decisions", {}).get("needs_recovery", False):
        risk_failure += 20

    risk_failure = min(100, risk_failure)

    # ------- Degradación -------
    if anomaly_trend > 0.2:
        risk_degradation += 30
    if cpu_trend > 0:
        risk_degradation += 20
    if ram_trend > 0:
        risk_degradation += 20
    if health_status == "degraded":
        risk_degradation += 40

    risk_degradation = min(100, risk_degradation)

    # ------- Anomalías futuras -------
    if anomaly_trend > 0:
        risk_anomaly_future += 40
    if error_trend > 0:
        risk_anomaly_future += 20
    if cpu_trend > 0.5:
        risk_anomaly_future += 30

    risk_anomaly_future = min(100, risk_anomaly_future)

    # --------------------------------------------------
    # PREDICCIONES
    # --------------------------------------------------
    prediction = {
        "timestamp": datetime.now().isoformat(),
        "trend_error": float(error_trend),
        "trend_anomaly": float(anomaly_trend),
        "trend_cpu": float(cpu_trend),
        "trend_ram": float(ram_trend),
        "risk_failure": risk_failure,
        "risk_degradation": risk_degradation,
        "risk_anomaly_future": risk_anomaly_future,
    }

    # --------------------------------------------------
    # RECOMENDACIONES
    # --------------------------------------------------
    recommendations = []

    if risk_failure > 70:
        recommendations.append("Ejecutar Recovery Engine preventivo inmediatamente.")
    elif risk_failure > 40:
        recommendations.append("Revisar módulos afectados y aumentar frecuencia del monitor.")

    if risk_degradation > 40:
        recommendations.append("Recomendado: ejecutar Maintenance Engine.")

    if risk_anomaly_future > 50:
        recommendations.append("Aumentar vigilancia: ajustar runtime_cycle y monitor_interval.")

    if cpu_trend > 0.4 or ram_trend > 0.4:
        recommendations.append("Carga al alza: ejecutar Self Optimizer.")

    # --------------------------------------------------
    # CONSTRUIR REPORTE FINAL
    # --------------------------------------------------
    report = {
        "timestamp": prediction["timestamp"],
        "prediction": prediction,
        "recommendations": recommendations,
        "source_data": {
            "logs_analyzed": len(runtime_log),
            "anomalies_analyzed": len(anomalies),
            "health_status": health_status,
        }
    }

    save_json(report, OUT_JSON)

    md = f"""
# 🔮 SRM Runtime — AI Predictor Report v1

Generado: **{prediction['timestamp']}**

---

## 📊 Tendencias Detectadas

### Errores
Tendencia: **{prediction['trend_error']}**

### Anomalías
Tendencia: **{prediction['trend_anomaly']}**

### CPU
Tendencia: **{prediction['trend_cpu']}**

### RAM
Tendencia: **{prediction['trend_ram']}**

---

## ⚠ Riesgos Estimados

- Riesgo de fallo crítico: **{prediction['risk_failure']}%**
- Riesgo de degradación futura: **{prediction['risk_degradation']}%**
- Riesgo de anomalías próximas: **{prediction['risk_anomaly_future']}%**

---

## 🧠 Recomendaciones Automáticas
