# -*- coding: utf-8 -*-
"""
score_candidates.py (extendido)
- Usa std_source para cargar sorteos
- Scoring Markov (opcional) con PageRank + prob. de siguiente sorteo
- PRNG seleccionable: mt / lfsr / sys
- Entropía y mixing report

CLI (compat):
  --db --game --gen --seed --top --shortlist --export --export-all --report
Nuevas:
  --use-markov
  --rng {mt,lfsr,sys}
  --markov-weight FLOAT
  --smoothing FLOAT
  --damping FLOAT
  --entropy-report
"""
import argparse, os, sys, math, csv, json, time, sqlite3
from datetime import datetime
from typing import List, Tuple, Dict, Optional

# ---- imports robustos desde std_source ----
try:
    from std_source import connect, sanity_check_source, load_draws, runs_has_column  # type: ignore
except Exception:
    from std_source import connect, sanity_check_source, load_draws  # type: ignore
    def runs_has_column(cnx:sqlite3.Connection, col:str)->bool:
        try:
            cols = [r[1] for r in cnx.execute("PRAGMA table_info(runs)")]
            return col in cols
        except Exception:
            return False

# ---- RNGs (iguales a score_markov) ----
import random
class RNGBase:
    def randint(self, a:int, b:int)->int: raise NotImplementedError
class RNG_MT(RNGBase):
    def __init__(self, seed:int): self.r = random.Random(seed)
    def randint(self,a,b): return self.r.randint(a,b)
class RNG_SYS(RNGBase):
    def __init__(self): self.r = random.SystemRandom()
    def randint(self,a,b): return self.r.randint(a,b)
class RNG_LFSR32(RNGBase):
    def __init__(self, seed:int):
        if seed==0: seed=0x1f123bb5
        self.state = seed & 0xFFFFFFFF or 0x9E3779B9
    def _next32(self)->int:
        bit = ((self.state>>0) ^ (self.state>>1) ^ (self.state>>21) ^ (self.state>>31)) & 1
        self.state = ((self.state<<1) & 0xFFFFFFFF) | bit
        return self.state
    def randint(self,a,b):
        span=b-a+1
        x=self._next32() & 0xFFFFFFFF
        return a + (x % span)
def make_rng(kind:str, seed:Optional[int])->RNGBase:
    kind=kind.lower()
    if kind=="mt": 
        if seed is None: seed=int(time.time()*1000)&0xFFFFFFFF
        return RNG_MT(seed)
    if kind=="lfsr":
        if seed is None: seed=int(time.time()*1000000)&0xFFFFFFFF
        return RNG_LFSR32(seed)
    if kind=="sys": return RNG_SYS()
    raise ValueError("RNG desconocido: "+kind)

# ---- utilidades Markov inline (para no depender del otro script) ----
def normalize_row(row):
    s=sum(row)
    if s<=0: return [1.0/len(row)]*len(row)
    return [x/s for x in row]

def power_iteration_left(P, alpha=0.85, eps=1e-9, max_steps=2000):
    k=len(P); 
    if k==0: return [],0
    pi=[1.0/k]*k; u=[1.0/k]*k
    steps=0
    while steps<max_steps:
        steps+=1
        y=[0.0]*k
        for i in range(k):
            pi_i=pi[i]; row=P[i]
            if pi_i==0: continue
            for j in range(k):
                y[j]+=pi_i*row[j]
        pi_next=[alpha*y[j]+(1-alpha)*u[j] for j in range(k)]
        diff=sum(abs(pi_next[j]-pi[j]) for j in range(k))
        pi=pi_next
        if diff<eps: break
    s=sum(pi)
    if s>0: pi=[x/s for x in pi]
    return pi, steps

def transitions_4d(draws:List[str], smoothing:float=1.0):
    K=10
    T=[[[0.0]*K for _ in range(K)] for _ in range(4)]
    for i in range(1,len(draws)):
        a=draws[i-1]; b=draws[i]
        for p in range(4):
            ia=ord(a[p])-48; ib=ord(b[p])-48
            if 0<=ia<10 and 0<=ib<10:
                T[p][ia][ib]+=1.0
    P=[]
    for p in range(4):
        PP=[]
        for ia in range(10):
            row=[T[p][ia][ib]+smoothing for ib in range(10)]
            PP.append(normalize_row(row))
        P.append(PP)
    return P

def stat_4d(Ppos, damping:float=0.85, eps:float=1e-9, max_steps:int=2000):
    pis=[]; mixing=[]
    for P in Ppos:
        pi,steps = power_iteration_left(P, alpha=damping, eps=eps, max_steps=max_steps)
        pis.append(pi); mixing.append(steps)
    return pis, mixing

def logprob_next_4d(Ppos, prev:str, cand:str, eps:float=1e-15)->float:
    import math
    lp=0.0
    for p in range(4):
        a=ord(prev[p])-48; b=ord(cand[p])-48
        prob = Ppos[p][a][b]
        if prob<=0: prob=eps
        lp+=math.log(prob)
    return lp

def logprob_prior_4d(pi_pos, cand:str, eps:float=1e-15)->float:
    import math
    lp=0.0
    for p in range(4):
        b=ord(cand[p])-48
        prob = pi_pos[p][b]
        if prob<=0: prob=eps
        lp+=math.log(prob)
    return lp

# ---- carga de draws con tolerancia ----
def _safe_load_draws(cnx, game:str)->List[str]:
    # usa std_source.load_draws si existe y devuelve 4D para astro_luna;
    # si viniera con 'numero' lo adaptamos.
    draws=[]
    for fecha, num in load_draws(cnx, game):
        s = str(num).strip()
        s = ''.join(ch for ch in s if ch.isdigit())
        if s=="":
            continue
        try:
            v=int(s)
            if 0<=v<=9999:
                draws.append(f"{v:04d}")
        except:
            if len(s)==4 and s.isdigit():
                draws.append(s)
    return draws

