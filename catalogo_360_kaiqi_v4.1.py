
# ===================================================================
# catalogo_360_kaiqi_v4.1.py — ENTERPRISE VERSION (REAL, NO PLACEHOLDERS)
# ===================================================================

import os, json, base64, time, csv
from openai import OpenAI

IMAGE_DIR="C:/img/IMAGENES_KAIQI_MAESTRAS"
OUT_CSV="C:/img/catalogo_360_kaiqi_v4.1.csv"
MODEL="gpt-4o"
RATE_LIMIT=15
MAX_RETRY=3

client=OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
LAST=[]

def rate():
    now=time.time()
    LAST.append(now)
    while LAST and now-LAST[0]>60:
        LAST.pop(0)
    if len(LAST)>=RATE_LIMIT:
        time.sleep(60-(now-LAST[0]))

def img64(p):
    try: return base64.b64encode(open(p,"rb").read()).decode()
    except: return None

PROMPT="""
Devuelve SOLO JSON con estructura 360°:
{
 "identificacion_repuesto":"",
 "funcion_principal":"",
 "sistema":"",
 "posicion_vehiculo":"",
 "tipo_vehiculo_principal":"",
 "caracteristicas_visuales":"",
 "numeros_referencia_visibles":[],
 "compatibilidad_probable_resumen":"",
 "fitment_detallado":[
    {
     "marca":"",
     "modelo":"",
     "cilindraje":"",
     "anios_aproximados":"",
     "sistema":"",
     "posicion":"",
     "es_motocarguero":false,
     "notas":""
    }
 ],
 "nivel_confianza_fitment":0.0,
 "riesgos_o_advertencias":"",
 "nombre_comercial_catalogo":"",
 "palabras_clave_sugeridas":[],
 "requiere_revision_humana":true
}
"""

def pedir(path):
    fn=os.path.basename(path)
    b=img64(path)
    if not b: return None
    for _ in range(MAX_RETRY):
        try:
            rate()
            r=client.chat.completions.create(
                model=MODEL,
                temperature=0,
                messages=[
                    {"role":"system","content":"Solo JSON."},
                    {"role":"user","content":[
                        {"type":"text","text":PROMPT},
                        {"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b}","detail":"high"}}
                    ]}
                ]
            )
            t=r.choices[0].message.content.strip().replace("```json","").replace("```","")
            return json.loads(t)
        except:
            time.sleep(2)
    return None

def main():
    imgs=[f for f in os.listdir(IMAGE_DIR) if f.lower().endswith((".jpg",".png",".jpeg",".webp"))]
    rows=[]
    for im in imgs:
        p=os.path.join(IMAGE_DIR,im)
        js=pedir(p)
        if not js:
            rows.append([im,"{}"])
            continue
        rows.append([im,json.dumps(js,ensure_ascii=False)])
        print("OK 360:",im)

    with open(OUT_CSV,"w",encoding="utf-8",newline="") as f:
        w=csv.writer(f)
        w.writerow(["filename","raw_json_360"])
        for r in rows: w.writerow(r)

    print("OK 360 v4.1 ENTERPRISE")

if __name__=="__main__":
    main()
