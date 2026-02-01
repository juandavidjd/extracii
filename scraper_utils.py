#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time, csv, re, os, sys, json, math
from pathlib import Path
from contextlib import contextmanager

import requests
from bs4 import BeautifulSoup

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")

def mk_session(timeout=20, retries=3, backoff=1.5):
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "es-CO,es;q=0.9"})
    s._timeout = timeout
    s._retries = retries
    s._backoff = backoff
    return s

def fetch(session, url):
    err = None
    for i in range(session._retries):
        try:
            r = session.get(url, timeout=session._timeout, allow_redirects=True)
            if r.status_code == 200 and r.text:
                return r.text
            err = f"HTTP {r.status_code}"
        except Exception as e:
            err = str(e)
        time.sleep(session._backoff * (i+1))
    raise RuntimeError(f"No pude obtener {url}: {err}")

def soupify(html):
    # lxml más rápido si está, html5lib más tolerante. bs4 decide.
    return BeautifulSoup(html, "lxml")

@contextmanager
def atomic_write(path: Path):
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        yield tmp
        tmp.replace(path)
    finally:
        if tmp.exists():
            try: tmp.unlink()
            except: pass

def read_csv_dict(path: Path):
    if not path.exists() or path.stat().st_size == 0:
        return [], []
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        rows = list(r)
        return r.fieldnames, rows

def write_csv_dict(path: Path, rows, headers):
    path.parent.mkdir(parents=True, exist_ok=True)
    with atomic_write(path) as tmp:
        with tmp.open("w", encoding="utf-8", newline="\r\n") as f:
            w = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
            w.writeheader()
            for row in rows:
                w.writerow({h: (row.get(h,"") if row.get(h) is not None else "") for h in headers})

def merge_unique(existing_rows, new_rows, key_tuple):
    """key_tuple = ('sorteo',) o ('fecha','numero') etc."""
    def key_of(r): return tuple((r.get(k) or "").strip() for k in key_tuple)
    seen = set(key_of(r) for r in existing_rows)
    merged = list(existing_rows)
    for r in new_rows:
        k = key_of(r)
        if not all(k):  # si clave incompleta, descarta
            continue
        if k in seen:
            # update liviano (por si mejoran campos)
            idx = next(i for i,er in enumerate(merged) if key_of(er)==k)
            merged[idx].update(r)
        else:
            merged.append(r)
            seen.add(k)
    return merged

def to_int(s):
    if s is None: return None
    s = str(s).strip()
    s = re.sub(r"[^\d\-]", "", s)
    if s == "": return None
    try: return int(s)
    except: return None

def clean_money(s):
    if s is None: return None
    s = str(s).strip()
    s = s.replace(".", "").replace(",", "")
    s = re.sub(r"[^\d]", "", s)
    return s or None

def pick_first(*vals):
    for v in vals:
        if v is not None and str(v).strip() != "":
            return v
    return None

def log(msg):
    print(msg, flush=True)
