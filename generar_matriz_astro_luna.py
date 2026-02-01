import os, csv, time
root=os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
outdir=os.path.join(root,"data","limpio")
os.makedirs(outdir, exist_ok=True)
path=os.path.join(outdir,"matriz_astro_luna.csv")
with open(path,"w",newline="",encoding="utf-8") as f:
    csv.writer(f).writerow(["d4","signo","freq"])
print(f"✅ Matriz generada: {path} (0 filas, stub)")
