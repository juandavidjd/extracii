import os
import csv
import time
import hashlib
import requests
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE = "https://www.todomecanica.com"
ROOT = r"C:\auteco\todomecanica"
CSV_PATH = os.path.join(ROOT, "manuales_todomecanica.csv")
PDF_DIR = os.path.join(ROOT, "pdfs")

os.makedirs(ROOT, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122 Safari/537.36",
    "Accept": "*/*"
})

CATEGORIAS = [
    "/categorias-manuales/taller/moto/honda.html",
    "/categorias-manuales/taller/moto/yamaha.html",
    "/categorias-manuales/taller/moto/suzuki.html",
    "/categorias-manuales/taller/moto/ktm.html",
    "/categorias-manuales/taller/moto/bmw.html",
    "/categorias-manuales/taller/moto/kawasaki.html",
]


def iniciar_driver():
    options = uc.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--start-maximized")

    driver = uc.Chrome(options=options)
    return driver


def cargar_html(driver, url):
    driver.get(url)
    time.sleep(4)
    return driver.page_source


def extraer_listado(driver, url_categoria):
    url = BASE + url_categoria
    print(f"\n🔎 Revisando categoría: {url}")

    html = cargar_html(driver, url)
    soup = BeautifulSoup(html, "html.parser")

    items = []

    for link in soup.select("a.catItemTitle"):
        titulo = link.get_text(strip=True)
        url_detalle = urljoin(BASE, link["href"])
        items.append((titulo, url_detalle))

    print(f"   → {len(items)} manuales detectados.")
    return items


def extraer_detalle(driver, titulo, url_detalle):
    html = cargar_html(driver, url_detalle)
    soup = BeautifulSoup(html, "html.parser")

    link = soup.select_one("a[href*='download']")
    if not link:
        return None

    url_descarga = urljoin(BASE, link["href"])

    size = "N/D"
    for txt in soup.stripped_strings:
        if "MB" in txt or "KB" in txt:
            size = txt
            break

    return {
        "titulo": titulo,
        "url_detalle": url_detalle,
        "url_descarga": url_descarga,
        "tamaño": size,
    }


def descargar_pdf(url, destino):
    try:
        r = session.get(url, stream=True)
        if r.status_code != 200:
            print(f"❌ Error HTTP {r.status_code}: {url}")
            return False

        with open(destino, "wb") as f:
            for chunk in r.iter_content(4096):
                f.write(chunk)

        return True

    except Exception as e:
        print(f"⚠ Error al descargar {url}: {e}")
        return False


def hash_md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(4096):
            h.update(chunk)
    return h.hexdigest()


def guardar_csv(datos):
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["titulo", "url_detalle", "url_descarga", "tamaño", "archivo", "md5"])

        for d in datos:
            w.writerow([d["titulo"], d["url_detalle"], d["url_descarga"], d["tamaño"], d["archivo"], d["md5"]])


if __name__ == "__main__":

    print("🚀 Iniciando navegador anti-bot (undetected-chromedriver)…")
    driver = iniciar_driver()

    listado = []

    for cat in CATEGORIAS:
        listado.extend(extraer_listado(driver, cat))

    print(f"\n📦 Total manuales detectados: {len(listado)}\n")

    detalles = []

    for titulo, url in listado:
        print(f"\n➡ Procesando: {titulo}")
        info = extraer_detalle(driver, titulo, url)
        if not info:
            print("⚠ No se pudo extraer este manual.")
            continue

        fname = titulo.replace(" ", "_") + ".pdf"
        destino = os.path.join(PDF_DIR, fname)

        print("   ⬇ Descargando archivo…")
        if descargar_pdf(info["url_descarga"], destino):
            info["archivo"] = destino
            info["md5"] = hash_md5(destino)
        else:
            info["archivo"] = "ERROR"
            info["md5"] = "ERROR"

        detalles.append(info)

    guardar_csv(detalles)

    print("\n🎉 PROCESO COMPLETO")
    print("📁 CSV generado:", CSV_PATH)
    print("📂 PDFs en:", PDF_DIR)

    driver.quit()
