import os
import csv
import time
import requests
import urllib3

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from urllib.parse import urljoin

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://imbrarepuestos.com/catalogos/"
OUTPUT_DIR = r"C:\auteco\imbra"
PDF_DIR = os.path.join(OUTPUT_DIR, "pdfs")
CSV_PATH = os.path.join(OUTPUT_DIR, "imbra_catalogos.csv")

os.makedirs(PDF_DIR, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0"}

def clean_filename(name):
    bad = '<>:"/\\|?*'
    for c in bad:
        name = name.replace(c, "_")
    return name.strip()

def download_file(url, dest):
    try:
        r = requests.get(url, headers=HEADERS, verify=False, timeout=20)
        if r.status_code == 200:
            with open(dest, "wb") as f:
                f.write(r.content)
            return True
    except:
        pass
    return False


def scrape_imbra():
    print("🚀 Iniciando Selenium…")

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(options=chrome_options)
    driver.get(BASE_URL)

    print("⏳ Cargando página…")

    # Esperar a que carguen tarjetas de catálogo
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "elementor-post__card"))
        )
    except:
        print("❌ No se detectaron tarjetas. Verifica la conexión.")
        driver.quit()
        return

    time.sleep(3)

    cards = driver.find_elements(By.CLASS_NAME, "elementor-post__card")
    print(f"📦 Catálogos detectados: {len(cards)}")

    rows = []

    for card in cards:
        title = card.find_element(By.CLASS_NAME, "elementor-post__title").text.strip()

        link = card.find_element(By.TAG_NAME, "a").get_attribute("href")
        pdf_url = urljoin(BASE_URL, link)

        img = card.find_element(By.TAG_NAME, "img").get_attribute("src")

        # Detectar marca desde el título
        brands = ["Honda", "Yamaha", "Suzuki", "Kawasaki", "AKT", "TVS", "Benelli",
                  "Victory", "Kymco", "NKD", "BOXER", "Pulsar", "Zontes",
                  "Piaggio", "Starker"]

        brand = "General"
        for b in brands:
            if b.lower() in title.lower():
                brand = b
                break

        brand_dir = os.path.join(PDF_DIR, clean_filename(brand))
        os.makedirs(brand_dir, exist_ok=True)

        pdf_name = clean_filename(title) + ".pdf"
        pdf_path = os.path.join(brand_dir, pdf_name)

        print(f"\n📄 {title}")
        print(f"   ├─ Marca: {brand}")
        print(f"   ├─ PDF: {pdf_url}")
        print(f"   └─ Guardando: {pdf_path}")

        ok = download_file(pdf_url, pdf_path)
        print("   ✔ Descargado" if ok else "   ❌ Error en descarga")

        rows.append([title, brand, pdf_url, img, pdf_path])

    driver.quit()

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["titulo", "marca", "pdf_url", "img_url", "ruta_local"])
        w.writerows(rows)

    print("\n🎉 PROCESO COMPLETADO")
    print("📁 CSV:", CSV_PATH)
    print("📂 PDFs:", PDF_DIR)


if __name__ == "__main__":
    scrape_imbra()
