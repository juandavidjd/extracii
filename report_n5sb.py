# report_n5sb.py
# Informe de comportamiento N5+SB (jackpot) para Baloto y Revancha.
# Lee las vistas creadas por std_views.sql:
#   - n5sb_top_tier_by_draw (game, sorteo, fecha, ganadores_5sb, premio_total_5sb, premio_ind_5sb)
#   - all_n5sb_std (para validar draws si hiciera falta)
#
# Salidas:
#   - {outdir}\n5sb_draws.csv       -> una fila por sorteo (hit/no-hit y métricas rodantes)
#   - {outdir}\n5sb_cycles.csv      -> una fila por ciclo de acumulación (entre jackpots)
#   - {outdir}\n5sb_summary.csv     -> KPIs por juego
#   - {outdir}\n5sb_report.html     -> resumen legible
#
# Uso típico:
#   python -X utf8 report_n5sb.py --db "C:\RadarPremios\radar_premios.db"
# Opcionales:
#   --out "C:\RadarPremios\reports" --window 12 --games "baloto,revancha"

import os, sys, argparse, sqlite3, csv, datetime as dt
from collections import defaultdict, namedtuple

def ensure_dir(p):
    os.makedirs(p, exist_ok=True)
    return p

def now_stamp():
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")

def read_table(cnx, sql, params=()):
    cur = cnx.execute(sql, params)
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    return rows

def to_int(x, default=0):
    try:
        return int(x)
    except:
        try:
            return int(float(x))
        except:
            return default

def to_float(x, default=0.0):
    try:
        return float(x)
    except:
        return default

def parse_args():
    ap = argparse.ArgumentParser(description="Reporte N5+SB (jackpot) Baloto/Revancha")
    rp_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    ap.add_argument("--db", default=os.path.join(rp_root, "radar_premios.db"))
    ap.add_argument("--out", default=os.path.join(rp_root, "reports"))
    ap.add_argument("--window", type=int, default=12, help="Ventana rolling (sorteos) para promedios")
    ap.add_argument("--games", default="baloto,revancha", help="baloto,revancha o all para ambos")
    return ap.parse_args()

def compute_rolling(seq, w):
    out = []
    s = 0.0
    from collections import deque
    q = deque()
    for i, val in enumerate(seq):
        v = to_float(val, 0.0)
        q.append(v); s += v
        if len(q) > w:
            s -= q.popleft()
        out.append(s / len(q))
    return out

def analyze_game(rows, game, window, outdir):
    # rows: ordenados por fecha/sorteo
    # Campos esperados: fecha, sorteo, ganadores_5sb, premio_total_5sb, premio_ind_5sb
    rows_sorted = sorted(
        rows,
        key=lambda r: (str(r.get("fecha") or ""), to_int(r.get("sorteo"), 0))
    )

    # Señales básicas
    hits = [1 if to_int(r.get("ganadores_5sb"), 0) > 0 else 0 for r in rows_sorted]
    premios_tot = [to_float(r.get("premio_total_5sb"), 0.0) for r in rows_sorted]
    premios_ind = [to_float(r.get("premio_ind_5sb"), 0.0) for r in rows_sorted]

    # Racha sin caer (no-hit streak)
    nohit_streak = []
    c = 0
    for h in hits:
        if h == 0:
            c += 1
        else:
            c = 0
        nohit_streak.append(c)

    # Rolling
    roll_prem_tot = compute_rolling(premios_tot, window)
    roll_hit_rate = compute_rolling(hits, window)

    # Construcción de CSV draw-level
    draws_csv = os.path.join(outdir, f"n5sb_draws_{game}.csv")
    with open(draws_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["game","fecha","sorteo","hit_5sb","ganadores_5sb","premio_total_5sb","premio_ind_5sb","nohit_streak","roll_prem_total","roll_hit_rate"])
        for i, r in enumerate(rows_sorted):
            w.writerow([
                game,
                r.get("fecha"),
                r.get("sorteo"),
                hits[i],
                to_int(r.get("ganadores_5sb"),0),
                premios_tot[i],
                premios_ind[i],
                nohit_streak[i],
                roll_prem_tot[i],
                roll_hit_rate[i],
            ])

    # Detectar ciclos: desde (después de un hit) hasta el siguiente hit
    # Def: un ciclo incluye el bloque de no-hits y cierra en el sorteo con hit.
    Cycle = namedtuple("Cycle", "game start_fecha start_sorteo end_fecha end_sorteo draws_en_ciclo max_premio_tot sum_premio_tot hits_en_ciclo")
    cycles = []
    start_i = 0
    # Normalizamos: si comienza con no-hit, abrimos ciclo desde el inicio y lo cerramos cuando llegue un hit.
    i = 0
    while i < len(rows_sorted):
        # Extender hasta que encontremos un hit, ese es el final del ciclo
        j = i
        max_p = 0.0
        sum_p = 0.0
        hits_c = 0
        while j < len(rows_sorted):
            max_p = max(max_p, premios_tot[j])
            sum_p += premios_tot[j]
            hits_c += hits[j]
            if hits[j] == 1:  # cierre de ciclo
                break
            j += 1
        # Registrar ciclo si hay al menos un sorteo en el intervalo
        if j >= i:
            si, sj = i, j
            cycles.append(Cycle(
                game=game,
                start_fecha=rows_sorted[si].get("fecha"),
                start_sorteo=rows_sorted[si].get("sorteo"),
                end_fecha=rows_sorted[sj].get("fecha"),
                end_sorteo=rows_sorted[sj].get("sorteo"),
                draws_en_ciclo=(sj - si + 1),
                max_premio_tot=max_p,
                sum_premio_tot=sum_p,
                hits_en_ciclo=hits_c
            ))
        i = j + 1

    cycles_csv = os.path.join(outdir, f"n5sb_cycles_{game}.csv")
    with open(cycles_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["game","start_fecha","start_sorteo","end_fecha","end_sorteo","draws_en_ciclo","max_premio_tot","sum_premio_tot","hits_en_ciclo"])
        for c in cycles:
            w.writerow(list(c))

    # KPIs por juego
    total_draws = len(rows_sorted)
    total_hits = sum(hits)
    kpi = {
        "game": game,
        "total_draws": total_draws,
        "total_hits_5sb": total_hits,
        "hit_rate": (total_hits/total_draws) if total_draws else 0.0,
        "max_nohit_streak": max(nohit_streak) if nohit_streak else 0,
        "avg_roll_prem_total": sum(roll_prem_tot)/len(roll_prem_tot) if roll_prem_tot else 0.0,
        "last_nohit_streak": nohit_streak[-1] if nohit_streak else 0,
        "last_premio_total": premios_tot[-1] if premios_tot else 0.0,
    }
    return kpi

