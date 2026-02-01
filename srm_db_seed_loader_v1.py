# ================================================================
# SRM DATABASE SEED LOADER v1
# ================================================================
# Autor: SRM-QK-ADSI Engine
# Descripción:
#   Genera archivos seed CSV para cargar datos iniciales
#   en Supabase/PostgreSQL.
#
# Genera:
#   seed_empresas.csv
#   seed_usuarios.csv
#   seed_productos_srm.csv
#   seed_inventarios.csv
#
# Ubicación de salida:
#   C:\SRM_ADSI\05_pipeline\sql\seeds\
# ================================================================

import os
import pandas as pd

# ================================================================
# RUTAS
# ================================================================
INPUT_DIR = r"C:\SRM_ADSI\02_cleaned_normalized"
OUTPUT_DIR = r"C:\SRM_ADSI\05_pipeline\sql\seeds"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Archivos que intentará leer (ajustables según tu pipeline)
PRODUCTOS_FILE = os.path.join(INPUT_DIR, "catalogo_unificado.csv")
INVENTARIOS_FILE = os.path.join(INPUT_DIR, "inventarios_unificados.csv")
EMPRESAS_FILE = os.path.join(INPUT_DIR, "empresas.csv")       # Opcional
USUARIOS_FILE = os.path.join(INPUT_DIR, "usuarios.csv")       # Opcional


# ================================================================
# FUNCIONES AUXILIARES
# ================================================================
def safe_read_csv(path):
    """Lee CSV si existe, si no genera dataframe vacío."""
    if os.path.exists(path):
        try:
            return pd.read_csv(path, dtype=str, encoding="utf-8", on_bad_lines="skip")
        except:
            return pd.read_csv(path, dtype=str, encoding="latin1", on_bad_lines="skip")
    else:
        print(f"[ADVERTENCIA] No se encontró el archivo: {path}")
        return pd.DataFrame()


def export_seed(df, name):
    """Exporta seed limpio."""
    out = os.path.join(OUTPUT_DIR, name)
    df.to_csv(out, index=False, encoding="utf-8")
    print(f"✔ Seed generado: {out}")


# ================================================================
# 1. SEED: EMPRESAS SRM
# ================================================================
def build_seed_empresas():
    df_emp = safe_read_csv(EMPRESAS_FILE)

    # Si no hay archivo de empresas, generamos una base mínima
    if df_emp.empty:
        df_emp = pd.DataFrame([
            {"id": 1, "nombre": "SRM Interno", "tipo": "srminterno"},
            {"id": 2, "nombre": "Importadora DFG", "tipo": "importador"},
            {"id": 3, "nombre": "Bara Importaciones", "tipo": "importador"},
            {"id": 4, "nombre": "Duna S.A.S.", "tipo": "importador"},
            {"id": 5, "nombre": "Vaisand", "tipo": "importador"},
            {"id": 6, "nombre": "Carguero Store", "tipo": "distribuidor"},
            {"id": 7, "nombre": "Kaiqi Parts", "tipo": "importador"},
            {"id": 8, "nombre": "Yokomar + KNT", "tipo": "importador"},
            {"id": 9, "nombre": "Industrias Japan", "tipo": "importador"},
            {"id": 10, "nombre": "Industrias Leo", "tipo": "fabricante"}
        ])

    df_emp.drop_duplicates(subset=["nombre"], inplace=True)
    export_seed(df_emp, "seed_empresas.csv")
    return df_emp


# ================================================================
# 2. SEED: USUARIOS SRM
# ================================================================
def build_seed_usuarios(df_emp):
    df_usr = safe_read_csv(USUARIOS_FILE)

    # Base mínima si no existe archivo de usuarios
    if df_usr.empty:
        df_usr = pd.DataFrame([
            {"id": 1, "empresa_id": 1, "nombre": "Administrador SRM",
             "email": "admin@srm.com", "telefono": "", "rol_id": 1}
        ])

    # Validación
    df_usr["empresa_id"] = df_usr["empresa_id"].astype(int)
    export_seed(df_usr, "seed_usuarios.csv")
    return df_usr


# ================================================================
# 3. SEED: PRODUCTOS SRM
# ================================================================
def build_seed_productos():
    df_prod = safe_read_csv(PRODUCTOS_FILE)

    if df_prod.empty:
        print("⚠ No se pudo generar seed_productos_srm.csv — no hay catálogo.")
        return pd.DataFrame()

    # Normalización de columnas
    columnas_mapeo = {
        "SKU": "sku",
        "sku": "sku",
        "codigo": "sku",
        "CODIGO_NEW": "sku",
        "DESCRIPCION": "nombre",
        "nombre": "nombre",
        "NOMBRE": "nombre",
        "categoria": "categoria",
        "Categoria": "categoria",
        "SISTEMA PRINCIPAL": "sistema",
        "SUBSISTEMA": "subsistema",
        "fitment_json": "fitment_json",
        "Fitment_JSON": "fitment_json"
    }

    df_prod = df_prod.rename(columns=lambda c: columnas_mapeo.get(c, c))

    # Selección final de columnas válidas
    cols_finales = ["sku", "nombre", "categoria", "sistema", "subsistema", "fitment_json"]
    for col in cols_finales:
        if col not in df_prod.columns:
            df_prod[col] = ""

    df_prod = df_prod[cols_finales].drop_duplicates(subset=["sku"])
    export_seed(df_prod, "seed_productos_srm.csv")
    return df_prod


# ================================================================
# 4. SEED: INVENTARIOS POR EMPRESA
# ================================================================
def build_seed_inventarios(df_prod, df_emp):
    df_inv = safe_read_csv(INVENTARIOS_FILE)

    if df_inv.empty:
        # Inventario mínimo para pruebas
        sample = df_prod.head(20)
        inventario_base = []
        for _, row in sample.iterrows():
            inventario_base.append({
                "empresa_id": 1,   # SRM Interno
                "sku": row["sku"],
                "stock": 5,
                "costo": "",
                "precio_venta": ""
            })
        df_inv = pd.DataFrame(inventario_base)

    # Normalización de columnas
    columnas_mapeo = {
        "Empresa": "empresa_id",
        "empresa_id": "empresa_id",
        "SKU": "sku",
        "sku": "sku",
        "stock": "stock",
        "STOCK": "stock",
        "COSTO": "costo",
        "precio": "precio_venta"
    }

    df_inv = df_inv.rename(columns=lambda c: columnas_mapeo.get(c, c))

    cols_finales = ["empresa_id", "sku", "stock", "costo", "precio_venta"]
    for col in cols_finales:
        if col not in df_inv.columns:
            df_inv[col] = ""

    df_inv = df_inv[cols_finales]

    export_seed(df_inv, "seed_inventarios.csv")
    return df_inv


# ================================================================
# MAIN
# ================================================================
def main():
    print("===============================================")
    print("        SRM SEED LOADER v1 — INICIO")
    print("===============================================")

    df_emp = build_seed_empresas()
    df_usr = build_seed_usuarios(df_emp)
    df_prod = build_seed_productos()
    df_inv = build_seed_inventarios(df_prod, df_emp)

    print("===============================================")
    print(" ✔ SEEDS GENERADOS CORRECTAMENTE")
    print(f" ✔ Ruta: {OUTPUT_DIR}")
    print("===============================================")


if __name__ == "__main__":
    main()
