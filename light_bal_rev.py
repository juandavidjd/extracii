# -*- coding: utf-8 -*-
"""
light_bal_rev.py
Reporte 'light' para Baloto y Revancha.

Mejoras clave:
- Fix KeyError ' font-family' (CSS con llaves escapadas para str.format).
- Rankings: frecuencias, last seen, pares y tríos (co-ocurrencias).
- Autodetección de columnas (n1.., bola1.., etc.) y 'super' si existe.
- Ventana reciente (--limit N) para los cálculos.
- Tabla de últimos sorteos (--show_last N) con orden por fila (--order_row as_is|asc|desc).
- NUEVO: switches --no-pairs / --no-trios para ocultar esas secciones.

No modifica scrapers ni el flujo existente.
"""

import argparse
import datetime
import os
import re
import sqlite3
from collections import Counter
from itertools import combinations

GAMES = [
    ("baloto",   "baloto_resultados_std"),
    ("revancha", "revancha_resultados_std"),
]

HTML_CSS = """
<style>
  body {{ font-family: Arial, sans-serif; margin: 24px; }}
  h1 {{ margin-top: 0; }}
  h2 {{ margin: 22px 0 8px 0; }}
  .card {{ border:1px solid #ddd; border-radius:10px; padding:16px; margin: 16px 0; }}
  .kpi {{ display:flex; gap:16px; flex-wrap:wrap; }}
  .box {{ border:1px solid #eee; border-radius:8px; padding:8px 10px; min-width: 180px; }}
  .small {{ font-size: 12px; color:#666; }}
  .mono {{ font-family: Consolas, Menlo, monospace; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border:1px solid #ddd; padding:6px 8px; text-align:left; }}
  th {{ background:#f6f6f6; }}
  .cols {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap:12px; }}
</style>
"""

HTML_LAYOUT = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8"/>
<title>{title}</title>
{css}
</head>
<body>
<h1>{title}</h1>

<div class="card">
  <div class="kpi">
    <div class="box"><b>Juego:</b> {game}</div>
    <div class="box"><b>Tabla:</b> {table}</div>
    <div class="box"><b>Filas:</b> {rows}</div>
    <div class="box"><b>Sorteos analizados:</b> {ndraws}</div>
    <div class="box"><b>Último sorteo:</b> {last_draw}</div>
    <div class="box"><b>Rango fechas:</b> {date_range}</div>
    <div class="box"><b>Ventana:</b> {window_info}</div>
  </div>
  <div class="small">DB: <span class="mono">{db_path}</span> &middot; Generado: {ts}</div>
</div>

{body}

</body>
</html>
"""

SECTION = """
<div class="card">
  <h2>{title}</h2>
  {content}
