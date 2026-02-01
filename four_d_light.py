# -*- coding: utf-8 -*-
"""
four_d_light.py — Paso '4D light' con HTML de salida.
- Sin dependencias externas.
- Genera C:\RadarPremios\reports\four_d_light.html
"""

from __future__ import annotations
import sys
import argparse
from pathlib import Path
from datetime import datetime, UTC
import os
import sqlite3
from typing import Iterable, Tuple, Any

APP_NAME = "4D light"
REPORT_NAME = "four_d_light.html"

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
    tables_4d = []
    counts = []

    # Intento de resumen mínimo desde la DB (opcional/seguro)
    if db_path.exists():
        try:
            with sqlite3.connect(str(db_path)) as conn:
                conn.row_factory = sqlite3.Row
                ok_db = True

                ok, tables_4d = safe_query(
                    conn,
                    "SELECT name FROM sqlite_master WHERE type='view' AND name LIKE 'v_4d_%' ORDER BY name;"
                )

                # Ejemplos de conteos 'suaves'; si no existen, se ignoran
                want_counts = [
                    ("v_4d_pos_expanded", "Filas en v_4d_pos_expanded"),
                    ("v_4d_pos_expanded_win", "Filas en v_4d_pos_expanded_win"),
                    ("v_4d_cfg", "Filas en v_4d_cfg"),
                ]
                for table, label in want_counts:
                    ok1, r = safe_query(conn, f"SELECT COUNT(*) FROM {table};")
                    if ok1 and r:
                        counts.append((label, int(r[0][0])))
        except Exception:
            ok_db = False

    # HTML básico
    css = """
    body{font-family:Segoe UI,Arial,sans-serif;margin:24px;color:#222}
    .card{border:1px solid #ddd;border-radius:10px;padding:16px;margin-bottom:16px}
    h1{margin:0 0 4px 0;font-size:20px}
    .muted{color:#666;font-size:12px}
    table{border-collapse:collapse;width:100%;margin-top:8px}
    th,td{border:1px solid #eee;padding:8px;text-align:left}
    th{background:#fafafa}
    """
    parts = []
    parts.append(f"<div class='card'><h1>{APP_NAME}</h1><div class='muted'>Generado: {utc_ts()}</div></div>")
    parts.append("<div class='card'><b>Entradas</b><br>")
    parts.append(f"DB: <code>{db_path}</code><br>Reporte: <code>{out_dir / REPORT_NAME}</code></div>")

    # Bloque DB
    if ok_db:
        parts.append("<div class='card'><b>Estado DB</b><br>Conexión OK.</div>")
        if tables_4d:
            parts.append("<div class='card'><b>Vistas 4D detectadas</b><table><tr><th>Vista</th></tr>")
            for (name,) in tables_4d:
                parts.append(f"<tr><td>{name}</td></tr>")
            parts.append("</table></div>")
        if counts:
            parts.append("<div class='card'><b>Conteos rápidos</b><table><tr><th>Métrica</th><th>Valor</th></tr>")
            for label, val in counts:
                parts.append(f"<tr><td>{label}</td><td>{val}</td></tr>")
            parts.append("</table></div>")
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
