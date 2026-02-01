# -*- coding: utf-8 -*-
import argparse
import json
from typing import List

from std_source import (
    connect,
    load_draws,
    runs_has_column,
    sanity_check_source,
)

def parse_shortlist(row, game_default="astro_luna") -> List[str]:
    cols = row.keys()
    # Nuevo esquema: shortlist_json (lista de enteros/cadenas)
    if "shortlist_json" in cols and row["shortlist_json"]:
        try:
            data = json.loads(row["shortlist_json"])
            return [f"{int(x):04d}" for x in data]
        except Exception:
            pass
    # Esquema antiguo: shortlist (csv de cadenas)
    if "shortlist" in cols and row["shortlist"]:
        return [s.strip().zfill(4) for s in row["shortlist"].split(",") if s.strip() != ""]
    # Si todo falla, intenta fallback usando top/export (sin shortlist real)
    return []

def pick_game(row, fallback="astro_luna") -> str:
    if "game" in row.keys() and row["game"]:
        return row["game"]
    return fallback

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--game", default=None, help="Juego a evaluar; por defecto el del último run o astro_luna.")
    args = ap.parse_args()

    conn = connect(args.db)

    # Último run (el más reciente por created_at o id si no hay created_at)
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(runs)")]
    order_col = "created_at" if "created_at" in cols else "id"
    run = conn.execute(f"SELECT * FROM runs ORDER BY {order_col} DESC LIMIT 1").fetchone()
    if not run:
        raise SystemExit("[INFO] No hay runs registrados todavía.")

    run = dict(run)
    game = args.game or pick_game(run, "astro_luna")

    # Fuente normalizada
    sanity_check_source(conn, game)
    draws = list(load_draws(conn, game, ascending=True))
    if not draws:
        raise SystemExit(f"[INFO] No hay sorteos para el juego {game}.")

    last_draw = draws[-1]                 # último sorteo disponible
    last_winner = last_draw["num"]        # 'NNNN'
    last_date = last_draw["fecha"]

    shortlist = parse_shortlist(run, game)
    if not shortlist:
        print(f"[INFO] Último run sin shortlist. Juego: {game}")
        print(f"[INFO] Último sorteo: {last_date} ({game}) -> ganador {last_winner}")
        return

    hit = last_winner in shortlist
    print(f"[INFO] Último run -> id={run.get('id','?')} juego={game}")
    print(f"[INFO] Shortlist: {shortlist}")
    print(f"[INFO] Último sorteo: {last_date} ({game}) -> ganador {last_winner}")
    print("[INFO] ✅ ACIERTO." if hit else "[INFO] ❌ Sin acierto.")

if __name__ == "__main__":
    main()
