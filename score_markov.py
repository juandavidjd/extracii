# -*- coding: utf-8 -*-
"""
score_markov.py
Motor de scoring basado en:
 - Cadenas de Markov (1er orden) por posición
 - PageRank (damping) para distribución estacionaria
 - Montecarlo opcional
 - Métricas de entropía y mixing time

Soporta:
 - Juegos 4D: astro_luna, boyaca, huila, manizales, medellin, quindio, tolima, all4d
 - Juegos N5+SB: baloto, revancha, n5sb, all_n5sb

Salida:
 - CSV con todas las puntuaciones (o muestra para N5+SB)
 - CSV top-N (si se indica)
 - Reporte HTML simple con entropías y mixing
"""
import argparse, sqlite3, os, sys, math, csv, json, time, random
from collections import defaultdict, Counter
from datetime import datetime
from typing import List, Tuple, Dict, Iterable, Optional

# ---------------- RNGs ----------------

class RNGBase:
    def randint(self, a:int, b:int)->int:
        raise NotImplementedError
    def random(self)->float:
        # [0,1)
        r = self.randint(0, (1<<53)-1)
        return r / float(1<<53)

class RNG_MT(RNGBase):
    def __init__(self, seed:int):
        self.r = random.Random(seed)
    def randint(self, a:int, b:int)->int:
        return self.r.randint(a,b)

class RNG_SYS(RNGBase):
    def __init__(self):
        self.r = random.SystemRandom()
    def randint(self, a:int, b:int)->int:
        return self.r.randint(a,b)

class RNG_LFSR32(RNGBase):
    """
    LFSR 32-bit taps: [32,22,2,1] (polinomio típico)
    """
    def __init__(self, seed:int):
        if seed == 0:
            seed = 0x1f123bb5
        self.state = seed & 0xFFFFFFFF
        if self.state == 0:
            self.state = 0x9E3779B9
    def _next32(self)->int:
        # XOR de taps: bits 0,1,21,31 si contamos desde 0
        bit = ((self.state >> 0) ^ (self.state >> 1) ^ (self.state >> 21) ^ (self.state >> 31)) & 1
        self.state = ((self.state << 1) & 0xFFFFFFFF) | bit
        return self.state
    def randint(self, a:int, b:int)->int:
        # rango inclusivo
        span = b - a + 1
        x = self._next32() & 0xFFFFFFFF
        return a + (x % span)

def make_rng(kind:str, seed:Optional[int])->RNGBase:
    kind = kind.lower()
    if kind == "mt":
        if seed is None:
            seed = int(time.time()*1000) & 0xFFFFFFFF
        return RNG_MT(seed)
    elif kind == "lfsr":
        if seed is None:
            seed = int(time.time()*1000000) & 0xFFFFFFFF
        return RNG_LFSR32(seed)
    elif kind == "sys":
        return RNG_SYS()
    else:
        raise ValueError("RNG desconocido: "+kind)

# ---------------- Utilidades ----------------

def shannon_entropy(p:List[float])->float:
    eps = 1e-15
    return -sum((x if x>eps else 0.0)*math.log(x if x>eps else 1.0,2) for x in p)

def normalize_row(row:List[float])->List[float]:
    s = sum(row)
    if s<=0:
        n = len(row)
        return [1.0/n]*n
    return [x/s for x in row]

def power_iteration_left(P:List[List[float]], alpha:float=0.85, eps:float=1e-9, max_steps:int=2000)->Tuple[List[float], int]:
    """
    P: matriz fila-estocástica (filas suman 1) de tamaño kxk.
    Retorna (pi, steps) donde pi es estacionaria (izquierda) con damping: pi_{t+1} = alpha*pi_t*P + (1-alpha)*u
    """
    k = len(P)
    if k==0:
        return [], 0
    pi = [1.0/k]*k
    u  = [1.0/k]*k
    steps=0
    while steps<max_steps:
        steps+=1
        # y = pi*P
        y = [0.0]*k
        for i in range(k):
            pi_i = pi[i]
            if pi_i==0: continue
            row = P[i]
            for j in range(k):
                y[j] += pi_i*row[j]
        # damping
        pi_next = [alpha*y[j] + (1-alpha)*u[j] for j in range(k)]
        # norma L1
        diff = sum(abs(pi_next[j]-pi[j]) for j in range(k))
        pi = pi_next
        if diff<eps:
            break
    # normaliza por si acaso
    s = sum(pi)
    if s>0: pi=[x/s for x in pi]
    return pi, steps

