#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Loterías 4D regionales -> data\crudo\{loteria}.csv
Header: fecha,numero,serie

Este scraper sirve como plantilla. Configura URL/parse por lotería.
Si no puede parsear, NO toca el CSV correspondiente.
"""
import argparse, re
from pathlib import Path
from scraper_utils import mk_session, fetch, soupify, read_csv_dict, write_csv_dict, merge_unique, log

# Configura fuentes por lotería
# Pon URLs reales y selectores por tabla/fila/columnas
SOURCES = {
    "boyaca":   {"url": "https://loteria-boyaca.example/resultados"},
    "huila":    {"url": "https://loteria-huila.example/resultados"},
    "manizales":{"url": "https://loteria-manizales.example/resultados"},
    "medellin": {"url": "https://loteria-medellin.example/resultados"},
    "quindio":  {"url": "https://loteria-quindio.example/resultados"},
    "tolima":   {"url": "https://loteria-tolima.example/resultados"},
}

SEL_ROW = ["table tr", ".tabla tr", ".resultados tr"]
# Para cada fila, intenta extraer en orden
SEL_FECHA = ["td.fecha",".fecha","time"]
SEL_NUMERO = ["td.numero",".numero"]
SEL_SERIE = ["td.serie",".serie"]

def pick_text(row, selectors):
    for s in selectors:
        el = row.select_one(s)
        if el:
            t = el.get_text(" ", strip=True)
            if t: return t
    return None

def parse_rows(html):
    soup = soupify(html)
    out=[]
    for sel in SEL_ROW:
        for tr in soup.select(sel):
            fecha = pick_text(tr, SEL_FECHA)
            numero = pick_text(tr, SEL_NUMERO)
            serie = pick_text(tr, SEL_SERIE)
            if fecha and numero:
                out.append({"fecha": fecha, "numero": numero, "serie": serie or ""})
    return out

def run_one(lot_key, outdir, session):
    cfg = SOURCES.get(lot_key, {})
    url = cfg.get("url")
    out = outdir / f"{lot_key}.csv"
    headers, existing = read_csv_dict(out)
    if not headers:
        headers = ["fecha","numero","serie"]

    if not url or "example" in url:
        log(f"[INFO] {lot_key}: sin URL configurada. No-op.")
        write_csv_dict(out, existing, headers)
        return

    try:
        html = fetch(session, url)
        rows = parse_rows(html)
        if not rows:
            log(f"[INFO] {lot_key}: sin nuevos registros.")
            write_csv_dict(out, existing, headers)
            return
        merged = merge_unique(existing, rows, key_tuple=("fecha","numero"))
        write_csv_dict(out, merged, headers)
        log(f"[OK ] {lot_key}: +{len(merged)-len(existing)} nuevas / total {len(merged)}")
    except Exception as e:
        log(f"[WARN] {lot_key} fallo: {e}. CSV intacto.")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--only", nargs="*", default=None, help="Ej: --only boyaca medellin")
    args = ap.parse_args()

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    session = mk_session()

    keys = args.only if args.only else list(SOURCES.keys())
    for k in keys:
        run_one(k, outdir, session)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
