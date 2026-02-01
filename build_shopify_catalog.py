#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_shopify_catalog.py

Genera un catálogo Shopify unificando:
- Inventario Excel (CODIGO, DESCRIPCION, CATEGORIA, PRECIO, ...)
- HTMLs exportados (Tienda Kaiqi Parts ...1.html hasta ...7.html)
- Carpetas *_files con imágenes

Reglas:
- Incluye TODOS los ítems:
  * Match inventario ↔ HTML
  * SIN_MATCH_INVENTARIO (HTML sin match): se agregan con CODIGO = SIN_CODIGO
  * INVENTARIO_NO_LISTADO_HTML (inventario sin HTML): se agregan con placeholder NO-DISPONIBLE.png
- Renombra físicamente imágenes en carpetas *_files al nombre normalizado Imagen_renombrada

Convención de renombrado:
- Espacios → "-"
- Acentos → eliminados (ASCII) / Ñ→N
- "/" → "-"
- "+" → "-"
- Paréntesis → eliminados
- Todo en MAYÚSCULAS
- Extensión fija ".png"

Salidas:
- catalogo_shopify.xlsx  (hojas: catalogo, log_inconsistencias, resumen)
- catalogo_shopify.csv
- log_inconsistencias.csv

Uso:
    python build_shopify_catalog.py --root "C:\\sqk\\html_pages" --inventario "Inventario Kaiqi.xlsx" --fuzzy 90

Dependencias:
    pip install pandas openpyxl beautifulsoup4 lxml unidecode rapidfuzz
