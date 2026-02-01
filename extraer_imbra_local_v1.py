import re
import json
import csv

INPUT_HTML = r"Productos – Imbra Repuestos.html"
OUTPUT_CSV = "imbra_catalogo_completo_v1.csv"
OUTPUT_IMGS = "imbra_urls_imagenes.csv"

# -------------------------
# 1. Cargar HTML completo
# -------------------------
with open(INPUT_HTML, "r", encoding="utf-8") as f:
    html = f.read()

# ------------------------------------------
# 2. Buscar los bloques JSON de productos
# ------------------------------------------
pattern = r'"productVariants":(\[.*?\])'
matches = re.findall(pattern, html, flags=re.DOTALL)

if not matches:
    print("❌ No se encontraron productVariants en el archivo HTML.")
    exit()

print(f"✅ Bloques JSON encontrados: {len(matches)}")

# ------------------------------------------
# 3. Convertir JSON a estructura Python
# ------------------------------------------
productos = []
imagenes = []

for block in matches:
    try:
        variants = json.loads(block)
    except Exception as e:
        print("Error JSON:", e)
        continue

    for variant in variants:
        p = variant.get("product", {})
        img = variant.get("image", {})

        productos.append({
            "product_id": p.get("id"),
            "variant_id": variant.get("id"),
            "titulo": p.get("title"),
            "titulo_original": p.get("untranslatedTitle"),
            "sku": variant.get("sku"),
            "precio": variant["price"]["amount"] if "price" in variant else None,
            "moneda": variant["price"]["currencyCode"] if "price" in variant else None,
            "imagen": img.get("src") if img else None,
            "url_producto": p.get("url"),
            "vendor": p.get("vendor"),
            "categoria": p.get("type")
        })

        if img and img.get("src"):
            imagenes.append({
                "sku": variant.get("sku"),
                "imagen_url": "https:" + img.get("src")
            })

# ------------------------------------------
# 4. Guardar CSV principal
# ------------------------------------------
with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow([
        "product_id","variant_id","sku","titulo","titulo_original","precio","moneda",
        "vendor","categoria","url_producto","imagen"
    ])
    for p in productos:
        w.writerow([
            p["product_id"], p["variant_id"], p["sku"],
            p["titulo"], p["titulo_original"],
            p["precio"], p["moneda"],
            p["vendor"], p["categoria"],
            "https://imbrastore.com" + p["url_producto"] if p["url_producto"] else "",
            "https:" + p["imagen"] if p["imagen"] else ""
        ])

# ------------------------------------------
# 5. Guardar CSV de URLs de imágenes
# ------------------------------------------
with open(OUTPUT_IMGS, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["sku", "imagen_url"])
    for img in imagenes:
        w.writerow([img["sku"], img["imagen_url"]])

print("\n🎉 PROCESO COMPLETADO")
print(f"📦 Productos extraídos: {len(productos)}")
print(f"🖼️ Imagenes encontradas: {len(imagenes)}")
print(f"📄 Archivo CSV: {OUTPUT_CSV}")
print(f"📄 Archivo IMG CSV: {OUTPUT_IMGS}")
