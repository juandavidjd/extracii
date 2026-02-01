# -*- coding: utf-8 -*-
import argparse, os
HTML = """<!doctype html><meta charset="utf-8"><title>{title}</title>
<body><h1>{title}</h1><p>Reporte generado (stub).</p></body>"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--reports", required=True)
    ap.add_argument("--mode", choices=["baloto","revancha"], required=True)
    args = ap.parse_args()
    os.makedirs(args.reports, exist_ok=True)
    out = os.path.join(args.reports, f"{args.mode}_light.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(HTML.format(title=f"{args.mode.capitalize()} light"))
    print(f"[OK ] {args.mode} light -> {out}")
    print("[OK ] Scoring light finalizado")

if __name__ == "__main__":
    main()
