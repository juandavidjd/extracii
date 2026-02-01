# -*- coding: utf-8 -*-
"""
Lista objetos de la DB.
Uso:
    python check_db.py --db "C:/RadarPremios/radar_premios.db"
"""
import argparse, sqlite3

ap = argparse.ArgumentParser(description="Listar objetos en SQLite.")
ap.add_argument("--db", required=True, help="Ruta a la DB SQLite.")
args = ap.parse_args()

con = sqlite3.connect(args.db)
cur = con.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view') ORDER BY name;")
rows = cur.fetchall()
print("[OK ] Objetos en DB:")
for (name,) in rows:
    print(f" - {name}")
con.close()
