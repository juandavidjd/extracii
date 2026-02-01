#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
analyze_multi_days.py
Analiza aciertos/misses de los últimos N días comparando números ganadores vs. candidatos del run más reciente previo.
Robusto a distintos esquemas de DB (descubre tablas/columnas).

Salida:
  - CSV:  <outdir>/analisis_multidias.csv
  - HTML: <outdir>/analisis_multidias.html
"""

import argparse
import sqlite3
import os
import datetime as dt
import csv
import html
from collections import defaultdict

# -------- Utilidades de introspección --------

def list_tables(conn):
    cur = conn.execute("SELECT name, type FROM sqlite_master WHERE type in ('table','view')")
    return [(r[0], r[1]) for r in cur.fetchall()]

def table_has_columns(conn, table, cols):
    # True si la tabla tiene TODAS las columnas de 'cols' (alguna puede ser alias si hay coincidencia laxa)
    cur = conn.execute(f"PRAGMA table_info('{table}')")
    existing = {r[1].lower() for r in cur.fetchall()}
    wanted  = set([c.lower() for c in cols])
    return wanted.issubset(existing)

def find_columns_like(conn, table, candidates):
    """Devuelve el primer nombre de columna de 'table' que coincida (case-insensitive) con alguna en 'candidates'."""
    cur = conn.execute(f"PRAGMA table_info('{table}')")
    names = [r[1] for r in cur.fetchall()]
    for want in candidates:
        for n in names:
            if n.lower() == want.lower():
                return n
    # coincidencia floja: contiene
    for want in candidates:
        for n in names:
            if want.lower() in n.lower():
                return n
    return None

def try_fetch_one(conn, sql, params=()):
    try:
        cur = conn.execute(sql, params)
        return cur.fetchone()
    except Exception:
        return None

# -------- Descubrimiento de tablas principales --------

def discover_run_tables(conn):
    """Intenta descubrir tablas de runs y candidatos."""
    candidates_for_runs = ["runs", "scoring_runs", "run", "ejecuciones"]
    candidates_for_rcand = ["run_candidates", "scoring_candidates", "candidatos", "run_cands"]

    tables = [t for t, _ in list_tables(conn)]

    # pick run table
    run_table = None
    for name in tables:
        low = name.lower()
        if any(x in low for x in candidates_for_runs):
            # debe tener created_at (o similar) y un id
            # nombre de id podría ser id o run_id
            cur = conn.execute(f"PRAGMA table_info('{name}')")
            cols = {r[1].lower() for r in cur.fetchall()}
            if any(c in cols for c in ("id","run_id")) and any(c in cols for c in ("created_at","fecha","datetime","ts","timestamp","created","fecha_creacion")):
                run_table = name
                break

    # pick run_candidates table
    rc_table = None
    for name in tables:
        low = name.lower()
        if any(x in low for x in candidates_for_rcand):
            cur = conn.execute(f"PRAGMA table_info('{name}')")
            cols = {r[1].lower() for r in cur.fetchall()}
            if any(c in cols for c in ("run_id","id_run")) and any(c in cols for c in ("rank","pos","puesto")):
                # alguna columna para el número candidato
                if any(c in cols for c in ("numero","num","candidate","cand","numero4","number")):
                    rc_table = name
                    break

    return run_table, rc_table

def discover_result_tables(conn):
    """Devuelve una lista de tablas candidatas de resultados con (tabla, col_fecha, col_numero)."""
    priority = [
        "baloto_resultados",
        "revancha_resultados",
        "astro_luna",
        "boyaca","huila","manizales","medellin","quindio","tolima",
        "todo"  # vista agregada si existe
    ]
    tables = [t for t, _ in list_tables(conn)]
    out = []

    for name in tables:
        low = name.lower()
        if low in priority or any(low.endswith(x) for x in ("_resultados","_premios")) or low in priority:
            # detectar columnas fecha/numero
            col_fecha = find_columns_like(conn, name, ["fecha","date","fecha_sorteo","draw_date"])
            col_num = find_columns_like(conn, name, ["numero","num","ganador","winning_number","resultado","resultado4"])
            if col_fecha and col_num:
                out.append((name, col_fecha, col_num))

    # eliminar duplicados preservando orden
    seen = set(); dedup=[]
    for it in out:
        if it[0] not in seen:
            dedup.append(it); seen.add(it[0])
    return dedup

# -------- Lógica de análisis --------

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="Ruta a la base SQLite")
    ap.add_argument("--days", type=int, default=3, help="Días hacia atrás a evaluar (por fecha real)")
    ap.add_argument("--topk", type=int, default=15, help="Top-K de candidatos a considerar")
    ap.add_argument("--outdir", default=".", help="Carpeta de salida para CSV/HTML")
    return ap.parse_args()

def as_date(s):
    if isinstance(s, (int, float)):
        try:
            return dt.date.fromtimestamp(s)
        except Exception:
            pass
    if isinstance(s, (dt.date, dt.datetime)):
        return s.date() if isinstance(s, dt.datetime) else s
    if s is None: return None
    s = str(s)
    for fmt in ("%Y-%m-%d","%Y/%m/%d","%d/%m/%Y","%Y-%m-%d %H:%M:%S","%Y/%m/%d %H:%M:%S"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except Exception:
            continue
    # fallback: cortar a 10 chars
    try:
        return dt.datetime.strptime(s[:10], "%Y-%m-%d").date()
    except Exception:
        return None

def as_text(x):
    return None if x is None else str(x).strip()

def load_latest_winners(conn, days, result_tables):
    """Devuelve una lista de (fecha, numero, tabla_origen) de los últimos N días, deduplicando por fecha."""
    today = dt.date.today()
    min_date = today - dt.timedelta(days=days+7)  # margen extra
    by_date = {}

    for table, col_fecha, col_num in result_tables:
        sql = f"""
            SELECT {col_fecha}, {col_num}
            FROM {table}
            WHERE DATE({col_fecha}) >= DATE(?) 
            ORDER BY {col_fecha} DESC
        """
        try:
            cur = conn.execute(sql, (min_date.isoformat(),))
            for row in cur.fetchall():
                d = as_date(row[0]); num = as_text(row[1])
                if not d or not num: continue
                if d < today - dt.timedelta(days=days):  # fuera de ventana útil
                    continue
                # conservar un ganador por fecha (prioriza tabla ya existente si ya hay)
                if d not in by_date:
                    by_date[d] = (num, table)
        except Exception:
            continue

    items = [(d, by_date[d][0], by_date[d][1]) for d in sorted(by_date.keys(), reverse=True)]
    return items

def load_runs(conn, run_table):
    """Carga runs con sus timestamps y run_id, ordenados desc."""
    # detectar columnas
    col_id  = None
    col_ts  = None
    cur = conn.execute(f"PRAGMA table_info('{run_table}')")
    cols = [r[1] for r in cur.fetchall()]
    for c in cols:
        cl = c.lower()
        if col_id is None and cl in ("id","run_id"):
            col_id = c
        if col_ts is None and cl in ("created_at","fecha","datetime","ts","timestamp","created","fecha_creacion"):
            col_ts = c
    if not col_id or not col_ts:
        raise RuntimeError(f"No pude identificar columnas id/created_at en {run_table}")

    rows = []
    for r in conn.execute(f"SELECT {col_id}, {col_ts} FROM {run_table} ORDER BY {col_ts} DESC"):
        run_id = r[0]
        ts = r[1]
        # a veces la columna es fecha y hora -> convertir a datetime (o date)
        d = None
        if isinstance(ts, (dt.datetime, dt.date)):
            d = ts if isinstance(ts, dt.datetime) else dt.datetime.combine(ts, dt.time(0,0))
        else:
            # intentar parsear
            s = str(ts)
            ok = False
            for fmt in ("%Y-%m-%d %H:%M:%S","%Y-%m-%dT%H:%M:%S","%Y-%m-%d","%Y/%m/%d %H:%M:%S"):
                try:
                    d = dt.datetime.strptime(s, fmt); ok=True; break
                except Exception:
                    continue
            if not ok:
                try:
                    d = dt.datetime.fromtimestamp(float(s))
                except Exception:
                    d = None
        if d:
            rows.append((run_id, d))
    return rows

def load_candidates_for_run(conn, rc_table, run_id, topk):
    # detectar columnas
    cur = conn.execute(f"PRAGMA table_info('{rc_table}')")
    cols = [r[1] for r in cur.fetchall()]
    col_run = next((c for c in cols if c.lower() in ("run_id","id_run")), None)
    col_rank = next((c for c in cols if c.lower() in ("rank","pos","puesto")), None)
    col_num = next((c for c in cols if c.lower() in ("numero","num","candidate","cand","numero4","number")), None)
    if not (col_run and col_rank and col_num):
        raise RuntimeError(f"No pude identificar columnas en {rc_table}")

    sql = f"""
        SELECT {col_num}, {col_rank}
        FROM {rc_table}
        WHERE {col_run} = ?
        ORDER BY {col_rank} ASC
        LIMIT ?
    """
    out = []
    for n, rnk in conn.execute(sql, (run_id, topk)).fetchall():
        out.append((as_text(n), int(rnk)))
    return out

def find_latest_run_before(runs, when_dt):
    """Devuelve (run_id, ts) del run más cercano ANTES de 'when_dt'."""
    candidates = [(rid, ts) for rid, ts in runs if ts <= when_dt]
    if not candidates:
        # si no hay uno anterior, usar el más reciente
        return runs[0] if runs else (None, None)
    return sorted(candidates, key=lambda x: x[1], reverse=True)[0]

def analyze(conn, days, topk):
    run_table, rc_table = discover_run_tables(conn)
    if not run_table or not rc_table:
        raise RuntimeError("No pude descubrir tablas de runs/candidatos. ¿Guardas los runs en la DB?")

    result_tables = discover_result_tables(conn)
    if not result_tables:
        raise RuntimeError("No pude descubrir tablas de resultados/ganadores.")

    # Cargar runs
    runs = load_runs(conn, run_table)
    if not runs:
        raise RuntimeError("No hay runs guardados en la DB.")

    # Cargar últimos ganadores por día (ventana)
    winners = load_latest_winners(conn, days, result_tables)
    if not winners:
        raise RuntimeError("No encontré ganadores en la ventana solicitada.")

    records = []
    total = len(winners)
    hit_count = 0
    rr_sum = 0.0

    for fecha, ganador, tabla in winners:
        when_dt = dt.datetime.combine(fecha, dt.time(23, 59, 59))
        run_id, run_ts = find_latest_run_before(runs, when_dt)
        if run_id is None:
            status = "NO_RUN"
            rank = None
            records.append({
                "fecha": fecha.isoformat(),
                "ganador": ganador,
                "origen": tabla,
                "run_id": "",
                "run_ts": "",
                "status": status,
                "rank": ""
            })
            continue

        cand = load_candidates_for_run(conn, rc_table, run_id, topk)
        pos = next((rnk for (num, rnk) in cand if as_text(num) == as_text(ganador)), None)
        if pos is not None:
            hit_count += 1
            rr_sum += 1.0/float(pos)
            status = "HIT"
        else:
            status = "MISS"

        records.append({
            "fecha": fecha.isoformat(),
            "ganador": ganador,
            "origen": tabla,
            "run_id": run_id,
            "run_ts": run_ts.isoformat(timespec="seconds"),
            "status": status,
            "rank": ("" if pos is None else pos)
        })

    hit_rate = hit_count/total if total else 0.0
    mrr = rr_sum/total if total else 0.0

    return records, {"total_dias": total, "hits": hit_count, "misses": total-hit_count, "hit_rate": hit_rate, "mrr": mrr, "topk": topk}

def write_csv(path, records, summary):
    cols = ["fecha","ganador","origen","run_id","run_ts","status","rank"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["# resumen",
                    f"total_dias={summary['total_dias']}",
                    f"hits={summary['hits']}",
                    f"misses={summary['misses']}",
                    f"hit_rate={summary['hit_rate']:.3f}",
                    f"mrr={summary['mrr']:.3f}",
                    f"topk={summary['topk']}"])
        w.writerow(cols)
        for r in records:
            w.writerow([r.get(c,"") for c in cols])

def write_html(path, records, summary):
    def esc(x): return html.escape(str(x)) if x is not None else ""
    rows = ""
    for r in records:
        cl = "style='color:green;font-weight:600;'" if r["status"]=="HIT" else ("style='color:#999;'" if r["status"]=="NO_RUN" else "")
        rows += f"<tr><td>{esc(r['fecha'])}</td><td>{esc(r['ganador'])}</td><td>{esc(r['origen'])}</td><td>{esc(r['run_id'])}</td><td>{esc(r['run_ts'])}</td><td {cl}>{esc(r['status'])}</td><td>{esc(r['rank'])}</td></tr>\n"

    html_doc = f"""<!doctype html>
