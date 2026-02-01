import pandas as pd
import os

BASE_DIR = r"C:/sqk/html_pages"
EXCEL_FILE = os.path.join(BASE_DIR, "LISTADO KAIQI NOV-DIC 2025.xlsx")

# --- Cargar archivo ---
df = pd.read_excel(EXCEL_FILE, sheet_name="Hoja1")

# --- Normalizar encabezados ---
df.columns = df.columns.str.strip().str.upper()

# --- Limpiar descripción ---
df["DESCRIPCION"] = (
    df["DESCRIPCION"]
    .astype(str)
    .str.replace(r"\s+", " ", regex=True)  # reemplaza múltiples espacios por uno
    .str.strip()
    .str.upper()
)

# --- Formatear precio con signo pesos ---
def format_precio(x):
    try:
        x = float(x)
        return f"${int(x):,}".replace(",", ".")  # separador de miles con punto
    except:
        return "$0"

df["PRECIO SIN IVA"] = df["PRECIO SIN IVA"].apply(format_precio)

# --- Prefijos por categoría ---
prefijos = {
    "BUJIA": "BUJ",
    "BANDAS FRENO TRASERO": "FRE",
    "PASTILLAS DE FRENO DEL HLK": "FRE",
    "DISCOS CLUTCH": "CLU",
    "KIT CILINDROS EOM": "MOT",
    "CULATA COMPLETA CON VALVULAS": "MOT",
    "CARBURADORES": "CAR",
    "RADIADOR": "RAD",
    "GUAYAS / VARIOS": "GUA",
    "KIT PISTONES +ANILLOS": "MOT",
    "KIT BIELA+CANASTILLA": "MOT",
    "KIT ANILLOS": "MOT",
    "CIGÜEÑAL+BALINERA": "MOT",
    "MOTOR ARRANQUE": "ARR",
    "EMPACUES": "EMP",
    "FILTRO DE AIRE": "FIL",
    "CAJA DIFERENCIAL": "DIF",
    "CAJA DE CAMBIOS": "CAM",
    "PIÑON DELANTERO": "PIN",
    "RIN": "RIN",
    "MANUBRIO": "MAN",
    "ESPEJOS": "ESP",
    "SWICHES": "ELE",
    "CDI": "ELE",
    "BOBINA DE ALTA CON CAPUCHON": "ELE",
    "BOBINA PULSORA": "ELE",
    "FLASHER ELETRONICO": "ELE",
    "VENTILADOR": "REF",
    "BOMBA AGUA": "REF",
    "BOMBA ACEITE": "LUB",
    "FILTRO ACEITE": "FIL",
    "FILTRO CENTRIFUGO": "FIL",
    # puedes seguir ampliando según tus categorías
}

# --- Generar CODIGO NEW lógico ---
counters = {}

def generar_codigo(categoria):
    prefijo = prefijos.get(str(categoria).upper(), "GEN")
    counters[prefijo] = counters.get(prefijo, 0) + 1
    return f"{prefijo}{counters[prefijo]:03d}"

df["CODIGO NEW"] = df["CATEGORIA"].apply(generar_codigo)

# --- Guardar archivo limpio ---
clean_file = os.path.join(BASE_DIR, "LISTADO_KAIQI_FINAL.xlsx")
df.to_excel(clean_file, index=False)

print(f"✅ Archivo final generado -> {clean_file}")
print(f"📊 Total de productos válidos: {len(df)}")
print(f"📂 Categorías únicas: {df['CATEGORIA'].unique()}")
