# -*- coding: utf-8 -*-
"""
eval_last_run.py
Evalúa el último run (tabla runs) contra el número más reciente de astro_luna_std.
Uso:
  python eval_last_run.py --db "C:\RadarPremios\radar_premios.db"
"""

import argparse
import json
import sqlite3
from datetime import datetime

def log(msg):
    print(f"[INFO] {msg}")

def eval_run(conn):
    cur = conn.cursor()
    cur.execute("SELECT run_id, created_at, shortlist FROM runs ORDER BY run_id DESC LIMIT 1")
    row = cur.fetchone()
    if not row:
        log("No hay runs para evaluar.")
        return

    run_id, created_at, shortlist_json = row
    try:
        shortlist = json.loads(shortlist_json)
    except Exception:
        shortlist = []

    # ganador más reciente
    cur.execute("SELECT fecha, numero FROM astro_luna_std ORDER BY fecha DESC LIMIT 1")
    last = cur.fetchone()
    if not last:
        log("No hay datos en astro_luna_std para evaluar.")
        return

    fecha, ganador = last
    ganador = str(ganador).zfill(4)[-4:]
    hit = 1 if ganador in set(shortlist) else 0
    rank = (shortlist.index(ganador)+1) if ganador in shortlist else None

    log(f"Último run: {run_id} ({created_at})")
    log(f"Último sorteo: {fecha} -> ganador {ganador}")
    log(f"Shortlist: {shortlist}")
    if hit:
        log(f"✅ ACIERTO. Rank={rank}")
    else:
        log("❌ Sin acierto.")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    eval_run(conn)
    conn.close()

if __name__ == "__main__":
    main()
