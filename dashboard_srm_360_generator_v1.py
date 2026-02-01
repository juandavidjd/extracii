# ================================================================
# SRM DASHBOARD 360° GENERATOR v1 — SRM-QK-ADSI
# ================================================================
# Autor: SRM-QK-ADSI Engine
#
# Propósito:
#   - Crear el Dashboard SRM 360° como archivo HTML autónomo.
#   - Integrarse con el KPI Engine.
#   - Generar matrices, tarjetas, tablas y resúmenes para Lovable.
#   - Servir como base del Panel SRM (Fase v28).
# ================================================================

import os
import json
from datetime import datetime
from srm_kpi_engine_v1 import kpi_api

# ---------------------------------------------------------------
# Ruta de salida
# ---------------------------------------------------------------
OUTPUT_PATH = r"C:\SRM_ADSI\09_dashboards\srm_dashboard_360.html"

# Asegurar directorio
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)


# ---------------------------------------------------------------
# Tarjeta HTML reutilizable
# ---------------------------------------------------------------
def card(title, value, color="#0046FF"):
    return f"""
    <div class='card' style='border-left: 6px solid {color};'>
        <h3>{title}</h3>
        <p>{value}</p>
    </div>
    """


# ---------------------------------------------------------------
# Generar tabla HTML desde DataFrame
# ---------------------------------------------------------------
def df_to_html(df):
    if df is None or df.empty:
        return "<p>Sin datos.</p>"
    return df.to_html(index=False, border=0, classes="srm-table")


# ---------------------------------------------------------------
# Generar Dashboard 360°
# ---------------------------------------------------------------
def generar_dashboard():

    api = kpi_api()
    data = api["data"]

    matriz = api["matriz_general"]()
    ranking = api["ranking_empresas"]()
    criticos = api["skus_criticos"]()
    top = api["top_skus"]()

    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>SRM 360° Dashboard</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #f5f6fa;
                padding: 20px;
            }}
            h1 {{
                color: #0046FF;
                font-size: 32px;
                margin-bottom: 10px;
            }}
            h2 {{
                color: #333;
                margin-top: 30px;
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 20px;
            }}
            .card {{
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 3px 8px rgba(0,0,0,0.1);
            }}
            .srm-table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }}
            .srm-table th {{
                background: #0046FF;
                color: white;
                padding: 8px;
            }}
            .srm-table td {{
                padding: 6px;
                border-bottom: 1px solid #ddd;
            }}
        </style>
    </head>

    <body>
        <h1>SRM Dashboard 360° — v1</h1>
        <p>Última actualización: {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>

        <h2>🔷 Métricas Generales</h2>
        <div class="grid">
            {card("Total SKUs", matriz['total_skus'])}
            {card("Total Empresas", matriz['total_empresas'])}
            {card("Stock Total (Red SRM)", matriz['stock_total'])}
            {card("Disponibilidad (%)", f"{matriz['porcentaje_catalogo_disponible']}%")}
            {card("Disponibilidad Promedio", matriz['disponibilidad_promedio'])}
            {card("Categorías Únicas", len(matriz["categorias"]))}
        </div>

        <h2>🏭 Ranking de Empresas por Nivel de Inventario</h2>
        {df_to_html(ranking)}

        <h2>⚠️ SKUs Críticos (stock bajo)</h2>
        {df_to_html(criticos)}

        <h2>📦 Top SKUs con Mayor Disponibilidad</h2>
        {df_to_html(top)}

        <h2>📘 Catálogo por Categoría</h2>
        <pre>{json.dumps(matriz["categorias"], indent=4, ensure_ascii=False)}</pre>

        <br><br>
        <hr>
        <p style="color:#888; font-size:12px;">SRM-QK-ADSI Engine — Dashboard generado automáticamente.</p>
    </body>
    </html>
    """

    # Guardar archivo
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print("===============================================")
    print(" ✔ SRM DASHBOARD 360° generado correctamente")
    print(f" ✔ Archivo: {OUTPUT_PATH}")
    print("===============================================")


# ---------------------------------------------------------------
# RUN
# ---------------------------------------------------------------
if __name__ == "__main__":
    generar_dashboard()