def index_min_max(vals:Iterable[int])->Tuple[int,int]:
    mn=10**9; mx=-10**9
    for v in vals:
        if v<mn: mn=v
        if v>mx: mx=v
    return mn,mx

# ---------------- Carga desde SQLite ----------------

def _has_obj(cnx:sqlite3.Connection, name:str)->bool:
    q = "SELECT 1 FROM sqlite_master WHERE (type='table' OR type='view') AND name=? LIMIT 1"
    return cnx.execute(q,(name,)).fetchone() is not None

def _columns(cnx:sqlite3.Connection, name:str)->List[str]:
    try:
        return [r[1] for r in cnx.execute(f"PRAGMA table_info({name})")]
    except Exception:
        return []

def _first_available(cnx:sqlite3.Connection, names:List[str])->Optional[str]:
    for n in names:
        if _has_obj(cnx,n):
            return n
    return None

def load_draws_4d(cnx:sqlite3.Connection, game:str)->List[str]:
    """
    Retorna lista de 'NNNN' ordenada por fecha (asc).
    game: 'astro_luna' o loterías 4D o 'all4d'
    """
    game = (game or "").lower()
    candidates = []
    if game in ("astro_luna","astro","astro luna"):
        candidates = ["astro_luna_std", "v_matriz_astro_luna_std"]
    elif game in ("boyaca","huila","manizales","medellin","quindio","tolima"):
        candidates = [f"{game}_std"]
    else:
        # all4d: une todas *_std que tengan fecha y (num|numero)
        candidates = []

    views=[]
    if candidates:
        v = _first_available(cnx, candidates)
        if v:
            views=[v]
    if not views:
        # descubrimiento dinámico
        names = [r[0] for r in cnx.execute("SELECT name FROM sqlite_master WHERE type='view' AND name LIKE '%_std'")]
        for n in names:
            cols = set(_columns(cnx,n))
            if "fecha" in cols and ("num" in cols or "numero" in cols):
                views.append(n)

    draws=[]
    for v in views:
        # preferimos 'num', si no 'numero'
        cols = set(_columns(cnx,v))
        numcol = "num" if "num" in cols else ("numero" if "numero" in cols else None)
        if not numcol: 
            continue
        q = f"SELECT fecha, {numcol} AS num FROM {v} WHERE {numcol} IS NOT NULL ORDER BY fecha ASC"
        for (fecha, s) in cnx.execute(q):
            if s is None: 
                continue
            s = str(s).strip()
            s = ''.join(ch for ch in s if ch.isdigit())
            if len(s)==0: 
                continue
            # normaliza a 4 dígitos si es posible
            try:
                val = int(s)
                if 0<=val<=9999:
                    draws.append(f"{val:04d}")
            except:
                if len(s)==4 and s.isdigit():
                    draws.append(s)
    return draws

def load_draws_n5sb(cnx:sqlite3.Connection, game:str)->List[Tuple[int,int,int,int,int,int]]:
    """
    Retorna lista de (n1..n5,sb) ordenada por fecha.
    game: 'baloto', 'revancha', 'n5sb', 'all_n5sb'
    Usa vistas *_n5sb_std si existen; si no, intenta all_n5sb_std.
    """
    game = (game or "").lower()
    names=[]
    if game in ("baloto",):
        names=["baloto_n5sb_std"]
    elif game in ("revancha",):
        names=["revancha_n5sb_std"]
    else:
        names=["all_n5sb_std","baloto_n5sb_std","revancha_n5sb_std"]

    v = _first_available(cnx, names)
    if not v:
        return []
    cols = set(_columns(cnx, v))
    needed = ["n1","n2","n3","n4","n5","sb"]
    if not all(c in cols for c in needed):
        # intenta variantes en mayúscula o similares
        raise RuntimeError(f"{v} no tiene columnas requeridas n1..n5,sb")
    rows=[]
    for row in cnx.execute(f"SELECT fecha,n1,n2,n3,n4,n5,sb FROM {v} ORDER BY fecha ASC"):
        _, n1,n2,n3,n4,n5,sb = row
        try:
            rows.append((int(n1),int(n2),int(n3),int(n4),int(n5),int(sb)))
        except:
            continue
    return rows

