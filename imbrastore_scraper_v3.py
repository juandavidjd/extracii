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
    "User-Agent": "Mozilla/5.0"
}


def clean(name):
    bad = '<>:"/\\|?*'
    for b in bad:
        name = name.replace(b, "_")
    return name.strip()


def extract_category(category_name, base_url):
    print(f"\n🔍 Categoría: {category_name}")
    full_url = base_url + "/?view=all"
    print(f"➡ URL: {full_url}")

    r = requests.get(full_url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")

    # ESTE SELECTOR SÍ EXISTE EN EL HTML QUE ENVIASTE
    products = soup.select("div.card-wrapper")
    print(f"   → Productos detectados: {len(products)}")

    data = []

    for p in products:
        # título
        title_el = p.select_one("h3.card__heading a")
        title = title_el.text.strip() if title_el else "Sin título"

        # url producto
        link = urljoin(base_url, title_el["href"]) if title_el else ""

        # precio
        price_el = p.select_one(".price-item")
        price = price_el.text.strip() if price_el else "Sin precio"

        # imagen
        img_el = p.select_one("img")
        img = img_el.get("src") if img_el else ""

        data.append({
            "categoria": category_name,
            "titulo": title,
            "precio": price,
            "url_producto": link,
            "url_imagen": img,
        })

    return data


def save_csv(category, items):
    cat_folder = os.path.join(BASE_OUTPUT, clean(category))
    os.makedirs(cat_folder, exist_ok=True)

    csv_path = os.path.join(cat_folder, f"{clean(category)}.csv")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["categoria", "titulo", "precio", "url_producto", "url_imagen"])
        for it in items:
            w.writerow([
                it["categoria"], it["titulo"], it["precio"], it["url_producto"], it["url_imagen"]
            ])

    print(f"   ✔ Guardado: {csv_path}")


def main():
    os.makedirs(BASE_OUTPUT, exist_ok=True)

    master = []

    for name, url in CATEGORIES.items():
        items = extract_category(name, url)
        save_csv(name, items)
        master.extend(items)

    # guarda maestro
    master_path = os.path.join(BASE_OUTPUT, "master_imbra_store.csv")
    with open(master_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["categoria", "titulo", "precio", "url_producto", "url_imagen"])
        for it in master:
            w.writerow([
                it["categoria"], it["titulo"], it["precio"],
                it["url_producto"], it["url_imagen"]
            ])

    print("\n🎉 PROCESO COMPLETO")
    print(f"📘 Archivo maestro: {master_path}")


if __name__ == "__main__":
    main()
