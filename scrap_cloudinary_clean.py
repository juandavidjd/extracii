import os
import pandas as pd
from bs4 import BeautifulSoup
import glob
import re

BASE_DIR = r"C:/sqk/html_pages"
CATALOGO = os.path.join(BASE_DIR, "kaiqi_catalogo.csv")
SHOPIFY_CSV = os.path.join(BASE_DIR, "kaiqi_shopify_import.csv")
OUT_MAPPING = os.path.join(BASE_DIR, "imagenes_mapping.csv")

CLOUD_NAME = "mi_cuenta"  # ⚡ cambia esto por tu nombre de cuenta en Cloudinary

# --- Funciones auxiliares ---
def clean_sku(s):
    """Normaliza el SKU para que sea un nombre de archivo válido"""
    s = str(s).strip()
    s = s.replace(" ", "").replace(",", "").replace("/", "-")
    # eliminar notación científica tipo 7,70102E+12
    s = re.sub(r"[^A-Za-z0-9_-]", "", s)
    return s if s else "SKU_desconocido"

def normalize_title(t):
    return str(t).strip() if pd.notna(t) else ""

# --- Cargar catálogo ---
df = pd.read_csv(CATALOGO, sep=";", encoding="latin-1")
df.columns = df.columns.str.strip().str.replace(" ", "_")
df = df.rename(columns={"CODIGO":"SKU","DESCRICION":"Title"})
df = df[df["SKU"].notna()]
df["SKU"] = df["SKU"].apply(clean_sku)
df["Title"] = df["Title"].apply(normalize_title)

mappings = {}
# --- Recorrer HTMLs y asociar imágenes ---
for html_file in glob.glob(os.path.join(BASE_DIR, "*.html")):
    with open(html_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
    items = soup.select("li.product")
    for item in items:
        title = normalize_title(item.select_one("h2.woocommerce-loop-product__title").get_text(strip=True))
        img = item.select_one("img")["src"] if item.select_one("img") else ""
        img_name = os.path.basename(img)
        # Buscar SKU en catálogo por coincidencia parcial
        match = df[df["Title"].str.contains(title[:10], case=False, na=False)]
        if not match.empty:
            sku = clean_sku(match.iloc[0]["SKU"])
        else:
            sku = clean_sku(title)
        # Evitar duplicados: si ya existe ese SKU en mapping, no lo sobrescribimos
        if sku not in mappings:
            mappings[sku] = {
                "SKU": sku,
                "Title": title,
                "Imagen_local": img_name,
                "Imagen_renombrada": f"{sku}.png",
                "Imagen_URL": f"https://res.cloudinary.com/{CLOUD_NAME}/image/upload/{sku}.png"
            }
            # Renombrar archivo local si existe y aún no fue renombrado
            for folder in glob.glob(os.path.join(BASE_DIR, "*_files")):
                old_path = os.path.join(folder, img_name)
                new_path = os.path.join(folder, f"{sku}.png")
                if os.path.exists(old_path) and not os.path.exists(new_path):
                    try:
                        os.rename(old_path, new_path)
                        print(f"🔄 {old_path} -> {new_path}")
                    except Exception as e:
                        print(f"⚠️ No se pudo renombrar {old_path}: {e}")

# --- Guardar mapping ---
pd.DataFrame(mappings.values()).to_csv(OUT_MAPPING, index=False, sep=";")
print(f"✅ Mapping generado: {len(mappings)} filas -> {OUT_MAPPING}")

# --- Actualizar CSV Shopify con URLs Cloudinary ---
shopify = pd.read_csv(SHOPIFY_CSV, sep=";", encoding="utf-8")
map_df = pd.DataFrame(mappings.values())

shopify = shopify.merge(map_df[["SKU","Imagen_URL"]], on="SKU", how="left")
shopify["Product image URL"] = shopify["Imagen_URL"].fillna(shopify["Product image URL"])

shopify.to_csv(SHOPIFY_CSV, index=False, sep=";")
print(f"🎉 Shopify CSV actualizado con URLs Cloudinary -> {SHOPIFY_CSV}")
