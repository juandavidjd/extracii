#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
================================================================================
 🚀 GENERADOR TAXONOMÍA SRM–QK–ADSI v1 (CSV + JSON)
================================================================================
Este script crea:
 - C:\img\Taxonomia_SRM_QK_ADSI_v1.csv
 - C:\img\Taxonomia_SRM_QK_ADSI_v1.json

SIN simulación.
SIN rutas invisibles.
SIN dependencias externas más allá de pandas.

Autor: Juan David + ADSI
Fecha: 2025-12-01
================================================================================
"""

import os
import json
import pandas as pd

# -------------------------------------------------------------------------
# 1. Definir ruta base
# -------------------------------------------------------------------------
BASE = r"C:\img"
os.makedirs(BASE, exist_ok=True)

CSV_PATH  = os.path.join(BASE, "Taxonomia_SRM_QK_ADSI_v1.csv")
JSON_PATH = os.path.join(BASE, "Taxonomia_SRM_QK_ADSI_v1.json")

# -------------------------------------------------------------------------
# 2. TAXONOMÍA SRM–QK–ADSI v1 (ESTRUCTURADA)
# -------------------------------------------------------------------------

TAXONOMIA = [
    # ===================== SISTEMA ELÉCTRICO =====================
    ["Sistema Eléctrico", "Encendido", "Bobina de Encendido", "bobina-encendido"],
    ["Sistema Eléctrico", "Encendido", "CDI / Unidad de Control", "cdi-unidad-control"],
    ["Sistema Eléctrico", "Encendido", "Bujía", "bujia"],
    ["Sistema Eléctrico", "Cargador", "Regulador / Rectificador", "regulador-rectificador"],
    ["Sistema Eléctrico", "Cargador", "Bobina de Luces", "bobina-luces"],
    ["Sistema Eléctrico", "Arranque", "Relay de Arranque", "relay-arranque"],
    ["Sistema Eléctrico", "Arranque", "Motor de Arranque", "motor-arranque"],
    ["Sistema Eléctrico", "Instrumentación", "Velocímetro / Tacómetro", "velocimetro-tacometro"],
    ["Sistema Eléctrico", "Iluminación", "Farola / Stop", "farola-stop"],
    ["Sistema Eléctrico", "Iluminación", "Direccionales", "direccionales"],

    # ===================== SISTEMA MOTOR =====================
    ["Sistema Motor", "Cigüeñal", "Balinera Cigüeñal", "balinera-ciguenal"],
    ["Sistema Motor", "Cigüeñal", "Biela", "biela"],
    ["Sistema Motor", "Cilindro", "Kit Cilindro", "kit-cilindro"],
    ["Sistema Motor", "Cilindro", "Pistón", "piston"],
    ["Sistema Motor", "Culata", "Válvulas", "valvulas"],
    ["Sistema Motor", "Culata", "Arbol de Levas", "arbol-levas"],
    ["Sistema Motor", "Lubricación", "Bomba de Aceite", "bomba-aceite"],

    # ===================== SISTEMA FRENOS =====================
    ["Sistema Frenos", "Disco", "Pastillas de Freno", "pastillas-freno"],
    ["Sistema Frenos", "Tambor", "Bandas de Freno", "bandas-freno"],
    ["Sistema Frenos", "Hidráulico", "Bomba de Freno", "bomba-freno"],
    ["Sistema Frenos", "Hidráulico", "Caliper", "caliper"],

    # ===================== SISTEMA SUSPENSIÓN =====================
    ["Sistema Suspensión", "Delantera", "Tijera / Horquilla", "tijera-horquilla"],
    ["Sistema Suspensión", "Trasera", "Amortiguador", "amortiguador"],
    ["Sistema Suspensión", "Dirección", "Tijas / Rodamientos", "tijas-rodamientos"],

    # ===================== SISTEMA TRANSMISIÓN =====================
    ["Sistema Transmisión", "Cadena", "Kit Arrastre", "kit-arrastre"],
    ["Sistema Transmisión", "Caja Cambios", "Engranaje", "engranaje"],
    ["Sistema Transmisión", "Clutch", "Discos de Clutch", "discos-clutch"],
    ["Sistema Transmisión", "Clutch", "Guaya de Clutch", "guaya-clutch"],

    # ===================== CARROCERÍA =====================
    ["Sistema Carrocería", "Carena", "Faro Delantero", "faro-delantero"],
    ["Sistema Carrocería", "Carena", "Stop Trasero", "stop-trasero"],
    ["Sistema Carrocería", "Asiento", "Sillín", "sillin"],
    ["Sistema Carrocería", "Guardabarros", "Guardabarro Delantero", "guardabarro-delantero"],
    ["Sistema Carrocería", "Guardabarros", "Guardabarro Trasero", "guardabarro-trasero"],

    # ===================== COMBUSTIBLE =====================
    ["Sistema Combustible", "Carburación", "Carburador", "carburador"],
    ["Sistema Combustible", "Carburación", "Flotador Carburador", "flotador-carburador"],
    ["Sistema Combustible", "Inyección", "Inyector", "inyector"],
    ["Sistema Combustible", "Inyección", "Bomba de Gasolina", "bomba-gasolina"],

    # ===================== AIRE / FILTRACIÓN =====================
    ["Sistema Aire", "Filtro", "Filtro de Aire", "filtro-aire"],
    ["Sistema Aire", "Filtro", "Caja Filtro", "caja-filtro"],

    # ===================== ESCAPE =====================
    ["Sistema Escape", "Silenciador", "Mofle Completo", "mofle-completo"],
    ["Sistema Escape", "Silenciador", "Puntera de Escape", "puntera-escape"],

    # ===================== CHASIS =====================
    ["Sistema Chasis", "Estructura", "Chasis", "chasis"],
    ["Sistema Chasis", "Estructura", "Soportes Metálicos", "soportes-metalicos"],
]

# -------------------------------------------------------------------------
# 3. Crear DataFrame
# -------------------------------------------------------------------------
df = pd.DataFrame(TAXONOMIA, columns=["SISTEMA", "SUBSISTEMA", "COMPONENTE", "SLUG_SEO"])

# -------------------------------------------------------------------------
# 4. Guardar CSV y JSON
# -------------------------------------------------------------------------
df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(df.to_dict(orient="records"), f, ensure_ascii=False, indent=4)

# -------------------------------------------------------------------------
# 5. Confirmación
# -------------------------------------------------------------------------
print("✅ Taxonomía generada con éxito")
print("CSV guardado en:", CSV_PATH)
print("JSON guardado en:", JSON_PATH)
