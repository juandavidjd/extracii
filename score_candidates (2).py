# -*- coding: utf-8 -*-
"""
score_candidates.py
Genera candidatos para AstroLuna y los puntúa con varias señales.
Lee de astro_luna_std y (si existe) matriz_astro_luna.
Guarda CSV/HTML y registra el run en la tabla runs.
Uso típico:
  python score_candidates.py --db "C:\RadarPremios\radar_premios.db" --gen 100 --seed 12345 --top 15 --shortlist 5 \
    --export "C:\RadarPremios\candidatos_scored.csv" --export-all "C:\RadarPremios\candidatos_all.csv" \
    --report "C:\RadarPremios\candidatos_scored.html" \
    --w-hotcold 0.25 --w-cal 0.20 --w-dp 0.20 --w-exact 0.35 --cap-digitpos 60 --cap-exact 180 --cal-horizon 30
"""
import argparse
import json
import os
import random
import sqlite3
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

def log(msg):
    print(f"[INFO] {msg}", flush=True)

def get_history(conn):
    df = pd.read_sql_query("SELECT fecha, numero FROM astro_luna_std ORDER BY fecha ASC", conn)
    if df.empty:
        return df
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.dropna()
    df["numero"] = df["numero"].astype(str).str.replace(r"\D", "", regex=True).str.zfill(4).str[-4:]
    return df

def digitpos_stats(df, horizon_days=None):
    if df.empty:
        return {i: np.ones(10)/10.0 for i in range(4)}  # uniforme
    if horizon_days:
        maxd = df["fecha"].max()
        df = df[df["fecha"] >= maxd - pd.Timedelta(days=horizon_days)]
        if df.empty:
            return {i: np.ones(10)/10.0 for i in range(4)}
    arr = df["numero"].astype(str).str.zfill(4).str[-4:].values
    pos = {0: np.zeros(10), 1: np.zeros(10), 2: np.zeros(10), 3: np.zeros(10)}
    for s in arr:
        for i, ch in enumerate(s):
            pos[i][int(ch)] += 1
    for i in range(4):
        if pos[i].sum() == 0:
            pos[i] = np.ones(10)/10.0
        else:
            pos[i] = pos[i] / pos[i].sum()
    return pos

def hotcold_exact(df):
    if df.empty:
        return {}
    return df["numero"].value_counts(normalize=True).to_dict()

def last_seen_days(df):
    # mapa numero -> días desde última aparición
    if df.empty:
        return {}
    maxd = df["fecha"].max()
    last = {}
    for numero, g in df.groupby("numero"):
        last_date = g["fecha"].max()
        last[numero] = (maxd - last_date).days
    return last

def score_candidates(cands, df_hist, w_hotcold, w_cal, w_dp, w_exact, cap_digitpos, cap_exact, cal_horizon):
    # Stats globales
    hot = hotcold_exact(df_hist)
    last_seen = last_seen_days(df_hist)
    dp_recent = digitpos_stats(df_hist, horizon_days=cal_horizon)  # para componente calendario
    dp_global = digitpos_stats(df_hist, horizon_days=None)

    rows = []
    for s in cands:
        # hot/cold exacto
        s_hot = hot.get(s, 0.0)

        # digitpos global
        dpg = 0.0
        for i, ch in enumerate(s):
            dpg += dp_global[i][int(ch)]
        dpg /= 4.0

        # digitpos reciente (calendario / tendencia)
        dpr = 0.0
        for i, ch in enumerate(s):
            dpr += dp_recent[i][int(ch)]
        dpr /= 4.0

        # exact recency (más días -> decae)
        days = last_seen.get(s, cap_exact)
        s_exact = np.exp(-(min(days, cap_exact) / max(cap_exact, 1)))

        # score compuesto
        score = (
            w_hotcold * s_hot +
            w_dp      * dpg +
            w_cal     * dpr +
            w_exact   * s_exact
        )

        rows.append({
            "numero": s,
            "score_hotcold": s_hot,
            "score_digitpos": dpg,
            "score_cal": dpr,
            "score_exact": s_exact,
            "score_total": score
        })

    df = pd.DataFrame(rows).sort_values("score_total", ascending=False).reset_index(drop=True)
    return df

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--gen", type=int, default=100)
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--shortlist", type=int, default=5)
    ap.add_argument("--export", default=None)
    ap.add_argument("--export-all", dest="export_all", default=None)
    ap.add_argument("--report", default=None)
    ap.add_argument("--w-hotcold", type=float, default=0.25)
    ap.add_argument("--w-cal", type=float, default=0.25)
    ap.add_argument("--w-dp", type=float, default=0.25)
    ap.add_argument("--w-exact", type=float, default=0.25)
    ap.add_argument("--cap-digitpos", type=int, default=60)
    ap.add_argument("--cap-exact", type=int, default=180)
    ap.add_argument("--cal-horizon", type=int, default=30)
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    hist = get_history(conn)
    if hist.empty:
        log("[ERROR] Historia vacía (astro_luna_std).")
        return 2

    # Generar candidatos: muestreo estable por semilla
    random.seed(args.seed)
    seen = set()
    candidates = []
    while len(candidates) < args.gen:
        s = f"{random.randint(0,9999):04d}"
        if s not in seen:
            seen.add(s)
            candidates.append(s)

    df_scored = score_candidates(
        candidates, hist,
        w_hotcold=args["w_hotcold"] if isinstance(args, dict) else args.w_hotcold,
        w_cal=args.w_cal, w_dp=args.w_dp, w_exact=args.w_exact,
        cap_digitpos=args.cap_digitpos, cap_exact=args.cap_exact, cal_horizon=args.cal_horizon
    )

    topn = df_scored.head(args.top).copy()
    shortlist = topn.head(args.shortlist)["numero"].tolist()

    # Export
    if args.export_all:
        df_scored.to_csv(args.export_all, index=False, encoding="utf-8")
        log(f"[OK] Export All: {args.export_all}")
    if args.export:
        topn.to_csv(args.export, index=False, encoding="utf-8")
        log(f"[OK] Export Top: {args.export}")
    if args.report:
        try:
            topn.to_html(args.report, index=False, border=0, justify="center")
            log(f"[OK] Reporte HTML: {args.report}")
        except Exception as e:
            log(f"[WARN] Reporte HTML no generado: {e}")

    # Registrar run
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                seed       INTEGER,
                gen        INTEGER,
                top_n      INTEGER,
                shortlist  TEXT,
                params     TEXT
            )
        """)
        params = {
            "w_hotcold": args.w_hotcold, "w_cal": args.w_cal, "w_dp": args.w_dp, "w_exact": args.w_exact,
            "cap_digitpos": args.cap_digitpos, "cap_exact": args.cap_exact, "cal_horizon": args.cal_horizon
        }
        conn.execute("""
            INSERT INTO runs(created_at, seed, gen, top_n, shortlist, params)
            VALUES(?,?,?,?,?,?)
        """, (datetime.now().isoformat(timespec="seconds"),
              args.seed, args.gen, args.top, json.dumps(shortlist), json.dumps(params)))
        conn.commit()
        log(f"[OK] Run registrado. Shortlist: {shortlist}")
    except Exception as e:
        log(f"[WARN] No pude registrar el run: {e}")

    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
