import os
import re
import glob
import pandas as pd
from bs4 import BeautifulSoup
from slugify import slugify

BASE_DIR = r"C:/sqk/html_pages"
CATALOGO_CSV = os.path.join(BASE_DIR, "kaiqi_catalogo.csv")
OUT_CSV = os.path.join(BASE_DIR, "kaiqi_shopify_import.csv")
PLACEHOLDER_DIR = os.path.join(BASE_DIR, "placeholders")

# --- Utilidades ---
def clean_text(s):
    if pd.isna(s):
        return ""
    return str(s).strip()

def normalize_price(raw):
    if pd.isna(raw):
        return ""
    s = str(raw)
    # quitar espacios y símbolos
    s = s.replace(" ", "").replace("$", "")
    # quitar separador de miles ".", y convertir "," a "."
    s = s.replace(".", "").replace(",", ".")
    # extraer número
    m = re.search(r"(\d+(\.\d+)?)", s)
    return float(m.group(1)) if m else ""

def guess_category(title):
    t = clean_text(title).lower()
    if any(k in t for k in ["bujia", "bujía"]): return "bujias"
    if any(k in t for k in ["freno","pastilla","banda","bomba freno","cilindro freno"]): return "frenos"
    if any(k in t for k in ["cilindro","culata","pistón","piston","balancin","biela","valvula","válvula"]): return "motor"
    if "carburador" in t or "pz" in t: return "carburadores"
    if any(k in t for k in ["piñon","piñón","transmision","transmisión","kit piñones","caja cambios","reversa"]): return "transmision"
    return "otros"

def placeholder_for_category(cat):
    file_map = {
        "bujias": "bujias.jpg",
        "frenos": "frenos.jpg",
        "motor": "motor.jpg",
        "carburadores": "carburadores.jpg",
        "transmision": "transmision.jpg",
        "otros": "otros.jpg",
    }
    fname = file_map.get(cat, "otros.jpg")
    path = os.path.join(PLACEHOLDER_DIR, fname)
    return path if os.path.exists(path) else ""

def to_bool_str(x): return "TRUE" if x else "FALSE"

def get_image_local_or_fallback(img_src, html_file, title):
    # 1) intentar resolver imagen local relativa de *_files
    if img_src:
        # si img_src es relativa, convertirla a ruta local
        html_base = os.path.splitext(os.path.basename(html_file))[0] + "_files"
        files_dir = os.path.join(BASE_DIR, html_base)
        # Nombre base del archivo remoto
        img_name = os.path.basename(img_src)
        local_candidate = os.path.join(files_dir, img_name)
        if os.path.exists(local_candidate):
            return local_candidate
    # 2) si viene URL absoluta desde HTML (http/https), usarla
    if img_src and img_src.startswith("http"):
        return img_src
    # 3) placeholder por categoría
    cat = guess_category(title)
    ph = placeholder_for_category(cat)
    return ph or ""

def safe_handle_from_link(link, title):
    # Intenta extraer un identificador del link
    if link and isinstance(link, str):
        base = os.path.basename(link.split("?")[0]).strip("/")
        if base and base != "":
            return slugify(base)
    # fallback al título
    return slugify(title or "producto-kaiqi")

# --- Parseo de HTMLs locales ---
def parse_listing_html(file_path):
    products = []
    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
    # cada producto en listados WooCommerce
    items = soup.select("li.product")
    for item in items:
        title_el = item.select_one("h2.woocommerce-loop-product__title")
        title = title_el.get_text(strip=True) if title_el else ""
        price_el = item.select_one("span.woocommerce-Price-amount")
        price_web = price_el.get_text(strip=True) if price_el else ""
        a_el = item.select_one("a")
        link = a_el["href"] if a_el and a_el.has_attr("href") else ""
        img_el = item.select_one("img")
        img_src = img_el["src"] if img_el and img_el.has_attr("src") else ""

        handle_guess = safe_handle_from_link(link, title)
        products.append({
            "Handle_web": handle_guess,
            "Title_web": clean_text(title),
            "Price_web": clean_text(price_web),
            "Image_src": clean_text(img_src),
            "Link": clean_text(link),
            "Source_html": file_path,
        })
    return products

