import os
import pandas as pd
from bs4 import BeautifulSoup
import glob
import re

BASE_DIR = r"C:/sqk/html_pages"
CATALOGO = os.path.join(BASE_DIR, "kaiqi_catalogo.csv")
SHOPIFY_CSV = os.path.join(BASE_DIR, "kaiqi_shopify_import.csv")
OUT_MAPPING = os.path.join(BASE_DIR, "imagenes_mapping.csv")

CLOUD_NAME = "dhegu1fzm"  # ⚡ tu cuenta en Cloudinary

# --- Funciones auxiliares ---
def clean_filename(name):
    """Convierte el título en un nombre de archivo válido"""
    name = str(name).strip()
    name = name.replace(" ", "_").replace("/", "-").replace("*", "x")
    name = re.sub(r"[^A-Za-z0-9_-]", "", name)
    return f"{name}.png"

def normalize_title(t):
    return str(t).strip() if pd.notna(t) else ""

def enrich_title(title, category):
    title = str(title).strip()
    if re.match(r"^\d+\*\d+\s*MM$", title.upper()):
        return f"{title} {category}"
    if len(title.split()) <= 3 and not any(k in title.lower() for k in [
        "bujia", "freno", "cilindro", "stop", "balinera", "motor", "kit", "piñon", "guaya", "biela", "valvula", "carburador"
    ]):
        return f"{title} {category}"
    return title

def infer_categoria(title):
    t = title.lower()
    if "cruceta" in t or re.match(r"^\d+\*\d+\s*mm$", t): return "Crucetas Carguero"
    if "bujia" in t: return "Encendido"
    if "cilindro" in t or "culata" in t or "piston" in t: return "Motor"
    if "freno" in t or "bomba" in t or "pastilla" in t: return "Frenos"
    if "carburador" in t or "pz" in t: return "Carburación"
    if "piñon" in t or "caja cambios" in t or "reversa" in t: return "Transmisión"
    if "guaya" in t: return "Controles"
    return "Repuestos para Moto"

# --- Cargar catálogo ---
df = pd.read_csv(CATALOGO, sep=";", encoding="latin-1")
df.columns = df.columns.str.strip().str.replace(" ", "_")
df = df.rename(columns={"CODIGO":"SKU","DESCRICION":"Title"})
df = df[df["SKU"].notna()]
df["SKU"] = df["SKU"].apply(lambda s: str(s).strip())
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
        match = df[df["Title"].str.contains(title[:10], case=False, na=False)]
        if not match.empty:
            sku = str(match.iloc[0]["SKU"]).strip()
        else:
            sku = title.replace(" ", "_")
        if sku not in mappings:
            categoria = infer_categoria(title)
            enriched_title = enrich_title(title, categoria)
            imagen_renombrada = clean_filename(enriched_title)
            mappings[sku] = {
                "SKU": sku,
                "Title": enriched_title,
                "Imagen_local": img_name,
                "Imagen_renombrada": imagen_renombrada,
                "Imagen_URL": f"https://res.cloudinary.com/{CLOUD_NAME}/image/upload/{imagen_renombrada}"
            }
            for folder in glob.glob(os.path.join(BASE_DIR, "*_files")):
                old_path = os.path.join(folder, img_name)
                new_path = os.path.join(folder, imagen_renombrada)
                if os.path.exists(old_path) and not os.path.exists(new_path):
                    try:
                        os.rename(old_path, new_path)
                        print(f"🔄 {old_path} -> {new_path}")
                    except Exception as e:
                        print(f"⚠️ No se pudo renombrar {old_path}: {e}")

# --- Guardar mapping ---
pd.DataFrame(mappings.values()).to_csv(OUT_MAPPING, index=False, sep=";")
print(f"✅ Mapping generado: {len(mappings)} filas -> {OUT_MAPPING}")

# --- Actualizar CSV Shopify ---
shopify = pd.read_csv(SHOPIFY_CSV, sep=";", encoding="utf-8")
map_df = pd.DataFrame(mappings.values())

shopify = shopify.merge(map_df[["SKU","Imagen_URL","Title"]], on="SKU", how="left")

if "Imagen_URL" in shopify.columns:
    shopify["Product image URL"] = shopify["Imagen_URL"].fillna(shopify["Product image URL"])
    shopify = shopify.drop(columns=["Imagen_URL"])

# Actualizar títulos y SEO
shopify["Title"] = shopify["Title_y"].fillna(shopify["Title_x"])
shopify = shopify.drop(columns=["Title_x","Title_y"])
shopify["Description"] = shopify["Title"]
shopify["SEO title"] = shopify["Title"].apply(lambda t: str(t)[:70])
shopify["SEO description"] = shopify["Title"].apply(lambda t: str(t)[:160])

shopify.to_csv(SHOPIFY_CSV, index=False, sep=";")
print(f"🎯 Shopify CSV actualizado con URLs Cloudinary y títulos enriquecidos -> {SHOPIFY_CSV}")
