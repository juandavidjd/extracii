import os
import csv
import time
import undetected_chromedriver as uc

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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

def clean(s):
    bad = '<>:"/\\|?*'
    for b in bad:
        s = s.replace(b, "_")
    return s.strip()

def scroll_to_bottom(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            return
        last_height = new_height

def extract_products_selenium(category, url):
    print(f"\n🔎 Procesando categoría: {category}")
    print(f"➡ URL: {url}")

    options = uc.ChromeOptions()
    options.headless = False
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = uc.Chrome(options=options)
    driver.get(url)

    # Esperar que cargue el contenedor react
    time.sleep(6)

    # Scroll dinámico para permitir la carga de productos
    scroll_to_bottom(driver)
    time.sleep(2)

    html = driver.page_source
    driver.quit()

    soup = BeautifulSoup(html, "html.parser")

    # ESTE SELECTOR SÍ EXISTE EN HYDROGEN
    products = soup.select("a.card__content")

    print(f"   → Productos encontrados: {len(products)}")

    items = []

    for p in products:
        title_el = p.select_one("h3")
        title = title_el.text.strip() if title_el else "Sin título"

        price_el = p.select_one(".price-item")
        price = price_el.text.strip() if price_el else "Sin precio"

        link = "https://imbrastore.com" + p["href"]

        img_el = p.parent.select_one("img")
        img_url = img_el["src"] if img_el else None

        items.append({
            "categoria": category,
            "titulo": title,
            "precio": price,
            "url_producto": link,
            "url_imagen": img_url,
        })

    return items

def save_category(category, items):
    folder = os.path.join(BASE_OUTPUT, clean(category))
    os.makedirs(folder, exist_ok=True)
    csv_path = os.path.join(folder, f"{clean(category)}.csv")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["categoria", "titulo", "precio", "url_producto", "url_imagen"])
        for it in items:
            w.writerow([it["categoria"], it["titulo"], it["precio"], it["url_producto"], it["url_imagen"]])

    print(f"   ✔ Guardado: {csv_path}")

def main():
    all_items = []

    for category, url in CATEGORIES.items():
        items = extract_products_selenium(category, url)
        save_category(category, items)
        all_items.extend(items)

    master = os.path.join(BASE_OUTPUT, "master_imbra_store.csv")
    with open(master, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["categoria", "titulo", "precio", "url_producto", "url_imagen"])
        for it in all_items:
            w.writerow([it["categoria"], it["titulo"], it["precio"], it["url_producto"], it["url_imagen"]])

    print("\n🎉 PROCESO COMPLETO")
    print(f"📘 CSV maestro: {master}")

if __name__ == "__main__":
    main()
