# -*- coding: utf-8 -*-
import os, re, csv, argparse, datetime
from typing import List, Dict, Tuple, Optional
from bs4 import BeautifulSoup
from scraper_utils import (
    log, make_session, fetch_with_fallback,
    append_row, write_heartbeat,
)

RP_ROOT = os.environ.get("RP_ROOT", os.getcwd())
CSV_PATH = os.path.join(RP_ROOT, "data", "crudo", "baloto_premios.csv")
FIELDNAMES = ["sorteo","modo","fecha","aciertos","premio_total","ganadores","premio_por_ganador"]

def _ensure_header():
    if not os.path.exists(CSV_PATH) or os.path.getsize(CSV_PATH)==0:
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=FIELDNAMES)
            w.writeheader()

def _clean_money(txt: str) -> int:
    if not txt: return 0
    txt = txt.replace(".", "").replace(",", "").replace("$", "").replace(" ", "")
    m = re.search(r"(\d+)", txt)
    return int(m.group(1)) if m else 0

def _clean_int(txt: str) -> int:
    if txt is None: return 0
    t = re.sub(r"[^\d]", "", str(txt))
    return int(t) if t else 0

def mapear_premio_row_a_csv(row_parser: dict, modo: str) -> dict:
    return {
        "sorteo": int(row_parser.get("sorteo")),
        "modo":   modo,
        "fecha":  row_parser.get("fecha") or "",
        "aciertos": str(row_parser.get("aciertos") or ""),
        "premio_total": int(row_parser.get("premio_total") or 0),
        "ganadores": int(row_parser.get("ganadores") or 0),
        "premio_por_ganador": int(row_parser.get("premio_por_ganador") or 0),
    }

def parse_premios(html: str, sorteo: int) -> Tuple[str, List[Dict]]:
    """
    Intenta extraer:
      fecha (dd/mm/YYYY)
      y filas de premios: aciertos, ganadores, premio_total, premio_por_ganador
    """
    soup = BeautifulSoup(html, "lxml")
    # Fecha: busca algo tipo "dd/MM/yyyy", o en un nodo con 'fecha' o 'draw'
    fecha = ""
    # 1) dd/mm/yyyy en todo el doc
    m = re.search(r"(\d{2}/\d{2}/\d{4})", soup.get_text(" ", strip=True))
    if m: fecha = m.group(1)
    # 2) alterno por meta/atributos
    if not fecha:
        for sel in ["time", ".date", ".fecha", "[data-date]"]:
            node = soup.select_one(sel)
            if node:
                t = node.get("datetime") or node.get("data-date") or node.get_text(" ", strip=True)
                m = re.search(r"(\d{2}/\d{2}/\d{4})", t)
                if m: 
                    fecha = m.group(1)
                    break

    # Tabla de premios: intenta selectores comunes
    tablas = soup.select("table") or []
    rows_out: List[Dict] = []

    def try_extract_from_table(tb):
        headers = [th.get_text(" ", strip=True).lower() for th in tb.select("thead th")]
        # fallback thead vacío -> usar primera fila como header
        if not headers:
            first = tb.select_one("tr")
            if first:
                headers = [x.get_text(" ", strip=True).lower() for x in first.select("th,td")]
        # nombres típicos
        # columnas esperadas: aciertos | ganadores | premio total | premio por ganador
        body_rows = tb.select("tbody tr") or tb.select("tr")[1:]
        for tr in body_rows:
            cols = [td.get_text(" ", strip=True) for td in tr.select("td")]
            if not cols: 
                tds = tr.select("th,td")
                cols = [td.get_text(" ", strip=True) for td in tds]
            line = " | ".join(cols).lower()
            # heurística: debe tener algo como "5+sb" o "4+sb" o "5" / "0 aciertos" no aplica
            if not re.search(r"\b(\d\+\s*sb|\d\+sb|\d{1})\b", line):
                # permitir cadenas como "5 + super balota"
                if "super" not in line:
                    continue
            aciertos = None
            # deduce aciertos
            m_acc = re.search(r"(5\s*\+\s*sb|4\s*\+\s*sb|3\s*\+\s*sb|2\s*\+\s*sb|1\s*\+\s*sb|5|4|3|2|1|0)", line, re.I)
            if m_acc:
                aciertos = m_acc.group(1).upper().replace(" ", "")
                aciertos = aciertos.replace("+SB", "+SB").replace("+S B", "+SB").replace("S B", "SB")
                aciertos = aciertos.replace("SUPERBALOTA", "SB").replace("SUPER", "SB")
                aciertos = aciertos.replace("+SB", "+SB")
                aciertos = aciertos.replace("SB", "+SB") if "+" not in aciertos and "SB" in aciertos else aciertos
                aciertos = aciertos.replace("++", "+")
            # localizar ganadores y premios
            ganadores = 0
            premio_total = 0
            premio_por_ganador = 0
            # intenta por patrones de dinero
            mvals = re.findall(r"(\$\s?[\d\.\,]+)", " ".join(cols))
            if mvals:
                # suele haber total y por ganador; si hay 2, el mayor será total
                vals = [_clean_money(v) for v in mvals]
                vals.sort()
                if len(vals)==1:
                    premio_total = vals[0]
                else:
                    premio_total = vals[-1]
                    premio_por_ganador = vals[-2]
            # ganadores: número suelto no-monetario
            # busca en columnas palabras clave:
            for idx, h in enumerate(headers):
                if "ganador" in h and idx < len(cols):
                    ganadores = _clean_int(cols[idx])
            if not ganadores:
                # fallback: primer entero pequeño en línea
                mgan = re.search(r"\b(\d{1,4})\b", re.sub(r"[\$\,\.\s]", "", " ".join(cols)))
                if mgan:
                    try:
                        val = int(mgan.group(1))
                        if val < 10000:
                            ganadores = val
                    except:
                        pass
            if aciertos:
                rows_out.append({
                    "sorteo": sorteo,
                    "fecha": fecha,
                    "aciertos": aciertos,
                    "ganadores": ganadores,
                    "premio_total": premio_total,
                    "premio_por_ganador": premio_por_ganador,
                })

    for tb in tablas:
        try_extract_from_table(tb)

    return fecha, rows_out