# ---------------- Modelos Markov ----------------

def transitions_4d(draws:List[str], smoothing:float=1.0):
    # 4 matrices 10x10 por posición
    K=10
    T = [[[0.0 for _ in range(K)] for _ in range(K)] for _ in range(4)]
    for i in range(1,len(draws)):
        prev = draws[i-1]
        curr = draws[i]
        for p in range(4):
            a = ord(prev[p])-48
            b = ord(curr[p])-48
            if 0<=a<10 and 0<=b<10:
                T[p][a][b]+=1.0
    # suavizado + normalización
    P=[]
    for p in range(4):
        rowP=[]
        for a in range(10):
            row = [T[p][a][b] + smoothing for b in range(10)]
            row = normalize_row(row)
            rowP.append(row)
        P.append(rowP)
    return P

def transitions_npos(draws:List[Tuple[int,...]], npos:int, smoothing:float=1.0):
    """
    Construye P[pos][i][j] para cada posición, donde i,j in [min..max] por datos.
    Retorna (P, offset, k) donde offset = min_val, k = domain_size
    """
    # domain discovery
    mins=[10**9]*npos; maxs=[-10**9]*npos
    for tup in draws:
        for p in range(npos):
            v = tup[p]
            if v<mins[p]: mins[p]=v
            if v>maxs[p]: maxs[p]=v
    # asumimos dominio común para todas las posiciones (p.ej. 1..43)
    mn = min(mins); mx = max(maxs)
    if mn<=0: mn=1
    k = mx - mn + 1
    if k<=1: k=2
    # matrices
    T = [ [[0.0]*k for _ in range(k)] for _ in range(npos) ]
    for i in range(1,len(draws)):
        prev = draws[i-1]
        curr = draws[i]
        for p in range(npos):
            a = prev[p]-mn
            b = curr[p]-mn
            if 0<=a<k and 0<=b<k:
                T[p][a][b]+=1.0
    # suavizado y normaliza
    P=[]
    for p in range(npos):
        rowP=[]
        for a in range(k):
            row = [T[p][a][b] + smoothing for b in range(k)]
            row = normalize_row(row)
            rowP.append(row)
        P.append(rowP)
    return P, mn, k

def stationary_per_pos(Ppos, alpha:float=0.85, eps:float=1e-9, max_steps:int=2000):
    """
    Ppos: lista de matrices fila-estocásticas por posición
    Retorna: (pi_pos, mixing_steps_pos, entropy_pos)
    """
    pis=[]; steps_list=[]; ent_list=[]
    for P in Ppos:
        pi, steps = power_iteration_left(P, alpha=alpha, eps=eps, max_steps=max_steps)
        ent = shannon_entropy(pi) if pi else 0.0
        pis.append(pi); steps_list.append(steps); ent_list.append(ent)
    return pis, steps_list, ent_list

def logprob_next_4d(Ppos, prev:str, cand:str, eps:float=1e-15)->float:
    lp=0.0
    for p in range(4):
        a = ord(prev[p])-48
        b = ord(cand[p])-48
        prob = Ppos[p][a][b]
        if prob<=0: prob=eps
        lp += math.log(prob)
    return lp

def logprob_prior_4d(pi_pos, cand:str, eps:float=1e-15)->float:
    lp=0.0
    for p in range(4):
        b = ord(cand[p])-48
        prob = pi_pos[p][b]
        if prob<=0: prob=eps
        lp += math.log(prob)
    return lp

def logprob_next_npos(Ppos, prev_tup:Tuple[int,...], cand_tup:Tuple[int,...], mn:int, eps:float=1e-15)->float:
    lp=0.0
    for p in range(len(prev_tup)):
        a = prev_tup[p]-mn
        b = cand_tup[p]-mn
        prob = Ppos[p][a][b]
        if prob<=0: prob=eps
        lp += math.log(prob)
    return lp

def logprob_prior_npos(pi_pos, cand_tup:Tuple[int,...], mn:int, eps:float=1e-15)->float:
    lp=0.0
    for p in range(len(cand_tup)):
        b = cand_tup[p]-mn
        prob = pi_pos[p][b]
        if prob<=0: prob=eps
        lp += math.log(prob)
    return lp

