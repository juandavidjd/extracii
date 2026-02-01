import os
import csv
import time
import requests
import urllib3
import undetected_chromedriver as uc

from bs4 import BeautifulSoup
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


def download_file(url, dest_path):
    try:
        r = requests.get(url, headers=HEADERS, verify=False, timeout=20)
        if r.status_code == 200:
            with open(dest_path, "wb") as f:
                f.write(r.content)
            return True
    except:
        pass
    return False


def scrape_imbra():

    print("🚀 Lanzando Chrome REAL con undetected-chromedriver…")

    options = uc.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--start-maximized")

    # OPCIÓN CLAVE: NO HEADLESS
    options.headless = False

    driver = uc.Chrome(options=options)
    driver.get(BASE_URL)

    print("⏳ Esperando carga real del DOM…")
    time.sleep(7)  # Elementor tarda en mostrar tarjetas

    html = driver.page_source
    driver.quit()

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(".elementor-post__card")

    print(f"📦 Catálogos detectados: {len(cards)}")

    if len(cards) == 0:
        print("\n❌ Aún aparece vacío.")
        print("👉 Motivo probable: Imbra carga contenido por AJAX después de scroll.")
        print("➡ Próximo paso: activar scroll automático y esperar eventos JS.\n")
        return

    rows = []

    for card in cards:
        title_el = card.select_one(".elementor-post__title")
        title = title_el.text.strip() if title_el else "Sin título"

        link_el = card.select_one("a")
        pdf_url = urljoin(BASE_URL, link_el["href"]) if link_el else None

        img_el = card.select_one("img")
        img_url = urljoin(BASE_URL, img_el["src"]) if img_el else None

        brand = "General"
        for b in ["Honda", "Yamaha", "Suzuki", "Kawasaki", "AKT", "TVS", "Benelli",
                  "Victory", "Kymco", "NKD", "BOXER", "Pulsar", "Zontes",
                  "Piaggio", "Starker"]:
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
        print("   ✔ Descargado" if ok else "   ❌ Error descargando")

        rows.append([title, brand, pdf_url, img_url, pdf_path])

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["titulo", "marca", "pdf_url", "img_url", "ruta_local"])
        w.writerows(rows)

    print("\n🎉 PROCESO COMPLETADO")
    print(f"📁 CSV: {CSV_PATH}")
    print(f"📂 PDFs: {PDF_DIR}")


if __name__ == "__main__":
    scrape_imbra()
