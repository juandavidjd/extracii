import argparse, glob, os, sqlite3 as sql, sys
p=argparse.ArgumentParser()
p.add_argument("--db", required=True)
g=p.add_mutually_exclusive_group(required=True)
g.add_argument("--file")
g.add_argument("--glob")
args=p.parse_args()

paths=[]
if args.file: 
    if os.path.exists(args.file): paths=[args.file]
    else: print(f"[WARN] No hay SQL a aplicar."); sys.exit(0)
if args.glob: paths=sorted(glob.glob(args.glob))
if not paths: print("[WARN] No hay SQL a aplicar."); sys.exit(0)

conn=sql.connect(args.db)
for fp in paths:
    try:
        with open(fp,"r",encoding="utf-8") as fh:
            conn.executescript(fh.read())
        print(f"[OK ] SQL: {fp}")
    except Exception as e:
        print(f"[ERR] SQL: {fp} -> {e}")
conn.commit(); conn.close()
print("[OK ] apply_sql_safe")
sys.exit(0)
