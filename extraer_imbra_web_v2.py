import os
import csv
import requests
import time

# ============================
# RUTAS DE SALIDA
# ============================
OUT_DIR = r"C:\auteco\IMBRA_v27"
os.makedirs(OUT_DIR, exist_ok=True)

OUT_PRODUCTS = os.path.join(OUT_DIR, "IMBRA_FULL.csv")
OUT_IMAGES = os.path.join(OUT_DIR, "IMBRA_IMAGENES.csv")

# ============================
# API BASE
# ============================
BASE = "https://imbrastore.com/collections/all/products.json"


def fetch_page(page):
    """Descarga la página N del feed JSON de Shopify."""
    url = f"{BASE}?limit=250&page={page}"
    print(f"🔎 Descargando página {page}…")

    try:
        data = requests.get(url, timeout=10).json()
    except Exception as e:
        print("❌ Error:", e)
        return []

    products = data.get("products", [])
    return products


def main():
    print("🚀 INICIANDO SCRAPER WEB IMBRA v2 — Shopify API\n")

    all_products = []
    page = 1

    while True:
        products = fetch_page(page)

        if not products:
            print("\n✔ Fin de paginación.")
            break

        print(f"   → {len(products)} productos en esta página.\n")

        all_products.extend(products)
        page += 1

        time.sleep(0.5)

    print(f"📦 Total productos descargados: {len(all_products)}\n")

    # ============================
    # GUARDAR CSV PRINCIPAL
    # ============================
    with open(OUT_PRODUCTS, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "id", "title", "handle", "url", "product_type", "vendor",
            "tags", "sku", "price", "variant_id", "images"
        ])

        for p in all_products:
            url = f"https://imbrastore.com/products/{p['handle']}"
            imgs = [img["src"] for img in p["images"]]

            for v in p["variants"]:
                w.writerow([
                    p["id"],
                    p["title"],
                    p["handle"],
                    url,
                    p.get("product_type", ""),
                    p.get("vendor", ""),
                    p.get("tags", ""),
                    v.get("sku", ""),
                    v.get("price", ""),
                    v.get("id", ""),
                    "|".join(imgs)
                ])

    # ============================
    # GUARDAR CSV IMÁGENES
    # ============================
    with open(OUT_IMAGES, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["product_id", "sku", "image_url"])

        for p in all_products:
            for v in p["variants"]:
                sku = v.get("sku", "")
                for img in p["images"]:
                    w.writerow([
                        p["id"],
                        sku,
                        img["src"]
                    ])

    print("🎉 SCRAPER COMPLETO")
    print(f"📄 Productos: {OUT_PRODUCTS}")
    print(f"🖼️ Imagenes: {OUT_IMAGES}")


if __name__ == "__main__":
    main()
