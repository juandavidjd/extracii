# ================================================================
# SRM INVENTORY 360° ENGINE v1
# ================================================================
# Autor: SRM-QK-ADSI Engine
# Propósito:
#   Este módulo implementa la lógica central del Inventario SRM:
#   - Consultas unificadas de inventario
#   - Respuesta para Escáner SRM 360°
#   - Funciones clave para Programas SRM
#   - Compatibilidad con Supabase / PostgreSQL
#   - Conectores para agentes SRM y Lovable
#
# Nota:
#   v1 utiliza archivos seed CSV.
#   v2/v3 se conectará directamente a Supabase vía API.
# ================================================================

import os
import pandas as pd
import json

# ---------------------------------------------------------------
# RUTAS BASE
# ---------------------------------------------------------------
SEED_DIR = r"C:\SRM_ADSI\05_pipeline\sql\seeds"

SEED_EMPRESAS      = os.path.join(SEED_DIR, "seed_empresas.csv")
SEED_INVENTARIOS   = os.path.join(SEED_DIR, "seed_inventarios.csv")
SEED_PRODUCTOS     = os.path.join(SEED_DIR, "seed_productos_srm.csv")

# ---------------------------------------------------------------
# CARGA SEGURA DE CSV
# ---------------------------------------------------------------
def load_csv(path):
    if not os.path.exists(path):
        print(f"[ADVERTENCIA] No existe: {path}")
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, encoding="utf-8", on_bad_lines="skip")


# ---------------------------------------------------------------
# CARGA DE DATOS
# ---------------------------------------------------------------
def load_data():
    return {
        "empresas": load_csv(SEED_EMPRESAS),
        "inventarios": load_csv(SEED_INVENTARIOS),
        "productos": load_csv(SEED_PRODUCTOS)
    }


# ===============================================================
#     FUNCIONES PRINCIPALES — INVENTARIO 360°
# ===============================================================

# ---------------------------------------------------------------
# 1. OBTENER INVENTARIO COMPLETO POR EMPRESA
# ---------------------------------------------------------------
def get_inventario_por_empresa(empresa_id, data):
    inv = data["inventarios"]
    prod = data["productos"]

    if inv.empty or prod.empty:
        return pd.DataFrame()

    df = inv[inv["empresa_id"].astype(str) == str(empresa_id)]
    df = df.merge(prod, on="sku", how="left")
    return df


# ---------------------------------------------------------------
# 2. OBTENER DISPONIBILIDAD DE UN SKU EN TODA LA RED SRM
# ---------------------------------------------------------------
def get_disponibilidad_sku(sku, data):
    inv = data["inventarios"]
    emp = data["empresas"]

    if inv.empty:
        return pd.DataFrame()

    df = inv[inv["sku"].astype(str) == str(sku)]
    df = df.merge(emp, left_on="empresa_id", right_on="id", how="left")
    return df[["empresa_id", "nombre", "stock", "costo", "precio_venta"]]


# ---------------------------------------------------------------
# 3. CONSULTA PRINCIPAL PARA EL ESCÁNER SRM 360°
# ---------------------------------------------------------------
def scanner_query(sku, data):
    prod = data["productos"]
    disp = get_disponibilidad_sku(sku, data)

    producto = prod[prod["sku"] == sku]

    if producto.empty:
        return {
            "sku": sku,
            "existe": False,
            "mensaje": "Producto no encontrado en el catálogo SRM"
        }

    p = producto.iloc[0]

    return {
        "sku": sku,
        "existe": True,
        "nombre": p.get("nombre", ""),
        "categoria": p.get("categoria", ""),
        "sistema": p.get("sistema", ""),
        "subsistema": p.get("subsistema", ""),
        "fitment": safe_json(p.get("fitment_json", "{}")),
        "disponibilidad": disp.to_dict(orient="records")
    }


# ---------------------------------------------------------------
# 4. MATRIZ DE DISPONIBILIDAD 360°
# ---------------------------------------------------------------
def get_matriz_disponibilidad(sku, data):
    disp = get_disponibilidad_sku(sku, data)

    if disp.empty:
        return {
            "sku": sku,
            "total_stock": 0,
            "proveedores": []
        }

    total_stock = disp["stock"].astype(int).sum()

    proveedores = []
    for _, row in disp.iterrows():
        proveedores.append({
            "empresa_id": row["empresa_id"],
            "nombre": row["nombre"],
            "stock": int(row["stock"]) if row["stock"] else 0,
            "costo": row.get("costo", ""),
            "precio_venta": row.get("precio_venta", "")
        })

    return {
        "sku": sku,
        "total_stock": total_stock,
        "proveedores": proveedores
    }


# ---------------------------------------------------------------
# 5. SELECCIÓN DE PROVEEDOR ÓPTIMO (para Redundancia SRM)
# ---------------------------------------------------------------
def seleccionar_proveedor_optimo(sku, data):
    matriz = get_matriz_disponibilidad(sku, data)

    if matriz["total_stock"] == 0:
        return None

    # Estrategia v1:
    # - Seleccionar el proveedor con mayor stock
    # - v2 incluirá distancia, SLA, costo logístico, tiempos, etc.

    proveedores = matriz["proveedores"]
    proveedores = sorted(proveedores, key=lambda x: x["stock"], reverse=True)

    return proveedores[0]


# ---------------------------------------------------------------
# 6. OBTENER ROTACIÓN SIMPLE (v1)
# ---------------------------------------------------------------
def get_rotacion_sku(sku, data, meses=3):
    # v1 = placeholder. En v2 conectar con tabla de pedidos.
    # Rotación ficticia mínima basada en stock.
    disp = get_disponibilidad_sku(sku, data)

    if disp.empty:
        return {"sku": sku, "rotacion": 0}

    total_stock = disp["stock"].astype(int).sum()
    rotacion = max(1, total_stock // 3)

    return {"sku": sku, "rotacion": rotacion}


# ---------------------------------------------------------------
# 7. FUNCIÓN AUXILIAR PARA JSON
# ---------------------------------------------------------------
def safe_json(texto):
    try:
        return json.loads(texto) if isinstance(texto, str) else texto
    except:
        return {}


# ===============================================================
#            API PÚBLICA DEL MÓDULO
# ===============================================================
def inventario_api():
    """Empaqueta funciones en un diccionario para agentes SRM."""
    data = load_data()

    return {
        "data": data,
        "get_inventario_por_empresa": lambda empresa_id: get_inventario_por_empresa(empresa_id, data),
        "get_disponibilidad_sku": lambda sku: get_disponibilidad_sku(sku, data),
        "scanner_query": lambda sku: scanner_query(sku, data),
        "matriz_disponibilidad": lambda sku: get_matriz_disponibilidad(sku, data),
        "rotacion_sku": lambda sku: get_rotacion_sku(sku, data),
        "proveedor_optimo": lambda sku: seleccionar_proveedor_optimo(sku, data)
    }


# ===============================================================
# TEST RÁPIDO
# ===============================================================
if __name__ == "__main__":
    api = inventario_api()

    print("=======================================")
    print("   TEST RÁPIDO — INVENTARIO 360°")
    print("=======================================")

    print("\n→ Consulta Escáner para SKU '00001':")
    print(api["scanner_query"]("00001"))

    print("\n→ Matriz disponibilidad '00001':")
    print(api["matriz_disponibilidad"]("00001"))

    print("\n→ Proveedor óptimo '00001':")
    print(api["proveedor_optimo"]("00001"))
