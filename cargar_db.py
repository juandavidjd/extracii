# -*- coding: utf-8 -*-
import argparse, csv, hashlib, os, sqlite3, sys

def log(msg):
    print(msg, flush=True)

def safe_table_name(path):
    name = os.path.splitext(os.path.basename(path))[0]
    # Mantén nombre tal cual aparece en tus tablas previas
    return name

def sniff_delimiter(sample_bytes):
    sample = sample_bytes.decode('utf-8', errors='ignore')
    # Heurística simple: cuenta comas vs punto y coma
    c = sample.count(',')
    s = sample.count(';')
    if s > c:
        return ';'
    return ','

def read_rows(csv_path):
    # Abre en binario para sniff, luego reabre en texto con el delimitador correcto
    with open(csv_path, 'rb') as fb:
        sample = fb.read(4096) or b''
    delim = sniff_delimiter(sample)
    # Relee en texto
    with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f, delimiter=delim)
        rows = list(reader)

    if not rows:
        return [], []

    # Normaliza encabezados: strip espacios
    headers = [h.strip() for h in rows[0]]
    data = []
    for r in rows[1:]:
        # Asegura longitud = headers (rellena con vacío o recorta)
        if len(r) < len(headers):
            r = r + [''] * (len(headers) - len(r))
        elif len(r) > len(headers):
            r = r[:len(headers)]
        data.append([ (v.strip() if isinstance(v, str) else v) for v in r ])
    return headers, data

def ensure_table(conn, table, headers):
    # Crea tabla si no existe, añade columnas faltantes, añade _rowhash y su índice único.
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table,))
    exists = cur.fetchone() is not None
    if not exists:
        cols_sql = ", ".join('"{}" TEXT'.format(h) for h in headers)
        sql = f'CREATE TABLE "{table}" ({cols_sql});'
        conn.execute(sql)

    # Trae esquema actual
    cur = conn.execute(f'PRAGMA table_info("{table}");')
    present = {row[1] for row in cur.fetchall()}  # set de nombres de columna

    # Añade columnas faltantes
    for h in headers:
        if h not in present:
            conn.execute(f'ALTER TABLE "{table}" ADD COLUMN "{h}" TEXT;')
    # Asegura _rowhash
    cur = conn.execute(f'PRAGMA table_info("{table}");')
    present = {row[1] for row in cur.fetchall()}
    if "_rowhash" not in present:
        conn.execute(f'ALTER TABLE "{table}" ADD COLUMN "_rowhash" TEXT;')
    # Índice único para deduplicar por hash
    conn.execute(f'CREATE UNIQUE INDEX IF NOT EXISTS "ux_{table}__rowhash" ON "{table}"(_rowhash);')

def row_hash(values):
    # Junta con separador que no aparece en números por lo general
    joined = "\u241F".join([str(v) if v is not None else "" for v in values])
    return hashlib.sha1(joined.encode('utf-8', errors='ignore')).hexdigest()

def upsert_rows(conn, table, headers, data):
    if not data:
        return 0, 0
    # Inserta con OR IGNORE para respetar cualquier UNIQUE existente y nuestro _rowhash
    cols = ', '.join('"{}"'.format(h) for h in headers)
    placeholders = ', '.join(['?'] * (len(headers) + 1))  # +1 por _rowhash
    sql = f'INSERT OR IGNORE INTO "{table}" ({cols}, "_rowhash") VALUES ({placeholders});'

    to_insert = []
    for r in data:
        h = row_hash(r)
        to_insert.append(tuple(r + [h]))
    cur_before = conn.execute(f'SELECT COUNT(1) FROM "{table}";').fetchone()[0]
    conn.executemany(sql, to_insert)
    cur_after = conn.execute(f'SELECT COUNT(1) FROM "{table}";').fetchone()[0]
    inserted = cur_after - cur_before
    ignored = len(to_insert) - inserted
    return inserted, ignored

def process_dir(db_path, src_dir):
    total_ins = total_ign = 0
    with sqlite3.connect(db_path) as conn:
        conn.execute('PRAGMA journal_mode = WAL;')
        conn.execute('PRAGMA synchronous = NORMAL;')
        conn.execute('PRAGMA temp_store = MEMORY;')
        for root, _, files in os.walk(src_dir):
            for fn in sorted(files):
                if not fn.lower().endswith('.csv'):
                    continue
                csv_path = os.path.join(root, fn)
                table = safe_table_name(csv_path)
                try:
                    headers, data = read_rows(csv_path)
                    if not headers:
                        log(f'[WARN] {table}: CSV vacío, omitido.')
                        continue
                    ensure_table(conn, table, headers)
                    ins, ign = upsert_rows(conn, table, headers, data)
                    conn.commit()
                    total_ins += ins; total_ign += ign
                    log(f'[OK ] {table}: +{ins} filas (omitidas: {ign})')
                except Exception as ex:
                    conn.rollback()
                    log(f'[ERR] {table}: {ex}')
                    # No re-levantar: permite continuar con otros archivos
    return total_ins, total_ign

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True, help='Ruta a radar_premios.db')
    ap.add_argument('--src', required=True, help='Directorio con CSVs limpios')
    args = ap.parse_args()

    if not os.path.isdir(args.src):
        log(f'[FATAL] No existe directorio --src: {args.src}')
        sys.exit(2)

    os.makedirs(os.path.dirname(args.db) or '.', exist_ok=True)
    ins, ign = process_dir(args.db, args.src)
    log(f'[OK ] cargar_db: insertadas={ins}, ignoradas={ign}')
    sys.exit(0)

if __name__ == '__main__':
    main()
