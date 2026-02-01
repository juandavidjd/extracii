# C:\RadarPremios\scripts\create_unique_indexes.py
# Uso: python -X utf8 create_unique_indexes.py --db "C:\RadarPremios\radar_premios.db"
import argparse, sqlite3, sys, re

REGIONALES = ["boyaca","huila","manizales","medellin","quindio","tolima"]

# Palabras clave para detectar la columna discriminante en *_premios
PREMIOS_HINTS = [
    "categoria","cat","tipo","nivel","descripcion","descr","detalle","rango",
    "aciertos","hits","grupos","modalidad","fraccion","fracciones","premio_id"
]

KEYS = {
    "baloto_resultados": [["sorteo"], ["fecha"]],
    "revancha_resultados": [["sorteo"], ["fecha"]],
    # Intentos estándar para *_premios
    "baloto_premios": [["sorteo","categoria"], ["sorteo","tipo"], ["sorteo","rango"]],
    "revancha_premios": [["sorteo","categoria"], ["sorteo","tipo"], ["sorteo","rango"]],
    "astro_luna": [["fecha","signo"], ["fecha","animal"], ["fecha","numero"], ["fecha","resultado"]],
}
for t in REGIONALES:
    KEYS[t] = [["fecha","numero"], ["fecha","resultado"], ["fecha","premio"]]

def table_exists(conn, name):
    cur = conn.execute("SELECT 1 FROM sqlite_master WHERE name=? AND type='table'", (name,))
    return cur.fetchone() is not None

def get_cols(conn, table):
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]

def first_key_if_exists(have, combos):
    for combo in combos:
        if all(c in have for c in combo):
            return combo
    return None

def guess_premios_key(have):
    # Queremos (sorteo, X) donde X sea una columna con pinta de categoría/tipo
    if "sorteo" not in have:
        return None
    lowered = [c.lower() for c in have]
    # 1) Buscar por hints
    for c in have:
        cl = c.lower()
        if cl == "sorteo":
            continue
        if any(h in cl for h in PREMIOS_HINTS):
            return ["sorteo", c]
    # 2) Si existe 'descripcion' exacta
    if "descripcion" in lowered:
        return ["sorteo", have[lowered.index("descripcion")]]
    # 3) Como último recurso seguro: no inventar
    return None

def dedup(conn, table, cols):
    keylist = ", ".join(cols)
    conn.execute(f"""
        DELETE FROM {table}
        WHERE rowid NOT IN (SELECT MIN(rowid) FROM {table} GROUP BY {keylist})
    """)

def create_unique(conn, table, cols):
    idx = f"uq_{table}_" + "_".join(cols)
    colsql = ", ".join(cols)
    conn.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {idx} ON {table}({colsql})")

def create_supporting_indexes(conn, table, have):
    if "fecha" in have:
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_fecha ON {table}(fecha)")
    if "sorteo" in have:
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_sorteo ON {table}(sorteo)")

def process_table(conn, table):
    if not table_exists(conn, table):
        print(f"[SKIP] {table}: no existe.")
        return False
    have = get_cols(conn, table)
    key = first_key_if_exists(have, KEYS.get(table, []))
    if not key and table in ("baloto_premios","revancha_premios"):
        key = guess_premios_key(have)  # heurística
    if key:
        print(f"[*] {table}: clave natural -> ({', '.join(key)})")
        dedup(conn, table, key)
        create_unique(conn, table, key)
        created = True
    else:
        print(f"[SKIP] {table}: sin combinación de columnas confiable para índice único.")
        created = False
    create_supporting_indexes(conn, table, have)
    return created

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")

    try:
        total = 0
        for t in ["baloto_resultados","revancha_resultados","baloto_premios","revancha_premios","astro_luna"] + REGIONALES:
            if process_table(conn, t):
                total += 1
        conn.execute("PRAGMA optimize")
        conn.commit()
        print(f"✅ Índices únicos creados/asegurados en {total} tablas (cuando aplicaba).")
    finally:
        conn.close()

if __name__ == "__main__":
    sys.exit(main())