def scrape_premios_baloto(desde: int, hasta: int, cache_dir: Optional[str], tries_per_host: int, no_network: bool):
    _ensure_header()
    ses = make_session()
    total_rows = 0
    for sorteo in range(desde, hasta + 1):
        log(f"⏳ Sorteo {sorteo} -> https://www.baloto.com/resultados-baloto/{sorteo}")
        try:
            if no_network:
                raise RuntimeError("offline")
            html, used = fetch_with_fallback(
                path_or_url=f"/resultados-baloto/{sorteo}",
                session=ses,
                tries_per_host=tries_per_host,
                cache_dir=cache_dir,
            )
        except Exception as ex:
            log("No se pudo obtener la página del sorteo {} (posible 500/corte); sigo.".format(sorteo))
            write_heartbeat(CSV_PATH, "premios", sorteo, "failed", "fetch_failed", str(ex), modo="baloto")
            continue

        fecha, rows = parse_premios(html, sorteo)
        if not rows:
            log(f"No encontré tabla de premios en {used}")
            write_heartbeat(CSV_PATH, "premios", sorteo, "failed", "parse_failed", used, modo="baloto")
            continue

        # Normaliza y escribe
        for r in rows:
            fila = mapear_premio_row_a_csv(r, modo="baloto")
            append_row(CSV_PATH, FIELDNAMES, fila)
            total_rows += 1

    if total_rows == 0:
        log("Sin filas de premios 'completas' (solo heartbeats).")
    else:
        log(f"OK: guardé {total_rows} filas de premios Baloto.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--desde", type=int, default=2540)
    parser.add_argument("--hasta", type=int, default=2547)
    parser.add_argument("--cache-dir", type=str, default=os.path.join(RP_ROOT, "logs", "cache_baloto"))
    parser.add_argument("--tries-per-host", type=int, default=2)
    parser.add_argument("--no-network", action="store_true")
    args = parser.parse_args()

    log("=== Inicio de scrapeo de premios Baloto ===")
    scrape_premios_baloto(args.desde, args.hasta, args.cache_dir, args.tries_per_host, args.no_network)
    print("✅ Scrapeo completado")

if __name__ == "__main__":
    main()