<html lang="es"><meta charset="utf-8">
<title>Análisis multi-días</title>
<style>
body{{font-family:system-ui,Segoe UI,Arial,sans-serif;padding:16px}}
h1{{margin:0 0 8px}}
.summary{{margin:10px 0 18px}}
table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #ddd;padding:6px 8px;font-size:14px}}
th{{background:#f5f5f5;text-align:left}}
tr:nth-child(even){{background:#fafafa}}
code{{background:#f6f8fa;padding:2px 4px;border-radius:3px}}
</style>
<h1>Análisis multi-días</h1>
<div class="summary">
  <div><b>Días evaluados:</b> {summary['total_dias']}</div>
  <div><b>Hits:</b> {summary['hits']} &nbsp; <b>Misses:</b> {summary['misses']}</div>
  <div><b>Hit rate:</b> {summary['hit_rate']:.3f} &nbsp; <b>MRR:</b> {summary['mrr']:.3f} &nbsp; <b>Top-K:</b> {summary['topk']}</div>
</div>
<table>
<thead><tr>
<th>Fecha</th><th>Ganador</th><th>Origen</th><th>run_id</th><th>run_ts</th><th>Veredicto</th><th>Rank</th>
</tr></thead>
<tbody>
{rows}
</tbody>
</table>
</html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_doc)

def main():
    args = parse_args()
    if not os.path.exists(args.db):
        raise SystemExit(f"No encuentro la base: {args.db}")
    if not os.path.exists(args.outdir):
        os.makedirs(args.outdir, exist_ok=True)

    with sqlite3.connect(args.db) as conn:
        conn.row_factory = sqlite3.Row
        records, summary = analyze(conn, args.days, args.topk)

    csv_path = os.path.join(args.outdir, "analisis_multidias.csv")
    html_path = os.path.join(args.outdir, "analisis_multidias.html")
    write_csv(csv_path, records, summary)
    write_html(html_path, records, summary)

    # Resumen a consola
    print("=== RESUMEN MULTI-DÍAS ===")
    print(f"Días: {summary['total_dias']}  Hits: {summary['hits']}  Misses: {summary['misses']}  HitRate: {summary['hit_rate']:.3f}  MRR: {summary['mrr']:.3f}  TopK: {summary['topk']}")
    print(f"CSV : {csv_path}")
    print(f"HTML: {html_path}")

if __name__ == "__main__":
    main()
