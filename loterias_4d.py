# -*- coding: utf-8 -*-
import os, csv
from scraper_utils import log, write_noop_row

RP_ROOT = os.environ.get("RP_ROOT", os.getcwd())
LOT_NAMES = ["boyaca","huila","manizales","quindio","medellin","tolima"]

def csv_path(name:str) -> str:
    return os.path.join(RP_ROOT, "data", "crudo", f"{name}.csv")

def obtener_nuevos(name:str) -> list:
    """
    Tu scraping real por lotería.
    Salida: lista de dicts con columnas: fecha(dd/mm/YYYY), numero(int)
    """
    # Simulamos “sin cambios” para ejemplificar no-op
    return []

def guardar(name:str, rows:list):
    path = csv_path(name)
    fieldnames = ["fecha","numero"]
    need_header = not os.path.exists(path) or os.path.getsize(path)==0
    with open(path, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        if need_header: w.writeheader()
        for r in rows: w.writerow(r)

def main():
    log("=== Inicio de scrapeo de loterías ===")
    for name in LOT_NAMES:
        rows = obtener_nuevos(name)
        if not rows:
            log(f"{name}: sin nuevos registros")
            write_noop_row(csv_path(name), schema="loteria_4d", reason="no_changes", nombre=name)
        else:
            guardar(name, rows)
            log(f"{name}: guardé {len(rows)} filas")
    print("✅ Scrapeo completado")

if __name__ == "__main__":
    main()
