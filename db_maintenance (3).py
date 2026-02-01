# -*- coding: utf-8 -*-
"""
db_maintenance.py
Mantenimiento de la base: pragmas, analyze, vacuum.
Uso:
  python db_maintenance.py --db "C:\RadarPremios\radar_premios.db"
"""

import argparse
import sqlite3
from datetime import datetime

def log(msg):
    print(f"[INFO] {msg}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--no-vacuum", action="store_true", help="Omitir VACUUM")
    args = ap.parse_args()

    log(f"db_maintenance.py — {datetime.now():%Y-%m-%d %H:%M:%S}")
    log(f"Base: {args.db}")

    conn = sqlite3.connect(args.db)
    cur  = conn.cursor()

    # PRAGMAs útiles
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA synchronous=NORMAL;")
    cur.execute("PRAGMA temp_store=MEMORY;")
    cur.execute("PRAGMA cache_size=-200000;")  # aprox 200MB cache
    cur.execute("PRAGMA mmap_size=30000000000;")  # si aplica

    # ANALYZE
    cur.execute("ANALYZE;")
    conn.commit()

    if not args.no_vacuum:
        cur.execute("VACUUM;")

    # Ping simple
    try:
        cur.execute("SELECT MAX(fecha) FROM astro_luna_std")
        log("astro_luna_std OK")
    except Exception as e:
        log(f"astro_luna_std verificación: {e}")

    conn.close()
    log("Mantenimiento completado.")

if __name__ == "__main__":
    main()
