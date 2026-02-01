import pandas as pd
import os
import re
from thefuzz import fuzz
from thefuzz import process

# --- CONFIGURACIÓN ---
PROJECT_DIR = r'C:\KAIQI_PROYECTO_FINAL'
KAIQI_INVENTARIO = os.path.join(PROJECT_DIR, 'Inventario_Limpio_CORREGIDO.csv')
COMPETENCIA_DB = os.path.join(PROJECT_DIR, 'Base_Datos_Competencia_Maestra.csv')
CATALOGO_PERFECCION = os.path.join(PROJECT_DIR, 'catalogo_shopify.xlsx - catalogo.csv')

# --- SALIDA ---
OUTPUT_INVENTARIO_ENRIQUECIDO = os.path.join(PROJECT_DIR, 'Inventario_FINAL_CON_TAXONOMIA.csv')

# --- LISTAS DE PALABRAS CLAVE PARA LÓGICA ---
STOP_WORDS = [
    'CAJA', 'X10', 'JUEGO', 'KIT', 'PAR', 'UNIDAD', 'ORIGINAL', 'TIPO', 'OEM', 'KAIQI', 
    'REPUESTO', 'DALU', 'SMG', 'HLK', 'TWOM', 'KAY', 'CHO', 'KET', 'MN', 'MV', 'EOM', 'CTO', 
    'COMPL', 'REF', 'GENERICO', 'PARA', 'CON', 'DE'
]
MOTO_KEYWORDS = ['PULSAR', 'BWS', 'AGILITY', 'SCOOTER', 'NKD', 'FZ', 'LIBERO', 'BOXER', 'GS', 'GN', 'JET', 'EVO', 'TTR', 'AKT', 'YAMAHA', 'HONDA', 'SUZUKI', 'KYMCO']
MOTOCARGUERO_KEYWORDS = ['CARGUERO', '3W', 'AYCO', 'VAISAND', 'MOTOCARRO', 'TORITO', 'BAJAJ']
CAPITALIZE_WORDS = ['AKT', 'AYCO', 'KYMCO', 'BWS', 'NKD', 'SLR', 'TTR', 'CGR', 'CG', 'CDI', 'LED', 'OEM', 'KAIQI']

print("--- SCRIPT DE ENRIQUECIMIENTO DE TAXONOMÍA (V7) ---")

