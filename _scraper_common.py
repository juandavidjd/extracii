# -*- coding: utf-8 -*-
import os, re, sys, time, json, csv, math, random
import datetime as dt
from typing import Optional, Tuple, Dict, List
import requests
from requests.adapters import HTTPAdapter, Retry

def log(msg:str):
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def get_env_paths() -> Dict[str, str]:
    root = os.environ.get("RP_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    data_crudo = os.environ.get("RP_DATA_CRUDO", os.path.join(root, "data", "crudo"))
    logs = os.environ.get("RP_LOGS", os.path.join(root, "logs"))
    os.makedirs(data_crudo, exist_ok=True)
    os.makedirs(logs, exist_ok=True)
    return {"root": root, "data_crudo": data_crudo, "logs": logs}

def session_with_retries() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=5, backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"])
    )
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/126.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.mount("http://", HTTPAdapter(max_retries=retries))
    return s

def read_draw_range_arg(default_last:int=2600, steps:int=60) -> List[int]:
    """
    Permite pasar opcionalmente:
      --from 2540 --to 2546
    Si no, intenta una ventana hacia atrás.
    """
    args = sys.argv[1:]
    f, t = None, None
    for i,a in enumerate(args):
        if a == "--from" and i+1 < len(args):
            try: f = int(args[i+1])
            except: pass
        if a == "--to" and i+1 < len(args):
            try: t = int(args[i+1])
            except: pass
    if f and t and f <= t:
        return list(range(f, t+1))
    # fallback: ventana hacia atrás (no conocemos el último; usamos default_last)
    return list(range(default_last-steps+1, default_last+1))

def ensure_csv(path:str, headers:List[str]):
    new = not os.path.exists(path)
    if new:
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(headers)

def append_unique_rows(path:str, headers:List[str], key_cols:List[str], rows:List[Dict]):
    ensure_csv(path, headers)
    # índice in-memory de claves ya presentes
    seen = set()
    with open(path, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            key = tuple(row.get(k, "") for k in key_cols)
            seen.add(key)
    cnew = 0
    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        for row in rows:
            key = tuple(str(row.get(k,"")) for k in key_cols)
            if key in seen: 
                continue
            w.writerow({h: row.get(h, "") for h in headers})
            seen.add(key); cnew += 1
    return cnew

def parse_numbers_generic(html:str) -> Tuple[Optional[List[int]], Optional[int]]:
    """
    Fallback muy tolerante: busca 5 números (1..43) y una 'super' (1..16)
    Útil si cambia el HTML de Baloto.
    """
    # encuentra secuencias de 1-2 dígitos plausibles
    nums = [int(x) for x in re.findall(r"\b([0-9]{1,2})\b", html)]
    # filtramos por rango del Baloto
    base = [n for n in nums if 1 <= n <= 43]
    sb = [n for n in nums if 1 <= n <= 16]
    five = None
    superb = None
    # intenta detectar un bloque probable de 5 distintos en [1..43]
    for i in range(0, max(0, len(base)-4)):
        bloc = base[i:i+5]
        if len(set(bloc))==5:
            five = bloc; break
    # intenta un super suelto
    if sb:
        superb = sb[-1]
    return five, superb
