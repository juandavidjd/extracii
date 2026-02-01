#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BUILD CATALOGO ARMOTOS — V2.0 NF
Robusto • Flexible • Produce catálogo limpio + imágenes asignadas

Entrada:
 - CATALOGONOVIEMBREV012025NF.html
 - ./images_nf/
 - Inventario_Cliente_NF_Local.csv
 - Inventario_Cliente_NF_Docx.csv

Salida:
 - Base_Datos_Catalogo_Armotos_NF.csv
 - FOTOS_COMPETENCIA_ARMOTOS_NF (carpeta limpia)
 - Reporte de auditoría
"""

import os
import re
import shutil
import pandas as pd
from bs4 import BeautifulSoup
from thefuzz import fuzz
from tqdm import tqdm

# =====================
# CONFIGURACIÓN
# =====================

BASE_DIR = r"C:\scrap"

HTML_FILE = os.path.join(BASE_DIR, "CATALOGONOVIEMBREV012025NF.html")
IMG_DIR = os.path.join(BASE_DIR, "images_nf")

INV_LOCAL = os.path.join(BASE_DIR, "Inventario_Cliente_NF_Local.csv")
INV_DOCX  = os.path.join(BASE_DIR, "Inventario_Cliente_NF_Docx.csv")

OUT_DB = os.path.join(BASE_DIR, "Base_Datos_Catalogo_Armotos_NF.csv")
OUT_IMG_DIR = os.path.join(BASE_DIR, "FOTOS_COMPETENCIA_ARMOTOS_NF")
AUDIT_FILE = os.path.join(BASE_DIR, "Audit_ARMOTOS_NF.txt")


# ===============================
# 1. ANALIZAR HTML ARMOTOS
# ===============================

def parse_html_rows(path):
    print("[1] Leyendo HTML principal...")

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    rows = []
    tables = soup.find_all("table")
    if not tables:
        print("   ❌ No se encontraron tablas en el HTML")
        return pd.DataFrame()

    for tbl in tables:
        trs = tbl.find_all("tr")
        for tr in trs:
            tds = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            if len(tds) >= 2:
                rows.append(tds)

    print(f"   ✔ Filas detectadas en HTML: {len(rows)}")

    # normalizar ancho
    max_cols = max(len(r) for r in rows)
    clean_rows = []
    for r in rows:
        if len(r) < max_cols:
            r = r + [""]*(max_cols-len(r))
        clean_rows.append(r)

    colnames = [f"col{i+1}" for i in range(max_cols)]
    return pd.DataFrame(clean_rows, columns=colnames)


# ===============================
# 2. INVENTARIOS FLEXIBLES
# ===============================

def load_inventarios():
    print("[2] Cargando inventarios oficiales (modo tolerante)...")

    def read_any_csv(path):
        rows = []
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # separador dinámico
                if ";" in line:
                    parts = [p.strip() for p in line.split(";")]
                elif "," in line:
                    parts = [p.strip() for p in line.split(",")]
                elif "\t" in line:
                    parts = [p.strip() for p in line.split("\t")]
                else:
                    parts = [line]

                rows.append(parts)

        max_cols = max(len(r) for r in rows)
        clean = []
        for r in rows:
            if len(r) < max_cols:
                r = r + [""]*(max_cols-len(r))
            clean.append(r)

        colnames = [f"col{i+1}" for i in range(max_cols)]
        return pd.DataFrame(clean, columns=colnames)

    df_local = read_any_csv(INV_LOCAL)
    df_docx  = read_any_csv(INV_DOCX)

    df = pd.concat([df_local, df_docx], ignore_index=True)

    df["codigo"] = ""
    df["descripcion"] = ""

    for idx, row in df.iterrows():
        posibles_cod = [row[c] for c in df.columns if re.search(r'cod|ref|sku', c, re.I)]
        posibles_desc = [row[c] for c in df.columns if re.search(r'desc|prod|nombre', c, re.I)]

        codigo = ""
        descripcion = ""

        # extraer código válido
        for c in posibles_cod:
            c = str(c).strip()
            if re.match(r"^[A-Za-z0-9\-\_\.]{3,}$", c):
                codigo = c
                break

        # descripción
        for d in posibles_desc:
            d = str(d).strip()
            if len(d) > 4:
                descripcion = d
                break

        # fallback descripción
        if not descripcion:
            descripcion = max([str(row[c]) for c in df.columns], key=lambda x: len(str(x)))

        df.at[idx, "codigo"] = codigo
        df.at[idx, "descripcion"] = descripcion

    print(f"   ✔ Filas limpias inventario total: {len(df)}")
    return df[["codigo", "descripcion"]]


# ===============================
# 3. ASIGNACIÓN DE IMÁGENES
# ===============================

def match_image(desc, img_list):
    desc_clean = re.sub(r"[^a-z0-9 ]", "", desc.lower())
    best_score = 0
    best_img = None

    for img in img_list:
        base = re.sub(r"[^a-z0-9 ]", "", img.lower())
        score = fuzz.token_set_ratio(desc_clean, base)

        if score > best_score:
            best_score = score
            best_img = img

    return best_img, best_score


# ===============================
# 4. PROCESO PRINCIPAL
# ===============================

def build_catalogo(df_html, df_inv):
    print("[3] Construyendo catálogo consolidado...")

    # crear directorio imágenes
    if os.path.exists(OUT_IMG_DIR):
        shutil.rmtree(OUT_IMG_DIR)
    os.makedirs(OUT_IMG_DIR, exist_ok=True)

    all_imgs = [f for f in os.listdir(IMG_DIR) if f.lower().endswith((".jpg",".png",".jpeg",".webp"))]

    productos = []
    audit_lines = []

    for idx, row in tqdm(df_html.iterrows(), total=len(df_html)):
        # obtener descripción desde HTML
        desc = ""
        for c in df_html.columns:
            if len(str(row[c])) > len(desc):
                desc = row[c]

        desc = desc.strip()
        if not desc or desc.lower() == "nan":
            continue

        # buscar referencia posible en inventario
        cod = ""
        best_score = 0

        for _, inv in df_inv.iterrows():
            score = fuzz.partial_ratio(desc.lower(), inv["descripcion"].lower())
            if score > best_score:
                best_score = score
                cod = inv["codigo"]

        # asignar imagen
        img_name, score_img = match_image(desc, all_imgs)

        img_out = ""
        if img_name:
            src = os.path.join(IMG_DIR, img_name)
            dst = os.path.join(OUT_IMG_DIR, img_name)
            try:
                shutil.copy2(src, dst)
                img_out = img_name
            except:
                pass

        productos.append({
            "codigo": cod,
            "descripcion": desc,
            "match_score_inv": best_score,
            "imagen": img_out,
            "match_score_img": score_img if img_name else 0
        })

        audit_lines.append(
            f"{cod}; {desc[:60]}; inv_score={best_score}; img={img_out}; img_score={score_img}"
        )

    pd.DataFrame(productos).to_csv(OUT_DB, index=False, encoding="utf-8-sig")

    with open(AUDIT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(audit_lines))

    print(f"   ✔ Catálogo Final: {OUT_DB}")
    print(f"   ✔ Imágenes asignadas: {OUT_IMG_DIR}")
    print(f"   ✔ Auditoría: {AUDIT_FILE}")


# ===============================
# EJECUCIÓN
# ===============================

print("=== BUILD CATALOGO ARMOTOS — V2.0 NF ===")

df_html = parse_html_rows(HTML_FILE)
df_inv  = load_inventarios()

build_catalogo(df_html, df_inv)

print("\n🎉 PROCESO COMPLETADO — Catálogo NF generado correctamente.")
