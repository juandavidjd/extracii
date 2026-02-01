# -*- coding: utf-8 -*-
import os, re, csv, argparse
from typing import Dict, Optional
from bs4 import BeautifulSoup
from scraper_utils import (
    log, make_session, fetch_with_fallback,
    append_row, write_heartbeat,
)

RP_ROOT = os.environ.get("RP_ROOT", os.getcwd())
CSV_PATH = os.path.join(RP_ROOT, "data", "crudo", "revancha_resultados.csv")
FIELDNAMES = ["sorteo","modo","fecha","n1","n2","n3","n4","n5","sb"]

def _ensure_header():
    if not os.path.exists(CSV_PATH) or os.path.getsize(CSV_PATH)==0:
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=FIELDNAMES); w.writeheader()

def parse_resultados(html: str, sorteo: int) -> Optional[Dict]:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)
    fecha = ""
    m = re.search(r"(\d{2}/\d{2}/\d{4})", text)
    if m: fecha = m.group(1)

    nums = []
    for sel in [".numbers li", ".resultados .numero", ".resultado .ball", ".balls .ball", ".numbers .ball"]:
        for node in soup.select(sel):
            t = re.sub(r"[^\d]", "", node.get_text(strip=True))
            if t.isdigit():
                nums.append(int(t))
        if len(nums) >= 6: break
    if len(nums) < 6:
        candidates = re.findall(r"\b(\d{1,2})\b", text)
        nums = [int(x) for x in candidates if x.isdigit()][:6]
    if len(nums) < 6:
        return None

    n1,n2,n3,n4,n5,sb = nums[:6]
    return {
        "sorteo": sorteo, "modo": "revancha", "fecha": fecha,
        "n1": n1, "n2": n2, "n3": n3, "n4": n4, "n5": n5, "sb": sb
    }

def scrape(desde: int, hasta: int, cache_dir: Optional[str], tries: int, no_network: bool):
    _ensure_header()
    ses = make_session()
    saved = 0
    for sorteo in range(desde, hasta + 1):
        log(f"⏳ Sorteo {sorteo} -> https://www.baloto.com/resultados-revancha/{sorteo}")
        try:
            if no_network: raise RuntimeError("offline")
            html, used = fetch_with_fallback(
                path_or_url=f"/resultados-revancha/{sorteo}",
                session=ses,
                tries_per_host=tries,
                cache_dir=cache_dir,
            )
        except Exception as ex:
            log("No se pudo obtener la página del sorteo {}; sigo.".format(sorteo))
            write_heartbeat(CSV_PATH, "resultados", sorteo, "failed", "fetch_failed", str(ex), modo="revancha")
            continue

        row = parse_resultados(html, sorteo)
        if not row:
            write_heartbeat(CSV_PATH, "resultados", sorteo, "failed", "parse_failed", used, modo="revancha")
            continue

        append_row(CSV_PATH, FIELDNAMES, row); saved += 1

    if saved:
        log(f"OK: Guardé {saved} resultados en {os.path.basename(CSV_PATH)}")
    else:
        log("Sin resultados completos (solo heartbeats).")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--desde", type=int, default=2540)
    parser.add_argument("--hasta", type=int, default=2547)
    parser.add_argument("--cache-dir", type=str, default=os.path.join(RP_ROOT, "logs", "cache_revancha"))
    parser.add_argument("--tries-per-host", type=int, default=2)
    parser.add_argument("--no-network", action="store_true")
    args = parser.parse_args()

    log("=== Inicio de scrapeo de resultados Revancha ===")
    scrape(args.desde, args.hasta, args.cache_dir, args.tries_per_host, args.no_network)
    print("✅ Scrapeo completado")

if __name__ == "__main__":
    main()
