# devuelve 0 si "listo", 2 si "no listo"
import sys, argparse
p=argparse.ArgumentParser()
p.add_argument("--db", required=False)
p.add_argument("--game", required=False)
args=p.parse_args()
# En stub, diremos que "no listo" para evitar llamar al trainer real si tu master lo consulta antes
sys.exit(2)
