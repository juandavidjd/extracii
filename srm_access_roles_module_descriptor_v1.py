# ================================================================
# SRM ACCESS ROLES MODULE DESCRIPTOR v1
# ================================================================
# Autor: SRM-QK-ADSI Engine
# Propósito:
#   - Definir los roles oficiales del ecosistema SRM 360°
#   - Definir permisos por módulo
#   - Exportar el descriptor para agentes, dashboards, UI Lovable,
#     Guided Tour, Shopify Sync, Systeme.io y Supabase RLS.
#
# Salida:
#   C:\SRM_ADSI\03_knowledge_base\config\roles_permisos_srm.json
# ================================================================

import os
import json

# ---------------------------------------------------------------
# RUTA DE SALIDA
# ---------------------------------------------------------------
OUTPUT_DIR = r"C:\SRM_ADSI\03_knowledge_base\config"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "roles_permisos_srm.json")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------------------------------------------------------
# DEFINICIÓN OFICIAL DE MÓDULOS SRM
# ---------------------------------------------------------------
MODULOS_SRM = [
    "catalogo_srm",
    "inventarios",
    "pedidos",
    "programa_flotas",
    "programa_moto_cliente",
    "stock_predictor",
    "redundancia_pedidos",
    "reportes_kpi",
    "scanner_srm",
    "panel_legal",
    "usuarios_roles",
    "academia_srm",
    "panel_srm"
]

# ---------------------------------------------------------------
# DEFINICIÓN DE ROLES SRM (v28)
# ---------------------------------------------------------------
ROLES_SRM = {
    "administrador_srm": {
        "descripcion": "Administrador general del ecosistema SRM",
        "modulos": MODULOS_SRM
    },

    "importador": {
        "descripcion": "Empresa importadora dentro del ecosistema",
        "modulos": [
            "catalogo_srm", "inventarios", "pedidos",
            "stock_predictor", "reportes_kpi",
            "scanner_srm", "redundancia_pedidos", "panel_legal",
            "academia_srm"
        ]
    },

    "distribuidor": {
        "descripcion": "Distribuidor mayorista",
        "modulos": [
            "catalogo_srm", "inventarios", "pedidos",
            "reportes_kpi", "scanner_srm", "academia_srm"
        ]
    },

    "almacen": {
        "descripcion": "Tienda o almacén minorista",
        "modulos": [
            "catalogo_srm", "inventarios", "pedidos",
            "scanner_srm", "programa_moto_cliente",
            "reportes_kpi", "academia_srm"
        ]
    },

    "taller": {
        "descripcion": "Taller de servicio o mecánico SRM",
        "modulos": [
            "catalogo_srm", "scanner_srm",
            "programa_moto_cliente", "reportes_kpi",
            "academia_srm"
        ]
    },

    "flota": {
        "descripcion": "Usuarios del Programa Flotas SRM",
        "modulos": [
            "programa_flotas", "scanner_srm",
            "reportes_kpi", "academia_srm"
        ]
    },

    "proveedor_srm": {
        "descripcion": "Proveedor que forma parte de la red de redundancia SRM",
        "modulos": [
            "inventarios", "redundancia_pedidos",
            "scanner_srm", "reportes_kpi"
        ]
    },

    "cliente_final": {
        "descripcion": "Usuario final SRM",
        "modulos": [
            "programa_moto_cliente", "scanner_srm", "academia_srm"
        ]
    },

    "invitado": {
        "descripcion": "Usuario con permisos mínimos",
        "modulos": [
            "catalogo_srm"
        ]
    }
}

# ---------------------------------------------------------------
# ENSAMBLE DEL DOCUMENTO FINAL
# ---------------------------------------------------------------
descriptor_final = {
    "version": "1.0",
    "descripcion": "Descriptor oficial de roles y permisos del ecosistema SRM 360°",
    "modulos": MODULOS_SRM,
    "roles": ROLES_SRM
}

# ---------------------------------------------------------------
# GUARDAR RESULTADO
# ---------------------------------------------------------------
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(descriptor_final, f, indent=4, ensure_ascii=False)

print("===================================================")
print(" ✔ SRM ROLES MODULE DESCRIPTOR generado correctamente")
print(f" ✔ Archivo: {OUTPUT_FILE}")
print("===================================================")
