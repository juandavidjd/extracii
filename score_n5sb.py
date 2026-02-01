# -*- coding: utf-8 -*-
"""
score_n5sb.py
Scoring para juegos N5+SB (Baloto / Revancha) usando std_source.load_n5sb.

CLI ejemplo:
python -X utf8 score_n5sb.py --db C:\RadarPremios\radar_premios.db --game baloto \
  --seed 12345 --top 15 --shortlist 5 \
  --export C:\RadarPremios\candidatos_scored_YYYYMMDD_HHMMSS_baloto.csv \
  --export-all C:\RadarPremios\candidatos_all_YYYYMMDD_HHMMSS_baloto.csv \
  --report C:\RadarPremios\reports\baloto\candidatos_scored_baloto_YYYYMMDD_HHMMSS.html
"""

import argparse
import csv
import html
import math
import os
import random
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime
from typing import List, Tuple

import std_source as SS

# -------------------- Utiles --------------------

def _now_iso():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _safe_mkdir(path: str):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except Exception:
        pass

def _write_csv(path: str, rows: List[dict], fieldnames: List[str]):
    _safe_mkdir(path)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

def _write_html_report(path: str, title: str, summary_rows: List[dict], all_rows: List[dict]):
    _safe_mkdir(path)
    def _table(rows: List[dict], head: List[str]) -> str:
        th = "".join(f"<th>{html.escape(h)}</th>" for h in head)
        trs = []
        for r in rows:
            tds = "".join(f"<td>{html.escape(str(r.get(h,'')))}</td>" for h in head)
            trs.append(f"<tr>{tds}</tr>")
        return f"<table border='1' cellspacing='0' cellpadding='6'><thead><tr>{th}</tr></thead><tbody>{''.join(trs)}</tbody></table>"
    head_summary = ["rank","combo","score","n1","n2","n3","n4","n5","sb"]
    head_all = ["rank","combo","score","n1","n2","n3","n4","n5","sb"]
    html_doc = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>body{{font-family:Segoe UI,Roboto,Arial,sans-serif}} h1{{margin:0}} .meta{{color:#666}} table{{margin-top:10px}} th{{background:#eee}}</style>
</head><body>
<h1>{html.escape(title)}</h1>
<div class="meta">Generado: {_now_iso()}</div>
<h2>Shortlist</h2>
{_table(summary_rows, head_summary)}
<h2>Top candidatos</h2>
{_table(all_rows[:100], head_all)}
</body></html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_doc)

# -------------------- Core N5+SB --------------------

def _decay_weights(n: int, half_life: int = 180) -> List[float]:
    """
    Pondera más lo reciente. half_life en draws: peso cae a la mitad cada HL.
    """
    if n <= 0: return []
    lam = math.log(2.0) / max(1, half_life)
    # índice 0 = más antiguo, n-1 = más reciente
    return [math.exp(lam * (i - (n-1))) for i in range(n)]

def _score_model(draws: List[Tuple[str,int,int,int,int,int,int]]):
    """
    Construye contadores ponderados por decaimiento:
    - Freq de cada bola para posiciones 1..5 (n-position) y para sb.
    - Freq marginal total de cada bola (para diversificación).
    """
    n = len(draws)
    w = _decay_weights(n, half_life=180)
    pos_counts = [Counter() for _ in range(5)]
    sb_count = Counter()
    total_count = Counter()
    last_seen = {}  # bola -> idx última aparición (para penalización por recencia)
    for i, (_, a,b,c,d,e,sb) in enumerate(draws):
        ww = w[i]
        balls = [a,b,c,d,e]
        for p, val in enumerate(balls):
            pos_counts[p][val] += ww
            total_count[val] += ww
            last_seen[val] = i
        sb_count[sb] += ww
    return {
        "pos_counts": pos_counts,
        "sb_count": sb_count,
        "total_count": total_count,
        "last_seen": last_seen,
        "n": n,
    }

def _penalty_recent(combo: Tuple[int,int,int,int,int], model, strength: float = 0.2) -> float:
    """
    Penaliza si varias bolas aparecieron muy recientemente (para ayudar a la diversidad).
    """
    last_seen = model["last_seen"]
    n = model["n"]
    tot = 0.0
    for v in combo:
        li = last_seen.get(v, -9999)
        # más grande (más reciente i ~ n-1) => mayor penalización
        rec = max(0, (li - (n-30)))  # ventana de 30 últimos
        tot += rec
    return -strength * tot

def _score_candidate(combo: Tuple[int,int,int,int,int], sb: int, model) -> float:
    pos_counts = model["pos_counts"]
    sb_count = model["sb_count"]
    total_count = model["total_count"]
    balls = list(combo)
    balls.sort()
    # suma de likelihoods posicionales
    s = 0.0
    for p, v in enumerate(balls):
        s += pos_counts[p][v]
    # bono por popularidad marginal (diversidad controlada)
    s += 0.25 * sum(total_count[v] for v in balls)
    # sb
    s += 0.6 * sb_count[sb]
    # penalización por repetición reciente
    s += _penalty_recent(tuple(balls), model, strength=0.2)
    return s

def _sample_ball(universe: range, weight_counter: Counter, rnd: random.Random) -> int:
    # Ruleta discreta con fallback uniforme si todo son ceros
    vals = list(universe)
    ws = [max(0.0, weight_counter[v]) for v in vals]
    total = sum(ws)
    if total <= 0:
        return rnd.choice(vals)
    r = rnd.random() * total
    acc = 0.0
    for v, w in zip(vals, ws):
        acc += w
        if r <= acc:
            return v
    return vals[-1]

def _generate_candidates(model, game: str, rnd: random.Random, n_gen: int = 2000):
    """
    Genera candidatos con muestreo ponderado por posición + barajado.
    Universo:
      - Baloto: 1..43 (ejemplo; ajusta a tu rango real si difiere)
      - Revancha: 1..43 (idéntico si comparten universo)
      - Superbola: 1..16 (ejemplo; ajusta si difiere)
    """
    g = (game or "").lower().strip()
    # TODO: si tus rangos reales difieren, cámbialos aquí:
    N_MAIN = 43
    N_SB = 16
    U = range(1, N_MAIN+1)
    USB = range(1, N_SB+1)

    pos_counts = model["pos_counts"]
    sb_count = model["sb_count"]

    seen = set()
    out = []
    for _ in range(n_gen):
        # muestreo por posición + evitar duplicados dentro del combo
        picks = set()
        tmp = []
        for p in range(5):
            for _try in range(20):
                v = _sample_ball(U, pos_counts[p], rnd)
                if v not in picks:
                    picks.add(v)
                    tmp.append(v)
                    break
            else:
                # fallback uniforme si no encontramos (muy improbable)
                v = rnd.choice([x for x in U if x not in picks])
                picks.add(v)
                tmp.append(v)
        tmp.sort()
        sb = _sample_ball(USB, sb_count, rnd)
        key = (tmp[0], tmp[1], tmp[2], tmp[3], tmp[4], sb)
        if key in seen:
            continue
        seen.add(key)
        score = _score_candidate(tuple(tmp), sb, model)
        out.append((score, key))
    # ordenar desc por score
    out.sort(key=lambda x: x[0], reverse=True)
    return out

# -------------------- Main --------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="Ruta a la base SQLite")
    ap.add_argument("--game", required=True, choices=["baloto", "revancha", "n5sb", "all_n5sb", "baloto_revancha"], help="Juego")
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--shortlist", type=int, default=5)
    ap.add_argument("--gen", type=int, default=3000, help="Generaciones de candidatos")
    ap.add_argument("--export", required=True, help="CSV top")
    ap.add_argument("--export-all", required=True, help="CSV all")
    ap.add_argument("--report", required=True, help="HTML report")
    args = ap.parse_args()

    cnx = SS.connect(args.db)
    # Sanity n5+sb
    SS.sanity_check_source(cnx, args.game)

    draws = SS.load_n5sb(cnx, args.game)
    if not draws:
        raise SystemExit(f"No hay datos de {args.game} para scoring.")

    rnd = random.Random(args.seed)
    model = _score_model(draws)
    ranked = _generate_candidates(model, args.game, rnd, n_gen=args.gen)

    # Exportar
    rows_all = []
    for i, (sc, (a,b,c,d,e,sb)) in enumerate(ranked, 1):
        rows_all.append({
            "rank": i,
            "score": round(sc, 6),
            "combo": f"{a:02d}-{b:02d}-{c:02d}-{d:02d}-{e:02d} + SB {sb:02d}",
            "n1": a, "n2": b, "n3": c, "n4": d, "n5": e, "sb": sb,
        })
    rows_top = rows_all[:max(1, args.top)]
    rows_short = rows_all[:max(1, args.shortlist)]

    _write_csv(args.export_all, rows_all, ["rank","score","combo","n1","n2","n3","n4","n5","sb"])
    _write_csv(args.export, rows_top, ["rank","score","combo","n1","n2","n3","n4","n5","sb"])
    _write_html_report(args.report, f"Scoring {args.game.upper()} (N5+SB)", rows_short, rows_top)

    print(f"[OK] Scoring {args.game} -> {args.export} | {args.export_all} | {args.report}")

if __name__ == "__main__":
    main()
