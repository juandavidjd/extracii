#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AstroLuna -> data\crudo\astro_luna.csv
Header: fecha,signo,numero,luna

Este scraper es prudente: si no encuentra nueva info, NO toca el CSV.
Debido a variaciones de fuente, deja un “hook” para que configures la URL
y los selectores sin riesgo de corromper datos.
"""
import argparse, re
from pathlib import Path
from scraper_utils import mk_session, fetch, soupify, read_csv_dict, write_csv_dict, merge_unique, log

# CONFIGURA A TU FUENTE REAL:
SOURCE_URL = "https://tu-fuente-astroluna.example/"   # <--- AJUSTA
# Selectores candidatos (ajusta a tu HTML real)
SEL_ROW = [".tabla-astro tr", ".listado tr", "table tr"]
SEL_FECHA = ["td.fecha", ".fecha", "time"]
SEL_SIGNO = ["td.signo", ".signo"]
SEL_NUMERO = ["td.numero", ".numero"]
SEL_LUNA = ["td.luna", ".luna"]

def pick_text(row, selectors):
    for s in selectors:
        el = row.select_one(s)
        if el:
            t = el.get_text(" ", strip=True)
            if t: return t
    return None

def parse_rows(html):
    soup = soupify(html)
    rows=[]
    for sel in SEL_ROW:
        for tr in soup.select(sel):
            fecha = pick_text(tr, SEL_FECHA)
            signo = pick_text(tr, SEL_SIGNO)
            numero = pick_text(tr, SEL_NUMERO)
            luna = pick_text(tr, SEL_LUNA)
            if numero and signo and fecha:
                rows.append({"fecha": fecha, "signo": signo, "numero": numero, "luna": luna or ""})
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--url", default=SOURCE_URL)
    args = ap.parse_args()

    out = Path(args.out)
    headers, existing = read_csv_dict(out)
    if not headers:
        headers = ["fecha","signo","numero","luna"]

    # si no hay URL real configurada aún, no hacemos nada
    if not args.url or "example" in args.url:
        log("[INFO] AstroLuna: sin URL configurada. No-op.")
        if not headers: headers = ["fecha","signo","numero","luna"]
        write_csv_dict(out, existing, headers)
        return 0

    session = mk_session()
    try:
        html = fetch(session, args.url)
        parsed = parse_rows(html)
        # Evita sobrescribir si no hay filas nuevas
        if not parsed:
            log("[INFO] AstroLuna: sin nuevos registros parseables.")
            write_csv_dict(out, existing, headers)
            return 0
        merged = merge_unique(existing, parsed, key_tuple=("fecha","signo"))
        write_csv_dict(out, merged, headers)
        log(f"[OK ] AstroLuna: +{len(merged)-len(existing)} nuevas / total {len(merged)}")
    except Exception as e:
        log(f"[WARN] AstroLuna fallo: {e}. CSV intacto.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