# ---------------- Candidatos ----------------

def enumerate_4d()->Iterable[str]:
    for x in range(10000):
        yield f"{x:04d}"

def sample_4d(rng:RNGBase, n:int)->List[str]:
    seen=set()
    out=[]
    while len(out)<n and len(seen)<10000:
        v = rng.randint(0,9999)
        if v in seen: continue
        seen.add(v)
        out.append(f"{v:04d}")
    return out

def sample_n5sb(rng:RNGBase, n:int, mn:int, mx:int)->List[Tuple[int,int,int,int,int,int]]:
    out=[]
    for _ in range(n):
        # cinco números 1..mx sin repetición (ordenados) + sb 1..mx (puede repetir respecto a los 5)
        picks=set()
        while len(picks)<5:
            picks.add(rng.randint(mn,mx))
        five = sorted(picks)
        sb = rng.randint(mn,mx)
        out.append((five[0],five[1],five[2],five[3],five[4],sb))
    return out

# ---------------- Export ----------------

def write_csv_4d(path:str, rows:List[Dict]):
    fieldnames=["num","score","markov_logp","prior_logp"]
    with open(path,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k:r[k] for k in fieldnames})

def write_csv_n5sb(path:str, rows:List[Dict]):
    fieldnames=["n1","n2","n3","n4","n5","sb","score","markov_logp","prior_logp"]
    with open(path,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k:r[k] for k in fieldnames})

def write_report_html(path:str, meta:Dict, entropies:List[float], mixing:List[int]):
    html = []
    html.append("<!doctype html><meta charset='utf-8'><title>Markov Scoring Report</title>")
    html.append("<style>body{font-family:Segoe UI, Arial, sans-serif;margin:24px} h1{font-size:20px} table{border-collapse:collapse} td,th{border:1px solid #ccc;padding:6px 10px}</style>")
    html.append("<h1>Reporte Markov / Montecarlo</h1>")
    html.append("<h3>Meta</h3><pre>"+json.dumps(meta, indent=2, ensure_ascii=False)+"</pre>")
    html.append("<h3>Entropías por posición</h3>")
    html.append("<table><tr><th>Pos</th><th>Entropía (bits)</th><th>Mixing steps</th></tr>")
    for i,(e,m) in enumerate(zip(entropies, mixing), start=1):
        html.append(f"<tr><td>{i}</td><td>{e:.6f}</td><td>{m}</td></tr>")
    html.append("</table>")
    with open(path,"w",encoding="utf-8") as f:
        f.write("\n".join(html))

