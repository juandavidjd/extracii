# -*- coding: utf-8 -*-
import argparse, sqlite3, os, glob

def tail(path, n=60):
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return ''.join(f.readlines()[-n:])
    except Exception:
        return "(sin log)"

ap=argparse.ArgumentParser()
ap.add_argument("--db", required=True)
ap.add_argument("--logs", required=True)
ap.add_argument("--game", choices=["baloto","revancha"], required=True)
args=ap.parse_args()

# último log master
logs = sorted(glob.glob(os.path.join(args.logs, "master_*.log")))
log_path = logs[-1] if logs else None
print("=== TAIL LOG MASTER ===")
print(tail(log_path) if log_path else "(no hay logs)")

conn=sqlite3.connect(args.db)
res_std=f"{args.game}_resultados_std"
pre_std=f"{args.game}_premios_std"

print("\n=== HEAD recientes ===")
for t in (res_std, pre_std):
    try:
        cur=conn.execute(f"select * from {t} order by sorteo desc limit 5;")
        cols=[d[0] for d in cur.description]
        print(f"\n{t} -> columnas: {cols}")
        for row in cur.fetchall():
            print(row)
    except Exception as e:
        print(f"{t}: error -> {e}")
