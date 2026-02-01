# C:\RadarPremios\scripts\gen_eval_candidates.py
# -*- coding: utf-8 -*-
import argparse
import json
import random
import sqlite3
from datetime import datetime, timezone

N5_MIN, N5_MAX = 1, 43         # rango Baloto/Revancha (números)
SB_MIN, SB_MAX = 1, 16         # rango SuperBalota
FOURD_DIGITS = list("0123456789")

def now_utc_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def get_table_columns(cur, table):
    cur.execute(f"PRAGMA table_info('{table}')")
    return [r[1] for r in cur.fetchall()]

def insert_row(cur, table, data):
    cols_present = get_table_columns(cur, table)
    payload = {k: v for k, v in data.items() if k in cols_present}
    ks = ",".join(payload.keys())
    qs = ",".join(["?"] * len(payload))
    cur.execute(f"INSERT INTO {table} ({ks}) VALUES ({qs})", list(payload.values()))
    return cur.lastrowid

def ensure_ts_utc(data):
    if "ts_utc" not in data or not data["ts_utc"]:
        data["ts_utc"] = now_utc_iso()

def gen_baloto_candidates(n):
    cands = set()
    out = []
    attempts = 0
    while len(out) < n and attempts < n * 50:
        attempts += 1
        nums = sorted(random.sample(range(N5_MIN, N5_MAX + 1), 5))
        sb = random.randint(SB_MIN, SB_MAX)
        key = tuple(nums) + (sb,)
        if key in cands:
            continue
        cands.add(key)
        out.append({"n1": nums[0], "n2": nums[1], "n3": nums[2], "n4": nums[3], "n5": nums[4], "sb": sb})
    return out

def gen_4d_candidates(n):
    cands = set()
    out = []
    attempts = 0
    while len(out) < n and attempts < n * 200:
        attempts += 1
        num = "".join(random.choice(FOURD_DIGITS) for _ in range(4))
        if num in cands:
            continue
        cands.add(num)
        out.append({"n4d": num})
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="Ruta del SQLite")
    ap.add_argument("--lots", default="", help="Lista separada por comas de loterías 4D")
    ap.add_argument("--n-4d", type=int, default=60)
    ap.add_argument("--n-baloto", type=int, default=80)
    ap.add_argument("--n-revancha", type=int, default=80)
    ap.add_argument("--win-4d", type=int, default=200, help="ventana de historia (no obligatorio)")
    ap.add_argument("--eval-last-4d", type=int, default=80)
    ap.add_argument("--eval-last-n5sb", type=int, default=200)
    ap.add_argument("--only", default="", help="Si se especifica, solo ese modo/lotería")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    lots = [x.strip() for x in args.lots.split(",") if x.strip()]
    if args.only:
        only = args.only.strip().lower()
        lots = [l for l in lots if l.lower() == only] or lots

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()

    # Detecta columnas disponibles
    runs_cols = get_table_columns(cur, "rp_runs") if True else []
    rc_cols   = get_table_columns(cur, "run_candidates") if True else []

    # Crea un run para cada "grupo" (baloto, revancha, 4d-<lot>)
    # Datos comunes del run (flexibles)
    def make_run(mode, target, params):
        run_row = {
            "ts_utc": now_utc_iso(),
            "mode": mode,                 # si existe
            "target": target,             # si existe
            "label": f"{mode}:{target}",  # si existe
            "params_json": json.dumps(params, ensure_ascii=False),  # si existe
            "status": "ok",               # si existe
        }
        ensure_ts_utc(run_row)
        run_id = insert_row(cur, "rp_runs", run_row)
        return run_id

    def make_candidate(run_id, lot, payload, source, score=0.0):
        cand_row = {
            "ts_utc": now_utc_iso(),
            "run_id": run_id,            # si existe
            "lot": lot,                  # si existe
            "candidate": json.dumps(payload, ensure_ascii=False),  # si existe
            "source": source,            # si existe
            "score": score,              # si existe
            "mode": source.split(":")[0] if ":" in source else source,  # si existe
        }
        ensure_ts_utc(cand_row)
        insert_row(cur, "run_candidates", cand_row)

    # === Baloto ===
    if not args.only or args.only.lower() in ("", "baloto"):
        params = {
            "n": args.n_baloto,
            "eval_last": args.eval_last_n5sb,
            "seed": args.seed
        }
        run_id = make_run("n5sb", "baloto", params)
        for c in gen_baloto_candidates(args.n_baloto):
            make_candidate(run_id, "baloto", c, "baloto:random")

    # === Revancha ===
    if not args.only or args.only.lower() in ("", "revancha"):
        params = {
            "n": args.n_revancha,
            "eval_last": args.eval_last_n5sb,
            "seed": args.seed
        }
        run_id = make_run("n5sb", "revancha", params)
        for c in gen_baloto_candidates(args.n_revancha):
            make_candidate(run_id, "revancha", c, "revancha:random")

    # === 4D por lotería ===
    for lot in lots:
        if args.only and args.only.lower() not in (lot.lower(),):
            continue
        params = {
            "n": args.n_4d,
            "win": args.win_4d,
            "eval_last": args.eval_last_4d,
            "seed": args.seed
        }
        run_id = make_run("4d", lot, params)
        for c in gen_4d_candidates(args.n_4d):
            make_candidate(run_id, lot, c, f"{lot}:random")

    conn.commit()
    conn.close()
    print("[OK ] gen_eval_candidates done")

if __name__ == "__main__":
    main()
