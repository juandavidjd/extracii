#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scrapea resultados Baloto (últimos N sorteos) y hace merge en data\crudo\baloto_resultados.csv
Header esperado: sorteo,fecha,n1,n2,n3,n4,n5,superbalota
"""
import argparse, re
from pathlib import Path
from scraper_utils import mk_session, fetch, soupify, read_csv_dict, write_csv_dict, merge_unique, to_int, log

URL_FMT = "https://www.baloto.com/resultados-baloto/{sorteo}"

# REGEX de respaldo para capturar 5 números + SB (con o sin prefijos)
RE_NUMS = re.compile(r"(?:Baloto|Resultados)?.*?(\d{1,2}).*?(\d{1,2}).*?(\d{1,2}).*?(\d{1,2}).*?(\d{1,2}).*?(?:super\s*balota|sb|superbalota)\D*(\d{1,2})", re.I | re.S)
RE_FECHA = re.compile(r"(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})")

def parse_page(html):
    soup = soupify(html)

    # 1) Intento por selectores habituales (puedes ajustar si cambia el sitio)
    # Busca "ball" como spans o lis
    balls = [b.get_text(strip=True) for b in soup.select(".ball, .numero, .ball-number, li.ball span")]
    balls = [x for x in balls if x.isdigit()]
    nums = None
    if len(balls) >= 6:
        # supón 5 primeros + último SB
        nums = list(map(int, balls[:6]))

    # 2) Fecha por selectores
    fecha = None
    for sel in (".date", ".fecha", ".draw-date", "time", "p"):
        el = soup.select_one(sel)
        if el:
            m = RE_FECHA.search(el.get_text(" ", strip=True))
            if m:
                fecha = m.group(1)
                break

    # 3) Fallback regex global
    if nums is None:
        m = RE_NUMS.search(html)
        if m:
            nums = list(map(int, m.groups()))

    if fecha is None:
        m = RE_FECHA.search(html)
        if m:
            fecha = m.group(1)

    if nums and len(nums) == 6:
        n1,n2,n3,n4,n5,sb = nums
        return {"fecha": fecha, "n1": n1, "n2": n2, "n3": n3, "n4": n4, "n5": n5, "superbalota": sb}
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--last", type=int, default=8, help="Cantidad de sorteos hacia atrás (incluye el último)")
    ap.add_argument("--from", dest="from_sorteo", type=int, default=None)
    ap.add_argument("--to", dest="to_sorteo", type=int, default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out = Path(args.out)
    headers, rows = read_csv_dict(out)
    if not headers:
        headers = ["sorteo","fecha","n1","n2","n3","n4","n5","superbalota"]

    session = mk_session()

    sorteos = []
    if args.from_sorteo and args.to_sorteo:
        step = 1 if args.to_sorteo >= args.from_sorteo else -1
        sorteos = list(range(args.from_sorteo, args.to_sorteo+step, step))
    else:
        # heurística: si ya hay datos, continúa desde el max sorteo
        max_s = 0
        for r in rows:
            s = to_int(r.get("sorteo"))
            if s and s > max_s: max_s = s
        start = max_s + 1 if max_s else None
        if start is None:
            # si no hay, intenta últimos N asumiendo numeración contínua (ajusta si prefieres pasar /from /to)
            # aquí el usuario típicamente usa /last 8 como en tus logs
            # sin base de "último sorteo" real, no podemos adivinar el número exacto -> pedimos N y probamos hacia atrás desde una ventana razonable
            # Para no golpear el sitio con 1000, usa rango corto y “sólo si existe”
            # Sugerencia: fija manualmente /from /to cuando quieras backfill.
            log("[INFO] No tengo base de sorteo inicial. Intenta usar --from/--to para backfill.")
            # No intentamos adivinar. Salimos sin cambios.
            write_csv_dict(out, rows, headers)
            return 0
        sorteos = list(range(start, start + args.last))

    new_rows = []
    for s in sorteos:
        url = URL_FMT.format(sorteo=s)
        log(f"[INFO] Sorteo {s} -> {url}")
        try:
            html = fetch(session, url)
            parsed = parse_page(html)
            if parsed:
                parsed["sorteo"] = s
                new_rows.append({k: str(v) for k,v in parsed.items()})
                log(f"[OK ] Sorteo {s}: {parsed}")
            else:
                log(f"[WARN] No pude parsear Sorteo {s} (selector/regex)")
        except Exception as e:
            log(f"[WARN] Sorteo {s} fallo: {e}")

    if not new_rows:
        log("[INFO] No hay filas nuevas válidas. CSV intacto.")
        return 0

    merged = merge_unique(rows, new_rows, key_tuple=("sorteo",))
    # ordenar por sorteo asc
    merged.sort(key=lambda r: to_int(r.get("sorteo")) or 0)
    write_csv_dict(out, merged, headers)
    log(f"[OK ] Guardé {len(new_rows)} nuevos / total {len(merged)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
