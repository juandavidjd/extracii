# -*- coding: utf-8 -*-
import argparse, csv, io, os, sys

def log(msg): 
    print(msg, flush=True)

def sniff_delimiter(sample_bytes):
    sample = sample_bytes.decode('utf-8', errors='ignore')
    return ';' if sample.count(';') > sample.count(',') else ','

def clean_file(src_path, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    # Sniff delimitador
    with open(src_path, 'rb') as fb:
        sample = fb.read(4096) or b''
    delim = sniff_delimiter(sample)

    # Lee => normaliza => escribe con coma
    rows = []
    with open(src_path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f, delimiter=delim)
        for row in reader:
            rows.append([ (c.strip() if isinstance(c, str) else c) for c in row ])

    if not rows:
        # genera archivo vacío
        open(out_path, 'w', encoding='utf-8', newline='').close()
        return 0

    headers = [h.strip() for h in rows[0]]
    data = rows[1:]

    with open(out_path, 'w', encoding='utf-8', newline='') as g:
        w = csv.writer(g, delimiter=',', lineterminator='\n')
        w.writerow(headers)
        w.writerows(data)
    return len(data)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True, help='Directorio con CSVs crudos')
    ap.add_argument('--out', required=True, help='Directorio destino CSVs limpios')
    args = ap.parse_args()

    if not os.path.isdir(args.src):
        log(f'[FATAL] No existe --src: {args.src}')
        sys.exit(2)
    os.makedirs(args.out, exist_ok=True)

    total = 0
    for root, _, files in os.walk(args.src):
        for fn in sorted(files):
            if not fn.lower().endswith('.csv'):
                continue
            src_path = os.path.join(root, fn)
            out_path = os.path.join(args.out, fn)
            try:
                n = clean_file(src_path, out_path)
                total += n
                log(f'[OK ] Limpio: {fn} -> {fn} (+{n})')
            except Exception as ex:
                log(f'[ERR] {fn}: {ex}')
                # Continúa con el resto

    log('[OK ] Limpiar CSVs')
    sys.exit(0)

if __name__ == '__main__':
    main()