def write_summary(kpis, outdir):
    summ_csv = os.path.join(outdir, "n5sb_summary.csv")
    with open(summ_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["game","total_draws","total_hits_5sb","hit_rate","max_nohit_streak","avg_roll_prem_total","last_nohit_streak","last_premio_total"])
        for g in kpis:
            w.writerow([g["game"], g["total_draws"], g["total_hits_5sb"], g["hit_rate"],
                        g["max_nohit_streak"], g["avg_roll_prem_total"], g["last_nohit_streak"], g["last_premio_total"]])

def write_html(kpis, outdir):
    html = os.path.join(outdir, "n5sb_report.html")
    def fmt_money(x):
        try:
            return f"${float(x):,.0f}".replace(",", ".")
        except:
            return str(x)
    rows = []
    for g in kpis:
        rows.append(
            f"<tr>"
            f"<td>{g['game']}</td>"
            f"<td style='text-align:right'>{g['total_draws']}</td>"
            f"<td style='text-align:right'>{g['total_hits_5sb']}</td>"
            f"<td style='text-align:right'>{g['hit_rate']:.3f}</td>"
            f"<td style='text-align:right'>{g['max_nohit_streak']}</td>"
            f"<td style='text-align:right'>{fmt_money(g['avg_roll_prem_total'])}</td>"
            f"<td style='text-align:right'>{g['last_nohit_streak']}</td>"
            f"<td style='text-align:right'>{fmt_money(g['last_premio_total'])}</td>"
            f"</tr>"
        )
    html_txt = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8"/>
<title>Reporte N5+SB (jackpot) - Baloto/Revancha</title>
<style>
body{{font-family:Segoe UI,Roboto,Arial,sans-serif;margin:24px}}
h1{{margin:0 0 8px}}
small{{color:#666}}
table{{border-collapse:collapse;width:100%;margin-top:16px}}
th,td{{border:1px solid #ddd;padding:8px}}
th{{background:#fafafa;text-align:left}}
tr:nth-child(even){{background:#f9f9f9}}
.code{{font-family:Consolas,monospace;color:#444}}
</style>
</head>
<body>
<h1>Reporte N5+SB (jackpot)</h1>
<small>Generado: {dt.datetime.now().isoformat(timespec='seconds')}</small>

<h2>KPIs por juego</h2>
<table>
<thead>
<tr>
  <th>Juego</th><th>Sort.</th><th>Hits 5+SB</th><th>Tasa hit</th>
  <th>Racha máx sin caer</th><th>Promedio móvil premio total</th>
  <th>Racha actual sin caer</th><th>Premio total último sorteo</th>
</tr>
</thead>
<tbody>
{''.join(rows)}
</tbody>
</table>

<p>Archivos producidos en esta carpeta:
<ul>
  <li><span class="code">n5sb_draws_*.csv</span> — por sorteo</li>
  <li><span class="code">n5sb_cycles_*.csv</span> — por ciclo de acumulación</li>
  <li><span class="code">n5sb_summary.csv</span> — KPIs</li>
</ul>
</p>
</body>
</html>
"""
    with open(html, "w", encoding="utf-8") as f:
        f.write(html_txt)

def main():
    args = parse_args()
    cnx = sqlite3.connect(args.db)

    # Validaciones mínimas
    # Debe existir n5sb_top_tier_by_draw
    try:
        cnx.execute("SELECT * FROM n5sb_top_tier_by_draw LIMIT 1")
    except Exception as e:
        print("[ERROR] Falta vista n5sb_top_tier_by_draw. Ejecuta apply_std_views.bat primero.")
        print(e)
        sys.exit(1)

    # Selección de juegos
    if args.games.strip().lower() == "all":
        games = ["baloto","revancha"]
    else:
        games = [g.strip().lower() for g in args.games.split(",") if g.strip()]

    outdir = ensure_dir(os.path.join(args.out, f"n5sb_{now_stamp()}"))

    kpis = []
    for g in games:
        data = read_table(
            cnx,
            "SELECT game, sorteo, fecha, ganadores_5sb, premio_total_5sb, premio_ind_5sb "
            "FROM n5sb_top_tier_by_draw WHERE game = ? ORDER BY date(fecha), sorteo",
            (g,)
        )
        if not data:
            print(f"[WARN] Sin datos en n5sb_top_tier_by_draw para '{g}'.")
            continue
        kpi = analyze_game(data, g, args.window, outdir)
        kpis.append(kpi)

    if not kpis:
        print("[WARN] No se generaron KPIs (¿sin datos?).")
        sys.exit(2)

    write_summary(kpis, outdir)
    write_html(kpis, outdir)
    print("[OK] Reporte N5+SB generado en:", outdir)

if __name__ == "__main__":
    main()
