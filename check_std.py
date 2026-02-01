import argparse, sqlite3 as sql, sys
p=argparse.ArgumentParser(); p.add_argument("--db", required=True)
args=p.parse_args()
conn=sql.connect(args.db)
need=["baloto_resultados_std","revancha_resultados_std","all_std"]
ok=True
for v in need:
    try:
        conn.execute(f"SELECT 1 FROM {v} LIMIT 1;").fetchone()
    except Exception as e:
        ok=False; print(f"[WARN] Falta vista/tabla: {v} ({e})")
if ok: print("[OK ] STD")
conn.close(); sys.exit(0 if ok else 1)
