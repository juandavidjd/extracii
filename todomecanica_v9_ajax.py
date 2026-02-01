import os
import csv
import time
import hashlib
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# =======================
# CONFIGURACIÓN
# =======================

ROOT = r"C:\auteco\todomecanica"
PDF_DIR = os.path.join(ROOT, "pdfs")
CSV_PATH = os.path.join(ROOT, "manuales_todomecanica.csv")

os.makedirs(ROOT, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})

URL = "https://www.todomecanica.com/component/jak2filter/?Itemid=173&issearch=1&swr=0&theme=manuales&isc=1&ordering=zdate&category_id=1&xf_1=2&xf_2=3&xf_3=19&xf_4=221"


# =======================
# FUNCIONES
# =======================

def iniciar_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver


def esperar_ajax(driver):
    """Espera a que el contenido AJAX termine de cargar."""
    time.sleep(2)
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.catItemView"))
    )


def extraer_listado(html):
    """Extrae los manuales del DOM renderizado completo."""
    soup = BeautifulSoup(html, "html.parser")
    items = []

    for item in soup.select("div.catItemView"):
        title_tag = item.select_one("a.catItemTitle")
        if not title_tag:
            continue

        titulo = title_tag.get_text(strip=True)
        url_detalle = urljoin("https://www.todomecanica.com", title_tag["href"])

        items.append((titulo, url_detalle))

    return items


def extraer_detalle(driver, url):
    """Abre el detalle y extrae el enlace de descarga."""
    driver.get(url)
    esperar_ajax(driver)

    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    link = soup.select_one("a[href*='download']")
    if not link:
        return None

    url_descarga = urljoin("https://www.todomecanica.com", link["href"])

    size = "N/D"
    for t in soup.stripped_strings:
        if "MB" in t.upper() or "KB" in t.upper():
            size = t
            break

    return url_descarga, size


def descargar_pdf(url, nombre):
    """Descarga el PDF usando requests."""
    path = os.path.join(PDF_DIR, nombre)

    r = session.get(url, stream=True)
    if r.status_code != 200:
        print("❌ Error HTTP", r.status_code)
        return None

    with open(path, "wb") as f:
        for chunk in r.iter_content(4096):
            f.write(chunk)

    return path


# =======================
# PROCESO PRINCIPAL
# =======================

def main():
    print("🚀 Iniciando scraper AJAX v9.0…")

    driver = iniciar_driver()
    driver.get(URL)

    esperar_ajax(driver)

    html = driver.page_source
    manuales = extraer_listado(html)

    print(f"📦 Manuales detectados en pantalla: {len(manuales)}")

    datos = []

    for titulo, url_detalle in manuales:
        print(f"\n➡ Procesando manual: {titulo}")
        detalle = extraer_detalle(driver, url_detalle)

        if not detalle:
            print("⚠ No se encontró enlace de descarga.")
            continue

        url_descarga, size = detalle
        filename = titulo.replace(" ", "_") + ".pdf"

        print("   ⬇ Descargando PDF…")
        archivo = descargar_pdf(url_descarga, filename)

        if not archivo:
            print("❌ Error descargando PDF")
            continue

        datos.append([titulo, url_detalle, url_descarga, size, archivo])

    # CSV
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["titulo", "url_detalle", "url_descarga", "tamaño", "archivo"])
        writer.writerows(datos)

    print("\n🎉 PROCESO COMPLETO")
    print("📁 CSV generado:", CSV_PATH)
    print("📂 PDFs guardados en:", PDF_DIR)

    driver.quit()


if __name__ == "__main__":
    main()
