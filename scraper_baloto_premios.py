#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scrapea premios Baloto por sorteo (múltiples filas por sorteo).
Header: sorteo,categoria,aciertos,ganadores,premio
"""
import argparse, re
from pathlib import Path
from scraper_utils import mk_session, fetch, soupify, read_csv_dict, write_csv_dict, merge_unique, clean_money, to_int, log

URL_FMT = "https://www.baloto.com/resultados-baloto/{sorteo}"

# Selectores candidatos típicos de tablas de premios
SELECTORES_TABLA = [
    "table", ".prizes table", ".tabla-premios table", ".results-table table"
]
RE_ROW = re.compile(r"(Acertantes|Ganadores|Categor[ií]a|Aciertos)", re.I)

def parse_premios(html):
    soup = soupify(html)
    tablas = []
    for sel in SELECTORES_TABLA:
        tablas.extend(soup.select(sel))
    # Filtra tablas que luzcan de premios
    candidatas = []
    for t in tablas:
        txt = t.get_text(" ", strip=True)
        if RE_ROW.search(txt):
            candidatas.append(t)
    rows=[]
    for t in candidatas:
        for tr in t.select("tr"):
            cols = [c.get_text(" ", strip=True) for c in tr.find_all(["td","th"])]
            if len(cols) < 3: 
                continue
            rowtxt = " | ".join(cols)
            if not RE_ROW.search(rowtxt) and (any(ch.isdigit() for ch in rowtxt) or "$" in rowtxt):
                # heurística: [categoria/aciertos] [ganadores] [premio]
                categoria = cols[0]
                aciertos = None
                # intenta detectar patrón “x+y” como aciertos
                m = re.search(r"\d\+\d|\d{1,2}", categoria)
                if m: aciertos = m.group(0)
                ganadores = None
                premio = None
                for c in cols[1:]:
                    if ganadores is None and re.search(r"\d", c) and not "$" in c:
                        ganadores = to_int(c)
                    if premio is None and "$" in c:
                        premio = clean_money(c)
                rows.append({
                    "categoria": categoria,
                    "aciertos": aciertos or "",
                    "ganadores": ganadores if ganadores is not None else "",
                    "premio": premio or ""
                })
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--last", type=int, default=8)
    ap.add_argument("--from", dest="from_sorteo", type=int, default=None)
    ap.add_argument("--to", dest="to_sorteo", type=int, default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out = Path(args.out)
    headers, rows = read_csv_dict(out)
    if not headers:
        headers = ["sorteo","categoria","aciertos","ganadores","premio"]

    session = mk_session()

    # Establece rango de sorteos como en resultados: intenta continuar desde el mayor sorteo existente.
    existentes_sorteos = set()
    for r in rows:
        s = to_int(r.get("sorteo"))
        if s: existentes_sorteos.add(s)

    if args.from_sorteo and args.to_sorteo:
        step = 1 if args.to_sorteo >= args.from_sorteo else -1
        sorteos = list(range(args.from_sorteo, args.to_sorteo+step, step))
    else:
        start = max(existentes_sorteos) + 1 if existentes_sorteos else None
        if start is None:
            log("[INFO] No hay base de sorteos. Usa --from/--to para backfill, o deja que resultados alimente el rango.")
            write_csv_dict(out, rows, headers)
            return 0
        sorteos = list(range(start, start + args.last))

    new_rows=[]
    for s in sorteos:
        url = URL_FMT.format(sorteo=s)
        log(f"[INFO] Sorteo {s} -> {url}")
        try:
            html = fetch(session, url)
            premios = parse_premios(html)
            if premios:
                for pr in premios:
                    pr["sorteo"] = s
                new_rows.extend(premios)
                log(f"[OK ] Sorteo {s}: {len(premios)} filas premios")
            else:
                log(f"[WARN] No pude encontrar tabla premios en {s}")
        except Exception as e:
            log(f"[WARN] Sorteo {s} fallo: {e}")

    if not new_rows:
        log("[INFO] No hay filas nuevas. CSV intacto.")
        return 0

    merged = merge_unique(rows, new_rows, key_tuple=("sorteo","categoria"))
    # ordenar por sorteo asc
    merged.sort(key=lambda r: (to_int(r.get("sorteo")) or 0, r.get("categoria","")))
    write_csv_dict(out, merged, headers)
    log(f"[OK ] Guardé {len(new_rows)} nuevas / total {len(merged)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
