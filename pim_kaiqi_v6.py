
# ===================================================================
# pim_kaiqi_v6.py — ENTERPRISE VERSION (REAL, NO PLACEHOLDERS)
# ===================================================================

import os, json, csv, hashlib, time, base64
import pandas as pd
from openai import OpenAI

# ------------------------------------------------------------
CONFIG_PATH="config_pim_kaiqi_v6.json"
with open(CONFIG_PATH,"r",encoding="utf-8") as f:
    CFG=json.load(f)

INVENTORY_CSV = CFG["inventory_path"]
IMAGE_DIR     = CFG["image_dir"]
OUTPUT_DIR    = CFG["output_dir"]
MODEL         = CFG["model"]
RATE_LIMIT    = CFG["rate_limit_per_minute"]
MAX_RETRY     = CFG["max_retries"]
VERBOSE       = CFG["verbose"]
DRY_RUN       = CFG["dry_run"]

COL_IMG       = CFG["col_imagen"]
SHOPIFY_OUT   = os.path.join(OUTPUT_DIR, CFG["shopify_csv"])
PIM_JSON_OUT  = os.path.join(OUTPUT_DIR, CFG["pim_json"])
CACHE_FILE    = os.path.join(OUTPUT_DIR, CFG["cache_json"])

os.makedirs(OUTPUT_DIR,exist_ok=True)

# ------------------------------------------------------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
LAST_CALLS=[]

def rate_limit():
    now=time.time()
    LAST_CALLS.append(now)
    while LAST_CALLS and now-LAST_CALLS[0]>60:
        LAST_CALLS.pop(0)
    if len(LAST_CALLS)>=RATE_LIMIT:
        sleep_t=60-(now-LAST_CALLS[0])
        if sleep_t>0: time.sleep(sleep_t)

# ------------------------------------------------------------
def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            return json.load(open(CACHE_FILE,"r",encoding="utf-8"))
        except:
            return {}
    return {}
def save_cache(c):
    json.dump(c,open(CACHE_FILE,"w",encoding="utf-8"),ensure_ascii=False,indent=2)

CACHE=load_cache()

# ------------------------------------------------------------
# MATCHING Opción C
# ------------------------------------------------------------
def read_img_base64(path):
    try:
        with open(path,"rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None

def pedir_match(desc, img_path):
    bname=os.path.basename(img_path)
    key=f"{bname}|{hashlib.md5(desc.encode()).hexdigest()}"
    if key in CACHE:
        return CACHE[key]

    img64=read_img_base64(img_path)
    if not img64:
        return {"match_conf":0,"notes":"no image"}

    prompt=f"""
Eres un modelo experto. Debes evaluar la similitud entre:

DESCRIPCION INVENTARIO:
{desc}

Y la IMAGEN del repuesto.

Devuelve SOLO JSON:
{{
 "match_conf": 0.0,
 "notes": "..."
}}
"""

    for _ in range(MAX_RETRY):
        try:
            rate_limit()
            r=client.chat.completions.create(
                model=MODEL,
                temperature=0,
                messages=[
                    {"role":"system","content":"Responde solo JSON."},
                    {"role":"user","content":[
                        {"type":"text","text":prompt},
                        {"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{img64}"}}
                    ]}
                ]
            )
            txt=r.choices[0].message.content.strip().replace("```json","").replace("```","")
            js=json.loads(txt)
            CACHE[key]=js; save_cache(CACHE)
            return js
        except Exception as e:
            time.sleep(2)
    return {"match_conf":0,"notes":"fail"}

# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def main():
    df=pd.read_csv(INVENTORY_CSV,encoding="utf-8")
    rows=[]; pim_json=[]

    for idx,row in df.iterrows():
        codigo=row.get(COL_IMG,"")
        desc=" ".join(str(row[c]) for c in df.columns if isinstance(row[c],str))

        # buscar imagen por nombre exacto o aproximación
        img_path=os.path.join(IMAGE_DIR,codigo) if isinstance(codigo,str) and len(codigo)>3 else None
        if not img_path or not os.path.exists(img_path):
            # buscar imagen candidata
            imgs=[f for f in os.listdir(IMAGE_DIR) if f.lower().endswith((".jpg",".png",".jpeg",".webp"))]
            best=None; best_conf=0
            for im in imgs:
                tmp=os.path.join(IMAGE_DIR,im)
                js=pedir_match(desc,tmp)
                c=js.get("match_conf",0)
                if c>best_conf:
                    best_conf=c; best=im
            if best:
                img_path=os.path.join(IMAGE_DIR,best)
        if not img_path or not os.path.exists(img_path):
            img_path=""

        # armar shopify row
        title=row.get("DESCRIPCION","")
        price=row.get("PRECIO",0)
        vendor="KAIQI"
        image=""

        if img_path:
            image=f"file://{img_path}"

        rows.append([row.get("CODIGO_NEW",""), title, title, vendor, row.get("COMPONENTE",""), row.get("SISTEMA",""), price, image])

        pim_json.append({
            "codigo": row.get("CODIGO_NEW",""),
            "title": title,
            "image": image,
            "desc": desc,
            "metadata": row.to_dict()
        })

    with open(SHOPIFY_OUT,"w",encoding="utf-8",newline="") as f:
        w=csv.writer(f)
        w.writerow(["HANDLE","TITLE","BODY","VENDOR","TYPE","TAGS","PRICE","IMAGE"])
        for r in rows: w.writerow(r)

    with open(PIM_JSON_OUT,"w",encoding="utf-8") as f:
        json.dump(pim_json,f,ensure_ascii=False,indent=2)

    print("OK PIM v6 ENTERPRISE")

if __name__=="__main__":
    main()
