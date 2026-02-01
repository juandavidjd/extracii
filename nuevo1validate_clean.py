# C:\RadarPremios\scripts\validate_clean.py
import argparse, os, csv
from datetime import datetime, date, time, timedelta

def safe_open_read(path):
    for enc in ("utf-8","utf-8-sig","latin-1"):
        try: return open(path,"r",encoding=enc,newline="")
        except Exception as e: last=e
    raise last

def read_csv_dicts(path):
    with safe_open_read(path) as f:
        sample=f.read(4096); f.seek(0)
        try:
            dialect=csv.Sniffer().sniff(sample)
        except Exception:
            dialect="excel"
        r=csv.DictReader(f,dialect=dialect)
        if r.fieldnames: r.fieldnames=[(h or "").strip() for h in r.fieldnames]
        rows=[]
        for row in r:
            rows.append({(k or "").strip(): (v.strip() if isinstance(v,str) else v) for k,v in row.items()})
        return r.fieldnames or [], rows

def parse_hora(hhmm):
    hh,mm = hhmm.split(":"); return time(int(hh),int(mm))

def parse_date(s):
    s=(s or "").strip()
    for fmt in ("%Y-%m-%d","%Y/%m/%d","%d/%m/%Y"):
        try: return datetime.strptime(s,fmt).date()
        except: pass
    raise ValueError(f"Fecha inválida: '{s}'")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--dst", default=r"C:\RadarPremios\data\limpio")
    ap.add_argument("--file", default="astro_luna.csv")
    ap.add_argument("--expect", default="fecha,ganador")
    ap.add_argument("--hora-corte", default="11:00")
    args=ap.parse_args()

    path=os.path.join(args.dst,args.file)
    if not os.path.exists(path):
        print(f"[ERROR] Requerido no existe: {path}"); return 2

    headers, rows = read_csv_dicts(path)
    if not rows:
        print(f"[ERROR] Archivo vacío (solo header): {path}"); return 2

    expected=[c.strip() for c in args.expect.split(",") if c.strip()]
    missing=[c for c in expected if c not in headers]
    if missing:
        print(f"[ERROR] Faltan headers {missing} en {args.file}. Encontrados: {headers}")
        return 3

    col="fecha"
    if col not in headers:
        print(f"[ERROR] Columna '{col}' no existe en {args.file}"); return 4

    dates=[]
    for r in rows:
        try: dates.append(parse_date(r.get(col,"")))
        except: pass
    if not dates:
        print(f"[ERROR] No se pudieron parsear fechas en {args.file}.{col}"); return 4

    maxf=max(dates)
    now=datetime.now()
    hoy=now.date()
    cut_dt=datetime.combine(hoy, parse_hora(args.hora_corte))
    ok_hoy=(maxf==hoy)
    ok_ayer=(now<cut_dt and maxf==hoy-timedelta(days=1))
    if not (ok_hoy or ok_ayer):
        print(f"[ERROR] Freshness: max(fecha)={maxf} ≠ hoy {hoy} ni ayer (antes de {args.hora_corte})"); return 4

    print(f"[OK] Validación limpia/frescura OK. max(fecha)={maxf}, headers={headers}")
    return 0

if __name__=="__main__":
    import sys; sys.exit(main())