# --- Cargar catálogo con limpieza de encabezados ---
def load_catalog(csv_path):
    df = pd.read_csv(csv_path, sep=";", encoding="latin-1")
    # limpiar encabezados
    df.columns = df.columns.str.strip().str.replace(" ", "_")
    # renombrar
    rename_map = {}
    for col in df.columns:
        if col.lower().startswith("codigo"):
            rename_map[col] = "Handle"
        elif col.lower().startswith("descricion"):
            rename_map[col] = "Title_pdf"
        elif col.lower().startswith("precio_sin_iva"):
            rename_map[col] = "Price_pdf"
    df = df.rename(columns=rename_map)
    # normalizar precio
    if "Price_pdf" in df.columns:
        df["Price_pdf"] = df["Price_pdf"].apply(normalize_price)
    else:
        df["Price_pdf"] = ""

    # limpiar títulos
    if "Title_pdf" in df.columns:
        df["Title_pdf"] = df["Title_pdf"].apply(clean_text)
    else:
        df["Title_pdf"] = ""

    # limpiar handle
    if "Handle" in df.columns:
        df["Handle"] = df["Handle"].apply(lambda x: clean_text(x))
    else:
        df["Handle"] = ""

    # eliminar filas vacías sin código
    df = df[df["Handle"] != ""]
    return df

