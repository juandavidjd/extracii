# -*- coding: utf-8 -*-
"""
clean_csvs.py
Uso:
  py -3 clean_csvs.py --in C:\RadarPremios\data\crudo\file.csv --out C:\RadarPremios\data\limpio\file.csv [--in ... --out ...]
Se pueden pasar varios pares --in/--out en la misma invocación.
"""

from __future__ import annotations
import argparse
from pathlib import Path

def clean_one(src: Path, dst: Path) -> bool:
    try:
        if not src.exists():
            print(f"[WARN] No existe: {src}")
            return False
        dst.parent.mkdir(parents=True, exist_ok=True)
        # Leer crudo (permite BOM); normalizar saltos de línea; quitar nulos
        text = src.read_text(encoding="utf-8", errors="replace")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.replace("\x00", "")
        dst.write_text(text, encoding="utf-8", newline="\n")
        print(f"[OK ] Limpio: {src.name} -> {dst.name} (+copiado)")
        return True
    except Exception as ex:
        print(f"[ERROR] Limpieza falló para {src.name}: {type(ex).__name__}: {ex}")
        return False

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="inputs", action="append", required=True, help="CSV de entrada (crudo)")
    p.add_argument("--out", dest="outputs", action="append", required=True, help="CSV de salida (limpio)")
    return p.parse_args()

def main() -> int:
    args = parse_args()
    ins = [Path(x) for x in args.inputs]
    outs = [Path(x) for x in args.outputs]
    if len(ins) != len(outs):
        print("[ERROR] Debes pasar el mismo número de --in y --out")
        return 2
    ok_all = True
    for src, dst in zip(ins, outs):
        ok_all &= clean_one(src, dst)
    return 0 if ok_all else 1

if __name__ == "__main__":
    raise SystemExit(main())
