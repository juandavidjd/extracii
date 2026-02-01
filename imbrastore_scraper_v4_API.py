import requests
import csv
import os
import time

CATEGORIAS = {
    "HERRAMIENTA_ESPECIALIZADA": "herramienta-especializada-1",
    "ELECTRICOS": "electricos-para-motocicletas",
    "CAUCHOS_PARA_MOTO": "cauchos-para-moto",
    "DISCOS_DE_FRENO": "discos-de-freno",
    "PASTILLAS_DE_FRENO": "pastillas-de-freno",
    "BANDAS_DE_FRENO": "bandas-de-freno",
    "DIRECCIONALES": "direccionales",
    "KIT_TIJERA": "kit-tijera",
    "SOSTENEDORES": "sostenedores",
    "HONDA_XRE_300": "honda-xre-300",
    "LINEA_CAN_AM": "linea-can-am"
}

BASE_PATH = r"C:\auteco\imbra_store"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def descargar_json(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json()
        return None
    except:
        return None

def scrape_categoria(nombre, slug):
    print(f"\n🔎 Categoría: {nombre}")
    url = f"https://imbrastore.com/collections/{slug}/products.json?limit=250"

    data = descargar_json(url)
    if not data or "products" not in data:
        print("❌ No se pudieron obtener productos.")
        return

    productos = data["products"]
    print(f"   → Productos detectados: {len(productos)}")

    # Crear carpeta
    folder = os.path.join(BASE_PATH, nombre)
    os.makedirs(folder, exist_ok=True)
    csv_path = os.path.join(folder, f"{nombre}.csv")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["titulo", "sku", "precio", "imagen", "url"])

        for p in productos:
            titulo = p.get("title")
            imagen = p["images"][0]["src"] if p.get("images") else ""
            handle = p.get("handle")
            url_producto = f"https://imbrastore.com/products/{handle}"

            variante = p["variants"][0]
            precio = variante.get("price")
            sku = variante.get("sku") or ""

            w.writerow([titulo, sku, precio, imagen, url_producto])

    print(f"   ✔ Guardado: {csv_path}")

def main():
    print("🚀 Iniciando scraper API Imbra Store…")

    for nombre, slug in CATEGORIAS.items():
        scrape_categoria(nombre, slug)
        time.sleep(1)

    print("\n🎉 PROCESO COMPLETO")
    print(f"📂 Carpeta base: {BASE_PATH}")

if __name__ == "__main__":
    main()
