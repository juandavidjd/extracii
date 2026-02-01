# -*- coding: utf-8 -*-
import argparse, os, sqlite3, sys

TARGETS = [
    "baloto_resultados", "revancha_resultados",
    "baloto_premios", "revancha_premios",
    "astro_luna", "boyaca", "huila", "manizales", "medellin", "quindio", "tolima"
]

def is_table(conn, name):
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND lower(name)=lower(?)", (name,)
    )
    return cur.fetchone() is not None

def is_view(conn, name):
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='view' AND lower(name)=lower(?)", (name,)
    )
    return cur.fetchone() is not None

def columns(conn, name):
    # [(cid, name, type, notnull, dflt_value, pk)]
    return conn.execute(f"PRAGMA table_info({name})").fetchall()

def text_cols(conn, name):
    cols = []
    for _, cname, ctype, *_ in columns(conn, name):
        if ctype is None:
            # sin tipo declarado: lo tratamos como texto de forma segura para TRIM
            cols.append(cname)
        else:
            t = ctype.upper()
            if "CHAR" in t or "CLOB" in t or "TEXT" in t:
                cols.append(cname)
    return cols

def trim_whitespace(conn, name):
    tcols = text_cols(conn, name)
    if not tcols:
        return 0
    cur = conn.cursor()
    total = 0
    for c in tcols:
        sql = f'UPDATE {name} SET "{c}"=TRIM("{c}") WHERE "{c}" IS NOT NULL AND (' \
              f'"{c}" LIKE " %" OR "{c}" LIKE "% " OR "{c}" LIKE CHAR(9)||"%" OR "{c}" LIKE "%"||CHAR(9))'
        cur.execute(sql)
        total += cur.rowcount if cur.rowcount is not None else 0
    conn.commit()
    return total

def dedup_exact(conn, name):
    # elimina duplicados exactos en TODAS las columnas (conserva el MIN(rowid))
    cols_meta = columns(conn, name)
    if not cols_meta:
        return 0
    col_names = [c[1] for c in cols_meta]
    quoted = [f'"{c}"' for c in col_names]
    group = ", ".join(quoted)
    sql = f'''DELETE FROM {name}
              WHERE rowid NOT IN (
                SELECT MIN(rowid) FROM {name}
                GROUP BY {group}
              );'''
    cur = conn.cursor()
    cur.execute("BEGIN")
    cur.execute(sql)
    ch = cur.rowcount if cur.rowcount is not None else 0
    conn.commit()
    return ch

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    args = ap.parse_args()

    db = os.path.abspath(args.db)
    print(f"[INFO] DB: {db}")

    conn = sqlite3.connect(db)
    conn.execute("PRAGMA foreign_keys=ON")
    changes_total = 0

    for t in TARGETS:
        if not is_table(conn, t) or is_view(conn, t):
            continue
        print(f"[TABLE] {t}")

        ch_trim = trim_whitespace(conn, t)
        if ch_trim:
            print(f"  - TRIM: {ch_trim} celdas saneadas")

        ch_dup = dedup_exact(conn, t)
        if ch_dup:
            print(f"  - DEDUP: {ch_dup} filas eliminadas")

        if not ch_trim and not ch_dup:
            print("  - OK: sin cambios")

        changes_total += (ch_trim + ch_dup)

    # mantenimiento rápido
    try:
        conn.execute("PRAGMA optimize")
    except Exception:
        pass
    conn.close()

    print(f"[DONE] Cambios totales: {changes_total}")
    sys.exit(0)

if __name__ == "__main__":
    main()
