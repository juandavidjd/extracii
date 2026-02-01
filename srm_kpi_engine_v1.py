# ================================================================
# SRM KPI ENGINE v1 — SRM-QK-ADSI 360° 
# ================================================================
# Autor: SRM-QK-ADSI Engine
#
# Propósito:
#   - Calcular KPIs de catálogo, inventario, pedidos, rotación,
#     disponibilidad 360°, actividad de flotas y motos cliente.
#   - Servir como base del Dashboard SRM 360°.
#   - Integración con Supabase (v2) y seeds CSV (v1).
#
# Este módulo es consumido por:
#   - Dashboard SRM 360° (Lovable)
#   - Guided Tour SRM
#   - Agentes SRM
#   - Programas SRM
#   - Shopify Sync
#   - Systeme.io automatizaciones
# ================================================================

import os
import pandas as pd
import numpy as np
from datetime import datetime

# ---------------------------------------------------------------
# Seeds del sistema
# ---------------------------------------------------------------
SEED_DIR = r"C:\SRM_ADSI\05_pipeline\sql\seeds"

SEED_EMPRESAS      = os.path.join(SEED_DIR, "seed_empresas.csv")
SEED_INVENTARIOS   = os.path.join(SEED_DIR, "seed_inventarios.csv")
SEED_PRODUCTOS     = os.path.join(SEED_DIR, "seed_productos_srm.csv")


# ---------------------------------------------------------------
# Load seguro de CSV
# ---------------------------------------------------------------
def safe_load(path):
    if not os.path.exists(path):
        print(f"[ADVERTENCIA] No existe: {path}")
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, encoding="utf-8", on_bad_lines="skip")


# ---------------------------------------------------------------
# Cargar todos los datos
# ---------------------------------------------------------------
def load_all_data():
    return {
        "empresas": safe_load(SEED_EMPRESAS),
        "inventarios": safe_load(SEED_INVENTARIOS),
        "productos": safe_load(SEED_PRODUCTOS)
    }


# ===============================================================
# KPI ENGINE — Funciones principales
# ===============================================================

# ---------------------------------------------------------------
# 1. Total de SKUs en el catálogo SRM
# ---------------------------------------------------------------
def kpi_total_skus(data):
    prod = data["productos"]
    if prod.empty:
        return 0
    return prod["sku"].nunique()


# ---------------------------------------------------------------
# 2. Total de empresas activas
# ---------------------------------------------------------------
def kpi_total_empresas(data):
    df = data["empresas"]
    if df.empty:
        return 0
    return df["id"].nunique()


# ---------------------------------------------------------------
# 3. Total de stock SRM (suma en toda la red)
# ---------------------------------------------------------------
def kpi_stock_total(data):
    inv = data["inventarios"]
    if inv.empty:
        return 0
    if "stock" not in inv.columns:
        return 0
    return inv["stock"].astype(int).sum()


# ---------------------------------------------------------------
# 4. Stock por empresa
# ---------------------------------------------------------------
def kpi_stock_por_empresa(data):
    inv = data["inventarios"]
    emp = data["empresas"]
    if inv.empty or emp.empty:
        return pd.DataFrame()

    df = inv.copy()
    df["stock"] = df["stock"].astype(int)

    res = df.groupby("empresa_id")["stock"].sum().reset_index()
    res = res.merge(emp, left_on="empresa_id", right_on="id", how="left")
    return res[["empresa_id", "nombre", "stock"]]


# ---------------------------------------------------------------
# 5. SKUs con ausencia total (stock 0 en toda la red)
# ---------------------------------------------------------------
def kpi_skus_sin_existencia(data):
    prod = data["productos"]
    inv = data["inventarios"]

    if prod.empty:
        return []

    if inv.empty:
        return prod["sku"].tolist()

    inv_grp = inv.groupby("sku")["stock"].agg(lambda x: x.astype(int).sum())
    sin_stock = inv_grp[inv_grp == 0].index.tolist()
    return sin_stock


# ---------------------------------------------------------------
# 6. Porcentaje de catálogo disponible (SKUs con stock > 0)
# ---------------------------------------------------------------
def kpi_porcentaje_catalogo_disponible(data):
    total = kpi_total_skus(data)
    if total == 0:
        return 0

    sin_stock = kpi_skus_sin_existencia(data)
    disponibles = total - len(sin_stock)

    return round((disponibles / total) * 100, 2)


