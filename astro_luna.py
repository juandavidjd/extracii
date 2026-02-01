# -*- coding: utf-8 -*-
import os, csv, datetime
from scraper_utils import log, write_noop_row

RP_ROOT = os.environ.get("RP_ROOT", os.getcwd())
CSV_PATH = os.path.join(RP_ROOT, "data", "crudo", "astro_luna.csv")

def obtener_nuevos_registros() -> list:
    """
    Aquí iría tu lógica real de scraping.
    Devuelvo lista de dicts con: fecha(dd/mm/YYYY), numero(int), signo(str).
    """
    # En este contexto asumimos que hoy no hay nuevos para demostrar no-op.
    return []

def guardar(regs):
    fieldnames = ["fecha","numero","signo"]
    header_needed = not os.path.exists(CSV_PATH) or os.path.getsize(CSV_PATH)==0
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        if header_needed:
            w.writeheader()
        for r in regs:
            w.writerow(r)

def main():
    log("=== Inicio de scrapeo de AstroLuna ===")
    regs = obtener_nuevos_registros()
    if not regs:
        log("AstroLuna: sin nuevos registros")
        write_noop_row(CSV_PATH, schema="astro_luna", reason="no_changes")
        print("✅ Scrapeo completado")
        return
    guardar(regs)
    log(f"AstroLuna: guardé {len(regs)} filas")
    print("✅ Scrapeo completado")

if __name__ == "__main__":
    main()
