# -*- coding: utf-8 -*-
"""
actualizar_base_astroluna.py
- Asegura vistas (alias) y crea índices útiles para AstroLuna
Uso:
  python actualizar_base_astroluna.py --db "C:\RadarPremios\radar_premios.db"
"""

import argparse
import sqlite3
from datetime import datetime

def log(msg):
    print(f"[INFO] {msg}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="Ruta a la base SQLite")
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    cur  = conn.cursor()

    log(f"Base: {args.db}")

    # Alias por compatibilidad si alguien consulta astro_luna_matrix
    cur.execute("DROP VIEW IF EXISTS astro_luna_matrix")
    cur.execute("CREATE VIEW astro_luna_matrix AS SELECT * FROM matriz_astro_luna")

    # Vistas rápidas
    cur.execute("DROP VIEW IF EXISTS astro_luna_recent")
    cur.execute("""
        CREATE VIEW astro_luna_recent AS
        SELECT * FROM astro_luna_std
        WHERE date(fecha) >= date('now','-120 day')
    """)

    # Índices (IF NOT EXISTS)
    # Sobre astro_luna (tabla física) - no sabemos nombres reales, pero al menos (numero)
    # Intento seguro: crear índice si existe la columna.
    def ensure_index(table, col, name):
        try:
            cur.execute(f'CREATE INDEX IF NOT EXISTS {name} ON {table}("{col}")')
        except sqlite3.OperationalError:
            pass

    # Intentar índices en tabla física astro_luna
    cols = [r[1] for r in cur.execute("PRAGMA table_info(astro_luna)").fetchall()]
    if "fecha" in cols:   ensure_index("astro_luna", "fecha",  "idx_astro_luna_fecha")
    if "Fecha" in cols:   ensure_index("astro_luna", "Fecha",  "idx_astro_luna_Fecha")
    if "numero" in cols:  ensure_index("astro_luna", "numero", "idx_astro_luna_numero")
    if "ganador" in cols: ensure_index("astro_luna", "ganador","idx_astro_luna_ganador")

    # Índices sobre matriz
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS idx_matriz_astro_fecha ON matriz_astro_luna(fecha)")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS idx_matriz_astro_num ON matriz_astro_luna(numero)")
    except sqlite3.OperationalError:
        pass

    # Tabla runs para registrar ejecuciones de scoring si no existe
    cur.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            seed       INTEGER,
            gen        INTEGER,
            top_n      INTEGER,
            shortlist  TEXT,
            params     TEXT
        )
    """)

    conn.commit()

    # Checks rápidos
    try:
        row = cur.execute("SELECT COUNT(*), MAX(fecha) FROM astro_luna_std").fetchone()
        log(f"astro_luna_std -> filas={row[0]} max_fecha={row[1]}")
    except Exception as e:
        log(f"astro_luna_std check: {e}")

    try:
        c = cur.execute("SELECT COUNT(*) FROM matriz_astro_luna").fetchone()[0]
        log(f"matriz_astro_luna -> filas={c}")
    except Exception as e:
        log(f"matriz_astro_luna check: {e}")

    log("Ajustes e índices aplicados.")
    conn.close()

if __name__ == "__main__":
    main()