# --- Recorrido principal ---
def main():
    # 1) Parsear todos los HTML
    listing_files = sorted(glob.glob(os.path.join(BASE_DIR, "*.html")))
    web_products = []
    for f in listing_files:
        web_products.extend(parse_listing_html(f))
    df_web = pd.DataFrame(web_products)

    # 2) Cargar catálogo
    df_pdf = load_catalog(CATALOGO_CSV)

    # 3) Intentar emparejar por código exacto si el título contiene el código
    # Generar clave de unión flexible:
    # - Preferimos el Handle del catálogo
    # - Si no tenemos, usar slug del título
    df_web["Handle_guess"] = df_web["Title_web"].apply(lambda t: slugify(t))
    df_pdf["Handle_slug"] = df_pdf["Handle"].apply(lambda h: slugify(h))

    # Unir por varias claves: Handle_slug ~ Handle_web o Handle_guess
    # Primero intentamos unir por coincidencia exacta del código en el título
    df_merge1 = pd.merge(
        df_web,
        df_pdf,
        left_on="Handle_guess",
        right_on="Handle_slug",
        how="left",
        suffixes=("_w", "_p")
    )

    # Si no encontró match, usar heurística: buscar códigos presentes en el título
    def match_handle_from_title(title, catalog_handles):
        t = clean_text(title).lower()
        for h in catalog_handles:
            if h and h.lower() in t:
                return h
        return ""

    catalog_handles = df_pdf["Handle"].tolist()
    df_merge1["Handle_pdf_match"] = df_merge1.apply(
        lambda r: match_handle_from_title(r.get("Title_web",""), catalog_handles)
        if pd.isna(r.get("Handle")) or r.get("Handle","")=="" else r.get("Handle",""),
        axis=1
    )
    # Resolver Handle final
    def resolve_handle(row):
        # Prefer catálogo
        if clean_text(row.get("Handle_pdf_match","")):
            return clean_text(row.get("Handle_pdf_match"))
        if clean_text(row.get("Handle","")):
            return clean_text(row.get("Handle"))
        # fallback al handle del link o slug del título
        if clean_text(row.get("Handle_web","")):
            return clean_text(row.get("Handle_web"))
        return slugify(clean_text(row.get("Title_web","producto-kaiqi")))

    df_merge1["Handle_final"] = df_merge1.apply(resolve_handle, axis=1)

    # 4) Título y descripción
    df_merge1["Title_final"] = df_merge1.apply(
        lambda r: clean_text(r.get("Title_pdf")) if clean_text(r.get("Title_pdf")) else clean_text(r.get("Title_web")),
        axis=1
    )
    df_merge1["Desc_final"] = df_merge1["Title_final"]  # si no tienes cuerpo técnico, usamos el título como descripción corta

    # 5) Precio: prefer catálogo → luego web → vacío
    df_merge1["Price_final"] = df_merge1.apply(
        lambda r: normalize_price(r.get("Price_pdf")) if clean_text(r.get("Price_pdf"))!=""
                  else normalize_price(r.get("Price_web")),
        axis=1
    )

    # 6) Imagen local / URL / placeholder
    df_merge1["Image_final"] = df_merge1.apply(
        lambda r: get_image_local_or_fallback(
            r.get("Image_src",""),
            r.get("Source_html",""),
            r.get("Title_final","")
        ),
        axis=1
    )

    # 7) Categoría y tipo
    df_merge1["Category"] = df_merge1["Title_final"].apply(guess_category)
    df_merge1["Product_category"] = "Vehicles & Parts > Vehicle Parts & Accessories > Motor Vehicle Parts"
    df_merge1["Type"] = df_merge1["Category"].map({
        "bujias": "Encendido",
        "frenos": "Frenos",
        "motor": "Motor",
        "carburadores": "Carburación",
        "transmision": "Transmisión",
        "otros": "Repuestos para Moto"
    }).fillna("Repuestos para Moto")
    df_merge1["Tags"] = df_merge1["Category"].apply(lambda c: f"KAIQI;Repuestos Moto;{c}")

    # 8) Filtrar filas inválidas (sin título o sin handle)
    df_out = df_merge1[(df_merge1["Title_final"]!="") & (df_merge1["Handle_final"]!="")].copy()

    # 9) Construir CSV Shopify completo
    df_out["URL_handle"] = df_out["Handle_final"].apply(lambda h: slugify(str(h)))
    df_out["Image_alt"] = df_out["Title_final"].apply(lambda t: t[:80])
    df_out["SEO_title"] = df_out["Title_final"].apply(lambda t: t[:70])
    df_out["SEO_desc"] = df_out["Desc_final"].apply(lambda d: d[:160])

    # Columnas Shopify
    shopify_cols = [
        "Title","URL handle","Description","Vendor","Product category","Type","Tags",
        "Published on online store","Status","SKU","Barcode","Option1 name","Option1 value",
        "Option2 name","Option2 value","Option3 name","Option3 value","Price","Compare-at price",
        "Cost per item","Charge tax","Tax code","Unit price total measure","Unit price total measure unit",
        "Unit price base measure","Unit price base measure unit","Inventory tracker","Inventory quantity",
        "Continue selling when out of stock","Weight value (grams)","Weight unit for display","Requires shipping",
        "Fulfillment service","Product image URL","Image position","Image alt text","Variant image URL","Gift card",
        "SEO title","SEO description","Google Shopping / Google product category","Google Shopping / Gender",
        "Google Shopping / Age group","Google Shopping / MPN","Google Shopping / AdWords Grouping",
        "Google Shopping / AdWords labels","Google Shopping / Condition","Google Shopping / Custom product",
        "Google Shopping / Custom label 0","Google Shopping / Custom label 1","Google Shopping / Custom label 2",
        "Google Shopping / Custom label 3","Google Shopping / Custom label 4"
    ]

    rows = []
    for _, r in df_out.iterrows():
        rows.append({
            "Title": r["Title_final"],
            "URL handle": r["URL_handle"],
            "Description": r["Desc_final"],
            "Vendor": "KAIQI",
            "Product category": r["Product_category"],
            "Type": r["Type"],
            "Tags": r["Tags"],
            "Published on online store": "TRUE",
            "Status": "active",
            "SKU": r["Handle_final"],
            "Barcode": "",
            "Option1 name": "Title",
            "Option1 value": "Default Title",
            "Option2 name": "",
            "Option2 value": "",
            "Option3 name": "",
            "Option3 value": "",
            "Price": r["Price_final"] if r["Price_final"] != "" else "",
            "Compare-at price": "",
            "Cost per item": "",
            "Charge tax": "TRUE",
            "Tax code": "",
            "Unit price total measure": "",
            "Unit price total measure unit": "",
            "Unit price base measure": "",
            "Unit price base measure unit": "",
            "Inventory tracker": "shopify",
            "Inventory quantity": 20,
            "Continue selling when out of stock": "FALSE",
            "Weight value (grams)": 500,
            "Weight unit for display": "g",
            "Requires shipping": "TRUE",
            "Fulfillment service": "manual",
            "Product image URL": r["Image_final"],
            "Image position": 1,
            "Image alt text": r["Image_alt"],
            "Variant image URL": "",
            "Gift card": "FALSE",
            "SEO title": r["SEO_title"],
            "SEO description": r["SEO_desc"],
            "Google Shopping / Google product category": r["Product_category"],
            "Google Shopping / Gender": "",
            "Google Shopping / Age group": "",
            "Google Shopping / MPN": r["Handle_final"],
            "Google Shopping / AdWords Grouping": r["Type"],
            "Google Shopping / AdWords labels": r["Tags"],
            "Google Shopping / Condition": "New",
            "Google Shopping / Custom product": "FALSE",
            "Google Shopping / Custom label 0": "",
            "Google Shopping / Custom label 1": "",
            "Google Shopping / Custom label 2": "",
            "Google Shopping / Custom label 3": "",
            "Google Shopping / Custom label 4": "",
        })

    out_df = pd.DataFrame(rows, columns=shopify_cols)

    # Eliminar duplicados por SKU/Handle (primer aparición)
    out_df = out_df.drop_duplicates(subset=["SKU"])

    # Exportar con separador ; para mantener consistencia con tu entorno
    out_df.to_csv(OUT_CSV, index=False, sep=";")
    print(f"✅ Exportado: {len(out_df)} productos -> {OUT_CSV}")

if __name__ == "__main__":
    main()
