import os
import csv
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


BASE_OUTPUT = r"C:\auteco\imbra_store"

CATEGORIES = {
    "HERRAMIENTA ESPECIALIZADA": "https://imbrastore.com/collections/herramienta-especializada-1",
    "ELECTRICOS": "https://imbrastore.com/collections/electricos-para-motocicletas",
    "CAUCHOS PARA MOTO": "https://imbrastore.com/collections/cauchos-para-moto",
    "DISCOS DE FRENO": "https://imbrastore.com/collections/discos-de-freno",
    "PASTILLAS DE FRENO": "https://imbrastore.com/collections/pastillas-de-freno",
    "BANDAS DE FRENO": "https://imbrastore.com/collections/bandas-de-freno",
    "DIRECCIONALES": "https://imbrastore.com/collections/direccionales",
    "KIT DE TIJERA": "https://imbrastore.com/collections/kit-tijera",
    "SOSTENEDORES": "https://imbrastore.com/collections/sostenedores",
    "HONDA XRE 300": "https://imbrastore.com/collections/honda-xre-300",
    "LINEA CAN AM": "https://imbrastore.com/collections/linea-can-am",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}


def clean(name):
    bad = '<>:"/\\|?*'
    for b in bad:
        name = name.replace(b, "_")
    return name.strip()


def extract_products(category, url):
    print(f"\n🔎 Extrayendo categoría: {category}")
    print(f"➡ URL: {url}")

    products = []
    page_url = url

    while page_url:
        print(f"   📄 Página: {page_url}")

        r = requests.get(page_url, headers=HEADERS)
        soup = BeautifulSoup(r.text, "html.parser")

        items = soup.select("div.grid__item")
        print(f"   → Productos detectados en esta página: {len(items)}")

        for it in items:
            # Nombre
            title_el = it.select_one("a.full-unstyled-link")
            title = title_el.text.strip() if title_el else "Sin título"

            # URL del producto
            link = urljoin(url, title_el["href"]) if title_el else None

            # Imagen
            img_el = it.select_one("img")
            img_url = urljoin(url, img_el["src"]) if img_el else None

            # Precio
            price_el = it.select_one("span.price-item")
            price = price_el.text.strip() if price_el else "No disponible"

            products.append({
                "categoria": category,
                "titulo": title,
                "precio": price,
                "url_producto": link,
                "url_imagen": img_url
            })

        # PAGINACIÓN
        next_btn = soup.select_one("a.pagination__item--next")
        if next_btn:
            page_url = urljoin(url, next_btn["href"])
            time.sleep(1)
        else:
            page_url = None

    return products


def save_category_csv(category, items):
    folder = os.path.join(BASE_OUTPUT, clean(category))
    os.makedirs(folder, exist_ok=True)

    csv_path = os.path.join(folder, f"{clean(category)}.csv")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["categoria", "titulo", "precio", "url_producto", "url_imagen"])

        for p in items:
            w.writerow([
                p["categoria"],
                p["titulo"],
                p["precio"],
                p["url_producto"],
                p["url_imagen"],
            ])

    print(f"   ✔ CSV guardado: {csv_path}")


def save_master_csv(all_items):
    csv_path = os.path.join(BASE_OUTPUT, "master_imbra_store.csv")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["categoria", "titulo", "precio", "url_producto", "url_imagen"])

        for p in all_items:
            w.writerow([
                p["categoria"],
                p["titulo"],
                p["precio"],
                p["url_producto"],
                p["url_imagen"],
            ])

    print(f"\n📘 CSV MAESTRO generado en: {csv_path}")


def main():
    os.makedirs(BASE_OUTPUT, exist_ok=True)

    all_items = []

    for category, url in CATEGORIES.items():
        items = extract_products(category, url)
        save_category_csv(category, items)
        all_items.extend(items)

    save_master_csv(all_items)
    print("\n🎉 PROCESO COMPLETADO")


if __name__ == "__main__":
    main()
