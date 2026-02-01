
# ============================================================
# renombrar_seo_kaiqi_v5.py — ENTERPRISE VERSION (REAL, NO PLACEHOLDERS)
# ============================================================

import os, re, json, base64, unicodedata, shutil, time, hashlib
import threading, queue
from openai import OpenAI

# ------------------------------------------------------------
# CARGA CONFIG
# ------------------------------------------------------------
CONFIG_PATH = "config_renombrado_seo_v5.json"
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CFG = json.load(f)

IMAGE_DIR   = CFG["image_dir"]
OUTPUT_DIR  = CFG["output_dir"]
NUM_WORKERS = CFG["num_workers"]
RATE_LIMIT  = CFG["rate_limit_per_minute"]
MAX_RETRY   = CFG["max_retries"]
VERBOSE     = CFG["verbose"]
CACHE_FILE  = os.path.join(OUTPUT_DIR, CFG["cache_filename"])
LOG_FILE    = os.path.join(OUTPUT_DIR, CFG["log_filename"])
MODEL       = CFG["model"]

DIR_DUP = os.path.join(OUTPUT_DIR, "IMAGENES_DUPLICADAS")
DIR_LOGS = os.path.join(OUTPUT_DIR, "LOGS")
DIR_CACHE = os.path.join(OUTPUT_DIR, "RENOMBRE_CACHE")

os.makedirs(DIR_DUP, exist_ok=True)
os.makedirs(DIR_LOGS, exist_ok=True)
os.makedirs(DIR_CACHE, exist_ok=True)

# ------------------------------------------------------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ------------------------------------------------------------
# UTILIDADES
# ------------------------------------------------------------
def slugify(text):
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c)!="Mn")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")

def encode_image(p):
    try:
        with open(p,"rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None

# ------------------------------------------------------------
# CACHE
# ------------------------------------------------------------
def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE,"r",encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_cache(c):
    with open(CACHE_FILE,"w",encoding="utf-8") as f:
        json.dump(c,f,ensure_ascii=False,indent=2)

CACHE = load_cache()

# ------------------------------------------------------------
# RATE LIMIT
# ------------------------------------------------------------
LAST_CALLS=[]
def rate_limit():
    now=time.time()
    LAST_CALLS.append(now)
    # limpiar historial 60s
    while LAST_CALLS and now - LAST_CALLS[0] > 60:
        LAST_CALLS.pop(0)
    if len(LAST_CALLS)>=RATE_LIMIT:
        sleep_t = 60-(now-LAST_CALLS[0])
        if sleep_t>0:
            time.sleep(sleep_t)

# ------------------------------------------------------------
# PROMPT
# ------------------------------------------------------------
PROMPT = """
Actúa como experto en repuestos de motos y triciclos. Devuelve SOLO JSON:
{
 "nombre_base_seo": "...",
 "componente": "...",
 "marca_moto": "...",
 "modelo_moto": "...",
 "cilindraje": "...",
 "es_motocarguero": true/false,
 "numeros_molde": "...",
 "observaciones": "..."
}
"""

# ------------------------------------------------------------
def pedir_ia(img_path):
    fname=os.path.basename(img_path)
    slug_base=os.path.splitext(fname)[0]

    # cache
    if slug_base in CACHE:
        return CACHE[slug_base]

    img64=encode_image(img_path)
    if not img64:
        return None

    # intentar
    for _ in range(MAX_RETRY):
        try:
            rate_limit()
            r = client.chat.completions.create(
                model=MODEL,
                temperature=0,
                messages=[
                    {"role":"system","content":"Responde solo JSON válido."},
                    {"role":"user","content":[
                        {"type":"text","text":PROMPT+f"\nNombre actual: {fname}"},
                        {"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{img64}","detail":"high"}}
                    ]}
                ]
            )
            txt=r.choices[0].message.content.strip()
            txt=txt.replace("```json","").replace("```","").strip()
            js=json.loads(txt)
            CACHE[slug_base]=js
            save_cache(CACHE)
            return js
        except Exception as e:
            time.sleep(2)
    return None

# ------------------------------------------------------------
def worker(q,res,slugs):
    while True:
        try:
            p=q.get_nowait()
        except:
            break
        fname=os.path.basename(p)
        data=pedir_ia(p)
        if not data:
            res.append({"archivo_original":fname,"archivo_nuevo":fname,"error":"IA"})
            q.task_done()
            continue

        slug=slugify(data.get("nombre_base_seo",""))
        if not slug:
            slug=slugify(os.path.splitext(fname)[0])

        ext=os.path.splitext(fname)[1].lower()
        new_name=f"{slug}{ext}"
        new_path=os.path.join(IMAGE_DIR,new_name)

        if slug in slugs:
            # duplicado
            shutil.move(p, os.path.join(DIR_DUP,fname))
            res.append({"archivo_original":fname,"archivo_nuevo":fname,"duplicado":"SI","slug":slug})
        else:
            slugs[slug]=fname
            if os.path.exists(new_path) and new_path!=p:
                shutil.move(p, os.path.join(DIR_DUP,fname))
                res.append({"archivo_original":fname,"archivo_nuevo":fname,"duplicado":"COLISION","slug":slug})
            else:
                try:
                    os.rename(p,new_path)
                    res.append({"archivo_original":fname,"archivo_nuevo":new_name,"slug":slug})
                except:
                    res.append({"archivo_original":fname,"archivo_nuevo":fname,"error":"rename_fail","slug":slug})

        q.task_done()

# ------------------------------------------------------------
def main():
    files=[os.path.join(IMAGE_DIR,f) for f in os.listdir(IMAGE_DIR)
           if os.path.isfile(os.path.join(IMAGE_DIR,f)) and
              f.lower().endswith((".jpg",".png",".jpeg",".webp"))]

    q=queue.Queue()
    for f in files: q.put(f)

    resultados=[]
    sl={}
    threads=[]
    for _ in range(NUM_WORKERS):
        t=threading.Thread(target=worker,args=(q,resultados,sl))
        t.start(); threads.append(t)
    for t in threads: t.join()

    with open(LOG_FILE,"w",encoding="utf-8") as f:
        f.write("archivo_original,archivo_nuevo,slug,error\n")
        for r in resultados:
            f.write(f"{r.get('archivo_original','')},{r.get('archivo_nuevo','')},{r.get('slug','')},{r.get('error','')}\n")

    print("OK RENOMBRE V5 enterprise")

if __name__=="__main__":
    main()
