#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Filtra IN-PLACE los CSV en data\crudo para eliminar 'HB'/'NOOP', -1 en campos numéricos,
fechas vacías/invalidas y filas completamente vacías. Está pensado para ejecutarse
INMEDIATAMENTE después de correr los scrapers, antes de sanitize_csvs.py.
"""
import argparse, csv, os, sys, io, tempfile, shutil
from datetime import datetime

HB_TOKENS = {"HB","HEARTBEAT","NOOP","HEART-BEAT","PING"}
NUM_COL_CANDIDATES = {"numero","número","num","n","N","NUMERO"}
DATE_COL_CANDIDATES = {"fecha","Fecha","FECHA","date","Date"}

def parse_date_maybe(x: str):
    x=(x or "").strip()
    if not x: return None
    for f in ("%Y-%m-%d","%d/%m/%Y","%d-%m-%Y","%Y/%m/%d","%d/%m/%y","%Y.%m.%d","%d.%m.%Y"):
        try: 
            return datetime.strptime(x,f).date()
        except: 
            pass
    return None

def looks_like_int(x:str):
    try: int(x); return True
    except: return False

def is_neg_digit_row(headers, row):
    for i,h in enumerate(headers):
        hl=h.strip().lower()
        if hl in [c.lower() for c in NUM_COL_CANDIDATES] or hl.startswith(("d","n","b","s")):
            if i < len(row):
                sv=(row[i] or "").strip()
                if sv and sv.lstrip("-").isdigit() and int(sv) < 0:
                    return True
    return False

def has_hb(row):
    for v in row:
        if (v or "").strip().upper() in HB_TOKENS:
            return True
    return False

def bad_or_empty_date(headers, row):
    for i,h in enumerate(headers):
        if h in DATE_COL_CANDIDATES or h.lower() in DATE_COL_CANDIDATES:
            sv=(row[i] if i < len(row) else "").strip()
            if not sv: return True
            if parse_date_maybe(sv) is None: return True
    return False

def is_all_empty(row):
    return all((v is None or str(v).strip()=="") for v in row)

def filter_csv(path):
    kept=0; dropped=0
    with io.open(path,"r",encoding="utf-8-sig",newline="") as f:
        rd=csv.reader(f)
        try: headers=[h.replace("\ufeff","").strip() for h in next(rd)]
        except StopIteration:
            return (0,0,headers if 'headers' in locals() else [])
        rows=list(rd)

    tmp_fd, tmp_path = tempfile.mkstemp(prefix="filtered_", suffix=".csv")
    os.close(tmp_fd)
    with io.open(tmp_path,"w",encoding="utf-8",newline="") as fo:
        wr=csv.writer(fo, lineterminator="\n")
        wr.writerow(headers)
        for r in rows:
            # normaliza longitudes
            if len(r) < len(headers): r = r + [""]*(len(headers)-len(r))
            elif len(r) > len(headers): r = r[:len(headers)]

            if is_all_empty(r): dropped+=1; continue
            if has_hb(r): dropped+=1; continue
            if is_neg_digit_row(headers, r): dropped+=1; continue
            if bad_or_empty_date(headers, r): dropped+=1; continue

            wr.writerow([ (c or "").replace("\r\n","\n").replace("\r","\n").strip() for c in r ])
            kept+=1

    # reemplazo atómico
    shutil.move(tmp_path, path)
    return (kept, dropped, headers)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--path", required=True, help=r"Ruta de entrada, ej: C:\RadarPremios\data\crudo")
    args=ap.parse_args()
    p=args.path
    if not os.path.isdir(p):
        print(f"[ERR] Carpeta no existe: {p}", file=sys.stderr)
        sys.exit(2)

    files=[fn for fn in os.listdir(p) if fn.lower().endswith(".csv")]
    if not files:
        print(f"[INFO] No hay CSV en {p}")
        return

    print(f"[INFO] Filtrando {len(files)} archivo(s) en '{p}'")
    for fn in sorted(files):
        ip=os.path.join(p,fn)
        try:
            kept, dropped, _ = filter_csv(ip)
            print(f"[OK ] {fn}: kept={kept} dropped={dropped}")
        except Exception as e:
            print(f"[ERR] {fn}: {e}", file=sys.stderr)
            sys.exit(3)

if __name__=="__main__":
    main()
