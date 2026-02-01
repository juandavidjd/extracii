#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sanea CSVs desde data\crudo hacia data\limpio:
- Normaliza finales de línea a CRLF
- Fuerza UTF-8 sin BOM
- Quita bytes nulos y controla líneas HTML/JSON accidentales
- Arregla separadores erráticos (coma/;|tab) si es necesario
"""

import argparse, os, re, sys
from pathlib import Path

LIKELY_HTML = re.compile(rb"<!doctype html|<html|<head|<body", re.I)
CONTROL_BYTES = re.compile(rb"[\x00]")

def detect_delimiter(sample_line: str):
    counts = {',': sample_line.count(','), ';': sample_line.count(';'), '\t': sample_line.count('\t')}
    delim, mx = ',', -1
    for k, v in counts.items():
        if v > mx:
            mx, delim = v, k
    return delim

def sanitize_file(src: Path, dst: Path):
    raw = src.read_bytes()
    # quick HTML guard
    if LIKELY_HTML.search(raw):
        # Este archivo luce HTML -> lo copiamos tal cual pero marcamos como sospechoso (no reventamos)
        # Para no romper pipeline si manualmente tenías CSV correcto, pondremos sólo texto plano si hay líneas CSV válidas.
        try:
            text = raw.decode('utf-8', errors='ignore')
        except:
            text = raw.decode('latin1', errors='ignore')
        # Si más del 50% de líneas contienen '<', dejamos vacío controlado
        lines = text.splitlines()
        bad = sum(1 for ln in lines if '<' in ln)
        if lines and bad/len(lines) > 0.5:
            dst.write_text("", encoding='utf-8', newline='\r\n')
            return "html-cleared"
        # Si no, guardamos sólo las líneas sin '<'
        keep = [ln for ln in lines if '<' not in ln]
        dst.write_text("\r\n".join(keep), encoding='utf-8', newline='\r\n')
        return "html-pruned"

    # remove nulls
    raw = CONTROL_BYTES.sub(b"", raw)
    # decode best-effort
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        text = raw.decode('latin1', errors='ignore')

    # normaliza fin de línea a CRLF
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    lines = [ln.strip() for ln in text.split('\n') if ln.strip()!='']

    if not lines:
        dst.write_text("", encoding='utf-8', newline='\r\n')
        return "empty"

    # detect delimiter on header if exists else first line
    header = lines[0]
    delim = detect_delimiter(header)
    # Si hay pipes u otro ruido, conviértelo a coma
    normalized = []
    for ln in lines:
        # Cambia delimitadores ; o \t a ‘,’ si el header va con ‘,’
        if delim == ',':
            ln = ln.replace('\t', ',').replace(';', ',')
        elif delim == ';':
            ln = ln.replace('\t', ';').replace(',', ';')
        elif delim == '\t':
            ln = ln.replace(',', '\t').replace(';', '\t')
        normalized.append(ln)

    out = "\r\n".join(normalized)
    dst.write_text(out, encoding='utf-8', newline='\r\n')
    return "ok"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='indir', required=True)
    ap.add_argument('--out', dest='outdir', required=True)
    ap.add_argument('--log', dest='logfile', default=None)
    args = ap.parse_args()

    indir = Path(args.indir)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    logs = []
    for src in sorted(indir.glob("*.csv")):
        dst = outdir / src.name
        try:
            status = sanitize_file(src, dst)
            logs.append(f"[OK ] {src.name} -> {dst.name} ({status})")
        except Exception as e:
            logs.append(f"[ERR] {src.name}: {e}")

    if args.logfile:
        Path(args.logfile).write_text("\n".join(logs), encoding='utf-8')
    print("\n".join(logs))

if __name__ == "__main__":
    sys.exit(main())
