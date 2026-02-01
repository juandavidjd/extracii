# scraper_fitment_japan.py
# -*- coding: utf-8 -*-

import os
import re
import csv
import json
import time
import random
import logging
from json.decoder import JSONDecodeError
from typing import List, Tuple, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup

# ----------------------------
# CONFIGURACIÓN GENERAL
# ----------------------------
INPUT_DB = 'Base_Datos_Competencia_Maestra_ULTRA_LIMPIA.csv'
OUTPUT_DB = 'Base_Datos_Fitment_JAPAN.csv'
ERROR_LOG = 'fitment_errors.log'
CHECKPOINT_FILE = 'fitment_checkpoint.txt'

MAX_URLS_TO_PROCESS = 200        # URLs por tanda
BATCH_SAVE_INTERVAL = 50         # Guardar cada N URLs
MAX_RETRIES = 4                  # Reintentos por URL
TIMEOUT = 20                     # Timeout por request

MIN_DELAY = 4.0
MAX_DELAY = 9.0

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 '
    '(KHTML, like Gecko) Version/16.6 Safari/605.1.15',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:117.0) Gecko/20100101 Firefox/117.0',
]

BASE_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'es-CO,es;q=0.9,en;q=0.8',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
}

# ----------------------------
# LOGGING
# ----------------------------
logging.basicConfig(
    filename=ERROR_LOG,
    filemode='a',
    format='%(asctime)s | %(levelname)s | %(message)s',
    level=logging.INFO
)

def log_error(sku_id: str, url: str, msg: str) -> None:
    logging.error(f'SKU: {sku_id} | URL: {url} | {msg}')

# ----------------------------
# UTILIDADES
# ----------------------------
def human_delay() -> None:
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

def rotate_headers() -> dict:
    headers = dict(BASE_HEADERS)
    headers['User-Agent'] = random.choice(USER_AGENTS)
    return headers

def read_csv_flexible(path: str) -> pd.DataFrame:
    for delimiter in [',', ';', '\t', '|']:
        try:
            df = pd.read_csv(path, delimiter=delimiter, encoding='utf-8-sig', dtype=str)
            df.columns = df.columns.str.strip()
            return df
        except Exception:
            continue
    raise RuntimeError(f"No se pudo leer el CSV '{path}' con delimitadores comunes.")

def extract_sku_from_name(name: str) -> Optional[str]:
    match = re.search(r'(\d{5,})', str(name))
    return match.group(1) if match else None

def is_listing_url(url: str) -> bool:
    return bool(re.search(r'/productos\?p=', str(url), flags=re.IGNORECASE))

def load_checkpoint() -> int:
    if not os.path.exists(CHECKPOINT_FILE):
        return 0
    try:
        with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
            value = f.read().strip()
            return int(value) if value.isdigit() else 0
    except Exception:
        return 0

def save_checkpoint(idx: int) -> None:
    with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
        f.write(str(idx))

# ----------------------------
# EXTRACCIÓN DE FITMENT
# ----------------------------
def parse_custom_product_attributes_from_html(html: str) -> Optional[List[dict]]:
    match = re.search(r'var\s+customProductAttributes\s*=\s*(

\[[\s\S]*?\]

);', html, re.IGNORECASE)
    if not match:
        return None

    raw_block = match.group(1).strip()
    sanitized = raw_block.replace("\r", "").replace("\n", "")
    sanitized = re.sub(r"'", '"', sanitized)
    sanitized = re.sub(r'""', 'null', sanitized)
    sanitized = re.sub(r',\s*]', ']', sanitized)
    sanitized = re.sub(r',\s*}', '}', sanitized)

    try:
        data = json.loads(sanitized)
        if isinstance(data, list):
            return data
        return None
    except JSONDecodeError:
        return None

def request_with_retries(url: str) -> Tuple[Optional[str], Optional[str]]:
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            human_delay()
            headers = rotate_headers()
            resp = requests.get(url, headers=headers, timeout=TIMEOUT)
            if resp.status_code >= 400:
                raise requests.exceptions.HTTPError(f'Status {resp.status_code}')
            return resp.text, None
        except requests.exceptions.RequestException as e:
            wait = (2 ** attempt) + random.uniform(0.0, 1.0)
            time.sleep(wait)
            last_error = f"Intento {attempt}/{MAX_RETRIES} fallo: {e}"
    return None, last_error

def extract_fitment_from_url(url: str) -> Tuple[Optional[List[dict]], Optional[str]]:
    html, err = request_with_retries(url)
    if err:
        return None, f'Error de conexión: {err}'
    fitments = parse_custom_product_attributes_from_html(html)
    if fitments:
        return fitments, None
    return None, 'No se encontró JSON de fitment'

# ----------------------------
# GUARDADO INCREMENTAL
# ----------------------------
FINAL_COLUMNS = [
    'SKU_ID', 'Nombre_Competencia', 'Marca', 'Modelo', 'Cilindraje',
    'Rango_Anios', 'Posicion', 'Lado', 'URL_Origen'
]

def ensure_output_exists():
    if not os.path.exists(OUTPUT_DB):
        with open(OUTPUT_DB, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(FINAL_COLUMNS)

def append_rows(rows: List[dict]) -> None:
    with open(OUTPUT_DB, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        for r in rows:
            writer.writerow([
                r.get('SKU_ID', ''),
                r.get('Nombre_Competencia', ''),
                r.get('Marca', ''),
                r.get('Modelo', ''),
                r.get('Cilindraje', ''),
                r.get('Rango_Anios', ''),
                r.get('Posicion', ''),
                r.get('Lado', ''),
                r.get('URL_Origen', ''),
            ])

# ----------------------------
# PROCESO PRINCIPAL
# ----------------------------
def process_fitment_scrape():
    if not os.path.exists(INPUT_DB):
        print(f"❌ ERROR: No existe el archivo de entrada '{INPUT_DB}'.")
        return

    print(f"1. Cargando URLs desde '{INPUT_DB}'...")
    try:
        df_urls = read_csv_flexible(INPUT_DB)
    except Exception as e:
        print(f"❌ ERROR FATAL: No se pudo abrir el archivo: {e}")
        return

    required_cols = {'URL_Origen', 'Nombre_Externo'}
    if not required_cols.issubset(set(df_urls.columns)):
        print("❌ ERROR: Faltan columnas requeridas: 'URL_Origen' y 'Nombre_Externo'.")
        return

    initial_count = len(df_urls)
    df_urls = df_urls.dropna(subset=['URL_Origen'])
    df_urls = df_urls[~df_urls['URL_Origen'].astype(str).apply(is_listing_url)]
    print(f"   -> URLs de detalle detectadas: {len(df_urls)} (filtradas {initial_count - len(df_urls)})")

    df_urls['SKU_ID'] = df_urls['Nombre_Externo'].apply(extract_sku_from_name)
    df_urls = df_urls.dropna(subset=['SKU_ID'])
    unique_urls = df_urls[['URL_Origen', 'SKU_ID', 'Nombre_Externo']].drop_duplicates()
    total_urls = len(unique_urls)
    if total_urls == 0:
        print("❌ ERROR: No hay URLs válidas con SKU_ID para procesar.")
        return

    start_idx = load_checkpoint()
    print(f"2. Iniciando scraping (máximo {MAX_URLS_TO_PROCESS} URLs) desde índice {start_idx}...")
    ensure_output_exists()

    processed = 0
    saved_since_last = 0
    batch_rows: List[dict] = []

    for i, row in unique_urls.iloc[start_idx:start_idx + MAX_URLS_TO_PROCESS].iter