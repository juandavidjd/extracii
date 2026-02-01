import pandas as pd
import os

BASE_DIR = r"C:/sqk/html_pages"
EXCEL_FILE = os.path.join(BASE_DIR, "LISTADO KAIQI NOV-DIC 2025.xlsx")

# --- Cargar Excel ---
df = pd.read_excel(EXCEL_FILE, sheet_name="Hoja1", header=0)

# --- Normalizar columnas ---
df.columns = df.columns.str.strip().str.upper()
df = df.rename(columns={"CODIGO":"SKU","DESCRICION":"Title","PRECIO SIN IVA":"Precio"})

# --- Eliminar filas vacías ---
df = df.dropna(subset=["SKU","Title"], how="any")   # borra filas sin SKU o sin título
df = df[df["SKU"].astype(str).str.strip() != ""]    # borra filas con SKU vacío
df = df[df["Title"].astype(str).str.strip() != ""]  # borra filas con título vacío

# --- Guardar archivo limpio ---
clean_file = os.path.join(BASE_DIR, "LISTADO_KAIQI_LIMPIO.xlsx")
df.to_excel(clean_file, index=False)

print(f"✅ Archivo limpio generado -> {clean_file}")
print(f"📊 Total de productos válidos: {len(df)}")
