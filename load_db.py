#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Carga CSVs 'limpio' a SQLite (radar_premios.db) con upsert.
No usa pandas: sólo stdlib.
"""

import argparse, csv, sqlite3, sys
from pathlib import Path

SCHEMAS = {
  'astro_luna.csv': """
    CREATE TABLE IF NOT EXISTS astro_luna(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      fecha TEXT,
      signo TEXT,
      numero TEXT,
      luna TEXT
    );
  """,
  'baloto_resultados.csv': """
    CREATE TABLE IF NOT EXISTS baloto_resultados(
      sorteo INTEGER PRIMARY KEY,
      fecha TEXT,
      n1 INTEGER, n2 INTEGER, n3 INTEGER, n4 INTEGER, n5 INTEGER,
      superbalota INTEGER
    );
  """,
  'baloto_premios.csv': """
    CREATE TABLE IF NOT EXISTS baloto_premios(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      sorteo INTEGER,
      categoria TEXT,
      aciertos TEXT,
      ganadores INTEGER,
      premio TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_bp_sorteo ON baloto_premios(sorteo);
  """,
  'revancha_resultados.csv': """
    CREATE TABLE IF NOT EXISTS revancha_resultados(
      sorteo INTEGER PRIMARY KEY,
      fecha TEXT,
      n1 INTEGER, n2 INTEGER, n3 INTEGER, n4 INTEGER, n5 INTEGER,
      superbalota INTEGER
    );
  """,
  'revancha_premios.csv': """
    CREATE TABLE IF NOT EXISTS revancha_premios(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      sorteo INTEGER,
      categoria TEXT,
      aciertos TEXT,
      ganadores INTEGER,
      premio TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_rp_sorteo ON revancha_premios(sorteo);
  """,
  # 4D
  'boyaca.csv': """
    CREATE TABLE IF NOT EXISTS boyaca(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      fecha TEXT,
      numero TEXT,
      serie TEXT
    );
    CREATE UNIQUE INDEX IF NOT EXISTS uq_boyaca_fecha_num ON boyaca(fecha, numero);
  """,
  'huila.csv': """
    CREATE TABLE IF NOT EXISTS huila(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      fecha TEXT,
      numero TEXT,
      serie TEXT
    );
    CREATE UNIQUE INDEX IF NOT EXISTS uq_huila_fecha_num ON huila(fecha, numero);
  """,
  'manizales.csv': """
    CREATE TABLE IF NOT EXISTS manizales(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      fecha TEXT,
      numero TEXT,
      serie TEXT
    );
    CREATE UNIQUE INDEX IF NOT EXISTS uq_manizales_fecha_num ON manizales(fecha, numero);
  """,
  'medellin.csv': """
    CREATE TABLE IF NOT EXISTS medellin(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      fecha TEXT,
      numero TEXT,
      serie TEXT
    );
    CREATE UNIQUE INDEX IF NOT EXISTS uq_medellin_fecha_num ON medellin(fecha, numero);
  """,
  'quindio.csv': """
    CREATE TABLE IF NOT EXISTS quindio(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      fecha TEXT,
      numero TEXT,
      serie TEXT
    );
    CREATE UNIQUE INDEX IF NOT EXISTS uq_quindio_fecha_num ON quindio(fecha, numero);
  """,
  'tolima.csv': """
    CREATE TABLE IF NOT EXISTS tolima(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      fecha TEXT,
      numero TEXT,
      serie TEXT
    );
    CREATE UNIQUE INDEX IF NOT EXISTS uq_tolima_fecha_num ON tolima(fecha, numero);
  """,
}

UPSERTS = {
  'baloto_resultados.csv': ("baloto_resultados",
    "INSERT INTO baloto_resultados(sorteo,fecha,n1,n2,n3,n4,n5,superbalota) "
    "VALUES(?,?,?,?,?,?,?,?) "
    "ON CONFLICT(sorteo) DO UPDATE SET fecha=excluded.fecha,n1=excluded.n1,n2=excluded.n2,n3=excluded.n3,n4=excluded.n4,n5=excluded.n5,superbalota=excluded.superbalota"
  ),
  'revancha_resultados.csv': ("revancha_resultados",
    "INSERT INTO revancha_resultados(sorteo,fecha,n1,n2,n3,n4,n5,superbalota) "
    "VALUES(?,?,?,?,?,?,?,?) "
    "ON CONFLICT(sorteo) DO UPDATE SET fecha=excluded.fecha,n1=excluded.n1,n2=excluded.n2,n3=excluded.n3,n4=excluded.n4,n5=excluded.n5,superbalota=excluded.superbalota"
  ),
}

def run_sql_batch(conn, sql_blob: str):
    for stmt in [s.strip() for s in sql_blob.split(';') if s.strip()]:
        conn.execute(stmt+';')

def load_csv(conn, path: Path):
    name = path.name
    if name not in SCHEMAS:
        return f"[SKIP] {name}: sin esquema conocido"

    run_sql_batch(conn, SCHEMAS[name])

    with path.open('r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = [h.strip().lower() for h in next(reader, [])]
        rows = list(reader)

    # Normaliza columnas requeridas por nombre de tabla
    table = name.replace('.csv','')
    inserted = 0
    if name in UPSERTS:
        # resultados Baloto/Revancha con sorteo PK
        insert_sql = UPSERTS[name][1]
        col_order = ['sorteo','fecha','n1','n2','n3','n4','n5','superbalota']
        h2i = {h:i for i,h in enumerate(headers)}
        def val(row, key):
            return row[h2i[key]].strip() if key in h2i and h2i[key] < len(row) else None
        data = []
        for r in rows:
            if not r or all(not c for c in r): continue
            tup = tuple(val(r,k) for k in col_order)
            data.append(tup)
        with conn:
            conn.executemany(insert_sql, data)
        inserted = len(data)
    else:
        # tablas genéricas: insert simple
        placeholders = ",".join("?" for _ in headers)
        cols_sql = ",".join(headers)
        sql = f"INSERT INTO {table}({cols_sql}) VALUES({placeholders})"
        with conn:
            for r in rows:
                if not r or all(not c for c in r): continue
                try:
                    conn.execute(sql, r[:len(headers)])
                    inserted += 1
                except sqlite3.IntegrityError:
                    # unique conflict -> ignora
                    pass

    return f"[OK ] {name}: +{inserted} filas"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True)
    ap.add_argument('--data', required=True)
    ap.add_argument('--log', default=None)
    args = ap.parse_args()

    data_dir = Path(args.data)
    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")

    msgs = []
    for src in sorted(data_dir.glob("*.csv")):
        try:
            msgs.append(load_csv(conn, src))
        except Exception as e:
            msgs.append(f"[ERR] {src.name}: {e}")

    if args.log:
        Path(args.log).write_text("\n".join(msgs), encoding='utf-8')
    print("\n".join(msgs))
    return 0

if __name__ == "__main__":
    sys.exit(main())
