#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Valida cabeceras mínimas por archivo. No falla por columnas extra.
Usa ‘--strict 1’ si quieres que falle cuando falte alguna requerida.
"""

import argparse, sys
from pathlib import Path

# Esquemas mínimos requeridos (ajústalos a tu formato actual)
REQUIRED_SCHEMA = {
  'astro_luna.csv': ['fecha','signo','numero','luna'],
  'baloto_premios.csv': ['sorteo','categoria','aciertos','ganadores','premio'],
  'baloto_resultados.csv': ['sorteo','fecha','n1','n2','n3','n4','n5','superbalota'],
  'revancha_premios.csv': ['sorteo','categoria','aciertos','ganadores','premio'],
  'revancha_resultados.csv': ['sorteo','fecha','n1','n2','n3','n4','n5','superbalota'],
  # Loterías 4D (puedes replicar por cada archivo regional)
  'boyaca.csv': ['fecha','numero','serie'],
  'huila.csv': ['fecha','numero','serie'],
  'manizales.csv': ['fecha','numero','serie'],
  'medellin.csv': ['fecha','numero','serie'],
  'quindio.csv': ['fecha','numero','serie'],
  'tolima.csv': ['fecha','numero','serie'],
}

def parse_header(path: Path):
    try:
        with path.open('r', encoding='utf-8') as f:
            first = f.readline().strip()
    except UnicodeDecodeError:
        with path.open('r', encoding='latin1', errors='ignore') as f:
            first = f.readline().strip()
    if not first:
        return []
    # separadores típicos
    for sep in (',',';','\t','|'):
        if sep in first:
            return [h.strip().lower() for h in first.split(sep)]
    # sin separador
    return [first.strip().lower()]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='indir', required=True)
    ap.add_argument('--strict', type=int, default=0)
    ap.add_argument('--log', dest='logfile', default=None)
    args = ap.parse_args()

    indir = Path(args.indir)
    logs = []
    ok = True

    for req_name, required_cols in REQUIRED_SCHEMA.items():
        p = indir / req_name
        if not p.exists():
            logs.append(f"[WARN] Falta archivo: {req_name}")
            if args.strict:
                ok = False
            continue
        header = parse_header(p)
        if not header:
            logs.append(f"[ERR ] Vacío o sin header: {req_name}")
            ok = False
            continue
        missing = [c for c in required_cols if c not in header]
        if missing:
            logs.append(f"[ERR ] {req_name} faltan: {missing} (header={header})")
            if args.strict:
                ok = False
        else:
            logs.append(f"[OK  ] {req_name} ✓ (header={header})")

    if args.logfile:
        Path(args.logfile).write_text("\n".join(logs), encoding='utf-8')
    print("\n".join(logs))
    return 0 if ok else 2

if __name__ == "__main__":
    sys.exit(main())
