import os
import csv
import re
import requests
from bs4 import BeautifulSoup

BASE_DIR = r"C:\auteco\IMBRA_v27"
HTML_DIR = os.path.join(BASE_DIR, "00_html_raw")
CSV_OUT = os.path.join(BASE_DIR, "02_csv")
IMG_OUT = os.path.join(BASE_DIR, "01_imagenes")

os.makedirs(HTML_DIR, exist_ok=True)
os.makedirs(CSV_OUT, exist_ok=True)
os.makedirs(IMG_OUT, exist_ok=True)

CSV_FULL = os.path.join(CSV_OUT, "IMBRA_FULL.csv")
CSV_IMAGES = os.path.join(CSV_OUT, "IMBRA_IMAGES.csv")

def clean_text(t):
    if not t:
        return ""
    return re.sub(r"\s+", " ", t).strip()

def extract_images(soup):
    imgs = []
    for tag in soup.find_all("img"):
        src = tag.get("src") or ""
        if "cdn.shopify.com" in src or "imbrastore.com/cdn" in src:
            if src.startswith("//"):
                src = "https:" + src
            imgs.append(src)
    return list(set(imgs))

def parse_html_file(filepath):
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")

    title = clean_text(soup.find("h1").text if soup.find("h1") else "")
    description = clean_text(soup.find("div", {"id": "tab_description"}) .text if soup.find("div", {"id": "tab_description"}) else "")

    sku_match = re.search(r'"sku":"([^"]+)"', html)
    sku = sku_match.group(1) if sku_match else ""

    price_match = re.search(r'"price":{"amount":([\d\.]+),', html)
    price = price_match.group(1) if price_match else ""

    vendor_match = re.search(r'"vendor":"([^"]+)"', html)
    vendor = vendor_match.group(1) if vendor_match else "IMBRA"

    handle_match = re.search(r'product_handle":"([^"]+)"', html)
    handle = handle_match.group(1) if handle_match else ""

    category = ""
    breadcrumb = soup.find("ul", {"class": "breadcrumb"})
    if breadcrumb:
        parts = breadcrumb.find_all("li")
        if len(parts) >= 2:
            category = clean_text(parts[-2].text)

    images = extract_images(soup)

    return {
        "titulo": title,
        "sku": sku,
        "precio": price,
        "categoria": category,
        "vendor": vendor,
        "handle": handle,
        "descripcion": description,
        "imagenes": images
    }

def build_master_catalog():
    rows = []
    image_rows = []

    print("\n🚀 Procesando archivos HTML de IMBRA...\n")

    for file in os.listdir(HTML_DIR):
        if not file.endswith(".html"):
            continue

        path = os.path.join(HTML_DIR, file)
        print(f"📄 Leyendo: {file}")

        data = parse_html_file(path)
        rows.append(data)

        for img in data["imagenes"]:
            image_rows.append({
                "sku": data["sku"],
                "handle": data["handle"],
                "imagen": img
            })

    print("\n💾 Guardando CSV maestro...")
    with open(CSV_FULL, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "titulo", "sku", "precio", "categoria", "vendor", "handle", "descripcion"
        ])
        writer.writeheader()
        writer.writerows(rows)

    print("💾 Guardando CSV imágenes...")
    with open(CSV_IMAGES, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["sku", "handle", "imagen"])
        writer.writeheader()
        writer.writerows(image_rows)

    print("\n🎉 PROCESO COMPLETADO")
    print(f"📄 Catálogo: {CSV_FULL}")
    print(f"🖼️ Imágenes: {CSV_IMAGES}")

if __name__ == "__main__":
    build_master_catalog()
