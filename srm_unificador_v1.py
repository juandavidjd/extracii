#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SRM–QK–ADSI — UNIFICADOR UNIVERSAL v1
-------------------------------------
Procesa todos los extract_<cliente>.csv generados por el EXTRACTOR v1.
Estandariza la información, limpia texto, separa entidades y construye:

1) unificado_<cliente>.csv   → dataset limpio por cliente
2) knowledge_base_unificada.csv → súper base enriquecida para IA y Matching

Totalmente robusto, tolerante a errores, no se rompe aunque el input sea irregular.
"""

import os
import re
import pandas as pd
from collections import defaultdict

BASE_DIR = r"C:\img\EXTRACT"
SALIDA_DIR = os.path.join(BASE_DIR, "UNIFICADO")
os.makedirs(SALIDA_DIR, exist_ok=True)

# Clientes
CLIENTES = [
    "Bara","DFG","Duna","Japan","Kaiqi",
    "Leo","Store","Vaisand","Yokomar"
]

# ============================================================
# UTILIDADES
# ============================================================

def clean(x):
    if not isinstance(x, str):
        return ""
    x = x.replace("\n"," ").replace("\r"," ")
    x = re.sub(r"\s+"," ", x).strip()
    return x

def normalizar_contenido(text):
    """
    Limpieza profunda del contenido extraído.
    """
    if not text:
        return ""

    t = clean(text)

    # eliminar caracteres basura
    t = re.sub(r"[^\w\s\-\./()]+", " ", t)

    # quitar múltiple espacios
    t = re.sub(r"\s+", " ", t)

    return t.strip()


def detectar_tipo_linea(t):
    """
    Clasifica la línea extraída:
    - IMAGEN (tiene nombre de archivo típico)
    - SKU/REF/CÓDIGO
    - DESCRIPCIÓN
    - TÉRMINOS TÉCNICOS
    """

    t_low = t.lower()

    if any(ext in t_low for ext in [".jpg",".png",".jpeg",".webp"]):
        return "IMAGEN"

    if re.search(r"\b\d{3,7}\b", t):
        return "CODIGO"

    if len(t) >= 5:
        return "DESCRIPCION"

    return "OTRO"


def enriquecer(text):
    """
    Extrae tokens útiles del texto.
    """
    tokens = re.findall(r"[A-Za-z0-9\-]+", text)
    tokens = [tok.upper() for tok in tokens]
    return " ".join(tokens)


# ============================================================
# PROCESO PRINCIPAL
# ============================================================

def procesar_cliente(cliente):
    in_file = os.path.join(BASE_DIR, f"extract_{cliente}.csv")

    if not os.path.exists(in_file):
        print(f"⚠ No existe: {in_file}")
        return pd.DataFrame()

    print(f"\n▶ Procesando {cliente}...")

    df = pd.read_csv(in_file, encoding="utf-8", errors="ignore")
    df = df.fillna("")
    df["CONTENIDO"] = df["CONTENIDO"].apply(normalizar_contenido)

    datos = []
    kb = []

    # Estructura por registro
    for _, row in df.iterrows():
        content = row["CONTENIDO"]
        tipo = detectar_tipo_linea(content)
        tokens = enriquecer(content)

        datos.append({
            "CLIENTE": cliente,
            "FUENTE": row["FUENTE"],
            "ORIGEN_TIPO": row["ORIGEN_TIPO"],
            "TIPO_LINEA": tipo,
            "TEXTO": content,
            "TOKENS": tokens
        })

        kb.append({
            "CLIENTE": cliente,
            "TEXTO": content,
            "TOKENS": tokens,
            "TIPO_LINEA": tipo
        })

    # Exportar por cliente
    df_cliente = pd.DataFrame(datos)
    out_cli = os.path.join(SALIDA_DIR, f"unificado_{cliente}.csv")
    df_cliente.to_csv(out_cli, index=False, encoding="utf-8-sig")

    print(f"  → OK: {out_cli} ({len(df_cliente)} filas)")

    return pd.DataFrame(kb)


def main():
    print("\n=== SRM UNIFICADOR UNIVERSAL v1 ===\n")

    all_kb = []

    for c in CLIENTES:
        df_k = procesar_cliente(c)
        if not df_k.empty:
            all_kb.append(df_k)

    # Construcción Knowledge Base Global
    if all_kb:
        kb_global = pd.concat(all_kb, ignore_index=True)

        # eliminamos duplicados globales
        kb_global = kb_global.drop_duplicates(subset=["TEXTO"])

        out_kb = os.path.join(SALIDA_DIR, "knowledge_base_unificada.csv")
        kb_global.to_csv(out_kb, index=False, encoding="utf-8-sig")

        print(f"\n📘 Knowledge Base global creada: {out_kb}")
        print(f"   Total líneas útiles: {len(kb_global)}")

    print("\n=== FINALIZADO ===\n")


if __name__ == "__main__":
    main()

