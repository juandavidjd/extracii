import pandas as pd
import os

BASE_DIR = r"C:/sqk/html_pages"
EXCEL_FILE = os.path.join(BASE_DIR, "LISTADO KAIQI NOV-DIC 2025.xlsx")

# --- Cargar Excel ---
df = pd.read_excel(EXCEL_FILE, sheet_name="Hoja1", header=0)

# --- Normalizar columnas ---
df.columns = df.columns.str.strip().str.upper()
df = df.rename(columns={"CODIGO":"SKU","DESCRICION":"Title","PRECIO SIN IVA":"Precio"})

# --- Crear columna Categoria ---
categoria_actual = None
categorias = []

for _, row in df.iterrows():
    sku = str(row["SKU"]).strip()
    title = str(row["Title"]).strip()
    precio = row["Precio"]

    # Si la fila es un encabezado de grupo (sin precio y sin SKU numérico/código válido)
    if (sku == "nan" or sku == "" or sku.isalpha()) and (pd.isna(precio) or precio == 0):
        categoria_actual = title.upper().strip()
        categorias.append(categoria_actual)  # opcional: lista de categorías detectadas
        df.at[_, "Categoria"] = categoria_actual
    else:
        # Asignar la categoría activa al producto
        df.at[_, "Categoria"] = categoria_actual if categoria_actual else "General"

# --- Eliminar filas que eran solo encabezados ---
df = df[df["SKU"].astype(str).str.strip() != ""]
df = df[df["Title"].astype(str).str.strip() != ""]

# --- Guardar archivo limpio y categorizado ---
clean_file = os.path.join(BASE_DIR, "LISTADO_KAIQI_CATEGORIZADO.xlsx")
df.to_excel(clean_file, index=False)

print(f"✅ Archivo categorizado generado -> {clean_file}")
print(f"📊 Total de productos válidos: {len(df)}")
print(f"📂 Categorías detectadas: {set(categorias)}")
