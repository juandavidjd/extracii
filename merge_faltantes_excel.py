import pandas as pd
import difflib
import re
import os

BASE_DIR = r"C:/sqk/html_pages"
EXCEL_FILE = r"C:/sqk/html_pages/LISTADO KAIQI NOV-DIC 2025.xlsx"
FALTANTES_FILE = os.path.join(BASE_DIR, "productos_faltantes.csv")
MAPPING_FILE = os.path.join(BASE_DIR, "imagenes_mapping.csv")
SHOPIFY_FILE = os.path.join(BASE_DIR, "kaiqi_shopify_import.csv")

CLOUD_NAME = "dhegu1fzm"

def clean_filename(name):
    name = str(name).strip()
    name = name.replace(" ", "_").replace("/", "-").replace("*", "x")
    name = re.sub(r"[^A-Za-z0-9_-]", "", name)
    return f"{name}.png"

# --- Cargar Excel maestro ---
excel_df = pd.read_excel(EXCEL_FILE, sheet_name="Hoja1")

# Normalizar nombres de columnas
excel_df.columns = excel_df.columns.str.strip().str.upper()

# Renombrar las columnas clave
excel_df = excel_df.rename(columns={"CODIGO":"SKU","DESCRICION":"Title"})

# Limpiar datos
excel_df["SKU"] = excel_df["SKU"].astype(str).str.strip()
excel_df["Title"] = excel_df["Title"].astype(str).str.strip()

# --- Cargar faltantes ---
faltantes_df = pd.read_csv(FALTANTES_FILE, sep=";")
faltantes_df["Title"] = faltantes_df["Title"].astype(str).str.strip()

# --- Cargar mapping existente ---
mapping_df = pd.read_csv(MAPPING_FILE, sep=";")

# --- Resolver faltantes con Excel ---
resolved_rows = []
for _, row in faltantes_df.iterrows():
    title = row["Title"]
    img_local = row["Imagen_local"]

    # Buscar coincidencia difusa en Excel
    match = difflib.get_close_matches(title, excel_df["Title"], n=1, cutoff=0.6)
    if match:
        matched_title = match[0]
        sku = excel_df.loc[excel_df["Title"] == matched_title, "SKU"].values[0]
        enriched_title = matched_title
    else:
        # Fallback: usar título como SKU
        sku = re.sub(r"[^A-Za-z0-9]", "", title)[:15]
        enriched_title = title

    imagen_renombrada = clean_filename(enriched_title)
    imagen_url = f"https://res.cloudinary.com/{CLOUD_NAME}/image/upload/{imagen_renombrada}"

    resolved_rows.append({
        "SKU": sku,
        "Title": enriched_title,
        "Imagen_local": img_local,
        "Imagen_renombrada": imagen_renombrada,
        "Imagen_URL": imagen_url
    })

# --- Integrar al mapping ---
resolved_df = pd.DataFrame(resolved_rows)
mapping_final = pd.concat([mapping_df, resolved_df], ignore_index=True)
mapping_final.to_csv(MAPPING_FILE, sep=";", index=False)
print(f"✅ Mapping actualizado con {len(resolved_df)} productos faltantes -> {MAPPING_FILE}")

# --- Actualizar Shopify ---
shopify_df = pd.read_csv(SHOPIFY_FILE, sep=";")
shopify_df = shopify_df.merge(mapping_final[["SKU","Imagen_URL","Title"]], on="SKU", how="left")

shopify_df["Product image URL"] = shopify_df["Imagen_URL"].fillna(shopify_df.get("Product image URL"))
shopify_df["Title"] = shopify_df["Title_y"].fillna(shopify_df["Title_x"])
shopify_df["Description"] = shopify_df["Title"]
shopify_df["SEO title"] = shopify_df["Title"].apply(lambda t: str(t)[:70])
shopify_df["SEO description"] = shopify_df["Title"].apply(lambda t: str(t)[:160])

shopify_df = shopify_df.drop(columns=["Imagen_URL","Title_x","Title_y"], errors="ignore")
shopify_df.to_csv(SHOPIFY_FILE, sep=";", index=False)
print(f"🎯 Shopify CSV actualizado con SKUs oficiales y títulos enriquecidos -> {SHOPIFY_FILE}")
