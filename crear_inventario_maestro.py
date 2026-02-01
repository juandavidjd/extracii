import pandas as pd
import re
from pathlib import Path

# ----------------------------
# Helpers de limpieza
# ----------------------------

def clean_price(value):
    if pd.isna(value):
        return None
    try:
        s = str(value)
        digits = re.sub(r"[^\d]", "", s)
        if digits == "":
            return None
        return int(digits)
    except Exception:
        return None

def clean_code(value):
    if pd.isna(value):
        return None
    s = str(value).strip()
    s = re.sub(r"(?i)c[oó]digo[:\s]*", "", s)
    if re.fullmatch(r"\d+\.0", s):
        s = s.split(".")[0]
    return s if s != "" else None

# ----------------------------
# Limpieza / barrido df_precios
# ----------------------------

def detect_categories_and_products(df_precios):
    rows = []
    current_category = None

    for _, row in df_precios.iterrows():
        raw_code = row.get("CÓDIGO", None)
        raw_desc = row.get("DESCRIPCIÓN", None)
        raw_price = row.get("PRECIO (S/IVA)", None)

        code = clean_code(raw_code)
        price = clean_price(raw_price)
        desc = None if pd.isna(raw_desc) else str(raw_desc).strip()

        if (code is None) and (price is None) and (desc not in (None, "", "nan", "NaN")):
            current_category = desc
            continue

        if (code is not None) or (price is not None):
            rows.append(
                {
                    "CODIGO": code,
                    "DESCRIPCION": desc,
                    "PRECIO": price if price is not None else 0,
                    "Categoria_detectada": current_category,
                }
            )

    df_clean = pd.DataFrame(rows)

    if not df_clean.empty:
        df_clean["PRECIO"] = df_clean["PRECIO"].fillna(0).astype(int)
        df_clean["CODIGO"] = df_clean["CODIGO"].astype(str)

    return df_clean

# ----------------------------
# Limpieza df_shopify
# ----------------------------

def clean_shopify(df_shopify):
    df = df_shopify.copy()

    rename_map = {}
    for col in df.columns:
        if col.lower() == "sku": rename_map[col] = "SKU"
        if col.lower().startswith("image"): rename_map[col] = "Image Src"
        if col.lower().startswith("category"): rename_map[col] = "Category"
        if col.lower().startswith("title"): rename_map[col] = "Title"
    if rename_map:
        df = df.rename(columns=rename_map)

    df["SKU"] = df["SKU"].apply(clean_code)
    df["Image Src"] = df.get("Image Src", "Sin Imagen").fillna("Sin Imagen")
    if "Category" not in df.columns: df["Category"] = None
    if "Title" not in df.columns: df["Title"] = None

    return df

# ----------------------------
# Construcción del inventario maestro
# ----------------------------

def build_master_inventory(df_shopify_raw, df_precios_raw):
    df_shop = clean_shopify(df_shopify_raw)
    df_prec = detect_categories_and_products(df_precios_raw)

    merged = pd.merge(
        df_shop,
        df_prec,
        left_on="SKU",
        right_on="CODIGO",
        how="outer",
        indicator=True,
    )

    merged["SKU_final"] = merged["SKU"].combine_first(merged["CODIGO"])
    merged["Descripcion"] = merged["DESCRIPCION"].combine_first(merged["Title"])

    merged["Precio"] = merged["PRECIO"]
    merged.loc[merged["Precio"].isna(), "Precio"] = 0
    merged["Precio"] = merged["Precio"].astype(int)

    merged["Categoria"] = merged["Category"].combine_first(merged["Categoria_detectada"])
    merged["Categoria"] = merged["Categoria"].fillna("Sin Categoria")
    merged["Categoria"] = merged["Categoria"].apply(lambda x: str(x).strip().title())

    merged["Imagen"] = merged["Image Src"].fillna("Sin Imagen")

    origen_map = {"both": "Ambos", "left_only": "Solo Shopify", "right_only": "Solo Lista"}
    merged["Origen_Dato"] = merged["_merge"].map(origen_map)

    final = merged[["SKU_final", "Descripcion", "Precio", "Categoria", "Imagen", "Origen_Dato"]].copy()
    final = final.rename(columns={"SKU_final": "SKU"})
    final = final.drop_duplicates(subset=["SKU"], keep="first")

    return final

# ----------------------------
# Main program
# ----------------------------

if __name__ == "__main__":
    path_shopify = Path("catalogo_shopify_completo.xlsx")
    path_precios = Path("Inventario Kaiqi.xlsx")

    df_shopify_raw = pd.read_excel(path_shopify)
    df_precios_raw = pd.read_excel(path_precios)

    master_df = build_master_inventory(df_shopify_raw, df_precios_raw)

    output_path = Path("Inventario_KAIQI_Maestro_Final.csv")
    master_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print("\n✅ Inventario maestro generado:", output_path)
    print("Total de ítems:", len(master_df))
    print("\nConteo por Origen_Dato:")
    print(master_df["Origen_Dato"].value_counts())
    print("\nPrimeras 5 filas:")
    print(master_df.head())
