#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ejecuta todos los .sql de un directorio (ordenados por nombre).
"""

import argparse, sqlite3, sys
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True)
    ap.add_argument('--dir', dest='sql_dir', required=True)
    ap.add_argument('--log', default=None)
    args = ap.parse_args()

    sql_dir = Path(args.sql_dir)
    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys=ON;")

    logs = []
    for p in sorted(sql_dir.glob("*.sql")):
        try:
            sql = p.read_text(encoding='utf-8')
            with conn:
                conn.executescript(sql)
            logs.append(f"[OK ] SQL: {p}")
        except Exception as e:
            logs.append(f"[ERR] SQL: {p} -> {e}")
            print("\n".join(logs))
            if args.log:
                Path(args.log).write_text("\n".join(logs), encoding='utf-8')
            return 2

    print("\n".join(logs))
    if args.log:
        Path(args.log).write_text("\n".join(logs), encoding='utf-8')
    return 0

if __name__ == "__main__":
    sys.exit(main())
