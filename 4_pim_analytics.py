#!/usr/bin/env python3
# ============================================================
# pim_analytics.py — ENTERPRISE KPI DASHBOARD (REAL)
# ============================================================

import os
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

PIM_JSON = "C:/img/pim_catalog_v7.json"
DASHBOARD_HTML = "C:/img/pim_analytics_dashboard.html"


def main():
    print("==============================================")
    print("   📊 PIM ANALYTICS — KPI Dashboard Kaiqi")
    print("==============================================\n")

    if not os.path.exists(PIM_JSON):
        raise FileNotFoundError("❌ No existe pim_catalog_v7.json")

    # ----------------------------------------------------------
    # Cargar PIM JSON
    # ----------------------------------------------------------
    data = json.load(open(PIM_JSON, "r", encoding="utf-8"))
    df = pd.DataFrame(data)

    if df.empty:
        raise ValueError("El archivo PIM está vacío.")

    # ----------------------------------------------------------
    # KPIs básicos
    # ----------------------------------------------------------
    df["has_image"] = df["imagen_elegida"].apply(lambda x: 0 if x in ("", None) else 1)
    df["conf_bucket"] = df["match_conf"].apply(lambda x: round(x, 1))

    total_items = len(df)
    con_img = df["has_image"].sum()
    sin_img = total_items - con_img
    pct_con_img = round((con_img / total_items) * 100, 2)

    print(f"Total ítems: {total_items}")
    print(f"Con imagen:  {con_img} ({pct_con_img}%)")
    print(f"Sin imagen:  {sin_img}")

    # ----------------------------------------------------------
    # FIGURA 1 — Porcentaje con imagen
    # ----------------------------------------------------------
    fig1 = px.pie(
        df,
        names="has_image",
        title="Distribución de ítems con/sin imagen",
        color="has_image",
        color_discrete_map={0: "red", 1: "green"},
        labels={1: "Con imagen", 0: "Sin imagen"}
    )

    # ----------------------------------------------------------
    # FIGURA 2 — Histograma match_conf
    # ----------------------------------------------------------
    fig2 = px.histogram(
        df,
        x="match_conf",
        nbins=20,
        title="Distribución de Confianza IA (match_conf)",
        labels={"match_conf": "Nivel de coincidencia IA"},
        color_discrete_sequence=["#2266dd"]
    )

    # ----------------------------------------------------------
    # FIGURA 3 — Tabla KPI
    # ----------------------------------------------------------
    kpi_table = go.Figure(
        data=[
            go.Table(
                header=dict(
                    values=["KPI", "Valor"],
                    fill_color="#0A2F7B",
                    font=dict(color="white", size=14),
                ),
                cells=dict(
                    values=[
                        ["Total productos", "Con imagen", "Sin imagen", "% Con imagen"],
                        [total_items, con_img, sin_img, f"{pct_con_img}%"],
                    ],
                    fill=dict(color=["#e6f0ff", "#ffffff"]),
                    font=dict(size=14),
                )
            )
        ]
    )
    kpi_table.update_layout(title="Resumen KPI — Catálogo Kaiqi")

    # ----------------------------------------------------------
    # ENSAMBLAR DASHBOARD HTML
    # ----------------------------------------------------------
    final_html = f"""
<html>
<head>
    <title>PIM Analytics Kaiqi</title>
    <meta charset="UTF-8">
</head>
<body style="font-family: Arial;">
    <h1>📊 Dashboard PIM Kaiqi — Indicadores de Catalogación</h1>

    <h2>1. Distribución ítems con/sin imagen</h2>
    {fig1.to_html(full_html=False, include_plotlyjs="cdn")}

    <h2>2. Distribución de confianza IA</h2>
    {fig2.to_html(full_html=False, include_plotlyjs=False)}

    <h2>3. Tabla de KPIs Generales</h2>
    {kpi_table.to_html(full_html=False, include_plotlyjs=False)}

    <br><br>
    <hr>
    <p style="font-size:12px;color:#555">
        Generado automáticamente por PIM Kaiqi v7 — Suite Ejecutiva Digital ADSI.
    </p>
</body>
</html>
"""

    with open(DASHBOARD_HTML, "w", encoding="utf-8") as f:
        f.write(final_html)

    print("\n🎯 Dashboard generado con éxito:")
    print(DASHBOARD_HTML)


if __name__ == "__main__":
    main()
