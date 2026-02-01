import argparse, sqlite3 as sql, sys
p=argparse.ArgumentParser()
p.add_argument("--db", required=True)
p.add_argument("--game", required=True, choices=["baloto","revancha","4d"])
p.add_argument("--min", type=int, required=True)
args=p.parse_args()

conn=sql.connect(args.db)
if args.game in ("baloto","revancha"):
    tbl=f"{args.game}_resultados"
    n=conn.execute(f"SELECT COUNT(*) FROM {tbl};").fetchone()[0]
else:
    n=0
conn.close()
print(f"[INFO] {args.game}: sorteos={n}")
sys.exit(0 if n>=args.min else 1)
