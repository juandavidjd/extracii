import pandas as pd
import difflib
import re
import os
from bs4 import BeautifulSoup

BASE_DIR = r"C:/sqk/html_pages"
EXCEL_FILE = os.path.join(BASE_DIR, "LISTADO KAIQI NOV-DIC 2025.xlsx")
FALTANTES_FILE = os.path.join(BASE_DIR, "productos_faltantes.csv")
SHOPIFY_FILE = os.path.join(BASE_DIR, "kaiqi_shopify_import.csv")

# 7 carpetas con HTMLs
HTML_DIRS = [
    os.path.join(BASE_DIR, f"Tienda _ Kaiqi Parts - Partes y Accesorios para Motocargueros y Motos en Villavicencio{i}.html")
    for i in range(1, 8)
]

IMG_DIRS = [
    os.path.join(BASE_DIR, f"Tienda _ Kaiqi Parts - Partes y Accesorios para Motocargueros y Motos en Villavicencio{i}_files")
    for i in range(1, 8)
]

CLOUD_NAME = "dhegu1fzm"

def clean_filename(name):
    name = str(name).strip()
    name = name.replace(" ", "_").replace("/", "-").replace("*", "x")
    name = re.sub(r"[^A-Za-z0-9_-]", "", name)
    return f"{name}.png"

# --- Cargar Excel maestro desde fila 11 ---
excel_df = pd.read_excel(EXCEL_FILE, sheet_name="Hoja1", header=10)
excel_df.columns = excel_df.columns.str.strip().str.upper()
excel_df = excel_df.rename(columns={"CODIGO":"SKU","DESCRICION":"Title"})
excel_df["SKU"] = excel_df["SKU"].astype(str).str.strip()
excel_df["Title"] = excel_df["Title"].astype(str).str.strip()

# --- Cargar productos faltantes ---
faltantes_df = pd.read_csv(FALTANTES_FILE, sep=";")
faltantes_df["Title"] = faltantes_df["Title"].astype(str).str.strip()

# --- Parsear HTMLs para extraer productos ---
html_products = []
for html_file, img_dir in zip(HTML_DIRS, IMG_DIRS):
    if not os.path.exists(html_file):
        continue
    with open(html_file, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f, "html.parser")
        # cada producto en WooCommerce suele estar en <li class="product"> o similar
        for prod in soup.find_all(["li","div"], class_="product"):
            title = prod.get_text(strip=True)
            img_tag = prod.find("img")
            img_file = None
            if img_tag and "src" in img_tag.attrs:
                img_file = os.path.basename(img_tag["src"])
            category = None
            cat_tag = prod.find_parent("ul", class_="products")
            if cat_tag and "data-category" in cat_tag.attrs:
                category = cat_tag["data-category"]
            html_products.append({
                "Title_html": title,
                "Imagen_local": img_file,
                "Categoria": category
            })

html_df = pd.DataFrame(html_products)

# --- Merge con Excel ---
resolved_rows = []
for _, row in excel_df.iterrows():
    sku = row["SKU"]
    title = row["Title"]

    # Buscar imagen en HTML por coincidencia difusa
    match = difflib.get_close_matches(title, html_df["Title_html"], n=1, cutoff=0.6)
    if match:
        matched_title = match[0]
        img_local = html_df.loc[html_df["Title_html"] == matched_title, "Imagen_local"].values[0]
        categoria = html_df.loc[html_df["Title_html"] == matched_title, "Categoria"].values[0]
    else:
        # Buscar en faltantes.csv
        match = difflib.get_close_matches(title, faltantes_df["Title"], n=1, cutoff=0.6)
        if match:
            matched_title = match[0]
            img_local = faltantes_df.loc[faltantes_df["Title"] == matched_title, "Imagen_local"].values[0]
            categoria = None
        else:
            img_local = None
            categoria = None

    imagen_renombrada = clean_filename(title)
    imagen_url = f"https://res.cloudinary.com/{CLOUD_NAME}/image/upload/{imagen_renombrada}" if img_local else None

    resolved_rows.append({
        "SKU": sku,
        "Title": title,
        "Categoria": categoria,
        "Imagen_local": img_local,
        "Imagen_renombrada": imagen_renombrada,
        "Imagen_URL": imagen_url
    })

mapping_final = pd.DataFrame(resolved_rows)
mapping_final.to_csv(os.path.join(BASE_DIR, "mapping_final.csv"), sep=";", index=False)

# --- Actualizar Shopify ---
shopify_df = pd.read_csv(SHOPIFY_FILE, sep=";")
shopify_df = shopify_df.merge(mapping_final[["SKU","Imagen_URL","Title","Categoria"]], on="SKU", how="left")

shopify_df["Product image URL"] = shopify_df["Imagen_URL"].fillna(shopify_df.get("Product image URL"))
shopify_df["Title"] = shopify_df["Title_y"].fillna(shopify_df["Title_x"])
shopify_df["Description"] = shopify_df["Title"]
shopify_df["SEO title"] = shopify_df["Title"].apply(lambda t: str(t)[:70])
shopify_df["SEO description"] = shopify_df["Title"].apply(lambda t: str(t)[:160])

shopify_df = shopify_df.drop(columns=["Imagen_URL","Title_x","Title_y"], errors="ignore")
shopify_df.to_csv(SHOPIFY_FILE, sep=";", index=False)

print(f"✅ Mapping final generado -> mapping_final.csv")
print(f"🎯 Shopify CSV enriquecido -> {SHOPIFY_FILE}")
