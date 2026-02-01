# C:\RadarPremios\scripts\inspect_db.py
# Lista tablas y vistas con tamaño y primeras columnas
import sqlite3, os, sys
DB = r"C:\RadarPremios\radar_premios.db"

def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print("== Tablas y Vistas ==")
    for row in cur.execute("SELECT name, type, COALESCE(sql,'') AS sql FROM sqlite_master WHERE type IN ('table','view') ORDER BY type, name"):
        name = row["name"]
        typ  = row["type"]
        sql  = row["sql"] or ""
        print(f"- {typ:5s} {name}")
        if typ == "table":
            try:
                cnt = cur.execute(f"SELECT COUNT(*) FROM [{name}]").fetchone()[0]
            except Exception:
                cnt = "?"
            cols = [r[1] for r in cur.execute(f"PRAGMA table_info([{name}])")]
            print(f"    filas={cnt} cols={', '.join(cols[:8])}{'...' if len(cols)>8 else ''}")
        else:
            print(f"    def={sql[:90].replace(chr(10),' ')}{'...' if len(sql)>90 else ''}")
    conn.close()

if __name__ == "__main__":
    main()
