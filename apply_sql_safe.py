# -*- coding: utf-8 -*-
import argparse, glob, sqlite3, os, sys

def exec_sql(cur, sql_text, path):
    try:
        cur.executescript(sql_text)
        print(f"[OK ] SQL: {path}")
    except sqlite3.Error as e:
        # degradar a WARN y seguir
        print(f"[WARN] SQL: {path} -> {e}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--file")
    g.add_argument("--glob")
    args = ap.parse_args()
    conn = sqlite3.connect(args.db); cur = conn.cursor()

    files = []
    if args.file:
        files = [args.file]
    else:
        files = sorted(glob.glob(args.glob))

    for f in files:
        if not os.path.isfile(f):
            print(f"[WARN] No existe: {f}")
            continue
        with open(f, "r", encoding="utf-8") as fh:
            sql_text = fh.read()
        exec_sql(cur, sql_text, f)

    conn.commit(); conn.close()
    print("[OK ] apply_sql_safe")

if __name__ == "__main__":
    main()
