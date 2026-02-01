#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
===============================================================================
 SRM–QK–ADSI — GENERADOR JSON PARA LOVELY.DEV v1
 Produce para cada cliente:
  - catalogo_360.json
  - catalogo_rico.json
  - productos.json
  - metadata.json
  - ui_data.json
  - lovely_model_cliente_<cliente>.json (para lovable.dev)
===============================================================================
"""

import os
import json
import pandas as pd

BASE = r"C:\SRM_ADSI"

KB_FILE = os.path.join(BASE, r"03_knowledge_base\knowledge_base_unificada.csv")
JSON360_DIR = os.path.join(BASE, r"07_json_360")
LOVELY_DIR = os.path.join(BASE, r"08_lovely_models")
SRC_DIR = os.path.join(BASE, r"01_sources_originales")

CLIENTES = [
    "Bara", "DFG", "Duna", "Japan",
    "Kaiqi", "Leo", "Store", "Vaisand",
    "Yokomar"
]


def load_csv(client, fname):
    """
    Carga cualquier CSV desde 01_sources_originales/<cliente>
    con tolerancia a encoding.
    """
    path = os.path.join(SRC_DIR, client, fname)
    if not os.path.exists(path):
        print(f"⚠ {fname} no encontrado para {client}")
        return pd.DataFrame()

    try:
        return pd.read_csv(path)
    except:
        return pd.read_csv(path, encoding="latin1")


def load_json_safe(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def build_catalogo_360(cliente):
    """
    Carga el archivo 360 generado en el PASO 5.
    """
    path = os.path.join(JSON360_DIR, cliente, "catalogo_360.json")
    return load_json_safe(path)


def build_catalogo_rico(cliente, catalogo_360, cat_rico):
    """
    Une información: catálogo rico + catálogo 360.
    """
    m360 = {item["codigo"]: item for item in catalogo_360}

    enriquecido = []

    for _, row in cat_rico.iterrows():
        codigo = str(row.get("Identificacion_Repuesto", "")).strip()

        item360 = m360.get(codigo, {})

        enriched = {
            "codigo": codigo,
            "nombre": row.get("Nombre_Comercial_Catalogo", ""),
            "sistema": row.get("Sistema", ""),
            "subsistema": row.get("SubSistema", ""),
            "componente": row.get("Componente_Taxonomia", ""),
            "tags": row.get("Tags_Sugeridos", ""),
            "thumbnail": item360.get("thumbnail", ""),
            "frames_360": item360.get("frames", []),
            "descripcion_rica": row.get("Descripcion_Rica", row.get("Identificacion_Repuesto", "")),
        }

        enriquecido.append(enriched)

    return enriquecido


def build_productos(cliente, catalogo_rico):
    """
    Genera un listado mínimo para UI.
    """
    productos = []
    for item in catalogo_rico:
        productos.append({
            "codigo": item["codigo"],
            "nombre": item["nombre"],
            "thumbnail": item["thumbnail"],
            "sistema": item["sistema"],
            "subsistema": item["subsistema"],
            "componente": item["componente"],
            "tags": item["tags"]
        })
    return productos


def build_metadata(cliente, catalogo_rico):
    """
    Genera información de navegación y conteos.
    """
    sistemas = {}
    for item in catalogo_rico:
        sis = item.get("sistema", "")
        if sis not in sistemas:
            sistemas[sis] = 0
        sistemas[sis] += 1

    return {
        "cliente": cliente,
        "total_items": len(catalogo_rico),
        "conteo_por_sistema": sistemas
    }


def build_ui_data(cliente):
    """
    Base de datos para Lovely.dev con configuración de UI por cliente.
    """
    return {
        "cliente": cliente,
        "theme": {
            "primary_color": "#0A2F7B",
            "secondary_color": "#00B6C8",
            "accent_color": "#F4C542"
        },
        "modules": {
            "catalogo": True,
            "busqueda": True,
            "vista360": True,
            "shopify_connect": True
        }
    }


def build_lovely_model(cliente):
    """
    Modelo base para lovable.dev
    """
    return {
        "model_name": f"lovely_model_{cliente.lower()}_v1",
        "description": f"Modelo de UI/UX para la tienda {cliente} dentro del Mall Digital SRM.",
        "routes": [
            {"path": "/", "component": "Home"},
            {"path": "/catalogo", "component": "Catalogo"},
            {"path": "/producto/:id", "component": "ProductoDetalle"},
        ],
        "components": ["Navbar", "Footer", "CardProducto", "Viewer360"],
        "data_sources": {
            "catalogo_360": f"/07_json_360/{cliente}/catalogo_360.json",
            "catalogo_rico": f"/07_json_360/{cliente}/catalogo_rico.json",
            "productos": f"/07_json_360/{cliente}/productos.json",
            "metadata": f"/07_json_360/{cliente}/metadata.json",
        }
    }


def generar_para_cliente(cliente, df_kb):
    print(f"\n===================================================")
    print(f"▶ Generando JSON Lovely.dev para {cliente}")
    print("===================================================")

    # Crear carpeta destino
    out_dir = os.path.join(JSON360_DIR, cliente)
    ensure_dir(out_dir)

    # Cargar catálogo rico original
    cat_rico = load_csv(cliente, f"catalogo_imagenes_{cliente}.csv")

    # Catálogo 360 (ya generado)
    cat360 = build_catalogo_360(cliente)

    # Catálogo enriquecido
    catalogo_rico = build_catalogo_rico(cliente, cat360, cat_rico)

    # Listado de productos
    productos = build_productos(cliente, catalogo_rico)

    # Metadata
    metadata = build_metadata(cliente, catalogo_rico)

    # UI base
    ui_data = build_ui_data(cliente)

    # Guardar JSONs
    json.dump(cat360, open(os.path.join(out_dir, "catalogo_360.json"), "w", encoding="utf-8"), indent=4, ensure_ascii=False)
    json.dump(catalogo_rico, open(os.path.join(out_dir, "catalogo_rico.json"), "w", encoding="utf-8"), indent=4, ensure_ascii=False)
    json.dump(productos, open(os.path.join(out_dir, "productos.json"), "w", encoding="utf-8"), indent=4, ensure_ascii=False)
    json.dump(metadata, open(os.path.join(out_dir, "metadata.json"), "w", encoding="utf-8"), indent=4, ensure_ascii=False)
    json.dump(ui_data, open(os.path.join(out_dir, "ui_data.json"), "w", encoding="utf-8"), indent=4, ensure_ascii=False)

    # Crear lovely_model_client
    lovely_path = os.path.join(LOVELY_DIR, f"lovely_model_{cliente.lower()}_v1.json")
    json.dump(build_lovely_model(cliente), open(lovely_path, "w", encoding="utf-8"), indent=4, ensure_ascii=False)

    print(f"✔ JSONs generados para {cliente}")
    print(f" Carpeta → {out_dir}")
    print(f" Modelo Lovely.dev → {lovely_path}")


def main():
    print("\n===================================================")
    print("         SRM–QK–ADSI — GENERADOR JSON LOVELY v1")
    print("===================================================\n")

    df_kb = pd.read_csv(KB_FILE)

    for cliente in CLIENTES:
        generar_para_cliente(cliente, df_kb)

    print("\n===================================================")
    print("   ✔ PASO 7 COMPLETADO — JSONs OK para Lovely.dev")
    print("===================================================\n")


if __name__ == "__main__":
    main()
