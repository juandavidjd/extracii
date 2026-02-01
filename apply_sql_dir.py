#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aplica todos los .sql de un directorio a la DB (en orden alfabético).
Uso:
  py -3 -X utf8 apply_sql_dir.py --db C:\RadarPremios\radar_premios.db --dir C:\RadarPremios\scripts\sql\apply
"""
import argparse, os, sys, sqlite3, io

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--dir", required=True)
    a=ap.parse_args()
    if not os.path.isdir(a.dir):
        print(f"[WARN] No hay SQL dir: {a.dir}")
        sys.exit(0)
    conn=sqlite3.connect(a.db)
    try:
        files=[fn for fn in os.listdir(a.dir) if fn.lower().endswith(".sql")]
        for fn in sorted(files):
            path=os.path.join(a.dir, fn)
            print(f"[OK ] SQL: {path}")
            with io.open(path,"r",encoding="utf-8") as f:
                sql=f.read()
            try:
                conn.executescript(sql)
                conn.commit()
            except Exception as e:
                print(f"[ERR] SQL {fn}: {e}", file=sys.stderr)
                conn.rollback()
                sys.exit(2)
        print("[OK ] sql_exec")
    finally:
        conn.close()

if __name__=="__main__":
    main()
