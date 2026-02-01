#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse, sqlite3

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--vacuum", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    try:
        con.execute("PRAGMA optimize;")
        if args.vacuum:
            con.execute("VACUUM;")
        con.commit()
        print("[OK ] maintenance")
    finally:
        con.close()