# ---------------- Main ----------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="Ruta a radar_premios.db")
    ap.add_argument("--game", required=True, help="astro_luna | boyaca | ... | all4d | baloto | revancha | n5sb")
    ap.add_argument("--rng", default="mt", choices=["mt","lfsr","sys"], help="Generador aleatorio para muestreos")
    ap.add_argument("--seed", type=int, default=None, help="Semilla (MT/LFSR)")
    ap.add_argument("--smoothing", type=float, default=1.0, help="Laplace smoothing")
    ap.add_argument("--damping", type=float, default=0.85, help="Damping (PageRank)")
    ap.add_argument("--eps", type=float, default=1e-9, help="Tolerancia de convergencia")
    ap.add_argument("--max-iter", type=int, default=2000, help="Pasos máx. power-iteration")
    ap.add_argument("--markov-weight", type=float, default=0.5, help="Peso de Markov vs Prior (0..1)")
    ap.add_argument("--gen", type=int, default=None, help="# candidatos a muestrear (solo n5sb). En 4D se ignora si None => evalúa 0000..9999")
    ap.add_argument("--candidates", help="CSV de candidatos (4D: col 'num'; n5sb: n1..n5,sb)")
    ap.add_argument("--export", help="CSV top-N (si se usa --top)")
    ap.add_argument("--export-all", help="CSV todos los candidatos evaluados")
    ap.add_argument("--top", type=int, default=50, help="Top-N a exportar")
    ap.add_argument("--report", help="HTML con entropías y mixing")
    args = ap.parse_args()

    rng = make_rng(args.rng, args.seed)

    cnx = sqlite3.connect(args.db)
    cnx.row_factory = sqlite3.Row

    game = args.game.lower().strip()
    is4d = game in ("astro_luna","astro","boyaca","huila","manizales","medellin","quindio","tolima","all4d")
    isn5 = game in ("baloto","revancha","n5sb","all_n5sb")

    if not (is4d or isn5):
        print(f"[ERROR] Juego no soportado: {args.game}", file=sys.stderr)
        sys.exit(2)

    meta = {
        "db": os.path.abspath(args.db),
        "game": args.game,
        "rng": args.rng,
        "seed": args.seed,
        "smoothing": args.smoothing,
        "damping": args.damping,
        "markov_weight": args.markov_weight,
        "generated_at": datetime.now().isoformat(timespec="seconds")
    }

    if is4d:
        draws = load_draws_4d(cnx, game)
        if len(draws)<2:
            print("[ERROR] Muy pocos sorteos 4D para entrenar.", file=sys.stderr)
            sys.exit(3)
        Ppos = transitions_4d(draws, smoothing=args.smoothing)
        pi_pos, mixing, ent = stationary_per_pos(Ppos, alpha=args.damping, eps=args.eps, max_steps=args.max_iter)
        prev = draws[-1]

        # candidatos
        cand_list: List[str] = []
        if args.candidates:
            # CSV con columna 'num'
            with open(args.candidates, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    s = str(row.get("num","")).strip()
                    if len(s)==4 and s.isdigit():
                        cand_list.append(s)
        if not cand_list:
            # evalúa todos (o muestrea si quieres)
            cand_list = list(enumerate_4d())

        rows=[]
        w = max(0.0, min(1.0, args.markov_weight))
        for s in cand_list:
            lp_m = logprob_next_4d(Ppos, prev, s)
            lp_p = logprob_prior_4d(pi_pos, s)
            score = w*lp_m + (1.0-w)*lp_p
            rows.append({"num":s, "score":score, "markov_logp":lp_m, "prior_logp":lp_p})
        rows.sort(key=lambda r: r["score"], reverse=True)

        if args.export_all:
            write_csv_4d(args.export_all, rows)
        if args.export:
            write_csv_4d(args.export, rows[:args.top])
        if args.report:
            write_report_html(args.report, meta, ent, mixing)

    else:
        # N5+SB
        draws = load_draws_n5sb(cnx, game)
        if len(draws)<2:
            print("[ERROR] Muy pocos sorteos n5+sb para entrenar.", file=sys.stderr)
            sys.exit(4)
        Ppos, mn, k = transitions_npos(draws, npos=6, smoothing=args.smoothing)
        pi_pos, mixing, ent = stationary_per_pos(Ppos, alpha=args.damping, eps=args.eps, max_steps=args.max_iter)
        prev = draws[-1]

        # candidatos: archivo o generados
        cand_list: List[Tuple[int,int,int,int,int,int]] = []
        if args.candidates:
            with open(args.candidates, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    try:
                        n1=int(row["n1"]); n2=int(row["n2"]); n3=int(row["n3"]); n4=int(row["n4"]); n5=int(row["n5"]); sb=int(row["sb"])
                        cand_list.append((n1,n2,n3,n4,n5,sb))
                    except:
                        continue
        if not cand_list:
            gen = args.gen or 10000
            mx = mn + k - 1
            cand_list = sample_n5sb(rng, gen, mn, mx)

        rows=[]
        w = max(0.0, min(1.0, args.markov_weight))
        for t in cand_list:
            lp_m = logprob_next_npos(Ppos, prev, t, mn=mn)
            lp_p = logprob_prior_npos(pi_pos, t, mn=mn)
            score = w*lp_m + (1.0-w)*lp_p
            n1,n2,n3,n4,n5,sb = t
            rows.append({"n1":n1,"n2":n2,"n3":n3,"n4":n4,"n5":n5,"sb":sb,
                         "score":score,"markov_logp":lp_m,"prior_logp":lp_p})
        rows.sort(key=lambda r: r["score"], reverse=True)

        if args.export_all:
            write_csv_n5sb(args.export_all, rows)
        if args.export:
            write_csv_n5sb(args.export, rows[:args.top])
        if args.report:
            write_report_html(args.report, meta, ent, mixing)

if __name__=="__main__":
    main()
