#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_shopify_catalog.py
--------------------------------------------------
Genera un catálogo limpio para Shopify uniendo:
- Inventario Excel (CODIGO, DESCRIPCION, CATEGORIA, PRECIO/PRECIO SIN IVA, ...)
- HTMLs exportados (Tienda Kaiqi Parts ...1.html hasta ...7.html)
- Carpetas *_files con imágenes

Características:
- Scraping real con BeautifulSoup (tolerante a distintas plantillas WooCommerce/WordPress).
- Normalización y fuzzy matching con RapidFuzz (token_set_ratio).
- Convención estricta de nombres de imagen:
  * MAYÚSCULAS sin acentos
  * Espacios → '-'
  * '/' y '+' → '-'
  * Paréntesis eliminados
  * Extensión fija ".png"
- Verificación de imágenes locales (warning si faltan en *_files)
- Logs de inconsistencias y conteos
- Salidas: Excel (3 hojas), CSV del catálogo y CSV del log

Uso típico (Windows):
    python build_shopify_catalog.py --root "C:\\sqk\\html_pages" --inventario "Inventario Kaiqi.xlsx" --sheet "Inventario" --fuzzy 90

Requisitos:
    pip install pandas openpyxl beautifulsoup4 lxml unidecode rapidfuzz
"""

import argparse
import csv
import os
import re
import sys
import json
import glob
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
from bs4 import BeautifulSoup
from unidecode import unidecode
from rapidfuzz import fuzz, process


CLOUDINARY_BASE = "https://res.cloudinary.com/dhegu1fzm/image/upload"

# -----------------------------
# Normalización
# -----------------------------

def normalize_text_for_match(s: str) -> str:
    """Normaliza texto para matching flexible (no para nombres de archivo)."""
    if s is None:
        return ""
    s = unidecode(str(s)).upper().strip()
    s = s.replace(" / ", "/")
    s = s.replace("/", "-").replace("+", "-").replace("\\", "-")
    s = re.sub(r"[()]", "", s)
    s = re.sub(r"[\s_]+", " ", s)
    s = re.sub(r"[^A-Z0-9\- ]+", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def normalize_image_basename(desc: str) -> str:
    """Convención rígida para renombrado de imágenes (extensión fija .png)."""
    if not desc:
        return "SIN-DESCRIPCION.png"
    base = unidecode(str(desc)).upper().strip()
    base = base.replace(" / ", "/").replace("/", "-").replace("+", "-").replace("\\", "-")
    base = re.sub(r"[()]", "", base)
    base = re.sub(r"[\s_]+", "-", base)            # espacios → '-'
    base = re.sub(r"[^A-Z0-9\-]", "", base)        # sólo letras, números y '-'
    base = re.sub(r"-{2,}", "-", base).strip("-")  # colapsar guiones
    return (base if base else "SIN-DESCRIPCION") + ".png"

def basename_from_src(src: str) -> str:
    """Obtiene basename de una ruta/URL de imagen, sin querystring."""
    if not src:
        return ""
    src = src.split("?")[0]
    src = src.replace("\\", "/")
    return os.path.basename(src)

# -----------------------------
# HTML parsing
# -----------------------------

def discover_html_files(root: Path) -> List[Path]:
    """Descubre archivos HTML de la tienda en el root."""
    pats = [
        "Tienda *Kaiqi* *.html",
        "Tienda*Kaiqi*.html",
        "Tienda _ Kaiqi Parts*.html",
        "*.html",
    ]
    hits: List[Path] = []
    for p in pats:
        hits.extend(sorted(root.glob(p)))
    # dedup preservando orden
    seen, ordered = set(), []
    for h in hits:
        if h not in seen:
            ordered.append(h)
            seen.add(h)
    return ordered

def parse_products_from_html(html_path: Path) -> List[Dict]:
    """Extrae pares (descripción, imagen_local) de un HTML de tienda."""
    prods: List[Dict] = []
    try:
        html = html_path.read_text(encoding="utf-8", errors="ignore")
    except UnicodeDecodeError:
        html = html_path.read_text(encoding="latin-1", errors="ignore")

    soup = BeautifulSoup(html, "lxml")

    # Candidatos frecuentes de WooCommerce / themes
    candidates = soup.select("li.product")
    if not candidates:
        candidates = soup.select("div.product, div.product-small, div.product-inner, div.product-item, div.product-card")

    def extract_one(tag) -> Optional[Dict]:
        """Extrae descripción y src de imagen de un contenedor de producto."""
        title_el = tag.select_one(".woocommerce-loop-product__title") or \
                           tag.select_one(".product-title a") or \
                           tag.select_one(".product-title") or \
                           tag.select_one("h2, h3, h4, .title, .name")
        title = title_el.get_text(" ", strip=True) if title_el else ""

        img_el = tag.select_one("img")
        img_src = ""
        if img_el:
            img_src = img_el.get("src") or img_el.get("data-src") or ""
            if not img_src and img_el.get("srcset"):
                img_src = img_el["srcset"].split(",")[0].strip().split(" ")[0]
        img_local = basename_from_src(img_src) if img_src else ""

        if not title and not img_local:
            return None

        return {
            "HTML_FILE": html_path.name,
            "HTML_DESCRIPCION": title.strip(),
            "Imagen_local": img_local,
        }

    for c in candidates:
        row = extract_one(c)
        if row:
            prods.append(row)

    # Fallback simple: tarjetas con <img> y texto cercano
    if not prods:
        for a in soup.select("a, div"):
            img = a.find("img")
            if img:
                txt = a.get_text(" ", strip=True)
                src = img.get("src") or img.get("data-src") or ""
                if txt:
                    prods.append({
                        "HTML_FILE": html_path.name,
                        "HTML_DESCRIPCION": txt,
                        "Imagen_local": basename_from_src(src),
                    })
    return prods

# -----------------------------
# Imágenes locales
# -----------------------------

def index_local_images(root: Path) -> Dict[str, str]:
    """Indexa todas las imágenes dentro de carpetas *_files -> {basename: fullpath}."""
    idx: Dict[str, str] = {}
    for folder in root.glob("*_files"):
        for dirpath, _, files in os.walk(folder):
            for f in files:
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                    full = os.path.join(dirpath, f)
                    idx[f] = full
    return idx

# -----------------------------
# Inventario
# -----------------------------

EXPECTED_COLS = [
    "CODIGO", "CODIGO NEW", "DESCRIPCION", "CATEGORIA", "CATEGORIA_NORM",
    "SISTEMA PRINCIPAL", "SUBSISTEMA", "COMPONENTE", "TIPO VEHICULO",
    "PREFIJO_BASE", "PRECIO", "PRECIO SIN IVA", "PRECIO SIN IVA RAW"
]

def load_inventory(inv_path: Path, sheet_name: Optional[str]) -> pd.DataFrame:
    """Carga Excel y añade columna de normalización para matching."""
    if sheet_name:
        df = pd.read_excel(inv_path, sheet_name=sheet_name, dtype=str)
    else:
        df = pd.read_excel(inv_path, dtype=str)

    # Normalizar nombres de columnas
    df.columns = [c.strip() for c in df.columns]

    # Asegurar columnas esperadas (si no existen, crearlas vacías)
    for col in EXPECTED_COLS:
        if col not in df.columns:
            df[col] = ""

    # Compatibilidad: algunas hojas usan "PRECIO SIN IVA" como precio base
    if "PRECIO" not in df.columns or (df["PRECIO"] == "").all():
        if "PRECIO SIN IVA" in df.columns:
            df["PRECIO"] = df["PRECIO SIN IVA"]

    if "DESCRIPCION" not in df.columns:
        raise ValueError("El inventario no contiene la columna 'DESCRIPCION'.")

    df["DESC_NORM_INV"] = df["DESCRIPCION"].map(normalize_text_for_match)
    # Eliminar duplicados por descripción normalizada (primer aparición)
    df = df.drop_duplicates(subset=["DESC_NORM_INV"], keep="first").copy()

    return df

# -----------------------------
# Matching
# -----------------------------

def fuzzy_match_desc(query_norm: str, candidates: List[str], threshold: int = 90) -> Tuple[Optional[str], float]:
    """Devuelve la mejor coincidencia >= umbral usando RapidFuzz token_set_ratio."""
    if not query_norm:
        return None, 0.0
    best = process.extractOne(query_norm, candidates, scorer=fuzz.token_set_ratio)
    if best and best[1] >= threshold:
        return best[0], float(best[1])
    return None, 0.0

def match_html_to_inventory(df_html: pd.DataFrame, df_inv: pd.DataFrame, fuzzy_threshold: int) -> Tuple[pd.DataFrame, List[Dict]]:
    """
    Hace matching HTML → inventario por descripción normalizada:
    - Primero exacto; si falla, fuzzy (token_set_ratio).
    - Devuelve df con columnas del inventario + HTML + score, y lista de inconsistencias.
    """
    inconsistencias: List[Dict] = []

    # Normalizaciones
    df_html = df_html.copy()
    df_html["DESC_NORM_HTML"] = df_html["HTML_DESCRIPCION"].map(normalize_text_for_match)

    # Desduplicar HTML por descripción normalizada antes de iterar (evita procesamiento redundante)
    df_html_unique = df_html.drop_duplicates(subset=["DESC_NORM_HTML", "Imagen_local"], keep="first")

    inv_index = df_inv.set_index("DESC_NORM_INV")
    inv_descs = df_inv["DESC_NORM_INV"].tolist()

    rows = []
    for _, h in df_html_unique.iterrows():
        desc_norm = h["DESC_NORM_HTML"]
        img_local = h.get("Imagen_local", "")
        html_file = h.get("HTML_FILE", "")

        matched_row = None
        score = 0.0
        matched_key = ""

        # Exacto
        if desc_norm in inv_index.index:
            mr = inv_index.loc[desc_norm]
            if isinstance(mr, pd.DataFrame):
                mr = mr.iloc[0]
            matched_row = mr
            score = 100.0
            matched_key = desc_norm
        else:
            # Fuzzy
            key, score = fuzzy_match_desc(desc_norm, inv_descs, threshold=fuzzy_threshold)
            if key:
                mr = inv_index.loc[key]
                if isinstance(mr, pd.DataFrame):
                    mr = mr.iloc[0]
                matched_row = mr
                matched_key = key

        if matched_row is None:
            inconsistencias.append({
                "tipo": "SIN_MATCH_INVENTARIO",
                "HTML_FILE": html_file,
                "HTML_DESCRIPCION": h["HTML_DESCRIPCION"],
                "DESC_NORM_HTML": desc_norm,
                "Imagen_local": img_local
            })
            continue

        # Construcción de fila de salida
        # Usamos la DESCRIPCION del inventario para el renombrado (fuente maestra)
        desc_maestra = matched_row.get("DESCRIPCION", h["HTML_DESCRIPCION"])
        img_ren = normalize_image_basename(desc_maestra)
        img_url = f"{CLOUDINARY_BASE}/{urllib.parse.quote(img_ren)}"

        row = {
            # Inventario principal
            **matched_row.to_dict(),

            # Enriquecimiento de HTML/imagen
            "Imagen_local": img_local,
            "Imagen_renombrada": img_ren,
            "Imagen_URL": img_url,
            "HTML_ORIGEN": html_file,

            # Auditoría matching
            "MATCH_SCORE": score,
            "DESC_NORM_HTML": desc_norm,
            "DESC_NORM_INV": matched_key,
        }
        rows.append(row)

    return pd.DataFrame(rows), inconsistencias

# -----------------------------
# Pipeline
# -----------------------------

def build_pipeline(root: Path, inv_file: str, sheet_name: Optional[str], out_xlsx: str, out_csv: str, fuzzy_threshold: int) -> Tuple[pd.DataFrame, List[Dict]]:
    # 1) Inventario
    inv_path = root / inv_file
    if not inv_path.exists():
        raise FileNotFoundError(f"No se encuentra el inventario en: {inv_path}")

    df_inv = load_inventory(inv_path, sheet_name)

    # 2) HTMLs
    html_files = discover_html_files(root)
    parsed: List[Dict] = []
    for h in html_files:
        parsed.extend(parse_products_from_html(h))
    df_html = pd.DataFrame(parsed, columns=["HTML_FILE", "HTML_DESCRIPCION", "Imagen_local"])

    # 3) Index imágenes (para validar presencia física)
    img_index = index_local_images(root)

    # 4) Matching
    df_out, inconsistencias = match_html_to_inventory(df_html, df_inv, fuzzy_threshold=fuzzy_threshold)

    # 4.1) Señalar imágenes faltantes físicamente (solo si hubo match exitoso)
    for _, r in df_out.iterrows():
        img = r.get("Imagen_local", "")
        if img and img not in img_index:
            inconsistencias.append({
                "tipo": "SIN_IMAGEN_LOCAL",
                "detalle": "El nombre existe en HTML pero no se encontró físicamente en *_files.",
                "Imagen_local": img,
                "CODIGO": r.get("CODIGO", ""),
            })
        if not img:
             inconsistencias.append({
                "tipo": "HTML_SIN_IMAGEN",
                "detalle": "El producto en HTML no tenía IMG detectable.",
                "CODIGO": r.get("CODIGO", ""),
                "DESCRIPCION": r.get("DESCRIPCION", ""),
             })


    # 4.2) Inventario no listado en HTML
    inv_norm_set = set(df_inv["DESC_NORM_INV"])
    matched_norms = set(df_out["DESC_NORM_INV"].astype(str))
    missing_in_html = inv_norm_set - matched_norms
    if missing_in_html:
        miss_df = df_inv[df_inv["DESC_NORM_INV"].isin(missing_in_html)]
        for _, r in miss_df.iterrows():
            inconsistencias.append({
                "tipo": "INVENTARIO_NO_LISTADO_HTML",
                "CODIGO": r.get("CODIGO", ""),
                "DESCRIPCION": r.get("DESCRIPCION", ""),
            })

    # 5) Unicidad por (CODIGO, Imagen_renombrada) y reporte de duplicados de salida
    seen = set()
    filtered_rows = []
    for _, row in df_out.iterrows():
        key = (str(row.get("CODIGO", "")), row.get("Imagen_renombrada", ""))
        if key not in seen:
            seen.add(key)
            filtered_rows.append(row)
        else:
             inconsistencias.append({
                "tipo": "DUPLICADO_SALIDA",
                "CODIGO": row.get("CODIGO", ""),
                "Imagen_renombrada": row.get("Imagen_renombrada", ""),
                "HTML_ORIGEN": row.get("HTML_ORIGEN", ""),
             })

    df_out = pd.DataFrame(filtered_rows) if filtered_rows else df_out.drop_duplicates(subset=["CODIGO", "Imagen_renombrada"])

    # 6) Orden columnas
    keep_cols = [
        "CODIGO","CODIGO NEW","DESCRIPCION","CATEGORIA","CATEGORIA_NORM",
        "SISTEMA PRINCIPAL","SUBSISTEMA","COMPONENTE","TIPO VEHICULO",
        "PREFIJO_BASE","PRECIO","PRECIO SIN IVA","PRECIO SIN IVA RAW",
        "Imagen_local","Imagen_renombrada","Imagen_URL","HTML_ORIGEN",
        "MATCH_SCORE","DESC_NORM_HTML","DESC_NORM_INV"
    ]
    df_out = df_out.reindex(columns=[c for c in keep_cols if c in df_out.columns])

    # 7) Guardar salidas
    out_xlsx_path = root / out_xlsx
    out_csv_path = root / out_csv
    log_csv_path = root / "log_inconsistencias.csv"
    img_index_json = root / "image_index.json"

    # Preparar resumen para hoja Excel
    resumen = pd.DataFrame()
    if not df_out.empty:
         resumen = (
            df_out.groupby(["CATEGORIA"], dropna=False)
            .size()
            .reset_index(name="conteo")
            .sort_values("conteo", ascending=False)
        )

    with pd.ExcelWriter(out_xlsx_path, engine="openpyxl") as writer:
        df_out.to_excel(writer, index=False, sheet_name="catalogo")
        pd.DataFrame(inconsistencias).to_excel(writer, index=False, sheet_name="log_inconsistencias")
        if not resumen.empty:
            resumen.to_excel(writer, index=False, sheet_name="resumen")

    df_out.to_csv(out_csv_path, index=False, encoding="utf-8", quoting=csv.QUOTE_MINIMAL)
    pd.DataFrame(inconsistencias).to_csv(log_csv_path, index=False, encoding="utf-8", quoting=csv.QUOTE_MINIMAL)

    with open(img_index_json, "w", encoding="utf-8") as jf:
        json.dump(index_local_images(root), jf, ensure_ascii=False, indent=2)

    return df_out, inconsistencias

# -----------------------------
# CLI
# -----------------------------

def main():
    parser = argparse.ArgumentParser(description="Genera catálogo Shopify (inventario + HTMLs + imágenes locales)")
    parser.add_argument("--root", type=str, required=True, help="Carpeta raíz con Excel + HTMLs + *_files")
    parser.add_argument("--inventario", type=str, default="Inventario Kaiqi.xlsx", help="Nombre del archivo Excel")
    parser.add_argument("--sheet", type=str, default=None, help="Nombre de la hoja de Excel (opcional)")
    parser.add_argument("--out", type=str, default="catalogo_shopify.xlsx", help="Excel de salida")
    parser.add_argument("--csv", type=str, default="catalogo_shopify.csv", help="CSV de salida")
    parser.add_argument("--fuzzy", type=int, default=90, help="Umbral fuzzy 0-100 (RapidFuzz token_set_ratio)")
    args = parser.parse_args()

    root = Path(args.root).expanduser()
    print(f"--- INICIO DE CATALOGACIÓN EN {root} ---")

    try:
        df_out, inconsist = build_pipeline(
            root=root,
            inv_file=args.inventario,
            sheet_name=args.sheet,
            out_xlsx=args.out,
            out_csv=args.csv,
            fuzzy_threshold=args.fuzzy
        )
        print(f"\n[OK] Catálogo (Excel): {root / args.out}")
        print(f"[OK] Catálogo (CSV):  {root / args.csv}")
        print(f"[OK] Log de Inconsistencias: {root / 'log_inconsistencias.csv'}")
        print(f"[OK] Mapa de imágenes: {root / 'image_index.json'}")
        print("Recuerda subir tus imágenes a Cloudinary con EXACTAMENTE el nombre de 'Imagen_renombrada'.")
    except FileNotFoundError as e:
        print(f"\n[ERROR CRÍTICO] Archivo no encontrado: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR CRÍTICO] Fallo general: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()