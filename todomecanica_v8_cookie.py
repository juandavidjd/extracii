import os
import csv
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# ================================
# CONFIGURACIÓN
# ================================

ROOT = r"C:\auteco\todomecanica"
PDF_DIR = os.path.join(ROOT, "pdfs")
CSV_PATH = os.path.join(ROOT, "manuales_todomecanica.csv")

os.makedirs(ROOT, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

# 🔥 Pega tu cookie EXACTA entre comillas
COOKIE = """
PON_AQUI_TU_COOKIE_REAL
""".strip()

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
    "Cookie": COOKIE,
}

BASE_URL = "https://www.todomecanica.com"
FILTRO_URL = "https://www.todomecanica.com/component/jak2filter/?Itemid=173&issearch=1&swr=0&theme=manuales&isc=1&ordering=zdate&category_id=1&xf_1=2&xf_2=3&xf_3=19&xf_4=221"

session = requests.Session()
session.headers.update(HEADERS)

# ================================
# FUNCIONES
# ================================

def obtener_pagina(url):
    """Carga página con tus cookies reales."""
    r = session.get(url)
    if r.status_code != 200:
        print("❌ Error HTTP:", r.status_code, url)
        return None
    return r.text


def extraer_manuales(html):
    """Extrae títulos, URLs de detalle desde el HTML de resultados."""
    soup = BeautifulSoup(html, "html.parser")

    items = []
    for box in soup.select("div.catItemView a.catItemTitle"):
        titulo = box.get_text(strip=True)
        url_detalle = urljoin(BASE_URL, box["href"])
        items.append((titulo, url_detalle))

    return items


def obtener_paginacion(html):
    """Encuentra enlaces a páginas adicionales (start=20, 40, 60…)."""
    soup = BeautifulSoup(html, "html.parser")

    pags = []
    for a in soup.select("a.pagenav"):
        link = urljoin(BASE_URL, a["href"])
        pags.append(link)

    return list(set(pags))


def extraer_detalle_manual(url):
    """Extrae enlace de descarga del manual."""
    html = obtener_pagina(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    link = soup.select_one("a[href*='download']")
    if not link:
        return None

    url_descarga = urljoin(BASE_URL, link["href"])

    size = "N/D"
    for t in soup.stripped_strings:
        if "MB" in t or "Kb" in t:
            size = t
            break

    return url_descarga, size


def descargar_pdf(url, nombre):
    path = os.path.join(PDF_DIR, nombre)
    r = session.get(url, stream=True)
    if r.status_code != 200:
        print("❌ Error descargando PDF:", url)
        return None

    with open(path, "wb") as f:
        for chunk in r.iter_content(4096):
            f.write(chunk)

    return path


# ================================
# PROCESO PRINCIPAL
# ================================

def main():
    print("🚀 Comenzando extracción TodoMecánica v8 (con cookies reales)")

    html = obtener_pagina(FILTRO_URL)
    if not html:
        print("❌ No se pudo obtener página inicial.")
        return

    # Paso 1 – obtener primeros manuales
    print("🔍 Extrayendo página 1…")
    items = extraer_manuales(html)

    # Paso 2 – obtener paginación
    paginas = obtener_paginacion(html)

    # Paso 3 – recorrer todas las páginas extra
    for pag in paginas:
        print("🔍 Extrayendo:", pag)
        pag_html = obtener_pagina(pag)
        if not pag_html:
            continue
        items.extend(extraer_manuales(pag_html))

    print(f"📦 Total manuales encontrados: {len(items)}")

    datos = []

    for titulo, url_detalle in items:
        print(f"\n➡ Procesando manual: {titulo}")

        info = extraer_detalle_manual(url_detalle)
        if not info:
            print("   ⚠ No se encontró enlace de descarga.")
            continue

        url_descarga, size = info
        fname = titulo.replace(" ", "_").replace("/", "-") + ".pdf"

        print("   ⬇ Descargando PDF…")
        archivo = descargar_pdf(url_descarga, fname)
        if not archivo:
            print("   ❌ Falló descarga")
            continue

        datos.append([titulo, url_detalle, url_descarga, size, archivo])

    # Guardar CSV
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["titulo", "url_detalle", "url_descarga", "tamaño", "archivo_local"])
        w.writerows(datos)

    print("\n🎉 PROCESO COMPLETO")
    print("📁 CSV generado:", CSV_PATH)
    print("📂 PDFs descargados en:", PDF_DIR)


if __name__ == "__main__":
    main()
