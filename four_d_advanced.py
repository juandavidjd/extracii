# -*- coding: utf-8 -*-
"""
four_d_advanced.py — Paso '4D advanced' con HTML de salida.
- Sin dependencias externas.
- Genera C:\RadarPremios\reports\four_d_advanced.html
"""

from __future__ import annotations
import sys
import argparse
from pathlib import Path
from datetime import datetime, UTC
import os
import sqlite3
from typing import Iterable, Tuple, Any

APP_NAME = "advanced 4d"
REPORT_NAME = "four_d_advanced.html"

def utc_ts() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")

def guess_paths() -> tuple[Path, Path]:
    rp_root = os.getenv("RP_ROOT", r"C:\RadarPremios")
    db = os.getenv("RP_DB", str(Path(rp_root) / "radar_premios.db"))
    reports = os.getenv("RP_REPORTS", str(Path(rp_root) / "reports"))
    return Path(db), Path(reports)

def safe_query(conn: sqlite3.Connection, sql: str, params: Iterable[Any] = ()) -> Tuple[bool, list[tuple]]:
    try:
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
        return True, rows
    except Exception:
        return False, []

def generate_html(db_path: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    ok_db = False
    samples = []

    # Intento obtener algún resumen útil (todo opcional)
    if db_path.exists():
        try:
            with sqlite3.connect(str(db_path)) as conn:
                conn.row_factory = sqlite3.Row
                ok_db = True

                # Top 10 de ejemplos de combinaciones (si existen vistas)
                candidates_sql = """
                SELECT * FROM v_4d_pos_expanded
                LIMIT 10;
                """
                ok1, r1 = safe_query(conn, candidates_sql)
                if ok1 and r1:
                    # Convertimos primeras columnas a texto
                    for row in r1:
                        # row es tuple o Row; nos quedamos con hasta 5 columnas
                        vals = list(row)[:5]
                        samples.append(", ".join(str(v) for v in vals))
        except Exception:
            ok_db = False

    css = """
    body{font-family:Segoe UI,Arial,sans-serif;margin:24px;color:#222}
    .card{border:1px solid #ddd;border-radius:10px;padding:16px;margin-bottom:16px}
    h1{margin:0 0 4px 0;font-size:20px}
    .muted{color:#666;font-size:12px}
    ul{margin:8px 0 0 18px}
    code{background:#f7f7f7;padding:2px 4px;border-radius:4px}
    """
    parts = []
    parts.append(f"<div class='card'><h1>{APP_NAME}</h1><div class='muted'>Generado: {utc_ts()}</div></div>")
    parts.append("<div class='card'><b>Entradas</b><br>")
    parts.append(f"DB: <code>{db_path}</code><br>Reporte: <code>{out_dir / REPORT_NAME}</code></div>")

    if ok_db:
        parts.append("<div class='card'><b>Estado DB</b><br>Conexión OK.</div>")
        if samples:
            parts.append("<div class='card'><b>Muestra (v_4d_pos_expanded)</b><ul>")
            for s in samples:
                parts.append(f"<li>{s}</li>")
            parts.append("</ul></div>")
        else:
            parts.append("<div class='card'>No se encontraron filas de muestra (vista ausente o vacía).</div>")
    else:
        parts.append("<div class='card'><b>Estado DB</b><br>"
                     "No se pudo abrir o consultar la base (se genera el HTML igualmente).</div>")

    html = f"<!doctype html><html><head><meta charset='utf-8'><title>{APP_NAME}</title><style>{css}</style></head><body>" \
           + "\n".join(parts) + "</body></html>"

    out_file = out_dir / REPORT_NAME
    out_file.write_text(html, encoding="utf-8")
    return out_file

def run(db_path: Path, out_dir: Path) -> int:
    out_html = generate_html(db_path, out_dir)
    print(f"[OK ] {APP_NAME} -> {out_html}")
    return 0


def parse_args(argv) -> argparse.Namespace:
    db_default, out_default = guess_paths()
    p = argparse.ArgumentParser(description=APP_NAME)
    p.add_argument("--db", default=str(db_default), help="Ruta a radar_premios.db")
    # --out (oficial) y --reports (alias por compatibilidad)
    p.add_argument("--out", dest="out", default=str(out_default), help="Directorio de reportes/salida")
    p.add_argument("--reports", dest="out", help=argparse.SUPPRESS)
    return p.parse_args(argv)


def main(argv=None) -> int:
    try:
        args = parse_args(argv or sys.argv[1:])
        return run(Path(args.db), Path(args.out))
    except KeyboardInterrupt:
        print("[WARN] Interrumpido por el usuario")
        return 130
    except Exception as ex:
        print(f"[ERROR] {APP_NAME} falló: {type(ex).__name__}: {ex}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