# ---------------------------------------------------------------
# 7. Ranking de empresas por nivel de inventario
# ---------------------------------------------------------------
def kpi_ranking_empresas_por_stock(data):
    df = kpi_stock_por_empresa(data)
    if df.empty:
        return df
    return df.sort_values(by="stock", ascending=False)


# ---------------------------------------------------------------
# 8. SKUs críticos (stock bajo)
# ---------------------------------------------------------------
def kpi_skus_criticos(data, umbral=3):
    inv = data["inventarios"]
    if inv.empty:
        return pd.DataFrame()

    inv["stock"] = inv["stock"].astype(int)
    criticos = inv[inv["stock"] <= umbral]
    return criticos.merge(data["productos"], on="sku", how="left")


# ---------------------------------------------------------------
# 9. SKUs top con mayor disponibilidad
# ---------------------------------------------------------------
def kpi_top_skus_mayor_stock(data, top=10):
    inv = data["inventarios"]
    prod = data["productos"]

    if inv.empty or prod.empty:
        return pd.DataFrame()

    inv["stock"] = inv["stock"].astype(int)
    df = inv.groupby("sku")["stock"].sum().reset_index()
    df = df.merge(prod, on="sku", how="left")

    return df.sort_values(by="stock", ascending=False).head(top)


# ---------------------------------------------------------------
# 10. Catálogo por categoría
# ---------------------------------------------------------------
def kpi_categorias_catalogo(data):
    prod = data["productos"]
    if prod.empty:
        return {}

    return prod["categoria"].value_counts().to_dict()


# ---------------------------------------------------------------
# 11. Disponibilidad promedio por SKU
# ---------------------------------------------------------------
def kpi_disponibilidad_promedio(data):
    inv = data["inventarios"]
    if inv.empty:
        return 0

    inv["stock"] = inv["stock"].astype(int)
    return round(inv["stock"].mean(), 2)


# ---------------------------------------------------------------
# 12. Matriz Inventario 360° general
# ---------------------------------------------------------------
def kpi_matriz_general(data):
    """Resumen total para el Dashboard SRM 360°."""
    return {
        "total_skus": kpi_total_skus(data),
        "total_empresas": kpi_total_empresas(data),
        "stock_total": kpi_stock_total(data),
        "porcentaje_catalogo_disponible": kpi_porcentaje_catalogo_disponible(data),
        "categorias": kpi_categorias_catalogo(data),
        "disponibilidad_promedio": kpi_disponibilidad_promedio(data)
    }


# ===============================================================
# API EXPORTADA PARA OTROS MÓDULOS
# ===============================================================

def kpi_api():
    """Retorna un contenedor con todas las funciones KPI."""
    data = load_all_data()

    return {
        "data": data,
        "total_skus": lambda: kpi_total_skus(data),
        "total_empresas": lambda: kpi_total_empresas(data),
        "stock_total": lambda: kpi_stock_total(data),
        "stock_por_empresa": lambda: kpi_stock_por_empresa(data),
        "skus_sin_existencia": lambda: kpi_skus_sin_existencia(data),
        "porcentaje_disponibilidad": lambda: kpi_porcentaje_catalogo_disponible(data),
        "ranking_empresas": lambda: kpi_ranking_empresas_por_stock(data),
        "skus_criticos": lambda: kpi_skus_criticos(data),
        "top_skus": lambda top=10: kpi_top_skus_mayor_stock(data, top),
        "categorias": lambda: kpi_categorias_catalogo(data),
        "disp_promedio": lambda: kpi_disponibilidad_promedio(data),
        "matriz_general": lambda: kpi_matriz_general(data),
    }


# ===============================================================
# TEST RÁPIDO
# ===============================================================

if __name__ == "__main__":
    api = kpi_api()
    print("=================================================")
    print("        TEST RÁPIDO — KPI ENGINE SRM v1")
    print("=================================================")
    print("Total SKUs:", api["total_skus"]())
    print("Total Empresas:", api["total_empresas"]())
    print("Stock Total Red SRM:", api["stock_total"]())
    print("Porcentaje Disponibilidad:", api["porcentaje_disponibilidad"](), "%")
    print("\nMatriz General:")
    print(api["matriz_general"]())
