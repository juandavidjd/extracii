import argparse, sqlite3 as sql, sys
p=argparse.ArgumentParser(); p.add_argument("--db", required=True)
args=p.parse_args()
conn=sql.connect(args.db)

DDL=[
# vistas mínimas seguras si no existen
"""CREATE TABLE IF NOT EXISTS meta_kv (k TEXT PRIMARY KEY, v TEXT);""",
"""CREATE VIEW IF NOT EXISTS all_premios_std AS
   SELECT 'baloto' AS juego, * FROM baloto_premios
   UNION ALL
   SELECT 'revancha' AS juego, * FROM revancha_premios;""",
"""CREATE VIEW IF NOT EXISTS all_std AS
   SELECT * FROM baloto_resultados
   UNION ALL
   SELECT * FROM revancha_resultados;"""
]

for stmt in DDL:
    try: conn.executescript(stmt)
    except Exception as e: print("[WARN]",e)

print("[OK ] fix_schema")
conn.commit(); conn.close()
sys.exit(0)
