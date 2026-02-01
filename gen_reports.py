#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reportes ligeros HTML (placeholders útiles) para Baloto/Revancha/4D.
Se apoya sólo en stdlib + SQLite.
"""

import argparse, sqlite3, sys, html
from pathlib import Path

TEMPL = """<!doctype html>
<meta charset="utf-8">
<title>{title}</title>
<h1>{title}</h1>
<p>Generado: {gen}</p>
{body}
"""

def html_table(rows, headers):
    th = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    trs=[]
    for r in rows:
        tds = "".join(f"<td>{html.escape(str(c) if c is not None else '')}</td>" for c in r)
        trs.append(f"<tr>{tds}</tr>")
    return f"<table border=1 cellspacing=0 cellpadding=4><thead><tr>{th}</tr></thead><tbody>{''.join(trs)}</tbody></table>"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--log', default=None)
    args = ap.parse_args()

    outdir = Path(args.out); outdir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(args.db)

    logs=[]

    # Baloto últimos 20 resultados
    try:
        cur = conn.execute("SELECT sorteo,fecha,n1,n2,n3,n4,n5,superbalota FROM baloto_resultados ORDER BY sorteo DESC LIMIT 20;")
        rows = cur.fetchall()
        body = "<h2>Baloto - últimos 20</h2>" + html_table(rows, ["sorteo","fecha","n1","n2","n3","n4","n5","SB"])
        (outdir/"baloto_light.html").write_text(TEMPL.format(title="Baloto - resumen", gen=str(Path().cwd()), body=body), encoding='utf-8')
        logs.append("[OK ] baloto_light.html")
    except Exception as e:
        logs.append(f"[WARN] baloto_light: {e}")

    # Revancha últimos 20 resultados
    try:
        cur = conn.execute("SELECT sorteo,fecha,n1,n2,n3,n4,n5,superbalota FROM revancha_resultados ORDER BY sorteo DESC LIMIT 20;")
        rows = cur.fetchall()
        body = "<h2>Revancha - últimos 20</h2>" + html_table(rows, ["sorteo","fecha","n1","n2","n3","n4","n5","SB"])
        (outdir/"revancha_light.html").write_text(TEMPL.format(title="Revancha - resumen", gen=str(Path().cwd()), body=body), encoding='utf-8')
        logs.append("[OK ] revancha_light.html")
    except Exception as e:
        logs.append(f"[WARN] revancha_light: {e}")

    # 4D vista simple (si alguna tabla existe)
    for lot in ("boyaca","huila","manizales","medellin","quindio","tolima"):
        try:
            cur = conn.execute(f"SELECT fecha,numero,serie FROM {lot} ORDER BY fecha DESC LIMIT 20;")
            rows = cur.fetchall()
            if rows:
                body = f"<h2>{lot.upper()} - últimos 20</h2>" + html_table(rows, ["fecha","numero","serie"])
                (outdir/f"{lot}_light.html").write_text(TEMPL.format(title=f"{lot.upper()} - resumen", gen=str(Path().cwd()), body=body), encoding='utf-8')
                logs.append(f"[OK ] {lot}_light.html")
        except Exception:
            pass

    if args.log:
        Path(args.log).write_text("\n".join(logs), encoding='utf-8')
    print("\n".join(logs))
    return 0

if __name__ == "__main__":
    sys.exit(main())