# ---- candidatos ----
def enumerate_4d():
    for x in range(10000):
        yield f"{x:04d}"

def sample_4d(rng:RNGBase, n:int)->List[str]:
    seen=set(); out=[]
    while len(out)<n and len(seen)<10000:
        v=rng.randint(0,9999)
        if v in seen: continue
        seen.add(v); out.append(f"{v:04d}")
    return out

# ---- export ----
def write_csv(path:str, rows:List[Dict], fields:List[str]):
    import csv
    with open(path,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k:r.get(k) for k in fields})

def write_report_html(path:str, meta:Dict, entropies:List[float], mixing:List[int]):
    def H(p): 
        import math
        return -sum(x*math.log(x,2) for x in p if x>1e-15)
    html=[]
    html.append("<!doctype html><meta charset='utf-8'><title>Scoring Report</title>")
    html.append("<style>body{font-family:Segoe UI,Arial,sans-serif;margin:24px} table{border-collapse:collapse} td,th{border:1px solid #ccc;padding:6px 10px}</style>")
    html.append("<h1>Scoring candidatos</h1>")
    html.append("<h3>Meta</h3><pre>"+json.dumps(meta, indent=2, ensure_ascii=False)+"</pre>")
    if entropies:
        html.append("<h3>Entropías y mixing (por posición)</h3>")
        html.append("<table><tr><th>Pos</th><th>Entropía (bits)</th><th>Mixing steps</th></tr>")
        for i,(e,m) in enumerate(zip(entropies, mixing), start=1):
            html.append(f"<tr><td>{i}</td><td>{e:.6f}</td><td>{m}</td></tr>")
        html.append("</table>")
    with open(path,"w",encoding="utf-8") as f:
        f.write("\n".join(html))

def shannon_entropy(p):
    import math
    return -sum(x*math.log(x,2) for x in p if x>1e-15)

# ---- main ----
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--game", required=True, help="astro_luna | ... (4D). Para n5+sb usar score_markov.py")
    ap.add_argument("--gen", type=int, default=100, help="# candidatos a generar si no hay lista externa")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--rng", default="mt", choices=["mt","lfsr","sys"])
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--shortlist", type=int, default=5)
    ap.add_argument("--export", required=True)
    ap.add_argument("--export-all", required=True)
    ap.add_argument("--report", required=True)
    # Markov extras
    ap.add_argument("--use-markov", action="store_true", help="Usar scoring Markov")
    ap.add_argument("--markov-weight", type=float, default=0.5)
    ap.add_argument("--smoothing", type=float, default=1.0)
    ap.add_argument("--damping", type=float, default=0.85)
    ap.add_argument("--entropy-report", action="store_true")
    args = ap.parse_args()

    cnx = connect(args.db)

    # sanity original
    sanity_check_source(cnx, args.game)

    # carga draws (4D)
    draws = _safe_load_draws(cnx, args.game)
    if len(draws)<2:
        print("[ERROR] Muy pocos sorteos 4D para entrenar.", file=sys.stderr)
        sys.exit(3)

    rng = make_rng(args.rng, args.seed)

    # Generación de candidatos
    if args.gen and args.gen<10000:
        cand = sample_4d(rng, args.gen)
    else:
        cand = list(enumerate_4d())

    # Scoring base (si tuvieras uno previo, podrías mezclar aquí)
    rows=[]
    if args.use_markov:
        # Modelo Markov
        Ppos = transitions_4d(draws, smoothing=args.smoothing)
        pi_pos, mixing = stat_4d(Ppos, damping=args.damping)
        entropies = [shannon_entropy(pi) for pi in pi_pos]
        prev = draws[-1]
        w = max(0.0, min(1.0, args.markov_weight))

        for s in cand:
            lp_m = logprob_next_4d(Ppos, prev, s)
            lp_p = logprob_prior_4d(pi_pos, s)
            score = w*lp_m + (1.0-w)*lp_p
            rows.append({"num":s, "score":score, "markov_logp":lp_m, "prior_logp":lp_p})
        rows.sort(key=lambda r: r["score"], reverse=True)

        # export
        write_csv(args.export_all, rows, ["num","score","markov_logp","prior_logp"])
        write_csv(args.export, rows[:args.top], ["num","score","markov_logp","prior_logp"])

        meta = {
            "db": os.path.abspath(args.db),
            "game": args.game,
            "rng": args.rng,
            "seed": args.seed,
            "gen": args.gen,
            "damping": args.damping,
            "smoothing": args.smoothing,
            "markov_weight": args.markov_weight,
            "generated_at": datetime.now().isoformat(timespec="seconds")
        }
        if args.report:
            write_report_html(args.report, meta, entropies if args.entropy_report else [], mixing if args.entropy_report else [])

    else:
        # Scoring simple (uniforme) para mantener compat si no activas --use-markov
        for s in cand:
            rows.append({"num":s, "score":0.0, "markov_logp":0.0, "prior_logp":0.0})
        rows.sort(key=lambda r: r["num"])
        write_csv(args.export_all, rows, ["num","score","markov_logp","prior_logp"])
        write_csv(args.export, rows[:args.top], ["num","score","markov_logp","prior_logp"])

    # shortlist (si necesitas un archivo adicional, aquí podrías escribirlo)
    # Por ahora la 'shortlist' es simplemente los primeros N
    # (Tu master puede ya tomar los primeros N del CSV export)
    return 0

if __name__=="__main__":
    sys.exit(main())
