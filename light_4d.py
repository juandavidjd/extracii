# -*- coding: utf-8 -*-
import argparse, os, sys, sqlite3, csv, html, datetime as dt
from collections import Counter, defaultdict

def eprint(*a, **k): print(*a, file=sys.stderr, **k)
def now(): return dt.datetime.now().strftime("%Y%m%d_%H%M%S")
def ensure_dir(p): 
    p = p.strip() or os.path.join(os.getcwd(), "reports")
    os.makedirs(p, exist_ok=True)
    return p

def parse_csv_list(s): return [x.strip() for x in (s or "").split(",") if x.strip()]

def page(title, body):
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
body{{font-family:system-ui,Segoe UI,Roboto,Arial,sans-serif;margin:20px}}
.card{{border:1px solid #e5e7eb;border-radius:12px;padding:12px;margin:12px 0}}
table{{border-collapse:collapse;width:100%;font-size:14px}}
th,td{{border:1px solid #e5e7eb;padding:6px 8px;text-align:center}} th{{background:#f9fafb}}
.help{{color:#6b7280;font-size:12px}}
</style></head><body>{body}</body></html>"""

def write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,"w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(header); w.writerows(rows)

def find_col(cols, candidates):
    s={c.lower():c for c in cols}
    for c in candidates:
        if c.lower() in s: return s[c.lower()]
    return None

def fetch_pos_stream(conn, lots, lot_window=None, use_windowed=True):
    view = "v_4d_pos_expanded_win" if use_windowed else "v_4d_pos_expanded"
    cur=conn.execute(f"SELECT * FROM {view} LIMIT 1")
    cols=[d[0] for d in cur.description]
    col_lot  = find_col(cols, ["lot","loteria","game","lot_name"]) or "lot"
    col_pos  = find_col(cols, ["pos","position"]) or "pos"
    col_dig  = find_col(cols, ["digit","dig","d"]) or "digit"

    # draw_id original o fallback a rn
    col_draw = find_col(cols, ["draw_id","sorteo_id","id_sorteo","id","turno","draw"])
    col_rn   = find_col(cols, ["rn","rownum","row_number","rank"])
    if not col_draw and not col_rn:
        raise KeyError("no draw_id-like column found")

    # Build SQL
    sel_key = f"{col_draw} AS draw_key" if col_draw else f"{col_rn} AS draw_key"
    sql = f"SELECT {col_lot} AS lot, {sel_key}, {col_pos} AS pos, {col_dig} AS digit FROM {view} WHERE 1=1"
    params=[]
    if lots:
        lots_lc=[x.lower() for x in lots]
        sql += f" AND LOWER({col_lot}) IN ({','.join(['?']*len(lots_lc))})"
        params.extend(lots_lc)
    if lot_window and lot_window>0 and col_rn:
        sql += " AND {0} <= ?".format(col_rn)
        params.append(int(lot_window))
    cur=conn.execute(sql, params)
    cols=[c[0] for c in cur.description]
    return [dict(zip(cols,r)) for r in cur.fetchall()]

def tab_pairs_trios(rows, pos_pairs, pos_trios, topk):
    by_draw=defaultdict(lambda:[None]*4)
    for r in rows:
        try:
            p=int(r["pos"]); d=int(r["digit"])
            if 0<=p<=3 and 0<=d<=9: by_draw[(r["lot"], r["draw_key"])][p]=d
        except: pass
    pc, tc = Counter(), Counter()
    for (lot,did),digits in by_draw.items():
        if any(v is None for v in digits): continue
        for (a,b) in pos_pairs:
            if a!=b and 0<=a<=3 and 0<=b<=3:
                pc[(lot,a,b,digits[a],digits[b])] += 1
        for (a,b,c) in pos_trios:
            if len({a,b,c})==3 and all(0<=x<=3 for x in (a,b,c)):
                tc[(lot,a,b,c,digits[a],digits[b],digits[c])] += 1
    p = pc.most_common(topk) if topk else pc.items()
    t = tc.most_common(topk) if topk else tc.items()
    pairs=[(lot,a,b,da,db,cnt) for ((lot,a,b,da,db),cnt) in p]
    trios=[(lot,a,b,c,da,db,dc,cnt) for ((lot,a,b,c,da,db,dc),cnt) in t]
    return pairs, trios

def crosstab(rows, a, b, topk):
    by_draw=defaultdict(lambda:[None]*4)
    for r in rows:
        try:
            p=int(r["pos"]); d=int(r["digit"])
            if 0<=p<=3 and 0<=d<=9: by_draw[(r["lot"], r["draw_key"])][p]=d
        except: pass
    cc = Counter()
    for (lot,did),digits in by_draw.items():
        if any(v is None for v in digits): continue
        cc[(lot,a,b,digits[a],digits[b])] += 1
    items = cc.most_common(topk) if topk else cc.items()
    return [(lot,a,b,da,db,cnt) for ((lot,_,__,da,db),cnt) in items]

def render_html(path, title, pairs, trios, pair_xtabs):
    def table(headers, rows):
        th="".join(f"<th>{html.escape(h)}</th>" for h in headers)
        trs=[]
        for r in rows:
            tds="".join(f"<td>{html.escape(str(x))}</td>" for x in r)
            trs.append(f"<tr>{tds}</tr>")
        return f"<table><thead><tr>{th}</tr></thead><tbody>{''.join(trs)}</tbody></table>"
    body=[]
    body.append(f"<h1>{html.escape(title)}</h1>")
    body.append("<div class='help'>Frecuencias descriptivas por lotería y posición (no determinista).</div>")
    body.append("<div class='card'><h3>Pares TOP</h3>"+table(["lot","posA","posB","dA","dB","freq"], pairs)+"</div>")
    body.append("<div class='card'><h3>Tríos TOP</h3>"+table(["lot","posA","posB","posC","dA","dB","dC","freq"], trios)+"</div>")
    if pair_xtabs:
        body.append("<div class='card'><h3>Crosstabs (pares)</h3>")
        for (a,b),rows in pair_xtabs.items():
            body.append(f"<h4>pos {a} vs {b}</h4>"+table(["lot","posA","posB","dA","dB","freq"], rows))
        body.append("</div>")
    with open(path,"w",encoding="utf-8") as f:
        f.write(page(title, "\n".join(body)))

def main():
    ap=argparse.ArgumentParser(description="4D light reports")
    ap.add_argument("--db", required=True)
    ap.add_argument("--reports", default="")
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--topk", type=int, default=100)
    ap.add_argument("--pair-crosstab-topk", type=int, default=50)
    ap.add_argument("--lot-window", type=int, default=200)
    ap.add_argument("--pos-pairs", default="0-1,1-2,2-3,0-2,1-3")
    ap.add_argument("--pos-trios", default="0-1-2,1-2-3,0-2-3,0-1-3")
    ap.add_argument("--csv", action="store_true")
    ap.add_argument("--csv-all", action="store_true")
    ap.add_argument("--only-lots", default="")
    ap.add_argument("--exclude-lots", default="")
    args=ap.parse_args()

    reports = ensure_dir(args.reports or os.environ.get("RP_REPORTS",""))
    lots_all = ["tolima","huila","manizales","quindio","medellin","boyaca"]
    only=[x.lower() for x in parse_csv_list(args.only_lots)]
    excl=[x.lower() for x in parse_csv_list(args.exclude_lots)]
    lots=[x for x in lots_all if (not only or x in only) and x not in excl]

    conn=sqlite3.connect(args.db); conn.row_factory=sqlite3.Row
    ts=now()

    def parse_pairs(s):
        out=[]; 
        for tok in parse_csv_list(s):
            try: a,b=tok.split("-"); out.append((int(a),int(b)))
            except: pass
        return out
    def parse_trios(s):
        out=[]; 
        for tok in parse_csv_list(s):
            try: a,b,c=tok.split("-"); out.append((int(a),int(b),int(c)))
            except: pass
        return out
    pos_pairs=parse_pairs(args.pos_pairs)
    pos_trios=parse_trios(args.pos_trios)

    for lot in lots:
        try:
            rows = fetch_pos_stream(conn, [lot], lot_window=args.lot_window, use_windowed=True)
            if not rows:
                eprint(f"[WARN] {lot}: sin datos, omito.")
                continue
            pairs,trios = [],[]
            pairs,_ = tab_pairs_trios(rows, pos_pairs, [], args.topk)
            _,trios = tab_pairs_trios(rows, [], pos_trios, args.topk)

            pair_xtabs={}
            for a,b in pos_pairs:
                pair_xtabs[(a,b)] = crosstab(rows, a, b, args.pair_crosstab_topk)

            if args.csv or args.csv_all:
                write_csv(os.path.join(reports, f"{lot}_pairs_{ts}.csv"),
                          ["lot","posA","posB","dA","dB","freq"], pairs)
                write_csv(os.path.join(reports, f"{lot}_trios_{ts}.csv"),
                          ["lot","posA","posB","posC","dA","dB","dC","freq"], trios)

            out_html=os.path.join(reports, f"{lot}_4d_light_{ts}.html")
            render_html(out_html, f"{lot} · 4D light", pairs, trios, pair_xtabs)

        except Exception as ex:
            eprint(f"[WARN] {lot} 4D light tuvo errores: {ex}")
    conn.close()
    print("[OK ] 4D light")

if __name__=="__main__":
    main()
