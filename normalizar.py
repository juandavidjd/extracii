import pandas as pd
import os

BASE_DIR = r"C:/sqk/html_pages"
EXCEL_FILE = os.path.join(BASE_DIR, "LISTADO_KAIQI_CATEGORIZADO.xlsx")

# --- Cargar archivo categorizado ---
df = pd.read_excel(EXCEL_FILE)

# --- Diccionario de normalización ---
map_categorias = {
    "BANDAS FRENO TRASERO": "Frenos",
    "PASTILLAS DE FRENO DEL HLK": "Frenos",
    "BOMBA FRENO -CILINDRO FRENO": "Frenos",
    "PERA FRENOS": "Frenos",
    "DISCOS CLUTCH": "Clutch",
    "PRENSA CLUTH CON DISCOS": "Clutch",
    "MANIGUETA CON BASE COMPLETAS": "Controles",
    "ARBOL LEVAS": "Motor",
    "CULATA COMPLETA CON VALVULAS": "Motor",
    "KIT VALVULAS": "Motor",
    "CIGÜEÑAL+BALINERA": "Motor",
    "KIT CILINDROS EOM": "Motor",
    "KIT ANILLOS": "Motor",
    "KIT BALANCINES INFERIOR": "Motor",
    "MOTOR ARRANQUE": "Arranque",
    "ESCOBILLAS": "Arranque",
    "CAPUCHON BUJIA": "Eléctrico",
    "BOBINA DE ALTA  CON CAPUCHON": "Eléctrico",
    "BOBINA PULSORA": "Eléctrico",
    "CDI": "Eléctrico",
    "STATOR -CORONA ENCENDIDO": "Eléctrico",
    "SWICHES": "Eléctrico",
    "FLASHER ELETRONICO": "Eléctrico",
    "STOP": "Luces",
    "PARTES DE SCOOTER-AGILLITY/DINAMIC": "Scooter",
    "CARBURADORES": "Carburación",
    "LLAVE GASOLINA": "Carburación",
    "CRUCETAS CARGUERO": "Transmisión",
    "CAJA DE CAMBIOS-REVERSA": "Transmisión",
    "PIÑON DEL": "Transmisión",
    "KIT PIÑONES  DEL/TRAS": "Transmisión",
    "PIÑON REVERSA 12 D + BALINERA GRUESO REFORZADO": "Transmisión",
    "GUAYAS / VARIOS": "Guayas",
    "KIT EMPAQUES CTO": "Empaques",
    "KIT RETENEDORES MOTOR": "Empaques",
    "FILTRO DE AIRE": "Filtros",
    "CAJA FILTROS": "Filtros",
    "BOMBA ACEITE": "Lubricación",
    "CADENILLAS": "Distribución",
    "CORREAS DISTRIBUCION": "Distribución",
    "GUIA CADENILLA": "Distribución",
    "TREN DEL  CARGUERO": "Chasis",
    "NAN": "General",
    "ACERO 1045": "General"
}

# --- Normalizar columna Categoria ---
df["Categoria"] = df["Categoria"].replace(map_categorias)

# --- Guardar archivo final ---
final_file = os.path.join(BASE_DIR, "LISTADO_KAIQI_CATEGORIZADO_NORMALIZADO.xlsx")
df.to_excel(final_file, index=False)

print(f"✅ Archivo normalizado generado -> {final_file}")
print(f"📊 Total de productos válidos: {len(df)}")
print(f"📂 Categorías únicas: {df['Categoria'].unique()}")
