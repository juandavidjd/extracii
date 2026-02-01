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
df = df.dropna(subset=["SKU","Title"], how="any")
df = df[df["SKU"].astype(str).str.strip() != ""]
df = df[df["Title"].astype(str).str.strip() != ""]

# --- Definir categorías por palabras clave ---
categorias = {
    "BANDAS FRENO": "Frenos",
    "PASTILLAS": "Frenos",
    "DISCOS CLUTCH": "Clutch",
    "MANIGUETA": "Controles",
    "CULATA": "Motor",
    "VALVULA": "Motor",
    "ARBOL LEVAS": "Motor",
    "CARBURADOR": "Carburación",
    "LLAVE GASOLINA": "Carburación",
    "CRUCETA": "Transmisión",
    "PIÑON": "Transmisión",
    "CAJA CAMBIOS": "Transmisión",
    "BOBINA": "Eléctrico",
    "CDI": "Eléctrico",
    "STATOR": "Eléctrico",
    "MOTOR ARRANQUE": "Arranque",
    "ESCOBILLAS": "Arranque",
    "STOP": "Luces",
    "CAPUCHON BUJIA": "Eléctrico",
    "SWICH": "Eléctrico",
    "PERA FRENO": "Frenos",
    "EMPQUE": "Empaques",
    "RETENEDOR": "Empaques",
    "FILTRO": "Filtros",
    "RADIADOR": "Refrigeración",
    "VENTILADOR": "Refrigeración",
    "BOMBA ACEITE": "Lubricación",
    "BOMBA AGUA": "Refrigeración",
    "RIN": "Rines",
    "MANUBRIO": "Controles",
    "GUAYA": "Guayas",
}

# --- Crear columna Categoria ---
def asignar_categoria(title):
    t = str(title).upper()
    for clave, cat in categorias.items():
        if clave in t:
            return cat
    return "General"

df["Categoria"] = df["Title"].apply(asignar_categoria)

# --- Eliminar filas que eran encabezados de grupo ---
df = df[~df["Title"].str.upper().isin(categorias.keys())]

# --- Guardar archivo limpio y parametrizado ---
clean_file = os.path.join(BASE_DIR, "LISTADO_KAIQI_PARAMETRIZADO.xlsx")
df.to_excel(clean_file, index=False)

print(f"✅ Archivo parametrizado generado -> {clean_file}")
print(f"📊 Total de productos válidos: {len(df)}")
