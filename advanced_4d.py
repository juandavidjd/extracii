# -*- coding: utf-8 -*-
import argparse, os, sys, sqlite3, csv, html, shutil, datetime as dt
from collections import defaultdict, Counter

def eprint(*a, **k): print(*a, file=sys.stderr, **k)
def ensure_dir(p):
    p = (p or os.environ.get("RP_REPORTS","")).strip() or os.path.join(os.getcwd(),"reports")
    os.makedirs(p, exist_ok=True)
    return p
def ts(): return dt.datetime.now().strftime("%Y%m%d_%H%M%S")

def page(title, body):
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
body{{font-family:system-ui,Segoe UI,Roboto,Arial,sans-serif;margin:20px}}
.card{{border:1px solid #e5e7eb;border-radius:12px;padding:12px;margin:12px 0}}
table{{border-collapse:collapse;width:100%;font-size:14px}}
th,td{{border:1px solid #e5e7eb;padding:6px 8px;text-align:center}} th{{background:#f9fafb}}
.help{{color:#6b7280;font-size:12px}}
</style></head><body>{body}</body></html>"""

def find_col(cols, candidates):
    s={c.lower():c for c in cols}
    for c in candidates:
        if c.lower() in s: return s[c.lower()]
    return None

def fetch_stream(conn, lot, use_window=True, lot_window=200):
    view="v_4d_pos_expanded_win" if use_window else "v_4d_pos_expanded"
    cur=conn.execute(f"SELECT * FROM {view} LIMIT 1")
    cols=[d[0] for d in cur.description]
    col_lot  = find_col(cols, ["lot","loteria","game","lot_name"]) or "lot"
    col_pos  = find_col(cols, ["pos","position"]) or "pos"
    col_dig  = find_col(cols, ["digit","dig","d"]) or "digit"
    col_draw = find_col(cols, ["draw_id","sorteo_id","id_sorteo","id","turno","draw"])
    col_rn   = find_col(cols, ["rn","rownum","row_number","rank"])
    if not col_draw and not col_rn:
        raise KeyError("no draw_id-like column found")

    sel_key = f"{col_draw} AS draw_key" if col_draw else f"{col_rn} AS draw_key"
    sql=f"SELECT {col_lot} AS lot, {sel_key}, {col_pos} AS pos, {col_dig} AS digit FROM {view} WHERE LOWER({col_lot})=?"
    params=[lot.lower()]
    if lot_window and lot_window>0 and col_rn:
        sql+=" AND {0} <= ?".format(col_rn); params.append(int(lot_window))
    cur=conn.execute(sql, params)
    cols=[c[0] for c in cur.description]
    return [dict(zip(cols,r)) for r in cur.fetchall()]

def rebuild_by_draw(rows):
    by=defaultdict(lambda:[None]*4)
    for r in rows:
        p=int(r["pos"]); d=int(r["digit"])
        if 0<=p<=3 and 0<=d<=9: by[(r["lot"], r["draw_key"])][p]=d
    return by

def freq_pairs_trios(by_draw, pos_pairs, pos_trios, topk):
    pc, tc = Counter(), Counter()
    for (lot,did),digits in by_draw.items():
        if any(v is None for v in digits): continue
        for (a,b) in pos_pairs:
            if a!=b and all(0<=x<=3 for x in (a,b)):
                pc[(lot,a,b,digits[a],digits[b])]+=1
        for (a,b,c) in pos_trios:
            if len({a,b,c})==3 and all(0<=x<=3 for x in (a,b,c)):
                tc[(lot,a,b,c,digits[a],digits[b],digits[c])]+=1
    pr = pc.most_common(topk) if topk else pc.items()
    tr = tc.most_common(topk) if topk else tc.items()
    pr=[(lot,a,b,da,db,cnt) for ((lot,a,b,da,db),cnt) in pr]
    tr=[(lot,a,b,c,da,db,dc,cnt) for ((lot,a,b,c,da,db,dc),cnt) in tr]
    return pr, tr

def markov_by_pos(by_draw):
    per_pos={0:defaultdict(Counter),1:defaultdict(Counter),2:defaultdict(Counter),3:defaultdict(Counter)}
    by_lot=defaultdict(list)
    for (lot,did),digits in by_draw.items():
        by_lot[lot].append((did,digits))
    for lot,arr in by_lot.items():
        # ordenar por clave de sorteo (string/num)
        try: arr.sort(key=lambda t: (int(t[0]) if str(t[0]).isdigit() else str(t[0])))
        except: arr.sort(key=lambda t: str(t[0]))
        for i in range(1,len(arr)):
            prev=arr[i-1][1]; curr=arr[i][1]
            if any(v is None for v in prev) or any(v is None for v in curr): continue
            for pos in range(4):
                per_pos[pos][(lot, prev[pos])][curr[pos]] += 1
    out=[]
    for pos in range(4):
        for (lot, frm), cnts in per_pos[pos].items():
            total=sum(cnts.values()) or 1
            for to, c in cnts.items():
                out.append((lot,pos,frm,to,c, round(c/total,6)))
    return out

def render(out_path, lot, pairs, trios, mk, label):
    def table(h, rows):
        th="".join(f"<th>{html.escape(x)}</th>" for x in h)
        trs=[]
        for r in rows:
            tds="".join(f"<td>{html.escape(str(x))}</td>" for x in r)
            trs.append(f"<tr>{tds}</tr>")
        return f"<table><thead><tr>{th}</tr></thead><tbody>{''.join(trs)}</tbody></table>"
    body=[]
    body.append(f"<h1>{html.escape(lot)} · 4D avanzado</h1>")
    body.append(f"<div class='help'>Corte: {html.escape(label)} · Indicadores descriptivos (pares/tríos/Markov).</div>")
    body.append("<div class='card'><h2>Pares TOP</h2>"+table(["lot","posA","posB","dA","dB","freq"], pairs)+"</div>")
    body.append("<div class='card'><h2>Tríos TOP</h2>"+table(["lot","posA","posB","posC","dA","dB","dC","freq"], trios)+"</div>")
    body.append("<div class='card'><h2>Markov por posición</h2>"+table(["lot","pos","from","to","cnt","prob"], mk)+"</div>")
    with open(out_path,"w",encoding="utf-8") as f:
        f.write(page(f"{lot} · 4D avanzado", "\n".join(body)))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--reports", default="")
    ap.add_argument("--lot-window", type=int, default=200)
    ap.add_argument("--only-lots", default="tolima,huila,manizales,quindio,medellin,boyaca")
    ap.add_argument("--pos-pairs", default="0-1,1-2,2-3,0-2,1-3")
    ap.add_argument("--pos-trios", default="0-1-2,1-2-3,0-2-3,0-1-3")
    ap.add_argument("--topk", type=int, default=100)
    args=ap.parse_args()

    reports = ensure_dir(args.reports)
    lots=[x.strip().lower() for x in args.only_lots.split(",") if x.strip()]
    label=ts()

    conn=sqlite3.connect(args.db); conn.row_factory=sqlite3.Row

    def _pairs(s):
        out=[]; 
        for tok in [t for t in s.split(",") if t.strip()]:
            try: a,b=tok.split("-"); out.append((int(a),int(b)))
            except: pass
        return out
    def _trios(s):
        out=[]; 
        for tok in [t for t in s.split(",") if t.strip()]:
            try: a,b,c=tok.split("-"); out.append((int(a),int(b),int(c)))
            except: pass
        return out
    pp=_pairs(args.pos_pairs); tt=_trios(args.pos_trios)

    for lot in lots:
        try:
            rows = fetch_stream(conn, lot, use_window=True, lot_window=args.lot_window)
            if not rows:
                eprint(f"[WARN] {lot}: sin datos para avanzado 4D, omito.")
                continue
            by = rebuild_by_draw(rows)
            pairs, trios = freq_pairs_trios(by, pp, tt, args.topk)
            mk = markov_by_pos(by)
            out_html=os.path.join(reports, f"{lot}_advanced_4d_{label}.html")
            render(out_html, lot, pairs, trios, mk, label)
            shutil.copyfile(out_html, os.path.join(reports, f"{lot}_advanced_4d_latest.html"))
        except Exception as ex:
            eprint(f"[WARN] avanzado 4D {lot} falló: {ex}")
    conn.close()
    print("[OK ] advanced 4d")

if __name__=="__main__":
    main()