# --- 1. Funciones de Limpieza y Formato ---
def clean_text_for_matching(text):
    text = str(text).upper()
    text = text.replace('Ã±', 'Ñ').replace('Ã', 'N') # Corregir 'Ñ'
    for word in STOP_WORDS:
        text = text.replace(word, '')
    text = re.sub(r'[^A-Z0-9\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

def format_title(text):
    text = str(text).title() 
    for word in CAPITALIZE_WORDS:
        text = re.sub(r'\b' + re.escape(word.title()) + r'\b', word, text, flags=re.IGNORECASE)
    # Corregir caracteres rotos
    text = text.replace('ã±', 'ñ').replace('ã¡', 'á').replace('ã©', 'é').replace('ã­', 'í').replace('ã³', 'ó').replace('ãº', 'ú')
    text = text.replace('ã‘', 'Ñ')
    return text

def get_tipo_vehiculo(desc, default):
    # Si el mapa de perfección ya nos dio un tipo, lo respetamos
    if default and default != "N/A":
        return default
    # Si no, intentamos adivinar
    desc_upper = str(desc).upper()
    if any(keyword in desc_upper for keyword in MOTOCARGUERO_KEYWORDS):
        return "MOTOCARGUERO"
    if any(keyword in desc_upper for keyword in MOTO_KEYWORDS):
        return "MOTO"
    return "MOTOCARGUERO" # Default KAIQI

def get_sistema_fallback(cat_text):
    cat_text = str(cat_text).upper()
    if any(word in cat_text for word in ['MOTOR', 'CULATA', 'CILINDRO', 'PISTON', 'BOMBA', 'CARBURADOR', 'CIGUEÑAL', 'BIELA', 'EMPAQUE', 'CLUTCH', 'ARBOL', 'BALANCIN']):
        return 'MOTOR'
    if any(word in cat_text for word in ['FRENO', 'RIN', 'TREN', 'CHASIS', 'AMORTIGUADOR', 'DIRECCION', 'GUARDABARRO', 'MANUBRIO']):
        return 'CHASIS Y FRENOS'
    if any(word in cat_text for word in ['ELECTRICO', 'CDI', 'BOBINA', 'ARRANQUE', 'REGULADOR', 'BENDIX', 'COMANDO', 'LUCES', 'PITO', 'SWICH']):
        return 'SISTEMA ELECTRICO'
    if any(word in cat_text for word in ['CAJA', 'TRANSMISION', 'CADENILLA', 'PIÑON']):
        return 'TRANSMISION'
    return 'ACCESORIOS Y OTROS'

# --- 2. Cargar Bases de Datos ---
try:
    print("1. Cargando inventario KAIQI (420 productos)...")
    df_kaiqi = pd.read_csv(KAIQI_INVENTARIO, sep=';', dtype=str, encoding='utf-8-sig')
    
    print("2. Cargando 'Catálogo de Perfección' (110 productos)...")
    df_perfeccion = pd.read_csv(CATALOGO_PERFECCION, sep=';', encoding='latin-1', dtype=str)
    df_perfeccion = df_perfeccion.applymap(lambda x: str(x).replace('Ã±', 'ñ').replace('Ã³', 'ó').replace('Ã¡', 'á').replace('Ã©', 'é').replace('Ã­', 'í').replace('Ãº', 'ú').replace('Ã‘', 'Ñ'))
    
    # --- CREAR EL MAPA DE TAXONOMÍA (EL CEREBRO) ---
    tax_map = {}
    df_perfeccion_limpio = df_perfeccion.dropna(subset=['CATEGORIA_NORM', 'SISTEMA PRINCIPAL'])
    for index, row in df_perfeccion_limpio.iterrows():
        cat_norm = str(row['CATEGORIA_NORM']).upper().strip()
        if cat_norm not in tax_map:
            tax_map[cat_norm] = (
                row['SISTEMA PRINCIPAL'],
                row['SUBSISTEMA'],
                row['COMPONENTE'],
                row['TIPO VEHICULO']
            )
    print(f"   -> Mapa de Taxonomía creado con {len(tax_map)} reglas.")

    print("3. Cargando base de datos de competencia (904 productos)...")
    df_competencia = pd.read_csv(COMPETENCIA_DB, dtype=str)
    
    print("   -> Pre-procesando esencias de Competencia...")
    df_competencia['query_clean'] = df_competencia['Nombre_Externo'].apply(clean_text_for_matching)
    choices = df_competencia['query_clean'].dropna().tolist()
    choice_map = {}
    for i, row in df_competencia.iterrows():
        choice_map[row['query_clean']] = row['Nombre_Externo']

except Exception as e:
    print(f"❌ Error fatal cargando archivos: {e}")
    exit()

print(f"4. Iniciando Enriquecimiento y Propagación...")

# Preparamos el DF KAIQI con las columnas finales
df_kaiqi['CODIGO NEW'] = ""
df_kaiqi['Descripcion_Rica'] = ""
df_kaiqi['Nivel_Confianza'] = 0

matches_100 = 0
matches_fuzzy = 0

# --- 5. Bucle de Enriquecimiento (Los 420 productos) ---
for index, row in df_kaiqi.iterrows():
    sku = str(row['SKU'])
    categoria_kaiqi_orig = str(row['Categoria']).upper().strip()
    
    # --- PASO A: PROPAGAR TAXONOMÍA ---
    if categoria_kaiqi_orig in tax_map:
        # Match 100%: Encontramos la regla en tu archivo de perfección
        matches_100 += 1
        mapa = tax_map[categoria_kaiqi_orig]
        df_kaiqi.at[index, 'Sistema Principal'] = mapa[0]
        df_kaiqi.at[index, 'Subsistema'] = mapa[1]
        df_kaiqi.at[index, 'Componente'] = mapa[2]
        df_kaiqi.at[index, 'Tipo Vehiculo'] = mapa[3]
    else:
        # Fallback: Usar lógica de palabras clave
        df_kaiqi.at[index, 'Sistema Principal'] = get_sistema_fallback(categoria_kaiqi_orig)
        df_kaiqi.at[index, 'Componente'] = categoria_kaiqi_orig.title()
        df_kaiqi.at[index, 'Tipo Vehiculo'] = "N/A" # Marcar para refinar luego

    # --- PASO B: ENRIQUECER DESCRIPCIÓN (FUZZY MATCH) ---
    query = clean_text_for_matching(f"{row['Categoria']} {row['Descripcion']}")
    best_match = process.extractOne(query, choices, scorer=fuzz.token_set_ratio, score_cutoff=85)
    
    desc_final = ""
    if best_match:
        # ¡Encontramos un gemelo!
        matches_fuzzy += 1
        nombre_esencia_match, score = best_match[0], best_match[1]
        desc_rica = choice_map[nombre_esencia_match]
        
        desc_final = format_title(desc_rica)
        df_kaiqi.at[index, 'Descripcion_Rica'] = desc_final
        df_kaiqi.at[index, 'Nivel_Confianza'] = score
    else:
        # No hubo match, usar la descripción KAIQI original (limpia)
        desc_final = format_title(row['Descripcion'])
        df_kaiqi.at[index, 'Descripcion_Rica'] = desc_final
        
    # --- PASO C: REFINAR TIPO VEHICULO ---
    # Usamos la descripción final (sea rica o no) para re-evaluar el tipo de vehículo
    tipo_vehiculo_default = df_kaiqi.at[index, 'Tipo Vehiculo']
    df_kaiqi.at[index, 'Tipo Vehiculo'] = get_tipo_vehiculo(desc_final, tipo_vehiculo_default)


# --- 6. GENERAR CODIGO NEW (PREFIJOS) ---
print("6. Generando CODIGO NEW (Prefijos)...")
prefijos = {
    'MOTOR': 'MOT',
    'CHASIS Y FRENOS': 'CHA',
    'SISTEMA ELECTRICO': 'ELE',
    'TRANSMISION': 'TRA',
    'ACCESORIOS Y OTROS': 'ACC'
}

# Creamos un contador para los prefijos
counters = {}

def generar_codigo_new(row):
    sistema = str(row['Sistema Principal']).upper()
    comp = str(row['Componente'])
    
    # 1. Prefijo de Sistema (MOT, CHA, etc.)
    pref1 = prefijos.get(sistema, 'VAR')
    
    # 2. Prefijo de Componente (primeras 3 letras)
    pref2 = re.sub(r'[^A-Z]', '', comp.upper())[:3]
    
    # 3. Contador
    pref_full = f"{pref1}-{pref2}"
    if pref_full not in counters:
        counters[pref_full] = 0
    counters[pref_full] += 1
    
    # 4. Formato: MOT-CUL-001
    return f"{pref_full}-{counters[pref_full]:03d}"

df_kaiqi['CODIGO NEW'] = df_kaiqi.apply(generar_codigo_new, axis=1)


# --- 7. LIMPIEZA Y GUARDADO FINAL ---
print("7. Limpiando y guardando archivo final...")

# Seleccionar y reordenar columnas
columnas_finales = [
    'CODIGO NEW', # La nueva columna
    'SKU',        # El código original (KAIQI)
    'Descripcion_Rica', # La descripción enriquecida
    'Precio',
    'Sistema Principal',
    'Subsistema',
    'Componente',
    'Tipo Vehiculo',
    'Categoria', # Categoría original (referencia)
    'Descripcion' # Descripción original (referencia)
]
df_final = df_kaiqi[columnas_finales]
# Renombrar 'Descripcion_Rica' a 'Descripcion' para la salida final
df_final = df_final.rename(columns={'Descripcion_Rica': 'Descripcion'})

# Guardar el CSV final
df_final.to_csv(OUTPUT_INVENTARIO_ENRIQUECIDO, index=False, sep=';', encoding='utf-8-sig')

print("\n" + "="*50)
print(f"✅ ¡PROYECTO DE TAXONOMÍA FINALIZADO!")
print(f"   -> {OUTPUT_INVENTARIO_ENRIQUECIDO}")
print(f"   -> {len(df_final)} productos procesados.")
print(f"   -> {matches_100} productos mapeados con 'catalogo.csv' (Taxonomía 100% precisa).")
print(f"   -> {matches_fuzzy} descripciones enriquecidas desde la competencia.")
print("="*50)
print("Revisa el archivo 'Inventario_FINAL_CON_TAXONOMIA.csv'.")