"""

import argparse
import csv
import os
import re
import sys
import urllib.parse
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
from bs4 import BeautifulSoup
from unidecode import unidecode
from rapidfuzz import fuzz, process

CLOUDINARY_BASE_URL = "https://res.cloudinary.com/dhegu1fzm/image/upload"


# -----------------------------
# Normalización y utilitarios
# -----------------------------
def normalize_text_for_match(s: str) -> str:
    """Normaliza texto para matching (alineado a convención, tolerante a HTML)."""
    if s is None:
        return ""
    s = unidecode(str(s)).upper().strip()
    s = s.replace(" / ", "/").replace("/", "-").replace("+", "-").replace("\\", "-")
    s = re.sub(r"[()]", "", s)
    s = re.sub(r"[\s_]+", " ", s)
    s = re.sub(r"[^A-Z0-9\- ]+", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_image_basename(desc: str) -> str:
    """Convierte una descripción en nombre de archivo PNG según la convención."""
    base = unidecode(str(desc or "")).upper().strip()
    base = base.replace(" / ", "/").replace("/", "-").replace("+", "-").replace("\\", "-")
    base = re.sub(r"[()]", "", base)
    base = re.sub(r"[\s_]+", "-", base)
    base = re.sub(r"[^A-Z0-9\-]", "", base)
    base = re.sub(r"-{2,}", "-", base).strip("-")
    return f"{base or 'NO-DISPONIBLE'}.png"


def best_local_image_name_from_src(src: str) -> str:
    """Obtiene el basename de una ruta/URL de imagen."""
    if not src:
        return ""
    try:
        path = urllib.parse.urlparse(src).path
        return os.path.basename(path)
    except Exception:
        return os.path.basename(src)


def find_image_in_files_folders(root: Path, filename: str) -> Optional[Path]:
    """Localiza la imagen en cualquier subcarpeta *_files dentro de root (case-insensitive)."""
    if not filename:
        return None
    for folder in root.glob("*_files"):
        cand = folder / filename
        if cand.exists():
            return cand
        # búsqueda case-insensitive
        for f in folder.iterdir():
            if f.is_file() and f.name.lower() == filename.lower():
                return f
    return None


# -----------------------------
# Parseo de HTMLs
# -----------------------------
def discover_html_files(root: Path) -> List[Path]:
    patterns = [
        "Tienda _ Kaiqi Parts - Partes y Accesorios para Motocargueros y Motos en Villavicencio*.html",
        "Tienda*Kaiqi*.html",
        "*.html",
    ]
    hits: List[Path] = []
    for pat in patterns:
        hits.extend(sorted(root.glob(pat)))
    # deduplicación preservando orden
    seen = set()
    ordered = []
    for h in hits:
        if h not in seen:
            ordered.append(h)
            seen.add(h)
    return ordered


def parse_products_from_html(html_path: Path) -> List[Dict]:
    """
    Extrae productos de páginas (WooCommerce/tema variado):
    - título (nombre/descripcion visible)
    - imagen (basename local si está referenciada)
    """
    products: List[Dict] = []
    try:
        html = html_path.read_text(encoding="utf-8", errors="ignore")
    except UnicodeDecodeError:
        html = html_path.read_text(encoding="latin-1", errors="ignore")

    soup = BeautifulSoup(html, "lxml")

    # múltiples selectores para robustez
    candidates = soup.select("li.product, .df-product-outer-wrap, .product-small, .product-inner, .product-item")
    if not candidates:
        # fallback genérico
        candidates = soup.find_all(True, class_=lambda c: c and ("product" in c or "df-product" in c))

    def extract_one(tag) -> Optional[Dict]:
        title_el = tag.select_one(
            ".woocommerce-loop-product__title, .product-title a, .product-title, h2, h3, h4, .title, .name, a"
        )
        title = title_el.get_text(" ", strip=True) if title_el else tag.get_text(" ", strip=True)

        img_el = tag.select_one("img")
        img_src = ""
        if img_el:
            img_src = img_el.get("src") or img_el.get("data-src") or ""
            if not img_src and img_el.get("srcset"):
                img_src = img_el["srcset"].split(",")[0].strip().split(" ")[0]
        local_img = best_local_image_name_from_src(img_src) if img_src else ""

        if not title and not img_src:
            return None

        return {
            "html_file": html_path.name,
            "title": title.strip(),
            "img_src": img_src.strip(),
            "img_local": local_img.strip(),
        }

    for c in candidates:
        d = extract_one(c)
        if d and d["title"]:
            products.append(d)

    return products


# -----------------------------
# Inventario
# -----------------------------
def read_inventory(inv_path: Path) -> pd.DataFrame:
    """Lee el Excel del inventario y estandariza columnas esperadas."""
    try:
        df = pd.read_excel(inv_path)
    except Exception as e:
        print(f"[ERROR] Al leer el Excel: {e}")
        sys.exit(1)

    # Estandarizar nombres de columnas
    df.columns = df.columns.str.strip().str.upper().str.replace(r"\s+", "_", regex=True)

    # Mapear posibles columnas
    if "CODIGO" not in df.columns and "CODIGO_NEW" in df.columns:
        df["CODIGO"] = df["CODIGO_NEW"]
    if "PRECIO" not in df.columns:
        if "PRECIO_SIN_IVA" in df.columns:
            df["PRECIO"] = df["PRECIO_SIN_IVA"]
        elif "PRECIO_SIN_IVA_RAW" in df.columns:
            df["PRECIO"] = df["PRECIO_SIN_IVA_RAW"]
        else:
            df["PRECIO"] = ""

    for col in ["CODIGO", "DESCRIPCION", "CATEGORIA", "PRECIO"]:
        if col not in df.columns:
            df[col] = ""

    df["DESC_NORM"] = df["DESCRIPCION"].astype(str).map(normalize_text_for_match)
    # Eliminar duplicados por descripción normalizada (primer aparición)
    df = df.drop_duplicates(subset=["DESC_NORM"], keep="first").copy()

    return df


# -----------------------------
# Renombrado físico de imágenes
# -----------------------------
def rename_images_on_disk(root: Path, df_catalogo: pd.DataFrame) -> List[Dict]:
    """
    Renombra físicamente las imágenes en las carpetas *_files
    según la columna Imagen_renombrada. Devuelve lista de eventos de log.
    """
    events: List[Dict] = []
    # Trabajar sobre copia deduplicada por (Imagen_local, Imagen_renombrada) para evitar colisiones
    df = (
        df_catalogo[["Imagen_local", "Imagen_renombrada"]]
        .dropna()
        .drop_duplicates()
    )

    for _, row in df.iterrows():
        orig = str(row["Imagen_local"]).strip()
        new = str(row["Imagen_renombrada"]).strip()
        if not orig or not new:
            continue

        found = find_image_in_files_folders(root, orig)
        if not found or not found.exists():
            events.append({
                "tipo": "RENAME_ERROR",
                "detalle": "Ruta física no encontrada en índice.",
                "Original_Name": orig,
                "New_Name": new,
            })
            continue

        target = found.parent / new
        try:
            # Evitar sobreescritura si ya existe con el nombre nuevo
            if target.exists():
                # Si ya existe, damos por renombrado OK (probablemente corridas previas)
                events.append({
                    "tipo": "RENAME_ALREADY_EXISTS",
                    "detalle": "Destino ya existía, se mantiene.",
                    "Original_Name": str(found),
                    "New_Name": str(target),
                })
            else:
                shutil.move(str(found), str(target))
                events.append({
                    "tipo": "RENAME_SUCCESS",
                    "detalle": "Renombrado exitoso.",
                    "Original_Name": str(found),
                    "New_Name": str(target),
                })
        except Exception as e:
            events.append({
                "tipo": "RENAME_ERROR",
                "detalle": f"Error renombrando: {e}",
                "Original_Name": str(found),
                "New_Name": str(target),
            })

    return events


# -----------------------------
# Matching (incluye SIN_MATCH + INVENTARIO_NO_LISTADO)
# -----------------------------
def match_products(
    parsed_products: List[Dict],
    inv_df: pd.DataFrame,
    fuzzy_threshold: float = 90,
    root: Optional[Path] = None
) -> Tuple[pd.DataFrame, List[Dict]]:
    """
    Une productos HTML con inventario:
    - Match exacto por DESC_NORM; si falla, fuzzy (token_set_ratio).
    - Genera nombre de imagen renombrada y URL Cloudinary.
    - Valida existencia física de imagen en *_files (solo para log).
    - Incluye SIN_MATCH_INVENTARIO y INVENTARIO_NO_LISTADO_HTML en el catálogo final.
    """
    inconsistencias: List[Dict] = []
    inv_map = inv_df.set_index("DESC_NORM")
    all_descs = inv_df["DESC_NORM"].tolist()
    rows = []
    seen_pairs = set()  # (CODIGO, Imagen_renombrada)

    # Desduplicar HTML por título normalizado + imagen local
    df_parsed = pd.DataFrame(parsed_products)
    if df_parsed.empty:
        inconsistencias.append({"tipo": "SIN_HTML", "detalle": "No se encontraron productos en los HTMLs."})
        return pd.DataFrame(), inconsistencias

    df_parsed["DESC_NORM_HTML"] = df_parsed["title"].map(normalize_text_for_match)
    df_parsed = df_parsed.drop_duplicates(subset=["DESC_NORM_HTML", "img_local"], keep="first")

    # 1) Recorrer HTMLs y agregar filas (match o SIN_MATCH)
    for _, p in df_parsed.iterrows():
        raw_title = (p.get("title") or "").strip()
        desc_norm_html = p["DESC_NORM_HTML"]

        # Intento exacto
        score = 0.0
        matched_key = None
        match_row = None
        if desc_norm_html in inv_map.index:
            matched_key = desc_norm_html
            match_row = inv_map.loc[matched_key]
            score = 100.0
        else:
            # Fuzzy
            best = process.extractOne(desc_norm_html, all_descs, scorer=fuzz.token_set_ratio)
            if best and best[1] >= fuzzy_threshold:
                matched_key = best[0]
                match_row = inv_map.loc[matched_key]
                score = float(best[1])

        if match_row is None:
            # SIN_MATCH_INVENTARIO → agregar igual con CODIGO= SIN_CODIGO
            img_renombrada = normalize_image_basename(raw_title)
            rows.append({
                "CODIGO": "SIN_CODIGO",
                "DESCRIPCION": raw_title,
                "CATEGORIA": "",
                "PRECIO": "",
                "Imagen_local": p.get("img_local", ""),
                "Imagen_renombrada": img_renombrada,
                "Imagen_URL": f"{CLOUDINARY_BASE_URL}/{urllib.parse.quote(img_renombrada)}",
                "MATCH_SCORE": 0,
                "DESC_NORM_HTML": desc_norm_html,
                "DESC_NORM_INV": "",
                "HTML_ORIGEN": p.get("html_file"),
            })
            inconsistencias.append({
                "tipo": "SIN_MATCH_INVENTARIO",
                "detalle": "Agregado al catálogo con CODIGO= SIN_CODIGO.",
                "html_file": p.get("html_file"),
                "HTML_DESCRIPCION": raw_title,
                "DESC_NORM_HTML": desc_norm_html,
                "Imagen_local": p.get("img_local", ""),
            })
            continue

        if isinstance(match_row, pd.DataFrame) and len(match_row) > 1:
            match_row = match_row.iloc[0]

        codigo = (match_row.get("CODIGO") or "")
        categoria = (match_row.get("CATEGORIA") or "")
        precio = match_row.get("PRECIO")
        descr_inv = match_row.get("DESCRIPCION") or raw_title

        # Validación imagen para log
        img_local = p.get("img_local") or ""
        if root is not None and img_local:
            if find_image_in_files_folders(root, img_local) is None:
                inconsistencias.append({
                    "tipo": "IMAGEN_NO_ENCONTRADA_FISICAMENTE",
                    "detalle": f"La imagen '{img_local}' citada en HTML no se encontró en *_files.",
                    "codigo": codigo,
                    "titulo_html": raw_title,
                })

        # Imagen renombrada y URL Cloudinary (usar DESCRIPCION del inventario)
        img_renombrada = normalize_image_basename(descr_inv)
        img_url = f"{CLOUDINARY_BASE_URL}/{urllib.parse.quote(img_renombrada)}"

        # Unicidad
        key_pair = (str(codigo), img_renombrada)
        if key_pair in seen_pairs:
            inconsistencias.append({
                "tipo": "DUPLICADO_SALIDA",
                "detalle": "Mismo CODIGO y misma Imagen_renombrada ya emitidos; se omitió la fila duplicada.",
                "codigo": codigo,
                "descripcion": descr_inv,
                "imagen_renombrada": img_renombrada,
            })
            continue
        seen_pairs.add(key_pair)

        rows.append({
            "CODIGO": codigo,
            "DESCRIPCION": descr_inv,
            "CATEGORIA": categoria,
            "PRECIO": precio,
            "Imagen_local": img_local,
            "Imagen_renombrada": img_renombrada,
            "Imagen_URL": img_url,
            "MATCH_SCORE": score,
            "DESC_NORM_HTML": desc_norm_html,
            "DESC_NORM_INV": matched_key or "",
            "HTML_ORIGEN": p.get("html_file"),
        })

    df_out = pd.DataFrame(rows).drop_duplicates()

    # 2) Inventario no listado en HTML → agregar con placeholder
    inv_norm_set = set(inv_df["DESC_NORM"])
    matched_norms = set(df_out["DESC_NORM_INV"].astype(str))
    missing_in_html = inv_norm_set - matched_norms

    if missing_in_html:
        miss_df = inv_df[inv_df["DESC_NORM"].isin(missing_in_html)].drop_duplicates(subset=["CODIGO", "DESCRIPCION"])
        for _, r in miss_df.iterrows():
            descr = r.get("DESCRIPCION", "")
            codigo = r.get("CODIGO", "")
            df_out = pd.concat([
                df_out,
                pd.DataFrame([{
                    "CODIGO": codigo,
                    "DESCRIPCION": descr,
                    "CATEGORIA": r.get("CATEGORIA", ""),
                    "PRECIO": r.get("PRECIO", ""),
                    "Imagen_local": "",
                    "Imagen_renombrada": "NO-DISPONIBLE.png",
                    "Imagen_URL": f"{CLOUDINARY_BASE_URL}/NO-DISPONIBLE.png",
                    "MATCH_SCORE": 0,
                    "DESC_NORM_HTML": "",
                    "DESC_NORM_INV": r.get("DESC_NORM", ""),
                    "HTML_ORIGEN": "",
                }])
            ], ignore_index=True)
            inconsistencias.append({
                "tipo": "INVENTARIO_NO_LISTADO_HTML",
                "detalle": "Agregado al catálogo con imagen placeholder NO-DISPONIBLE.png.",
                "codigo": codigo,
                "descripcion": descr,
            })

    return df_out, inconsistencias


# -----------------------------
# Flujo principal
# -----------------------------
def main():
    parser = argparse.ArgumentParser(description="Genera catálogo Shopify desde inventario + HTMLs + imágenes locales, incluyendo SIN_MATCH e INVENTARIO_NO_LISTADO con placeholder.")
    parser.add_argument("--root", type=str, required=True, help="Carpeta raíz (Excel, HTMLs y carpetas *_files)")
    parser.add_argument("--inventario", type=str, default="Inventario Kaiqi.xlsx", help="Nombre del Excel de inventario")
    parser.add_argument("--out", type=str, default="catalogo_shopify.xlsx", help="Nombre de salida Excel")
    parser.add_argument("--csv", type=str, default="catalogo_shopify.csv", help="Nombre de salida CSV")
    parser.add_argument("--fuzzy", type=float, default=90, help="Umbral de similitud fuzzy (0-100)")
    parser.add_argument("--rename", action="store_true", help="Si se pasa, renombra físicamente imágenes en *_files al nombre normalizado.")
    args = parser.parse_args()

    root = Path(args.root).expanduser()
    inv_path = root / args.inventario

    print(f"--- INICIO DE CATALOGACIÓN EN {root} ---")

    if not root.exists() or not inv_path.exists():
        if not root.exists():
            print(f"[ERROR] Carpeta raíz no encontrada: {root}")
        if not inv_path.exists():
            print(f"[ERROR] Excel de inventario no encontrado: {inv_path}")
        sys.exit(1)

    # 1. Leer inventario
    inv_df = read_inventory(inv_path)

    # 2. Descubrir/parsear HTMLs
    html_files = discover_html_files(root)
    if not html_files:
        print("[ADVERTENCIA] No se encontraron HTMLs de tienda en la carpeta.", file=sys.stderr)

    parsed: List[Dict] = []
    for h in html_files:
        try:
            parsed.extend(parse_products_from_html(h))
        except Exception as e:
            print(f"[WARN] No se pudo procesar {h.name}: {e}", file=sys.stderr)

    print(f"-> Productos únicos en Inventario: {len(inv_df)}")
    print(f"-> Productos extraídos de HTML: {len(parsed)}")

    # 3. Matching (incluye SIN_MATCH e INVENTARIO_NO_LISTADO con placeholder)
    df_out, inconsist = match_products(parsed, inv_df, fuzzy_threshold=args.fuzzy, root=root)

    # 4. Columnas finales (incluimos campos de auditoría)
    keep_cols = [
        "CODIGO","DESCRIPCION","CATEGORIA","PRECIO",
        "Imagen_local","Imagen_renombrada","Imagen_URL",
        "MATCH_SCORE","DESC_NORM_HTML","DESC_NORM_INV","HTML_ORIGEN"
    ]
    df_out = df_out.reindex(columns=keep_cols)

    # 5. Renombrado físico (opcional con --rename)
    rename_events: List[Dict] = []
    if args.rename:
        print("[INFO] Renombrando imágenes en disco (carpetas *_files)...")
        rename_events = rename_images_on_disk(root, df_out)
        # Agregar eventos de renombrado al log de inconsistencias
        inconsist.extend(rename_events)

    # 6. Resumen por categoría (opcional)
    resumen = pd.DataFrame()
    if not df_out.empty:
        resumen = (
            df_out.groupby(["CATEGORIA"], dropna=False)
                  .size()
                  .reset_index(name="conteo")
                  .sort_values("conteo", ascending=False)
        )

    # 7. Guardar salidas
    out_excel = root / args.out
    out_csv = root / args.csv
    log_csv = root / "log_inconsistencias.csv"

    with pd.ExcelWriter(out_excel, engine="openpyxl") as writer:
        df_out.to_excel(writer, index=False, sheet_name="catalogo")
        pd.DataFrame(inconsist).to_excel(writer, index=False, sheet_name="log_inconsistencias")
        if not resumen.empty:
            resumen.to_excel(writer, index=False, sheet_name="resumen")

    df_out.to_csv(out_csv, index=False, encoding="utf-8", quoting=csv.QUOTE_MINIMAL)
    pd.DataFrame(inconsist).to_csv(log_csv, index=False, encoding="utf-8", quoting=csv.QUOTE_MINIMAL)

    print(f"\n[OK] Catálogo (Excel): {out_excel}")
    print(f"[OK] Catálogo (CSV):  {out_csv}")
    print(f"[OK] Log de Inconsistencias: {log_csv}")
    if args.rename:
        renamed_ok = sum(1 for e in rename_events if e["tipo"].startswith("RENAME_SUCCESS"))
        renamed_err = sum(1 for e in rename_events if e["tipo"].startswith("RENAME_ERROR"))
        print(f"[INFO] Renombrados OK: {renamed_ok} | Errores de renombrado: {renamed_err}")
    print("\n⚠️ Sube tus imágenes a Cloudinary usando EXACTAMENTE el nombre 'Imagen_renombrada'.")
    print("Si usaste --rename, las imágenes locales ya coinciden con esos nombres en las carpetas *_files.")


if __name__ == "__main__":
    main()
