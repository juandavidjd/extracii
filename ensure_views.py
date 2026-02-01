# -*- coding: utf-8 -*-
"""
ensure_views.py
Crea/actualiza el VIEW astro_luna_std(fecha, numero, signo) sobre la tabla astro_luna
mapeando nombres reales a estándar (fecha/numero/signo).
Uso:
  python ensure_views.py --db "C:\RadarPremios\radar_premios.db"
"""
import argparse
import sqlite3
import sys
import unicodedata

def norm(s):
    if s is None: return ""
    s = str(s)
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")  # quita acentos
    s = s.strip().lower()
    s = s.replace("\ufeff", "")  # BOM
    s = s.replace(" ", "_").replace("-", "_")
    return s

def pick(colnames_norm, original_names, candidates):
    for cand in candidates:
        if cand in colnames_norm:
            idx = colnames_norm.index(cand)
            return original_names[idx]
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="Ruta a la base SQLite")
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    row = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='astro_luna'").fetchone()
    if not row:
        print("[ERROR] No existe la tabla 'astro_luna'.", file=sys.stderr)
        sys.exit(2)

    cols = cur.execute("PRAGMA table_info(astro_luna)").fetchall()
    if not cols:
        print("[ERROR] 'astro_luna' sin columnas.", file=sys.stderr)
        sys.exit(2)

    original = [c["name"] for c in cols]
    normalized = [norm(c["name"]) for c in cols]

    fecha_cands   = ["fecha", "fecha_sorteo", "dia", "dia_sorteo", "date", "fech"]
    numero_cands  = ["numero", "ganador", "num", "n"]
    signo_cands   = ["signo", "zodiaco", "zodiac", "sign"]

    col_fecha  = pick(normalized, original, fecha_cands)
    col_numero = pick(normalized, original, numero_cands)
    col_signo  = pick(normalized, original, signo_cands)

    if not col_fecha or not col_numero:
        print("[ERROR] No pude mapear columnas mínimas en astro_luna. Encontradas:", original, file=sys.stderr)
        sys.exit(3)

    cur.execute("DROP VIEW IF EXISTS astro_luna_std")
    if col_signo:
        view_sql = f'''CREATE VIEW astro_luna_std AS
                       SELECT "{col_fecha}"  AS fecha,
                              "{col_numero}" AS numero,
                              "{col_signo}"  AS signo
                       FROM astro_luna'''
    else:
        view_sql = f'''CREATE VIEW astro_luna_std AS
                       SELECT "{col_fecha}"  AS fecha,
                              "{col_numero}" AS numero,
                              ''             AS signo
                       FROM astro_luna'''
    cur.execute(view_sql)

    # Alias histórico si algún script esperaba este nombre:
    cur.execute("DROP VIEW IF EXISTS astro_luna_matrix")
    cur.execute("""
        CREATE VIEW astro_luna_matrix AS
        SELECT * FROM matriz_astro_luna
    """)

    conn.commit()
    print(f"[OK] astro_luna_std creado. Mapeo: fecha<-{col_fecha} | numero<-{col_numero} | signo<-{col_signo or '(vacío)'}")

if __name__ == "__main__":
    sys.exit(main())
