# ================================================================
# SRM DATABASE SCHEMA INITIALIZER v1
# ================================================================
# Autor: SRM-QK-ADSI Engine
# Descripción:
#    Genera el archivo SQL oficial del esquema SRM v1
#    recomendado para Supabase/PostgreSQL.
#
# Ubicación de salida:
#    C:\SRM_ADSI\05_pipeline\sql\srm_schema_v1.sql
#
# Basado en:
#   - Funciones + Programas + Base de Datos Relacionales Vivas.pdf
#   - Pipeline SRM-QK-ADSI v28
#   - Inventario 360°
#   - Programas SRM (Flotas, MotoCliente, StockPredictor, Redundancia)
# ================================================================

import os

OUTPUT_PATH = r"C:\SRM_ADSI\05_pipeline\sql"
OUTPUT_FILE = os.path.join(OUTPUT_PATH, "srm_schema_v1.sql")

# ================================================================
# SQL — Esquema SRM
# ================================================================

SQL_SCHEMA = r"""
-- ================================================================
-- SRM DATABASE SCHEMA v1 — Supabase/PostgreSQL
-- ================================================================
-- Estructura oficial del ecosistema SRM-QK-ADSI
-- Basado en el documento "Funciones + Programas + BD Relacionales Vivas"
-- ================================================================

CREATE SCHEMA IF NOT EXISTS srm;

-- ================================================================
-- 1. EMPRESAS / CLIENTES SRM
-- ================================================================
CREATE TABLE IF NOT EXISTS srm.empresas (
    id            SERIAL PRIMARY KEY,
    nombre        TEXT NOT NULL,
    tipo          TEXT CHECK (tipo IN ('importador','distribuidor','almacen','taller','flota','proveedor','srminterno')),
    nit           TEXT,
    telefono      TEXT,
    email         TEXT,
    ciudad        TEXT,
    direccion     TEXT,
    fecha_registro TIMESTAMP DEFAULT NOW()
);

-- ================================================================
-- 2. USUARIOS + ROLES
-- ================================================================
CREATE TABLE IF NOT EXISTS srm.roles (
    id        SERIAL PRIMARY KEY,
    nombre    TEXT UNIQUE,
    descripcion TEXT
);

CREATE TABLE IF NOT EXISTS srm.usuarios (
    id              SERIAL PRIMARY KEY,
    empresa_id      INT REFERENCES srm.empresas(id),
    nombre          TEXT NOT NULL,
    email           TEXT UNIQUE,
    telefono        TEXT,
    rol_id          INT REFERENCES srm.roles(id),
    activo          BOOLEAN DEFAULT TRUE,
    fecha_registro  TIMESTAMP DEFAULT NOW()
);

-- ================================================================
-- 3. CATÁLOGO SRM UNIFICADO
-- ================================================================
CREATE TABLE IF NOT EXISTS srm.productos_srm (
    id               SERIAL PRIMARY KEY,
    sku              TEXT UNIQUE,
    nombre           TEXT,
    descripcion      TEXT,
    categoria        TEXT,
    subsistema       TEXT,
    sistema          TEXT,
    oem_codes        TEXT,
    fitment_json     JSONB,
    marca_original   TEXT,
    imagen_url       TEXT,
    fecha_actualizacion TIMESTAMP DEFAULT NOW()
);

-- ================================================================
-- 4. INVENTARIOS POR EMPRESA
-- ================================================================
CREATE TABLE IF NOT EXISTS srm.inventarios_empresa (
    id            SERIAL PRIMARY KEY,
    empresa_id    INT REFERENCES srm.empresas(id),
    sku           TEXT REFERENCES srm.productos_srm(sku),
    stock         INT DEFAULT 0,
    costo         NUMERIC,
    precio_venta  NUMERIC,
    actualizado_en TIMESTAMP DEFAULT NOW()
);

-- ================================================================
-- 5. PEDIDOS
-- ================================================================
CREATE TABLE IF NOT EXISTS srm.pedidos (
    id            SERIAL PRIMARY KEY,
    empresa_id    INT REFERENCES srm.empresas(id),
    usuario_id    INT REFERENCES srm.usuarios(id),
    fecha         TIMESTAMP DEFAULT NOW(),
    estado        TEXT CHECK (estado IN ('pendiente','confirmado','procesando','completado','cancelado')),
    origen        TEXT CHECK (origen IN ('shopify','whatsapp','audio','lovable','manual'))
);

CREATE TABLE IF NOT EXISTS srm.pedidos_items (
    id          SERIAL PRIMARY KEY,
    pedido_id   INT REFERENCES srm.pedidos(id),
    sku         TEXT REFERENCES srm.productos_srm(sku),
    cantidad    INT,
    precio      NUMERIC
);

-- ================================================================
-- 6. BITÁCORA TÉCNICA (360°)
-- ================================================================
CREATE TABLE IF NOT EXISTS srm.bitacora_tecnica (
    id              SERIAL PRIMARY KEY,
    empresa_id      INT REFERENCES srm.empresas(id),
    usuario_id      INT REFERENCES srm.usuarios(id),
    sku             TEXT REFERENCES srm.productos_srm(sku),
    descripcion     TEXT,
    metadata        JSONB,
    fecha           TIMESTAMP DEFAULT NOW()
);

-- ================================================================
-- 7. AUDITORÍA SRM
-- ================================================================
CREATE TABLE IF NOT EXISTS srm.auditoria (
    id            SERIAL PRIMARY KEY,
    modulo        TEXT,
    usuario_id    INT REFERENCES srm.usuarios(id),
    descripcion   TEXT,
    datos         JSONB,
    fecha         TIMESTAMP DEFAULT NOW()
);

-- ================================================================
-- 8. PROGRAMA SRM — FLOTA 360°
-- ================================================================
CREATE TABLE IF NOT EXISTS srm.flotas_motos (
    id              SERIAL PRIMARY KEY,
    empresa_id      INT REFERENCES srm.empresas(id),
    placa           TEXT UNIQUE,
    marca_modelo    TEXT,
    cilindraje      TEXT,
    fecha_registro  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS srm.flotas_mantenimientos (
    id              SERIAL PRIMARY KEY,
    moto_id         INT REFERENCES srm.flotas_motos(id),
    descripcion     TEXT,
    repuestos_json  JSONB,
    fecha           TIMESTAMP DEFAULT NOW()
);

-- ================================================================
-- 9. PROGRAMA SRM — EL CLIENTE REGISTRA SU MOTO
-- ================================================================
CREATE TABLE IF NOT EXISTS srm.motos_cliente (
    id              SERIAL PRIMARY KEY,
    usuario_id      INT REFERENCES srm.usuarios(id),
    placa           TEXT,
    marca_modelo    TEXT,
    cilindraje      TEXT,
    ano             INT,
    fecha_registro  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS srm.motos_historial (
    id              SERIAL PRIMARY KEY,
    moto_id         INT REFERENCES srm.motos_cliente(id),
    descripcion     TEXT,
    repuestos_json  JSONB,
    fecha           TIMESTAMP DEFAULT NOW()
);

-- ================================================================
-- 10. PROGRAMA SRM — PREDICTOR DE STOCK
-- ================================================================
CREATE TABLE IF NOT EXISTS srm.stock_predicciones (
    id              SERIAL PRIMARY KEY,
    empresa_id      INT REFERENCES srm.empresas(id),
    sku             TEXT REFERENCES srm.productos_srm(sku),
    demanda_predicha NUMERIC,
    fecha_prediccion TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS srm.stock_alertas (
    id              SERIAL PRIMARY KEY,
    empresa_id      INT REFERENCES srm.empresas(id),
    sku             TEXT REFERENCES srm.productos_srm(sku),
    tipo_alerta     TEXT,
    fecha           TIMESTAMP DEFAULT NOW()
);

-- ================================================================
-- 11. PROGRAMA SRM — REDUNDANCIA AUTOMÁTICA DE PEDIDOS
-- ================================================================
CREATE TABLE IF NOT EXISTS srm.proveedores_srm (
    id              SERIAL PRIMARY KEY,
    empresa_id      INT REFERENCES srm.empresas(id),
    nombre          TEXT,
    tiempo_entrega  INT,
    costo_logistico NUMERIC
);

CREATE TABLE IF NOT EXISTS srm.proveedores_srm_inventario (
    id            SERIAL PRIMARY KEY,
    proveedor_id  INT REFERENCES srm.proveedores_srm(id),
    sku           TEXT REFERENCES srm.productos_srm(sku),
    stock         INT
);

-- ================================================================
-- FIN DEL ESQUEMA SRM v1
-- ================================================================
"""


# ================================================================
# GENERADOR DEL ARCHIVO
# ================================================================
def main():
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(SQL_SCHEMA)

    print("===============================================")
    print(" ✔ SRM SCHEMA v1 generado correctamente")
    print(f" ✔ Archivo: {OUTPUT_FILE}")
    print("===============================================")


if __name__ == "__main__":
    main()