</div>
"""

def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def exists(conn, name):
    cur = conn.execute("SELECT 1 FROM sqlite_master WHERE name=? LIMIT 1", (name,))
    return cur.fetchone() is not None

def fetch_all(conn, table):
    cur = conn.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    if not cols:
        return [], []

    order_cols = []
    for pref in ("fecha", "date", "fechasorteo", "ts_sorteo", "created_at"):
        if pref in [c.lower() for c in cols]:
            real = next(c for c in cols if c.lower() == pref)
            order_cols.append(f'"{real}"')
            break
    for pref in ("sorteo", "concurso", "draw", "n_sorteo", "draw_id", "id_sorteo"):
        if pref in [c.lower() for c in cols]:
            real = next(c for c in cols if c.lower() == pref)
            order_cols.append(f'"{real}"')
            break

    order_sql = " ORDER BY " + ", ".join([c + " DESC" for c in order_cols]) if order_cols else ""
    sel = ", ".join(f'"{c}"' for c in cols)
    rows = conn.execute(f'SELECT {sel} FROM "{table}"{order_sql}').fetchall()
    return [dict(zip(cols, r)) for r in rows], cols

def detect_num_cols(cols):
    lc = [c.lower() for c in cols]

    super_col = None
    for cand in ("super", "superbalota", "super_bola", "superbola", "sb", "superball"):
        if cand in lc:
            super_col = cols[lc.index(cand)]
            break

    main_cols = []
    for c in cols:
        cl = c.lower()
        if re.fullmatch(r"(n|num|bola|b)\d+", cl):
            main_cols.append(c)
    if not main_cols:
        for c in cols:
            cl = c.lower()
            if re.search(r"(n|num|bola|b)\d+", cl):
                main_cols.append(c)

    def tail_num(name):
        m = re.search(r"(\d+)$", name)
        return int(m.group(1)) if m else 10**6
    main_cols = sorted(set(main_cols), key=tail_num)

    if not main_cols:
        maybe = []
        for c in cols:
            if re.search(r"\d", c.lower()):
                maybe.append(c)
        main_cols = maybe[:6]

    return main_cols, super_col

def draw_key(row, cols):
    fecha = None
    sorteo = None
    for k in ("fecha","date","fechasorteo","ts_sorteo","created_at"):
        for c in cols:
            if c.lower() == k:
                fecha = row[c]; break
        if fecha: break
    for k in ("sorteo","n_sorteo","concurso","draw","draw_id","id_sorteo"):
        for c in cols:
            if c.lower() == k:
                sorteo = row[c]; break
        if sorteo: break
    if fecha and sorteo is not None:
        return f"{fecha} / {sorteo}"
    return str(fecha or sorteo or "")

def to_int(v):
    try:
        s = str(v).strip()
        if not re.fullmatch(r"-?\d+", s):
            return None
        return int(s)
    except Exception:
        return None

def extract_draw_numbers(rows, cols, limit, main_cols, super_col):
    if limit and limit > 0:
        rows = rows[:limit]

    draw_keys = []
    draws_main = []
    draws_super = []
    date_vals = []

    for r in rows:
        dk = draw_key(r, cols)
        draw_keys.append(dk)

        for k in ("fecha","date","fechasorteo","ts_sorteo","created_at"):
            if k in [c.lower() for c in cols]:
                real = next(c for c in cols if c.lower() == k)
                date_vals.append(r.get(real))
                break

        mains = []
        for c in main_cols:
            v = to_int(r.get(c))
            if v is not None:
                mains.append(v)
        draws_main.append(mains)

        sp = None
        if super_col:
            sp = to_int(r.get(super_col))
        draws_super.append(sp)

    def safe_min(it):
        try: return min(x for x in it if x is not None)
        except ValueError: return "N/D"
    def safe_max(it):
        try: return max(x for x in it if x is not None)
        except ValueError: return "N/D"

    date_range = f"{safe_min(date_vals)} → {safe_max(date_vals)}"
    return draws_main, draws_super, draw_keys, date_range

def freq_numbers(draws_main):
    cnt = Counter()
    for nums in draws_main:
        for n in nums:
            cnt[n] += 1
    total = sum(cnt.values()) or 1
    return [(n, c, 100.0*c/total) for n, c in cnt.most_common()]

def last_seen(draws_main):
    seen = {}
    for idx, nums in enumerate(draws_main):
        for n in nums:
            if n not in seen:
                seen[n] = idx
    return sorted(seen.items(), key=lambda x: x[1], reverse=True)

def combo_counts(draws_main, k):
    cnt = Counter()
    for nums in draws_main:
        uniq = sorted(set(nums))
        if len(uniq) >= k:
            for comb in combinations(uniq, k):
                cnt[comb] += 1
    total = sum(cnt.values()) or 1
    return [(comb, c, 100.0*c/total) for comb, c in cnt.most_common()]

def html_table(headers, rows):
    thead = "".join(f"<th>{h}</th>" for h in headers)
    body = []
    for r in rows:
        body.append("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>")
    return f"<table><thead><tr>{thead}</tr></thead><tbody>{''.join(body)}</tbody></table>"

def recent_draws_table(draw_keys, draws_main, draws_super, show_last, order_row):
    n = min(show_last, len(draw_keys))
    keys = draw_keys[:n]
    mains = [list(x) for x in draws_main[:n]]

    if order_row == "asc":
        mains = [sorted(row) for row in mains]
    elif order_row == "desc":
        mains = [sorted(row, reverse=True) for row in mains]

    supers = draws_super[:n] if any(s is not None for s in draws_super) else [None]*n

    max_len = max((len(x) for x in mains), default=0)
    headers = ["Sorteo"] + [f"N{i}" for i in range(1, max_len+1)]
    if any(s is not None for s in supers):
        headers.append("Super")

    rows = []
    for i in range(n):
        nums = mains[i] + [""] * (max_len - len(mains[i]))
        row = [keys[i]] + nums
        if any(s is not None for s in supers):
            row.append(supers[i] if supers[i] is not None else "")
        rows.append(row)

    return html_table(headers, rows)

def render_game(conn, db_path, game, table, out_dir,
                sample_limit=0, topk=15, show_last=20, order_row="as_is",
                include_pairs=True, include_trios=True):
    ts = now_str()

    if not exists(conn, table):
        body = SECTION.format(
            title="Estado",
            content=f"<p>No existe la tabla/vista <b>{table}</b>.</p>"
        )
        html = HTML_LAYOUT.format(
            title=f"{game.capitalize()} - Light",
            css=HTML_CSS, game=game, table=table, rows=0, ndraws=0,
            last_draw="N/D", date_range="N/D",
            window_info="N/D", db_path=db_path, ts=ts, body=body
        )
        out_path = os.path.join(out_dir, f"{game}_light.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[WARN] No pude leer datos para {game}.")
        return 0

    rows, cols = fetch_all(conn, table)
    if not rows:
        body = SECTION.format(
            title="Estado",
            content=f"<p>La tabla <b>{table}</b> no tiene filas.</p>"
        )
        html = HTML_LAYOUT.format(
            title=f"{game.capitalize()} - Light",
            css=HTML_CSS, game=game, table=table, rows=0, ndraws=0,
            last_draw="N/D", date_range="N/D",
            window_info=("Últimos N" if sample_limit else "Completo"),
            db_path=db_path, ts=ts, body=body
        )
        out_path = os.path.join(out_dir, f"{game}_light.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[WARN] {game}: tabla vacía.")
        return 0

    main_cols, super_col = detect_num_cols(cols)
    draws_main, draws_super, draw_keys, date_range = extract_draw_numbers(
        rows, cols, sample_limit, main_cols, super_col
    )

    ndraws = len(draw_keys)
    last_draw = draw_keys[0] if draw_keys else "N/D"
    window_info = f"Últimos {ndraws}" if sample_limit else "Completo"

    body_parts = []

    # Últimos sorteos
    recent_tbl = recent_draws_table(draw_keys, draws_main, draws_super, show_last, order_row)
    body_parts.append(SECTION.format(
        title=f"Últimos {min(show_last, ndraws)} sorteos (más reciente primero) — orden por fila: {order_row}",
        content=recent_tbl
    ))

    # Columnas detectadas
    summary = html_table(
        ["Columnas principales", "Columna super"],
        [[", ".join(main_cols) if main_cols else "N/D", super_col or "N/D"]]
    )
    body_parts.append(SECTION.format(title="Columnas detectadas", content=summary))

    # Frecuencias
    freq = freq_numbers(draws_main)
    body_parts.append(SECTION.format(
        title=f"Frecuencias (números principales) - Top {topk}",
        content=html_table(["Número", "Conteo", "%"],
                           [(n, c, f"{p:.2f}%") for (n, c, p) in freq[:topk]])
    ))

    # Last seen
    ls = last_seen(draws_main)
    body_parts.append(SECTION.format(
        title=f"Last Seen (números principales) - Top {topk} rezagados",
        content=html_table(["Número", "Sorteos desde última aparición"], ls[:topk])
    ))

    # Pares
    if include_pairs:
        pairs = combo_counts(draws_main, 2)
        body_parts.append(SECTION.format(
            title=f"Pares más frecuentes (co-ocurrencia por sorteo) - Top {topk}",
            content=html_table(["Par", "Conteo", "%"],
                               [(str(list(c)), n, f"{p:.2f}%") for (c, n, p) in pairs[:topk]])
        ))

    # Tríos
    if include_trios:
        trios = combo_counts(draws_main, 3)
        body_parts.append(SECTION.format(
            title=f"Tríos más frecuentes (co-ocurrencia por sorteo) - Top {topk}",
            content=html_table(["Trío", "Conteo", "%"],
                               [(str(list(c)), n, f"{p:.2f}%") for (c, n, p) in trios[:topk]])
        ))

    # Super (si existe)
    if super_col:
        cnt_super = Counter(x for x in draws_super if x is not None)
        total_s = sum(cnt_super.values()) or 1
        freq_super = [(n, c, 100.0*c/total_s) for n, c in cnt_super.most_common()]
        body_parts.append(SECTION.format(
            title=f"Frecuencias Super ({super_col}) - Top {topk}",
            content=html_table(["Número", "Conteo", "%"],
                               [(n, c, f"{p:.2f}%") for (n, c, p) in freq_super[:topk]])
        ))

        seen_s = {}
        for idx, sp in enumerate(draws_super):
            if sp is not None and sp not in seen_s:
                seen_s[sp] = idx
        ls_s = sorted(seen_s.items(), key=lambda x: x[1], reverse=True)
        body_parts.append(SECTION.format(
            title=f"Last Seen Super ({super_col}) - Top {topk} rezagados",
            content=html_table(["Número", "Sorteos desde última aparición"], ls_s[:topk])
        ))

    out_html = HTML_LAYOUT.replace("{css}", "{css}").format(
        title=f"{game.capitalize()} - Light",
        css=HTML_CSS,
        game=game,
        table=table,
        rows=len(rows),
        ndraws=ndraws,
        last_draw=last_draw,
        date_range=date_range,
        window_info=window_info,
        db_path=db_path,
        ts=ts,
        body="\n".join(body_parts)
    )

    out_path = os.path.join(out_dir, f"{game}_light.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out_html)
    print(f"[OK ] {game} light -> {out_path}")
    return 0

def ensure_dir(p):
    if not os.path.isdir(p):
        os.makedirs(p, exist_ok=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="Ruta a radar_premios.db")
    ap.add_argument("--reports", required=True, help="Carpeta de salida HTML")
    ap.add_argument("--limit", type=int, default=0, help="Si >0, usa los últimos N sorteos para cálculos")
    ap.add_argument("--topk", type=int, default=15, help="Top K filas por ranking")
    ap.add_argument("--show_last", type=int, default=20, help="Cuántos sorteos mostrar en la tabla inicial")
    ap.add_argument("--order_row", choices=["as_is", "asc", "desc"], default="as_is",
                    help="Ordenar números por fila en la tabla de últimos sorteos")
    ap.add_argument("--no-pairs", dest="no_pairs", action="store_true", help="Oculta la sección de pares")
    ap.add_argument("--no-trios", dest="no_trios", action="store_true", help="Oculta la sección de tríos")
    args = ap.parse_args()

    db_path = os.path.abspath(args.db)
    out_dir = os.path.abspath(args.reports)
    ensure_dir(out_dir)

    if not os.path.isfile(db_path):
        print(f"[WARN] DB no existe: {db_path}")
        return 0

    conn = sqlite3.connect(db_path)
    try:
        for game, table in GAMES:
            render_game(
                conn, db_path, game, table, out_dir,
                sample_limit=args.limit, topk=args.topk,
                show_last=args.show_last, order_row=args.order_row,
                include_pairs=not args.no_pairs,
                include_trios=not args.no_trios
            )
    finally:
        conn.close()
    print("[OK ] Scoring light finalizado")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
