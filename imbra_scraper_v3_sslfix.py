import os
import csv
import time
import requests
import urllib3
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# 🔧 Desactivar warnings de SSL para evitar spam en consola
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ----------------------------------------------------
# CONFIGURACIÓN
# ----------------------------------------------------
BASE_URL = "https://imbrarepuestos.com/catalogos/"
OUTPUT_DIR = r"C:\auteco\imbra"
PDF_DIR = os.path.join(OUTPUT_DIR, "pdfs")
CSV_PATH = os.path.join(OUTPUT_DIR, "imbra_catalogos.csv")

os.makedirs(PDF_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# ----------------------------------------------------
# DESCARGA DE ARCHIVOS
# ----------------------------------------------------
def download_file(url, dest_path, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20, verify=False)
            if r.status_code == 200:
                with open(dest_path, "wb") as f:
                    f.write(r.content)
                return True
        except:
            time.sleep(2)
    return False

# ----------------------------------------------------
# SANEAR NOMBRE
# ----------------------------------------------------
def clean_filename(name):
    bad = '<>:"/\\|?*'
    for c in bad:
        name = name.replace(c, "_")
    return name.strip()

# ----------------------------------------------------
# EXTRAER CATÁLOGOS
# ----------------------------------------------------
def scrape_imbra():
    print("🔍 Cargando página principal de Imbra…")

    # 🚀 FIX CRÍTICO: verify=False
    response = requests.get(BASE_URL, headers=HEADERS, verify=False)

    html = response.text
    soup = BeautifulSoup(html, "html.parser")

    items = soup.select(".elementor-post__card")
    print(f"📦 Catálogos detectados: {len(items)}")

    data_rows = []

    possible_brands = [
        "Honda", "Yamaha", "Suzuki", "Kawasaki", "AKT", "TVS", "Benelli",
        "Victory", "Kymco", "NKD", "BOXER", "Pulsar", "Zontes",
        "Piaggio", "Starker"
    ]

    for item in items:
        title_tag = item.select_one(".elementor-post__title")
        title = title_tag.text.strip() if title_tag else "Sin título"

        link_tag = item.select_one("a")
        pdf_url = urljoin(BASE_URL, link_tag["href"]) if link_tag else None

        img_tag = item.select_one("img")
        img_url = urljoin(BASE_URL, img_tag["src"]) if img_tag else None

        brand = "General"
        for b in possible_brands:
            if b.lower() in title.lower():
                brand = b
                break

        brand_dir = os.path.join(PDF_DIR, clean_filename(brand))
        os.makedirs(brand_dir, exist_ok=True)

        pdf_name = clean_filename(title) + ".pdf"
        pdf_path = os.path.join(brand_dir, pdf_name)

        print(f"\n📄 Catálogo: {title}")
        print(f"   ├─ Marca: {brand}")
        print(f"   ├─ PDF URL: {pdf_url}")
        print(f"   └─ Guardando en: {pdf_path}")

        if pdf_url:
            ok = download_file(pdf_url, pdf_path)
            if ok:
                print("   ✔ Descargado")
            else:
                print("   ❌ Error al descargar")

        data_rows.append([title, brand, pdf_url, img_url, pdf_path])

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["titulo", "marca", "pdf_url", "img_url", "ruta_local"])
        w.writerows(data_rows)

    print("\n🎉 PROCESO COMPLETADO")
    print(f"📁 CSV inventario: {CSV_PATH}")
    print(f"📂 PDFs descargados en: {PDF_DIR}")

# ----------------------------------------------------
# MAIN
# ----------------------------------------------------
if __name__ == "__main__":
    scrape_imbra()
