import os
import re
import time
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import pandas as pd

# 📁 Carpeta donde tienes los 7 HTML de tienda + sus carpetas *_files
HTML_DIR = r"C:\sqk\html_pages"
BASE_DOMAIN = "https://kaiqiparts.com"

# 🧠 User-Agent para que el servidor no se enfade
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0 Safari/537.36"
}

productos = []


def solo_nombre_archivo(src: str) -> str:
    """Devuelve solo el nombre de archivo a partir de un src (URL o ruta relativa)."""
    if not src:
        return ""
    path = urlparse(src).path  # funciona para URLs y rutas tipo ./carpeta/97-300x300.png
    return os.path.basename(path)


def obtener_sku_desde_web(url_producto: str) -> str:
    """Scrapea la página individual para extraer el SKU dentro de <span class="sku_wrapper"><span class="sku">."""
    try:
        resp = requests.get(url_producto, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"[WARN] No se pudo obtener SKU desde {url_producto}: {e}")
        return ""

    psoup = BeautifulSoup(resp.text, "html.parser")
    sku_tag = psoup.select_one("span.sku_wrapper span.sku")
    sku = sku_tag.get_text(strip=True) if sku_tag else ""
    if not sku:
        print(f"[WARN] No se encontró SKU en {url_producto}")
    else:
        print(f"[OK] SKU {sku} desde {url_producto}")
    return sku


def renombrar_imagenes_por_sku(img_src: str, sku: str) -> str:
    """
    Renombra físicamente las imágenes locales asociadas a un producto según el SKU.

    - Busca en la carpeta *_files las imágenes cuyo nombre comienza con el mismo prefijo
      que la miniatura (ej. 97-300x300.png → prefijo '97').
    - Las renombra a: SKU.png, SKU_1.png, SKU_2.png, ...
    - Devuelve el nombre del archivo principal (SKU.png o similar) para CSV.
    """
    if not img_src or not sku:
        return solo_nombre_archivo(img_src) if img_src else ""

    # Quitar ./ inicial si viene así: ./Tienda..._files/97-300x300.png
    src_rel = img_src.lstrip("./")
    img_path = os.path.join(HTML_DIR, src_rel)

    if not os.path.exists(img_path):
        print(f"[WARN] No encuentro imagen local para {img_src} → no se renombra.")
        return solo_nombre_archivo(img_src)

    folder = os.path.dirname(img_path)
    original_name = os.path.basename(img_path)

    # Prefijo base "97" a partir de "97-300x300.png" o "97.png"
    m = re.match(r"^([^. -]+)", original_name)  # hasta primer punto, espacio o guion
    base_prefix = m.group(1) if m else os.path.splitext(original_name)[0]

    # Todas las imágenes del producto (múltiples tamaños/variantes)
    candidates = [
        f for f in os.listdir(folder)
        if f.startswith(base_prefix) and f.lower().endswith((".png", ".jpg", ".jpeg"))
    ]

    if not candidates:
        print(f"[WARN] No encontré variantes de imagen para prefijo {base_prefix}")
        return solo_nombre_archivo(img_src)

    candidates.sort()
    nuevos_nombres = []

    for idx, old in enumerate(candidates):
        ext = os.path.splitext(old)[1].lower()
        # SKU.png para la primera, SKU_1.png, SKU_2.png... para el resto
        new_name = f"{sku}{'' if idx == 0 else f'_{idx}'}{ext}"

        old_path = os.path.join(folder, old)
        new_path = os.path.join(folder, new_name)

        if old_path == new_path:
            nuevos_nombres.append(new_name)
            continue

        # Evitar sobrescribir archivos existentes
        if os.path.exists(new_path):
            extra = 1
            tmp_name = f"{sku}{'' if idx == 0 else f'_{idx}'}_{extra}{ext}"
            tmp_path = os.path.join(folder, tmp_name)
            while os.path.exists(tmp_path):
                extra += 1
                tmp_name = f"{sku}{'' if idx == 0 else f'_{idx}'}_{extra}{ext}"
                tmp_path = os.path.join(folder, tmp_name)
            new_name = tmp_name
            new_path = tmp_path

        os.rename(old_path, new_path)
        nuevos_nombres.append(new_name)
        print(f"[IMG] {old} → {new_name}")

    return nuevos_nombres[0] if nuevos_nombres else solo_nombre_archivo(img_src)


# 🔍 Recorremos los 7 HTML de tienda
for file in os.listdir(HTML_DIR):
    if not file.lower().endswith(".html"):
        continue

    # Si quieres limitar a los 7 listados, puedes usar un if por nombre; de momento filtro por "Tienda"
    if "Tienda _ Kaiqi Parts" not in file:
        continue

    html_path = os.path.join(HTML_DIR, file)
    print(f"\n[INFO] Procesando listado: {file}")

    with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # Cada tarjeta de producto en el grid
    product_cards = soup.select("div.df-product-outer-wrap")
    print(f"[INFO] Productos encontrados en {file}: {len(product_cards)}")

    for card in product_cards:
        # 1) Nombre + URL
        title_tag = card.select_one("h2.df-product-title a")
        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        product_url = title_tag.get("href", "").strip()

        # 2) Imagen en la tienda
        img_tag = card.select_one("img")
        img_src = img_tag.get("src", "").strip() if img_tag else ""
        img_filename_original = solo_nombre_archivo(img_src) if img_src else ""

        # 3) Categoría
        cat_tag = card.select_one(".df-product-categories-wrap .df_term_item")
        category = cat_tag.get_text(strip=True) if cat_tag else ""

        # 4) SKU scrappeado de la página individual online
        sku = ""
        if product_url:
            # Normalizar URL relativa
            if product_url.startswith("/"):
                product_url = BASE_DOMAIN.rstrip("/") + product_url

            sku = obtener_sku_desde_web(product_url)
            time.sleep(1)  # pequeña pausa para no saturar el servidor

        # 5) Renombrar físicamente imágenes según SKU
        if img_src and sku:
            img_final = renombrar_imagenes_por_sku(img_src, sku)
        else:
            img_final = img_filename_original

        productos.append({
            "Title": title,
            "Image Src": img_final,
            "Category": category,
            "SKU": sku
        })

# 🧾 DataFrame principal: 1 fila por producto
df = pd.DataFrame(productos)

# Quitar duplicados por Title + SKU por si algún producto aparece en varias páginas
df.drop_duplicates(subset=["Title", "SKU"], inplace=True)

# 📘 Tabla de convenciones para añadir al final del CSV
convenciones = pd.DataFrame({
    "Convención": [
        "SKU como identificador único",
        "Imagen renombrada físicamente → SKU.png o SKU_1.png …",
        "Categorías extraídas desde <span class='df_term_item'>",
        "Sistema listo para Shopify y Cloudinary"
    ],
    "Descripción": [
        "El SKU define el vínculo entre producto, imagen e inventario.",
        "Todas las imágenes locales relacionadas con el producto se renombran usando el SKU.",
        "La categoría se toma literal del HTML de la tienda para mantener consistencia.",
        "Al usar el SKU en el nombre de archivo, las futuras URLs en Cloudinary quedan limpias y predecibles."
    ]
})

# 📤 Exportar CSV para Shopify + convenciones al final
output_csv = os.path.join(HTML_DIR, "productos_shopify_con_sku.csv")

with open(output_csv, "w", encoding="utf-8", newline="") as f:
    df.to_csv(f, index=False)
    f.write("\n\n# Convenciones\n")
    convenciones.to_csv(f, index=False)

print("\n✅ Proceso terminado.")
print("📄 CSV generado:", output_csv)
