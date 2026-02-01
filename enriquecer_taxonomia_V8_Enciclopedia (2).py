import pandas as pd
import os
import re
import shutil
from thefuzz import fuzz
from thefuzz import process
from PIL import Image

# --- CONFIGURACIÓN ---
PROJECT_DIR = r'C:\KAIQI_PROYECTO_FINAL'
KAIQI_INVENTARIO = os.path.join(PROJECT_DIR, 'Inventario_Limpio_CORREGIDO.csv')
COMPETENCIA_DB = os.path.join(PROJECT_DIR, 'Base_Datos_Competencia_Maestra.csv')
COMPETENCIA_FOTOS_DIR = os.path.join(PROJECT_DIR, 'FOTOS_COMPETENCIA')

# --- SALIDAS ---
OUTPUT_SHOPIFY_CSV = os.path.join(PROJECT_DIR, 'Shopify_Import_FINAL_TAXONOMIA.csv')
OUTPUT_FOTOS_DIR = os.path.join(PROJECT_DIR, 'IMAGENES_PARA_SHOPIFY')
OUTPUT_INVENTARIO_ENRIQUECIDO = os.path.join(PROJECT_DIR, 'Inventario_FINAL_CON_TAXONOMIA.csv')

# --- 1. MAPA DE TAXONOMÍA (Basado en Enciclopedia y Categorías KAIQI) ---
# Este es el "cerebro" que traduce tus categorías a una estructura profesional
TAXONOMY_MAP = {
    # SISTEMA: MOTOR
    'CULATA COMPLETA CON VALVULAS': ('MOTOR', 'CULATA', 'CULATA COMPLETA'),
    'EMPAQUES TAPA CULATIN ORING': ('MOTOR', 'CULATA', 'EMPAQUE TAPA CULATIN'),
    'KIT VALVULAS': ('MOTOR', 'CULATA', 'VALVULAS'),
    'GUIA VALVULA': ('MOTOR', 'CULATA', 'GUIAS DE VALVULA'),
    'SELLOS DOBLE RESORTE VERDES': ('MOTOR', 'CULATA', 'SELLOS DE VALVULA'),
    'BALANCIN SUPERIOR': ('MOTOR', 'CULATA', 'BALANCINES'),
    'ARBOL LEVAS': ('MOTOR', 'DISTRIBUCION', 'ARBOL DE LEVAS'),
    'CADENILLAS': ('MOTOR', 'DISTRIBUCION', 'CADENILLA'),
    'GUIA CADENILLA': ('MOTOR', 'DISTRIBUCION', 'GUIAS CADENILLA'),
    'TENSOR CADENILLA': ('MOTOR', 'DISTRIBUCION', 'TENSOR CADENILLA'),
    'KIT CILINDRO EOM': ('MOTOR', 'TREN ALTERNATIVO', 'CILINDRO COMPLETO'),
    'KIT PISTONES +ANILLOS': ('MOTOR', 'TREN ALTERNATIVO', 'PISTON Y ANILLOS'),
    'KIT ANILLOS': ('MOTOR', 'TREN ALTERNATIVO', 'ANILLOS'),
    'KIT BIELA+CANASTILLA': ('MOTOR', 'TREN ALTERNATIVO', 'BIELA'),
    'CIGÜEÑAL+BALINERA': ('MOTOR', 'TREN ALTERNATIVO', 'CIGÜEÑAL'),
    'CARBURADORES': ('MOTOR', 'ALIMENTACION', 'CARBURADOR'),
    'CONECTOR CARBURADOR': ('MOTOR', 'ALIMENTACION', 'CONECTOR CARBURADOR'),
    'BAQUELA CARBURADOR': ('MOTOR', 'ALIMENTACION', 'BAQUELA CARBURADOR'),
    'FILTRO DE AIRE': ('MOTOR', 'ALIMENTACION', 'FILTRO DE AIRE'),
    'CAJA FILTROS': ('MOTOR', 'ALIMENTACION', 'CAJA FILTRO'),
    'LLAVE GASOLINA': ('MOTOR', 'ALIMENTACION', 'LLAVE GASOLINA'),
    'BOMBA ACEITE': ('MOTOR', 'LUBRICACION', 'BOMBA DE ACEITE'),
    'FILTRO ACEITE': ('MOTOR', 'LUBRICACION', 'FILTRO DE ACEITE'),
    'FILTRO CENTRIFUGO': ('MOTOR', 'LUBRICACION', 'FILTRO CENTRIFUGO'),
    'RADIADOR': ('MOTOR', 'REFRIGERACION', 'RADIADOR'),
    'VENTILADOR': ('MOTOR', 'REFRIGERACION', 'VENTILADOR'),
    'BASE VENTILADOR': ('MOTOR', 'REFRIGERACION', 'BASE VENTILADOR'),
    'BOMBA AGUA': ('MOTOR', 'REFRIGERACION', 'BOMBA DE AGUA'),
    'TERMOSTATO': ('MOTOR', 'REFRIGERACION', 'TERMOSTATO'),
    'TANQUE AGUA': ('MOTOR', 'REFRIGERACION', 'TANQUE AUXILIAR'),
    'TROMPO TEMPERATURA': ('MOTOR', 'REFRIGERACION', 'SENSOR TEMPERATURA'),
    'TAPAS REFRIGERANTE DE MOTOR': ('MOTOR', 'REFRIGERACION', 'TAPAS MOTOR'),
    'PRENSA CLUTH CON DISCOS': ('MOTOR', 'EMBRAGUE', 'PRENSA CLUTCH'),
    'DISCOS CLUTCH': ('MOTOR', 'EMBRAGUE', 'DISCOS CLUTCH'),
    'EJE CRANK COMPLETO': ('MOTOR', 'ARRANQUE MECANICO', 'EJE CRANK'),
    'PEDAL CAMBIOS-CRANK- EJE SALIDA': ('MOTOR', 'ARRANQUE MECANICO', 'PEDAL CRANK'),
    'KIT EMPAQUES CTO': ('MOTOR', 'EMPAQUES', 'JUEGO EMPAQUES COMPLETO'),
    'EMPAQUES ANILLO EXOSTO': ('MOTOR', 'EMPAQUES', 'EMPAQUE EXOSTO'),
    'KIT RETENEDORES MOTOR': ('MOTOR', 'EMPAQUES', 'KIT RETENEDORES'),
    'MOFLE': ('MOTOR', 'SISTEMA DE ESCAPE', 'MOFLE'),
    'VALVULA PAIR': ('MOTOR', 'SISTEMA DE ESCAPE', 'VALVULA PAIR'),
    # SISTEMA: CHASIS Y FRENOS
    'PASTILLAS DE FRENO DELANTERAS HLK': ('CHASIS Y FRENOS', 'FRENOS', 'PASTILLAS DE FRENO'),
    'BANDAS FRENO TRASERO': ('CHASIS Y FRENOS', 'FRENOS', 'BANDAS DE FRENO'),
    'DISCO FRENO DELANTERO': ('CHASIS Y FRENOS', 'FRENOS', 'DISCO DE FRENO'),
    'BOMBA FRENO -CILINDRO FRENO': ('CHASIS Y FRENOS', 'FRENOS', 'BOMBA DE FRENO'),
    'CILINDRO FRENO TRASERO': ('CHASIS Y FRENOS', 'FRENOS', 'CILINDRO DE FRENO'),
    'PERA FRENOS': ('CHASIS Y FRENOS', 'FRENOS', 'PERA DE FRENO'),
    'DEPOSITO LIQUIDO FRENO': ('CHASIS Y FRENOS', 'FRENOS', 'DEPOSITO LIQUIDO'),
    'KIT MORDAZA': ('CHASIS Y FRENOS', 'FRENOS', 'MORDAZA'),
    'TREN DELANTERO CARGUERO': ('CHASIS Y FRENOS', 'SUSPENSION Y DIRECCION', 'TREN DELANTERO'),
    'SUSPENSION TRASERA': ('CHASIS Y FRENOS', 'SUSPENSION Y DIRECCION', 'AMORTIGUADOR'),
    'KIT CUNAS': ('CHASIS Y FRENOS', 'SUSPENSION Y DIRECCION', 'CUNAS DE DIRECCION'),
    'MANUBRIO': ('CHASIS Y FRENOS', 'SUSPENSION Y DIRECCION', 'MANUBRIO'),
    'GUARDA BARRO DELANTERO METALICO': ('CHASIS Y FRENOS', 'CARROCERIA', 'GUARDABARRO'),
    'ESPEJOS / VARIOS': ('CHASIS Y FRENOS', 'CARROCERIA', 'ESPEJOS'),
    'CHAPAS COMPUERTA': ('CHASIS Y FRENOS', 'CARROCERIA', 'CHAPAS'),
    'SOPORTE MOTOR': ('CHASIS Y FRENOS', 'CARROCERIA', 'SOPORTE MOTOR'),
    'RIN': ('CHASIS Y FRENOS', 'RUEDAS', 'RIN'),
    'CAMPANA DELANTERA': ('CHASIS Y FRENOS', 'RUEDAS', 'CAMPANA'),
    # SISTEMA: TRANSMISION
    'CAJA DE CAMBIOS': ('TRANSMISION', 'CAJA DE CAMBIOS', 'CAJA DE CAMBIOS'),
    'KIT HORQUILLAS': ('TRANSMISION', 'CAJA DE CAMBIOS', 'HORQUILLAS'),
    'EJE CAMBIOS': ('TRANSMISION', 'CAJA DE CAMBIOS', 'EJE DE CAMBIOS'),
    'PEDAL CAMBIOS': ('TRANSMISION', 'CAJA DE CAMBIOS', 'PEDAL DE CAMBIOS'),
    'SELECTOR DE CAMBIOS': ('TRANSMISION', 'CAJA DE CAMBIOS', 'SELECTOR'),
    'CAJA DIFERENCIAL': ('TRANSMISION', 'REVERSA Y DIFERENCIAL', 'CAJA DIFERENCIAL'),
    'CAJA REVERSA': ('TRANSMISION', 'REVERSA Y DIFERENCIAL', 'CAJA REVERSA'),
    'CAJA DE CAMBIOS-REVERSA': ('TRANSMISION', 'REVERSA Y DIFERENCIAL', 'PIÑONES REVERSA'),
    'PIÑON REVERSA': ('TRANSMISION', 'REVERSA Y DIFERENCIAL', 'PIÑON REVERSA'),
    'TOMA FUERZA': ('TRANSMISION', 'REVERSA Y DIFERENCIAL', 'TOMA FUERZA'),
    'UNION REVERSA': ('TRANSMISION', 'REVERSA Y DIFERENCIAL', 'UNION REVERSA'),
    'KIT PIÑONES DELANTERO/TRASERO': ('TRANSMISION', 'TRANSMISION FINAL', 'KIT ARRASTRE'),
    'PIÑON SALIDA': ('TRANSMISION', 'TRANSMISION FINAL', 'PIÑON SALIDA'),
    'CRUCETAS CARGUERO': ('TRANSMISION', 'TRANSMISION FINAL', 'CRUCETAS'),
    'EJE SALIDA': ('TRANSMISION', 'TRANSMISION FINAL', 'EJE SALIDA'),
    'PARTES DE SCOOTER-AGILLITY/DINAMIC': ('TRANSMISION', 'SCOOTER', 'VARIADOR'),
    'CORREAS DISTRIBUCION': ('TRANSMISION', 'SCOOTER', 'CORREA'),
    'ZAPATAS': ('TRANSMISION', 'SCOOTER', 'ZAPATAS CLUTCH SCOOTER'),
    'CENTRIFUGA': ('TRANSMISION', 'SCOOTER', 'CENTRIFUGO'),
    'ROLEX': ('TRANSMISION', 'SCOOTER', 'RODILLOS VARIADOR'),
    'ANTIVIBRANTES': ('TRANSMISION', 'SCOOTER', 'ANTIVIBRANTES'),
    # SISTEMA: ELECTRICO
    'CDI': ('SISTEMA ELECTRICO', 'ENCENDIDO Y CARGA', 'CDI'),
    'BOBINA DE ALTA CON CAPUCHON': ('SISTEMA ELECTRICO', 'ENCENDIDO Y CARGA', 'BOBINA DE ALTA'),
    'CAPUCHON BUJIA': ('SISTEMA ELECTRICO', 'ENCENDIDO Y CARGA', 'CAPUCHON BUJIA'),
    'BUJIA': ('SISTEMA ELECTRICO', 'ENCENDIDO Y CARGA', 'BUJIA'),
    'BOBINA PULSORA': ('SISTEMA ELECTRICO', 'ENCENDIDO Y CARGA', 'BOBINA PULSORA'),
    'STATOR -CORONA ENCENDIDO': ('SISTEMA ELECTRICO', 'ENCENDIDO Y CARGA', 'ESTATOR'),
    'VOLANTE': ('SISTEMA ELECTRICO', 'ENCENDIDO Y CARGA', 'VOLANTE'),
    'REGULADOR': ('SISTEMA ELECTRICO', 'ENCENDIDO Y CARGA', 'REGULADOR'),
    'REGULADOR TRIFASICO': ('SISTEMA ELECTRICO', 'ENCENDIDO Y CARGA', 'REGULADOR TRIFASICO'),
    'MOTOR ARRANQUE': ('SISTEMA ELECTRICO', 'ARRANQUE ELECTRICO', 'MOTOR ARRANQUE'),
    'ESCOBILLAS CON BASE': ('SISTEMA ELECTRICO', 'ARRANQUE ELECTRICO', 'ESCOBILLAS ARRANQUE'),
    'RELAY UNIVERSAL': ('SISTEMA ELECTRICO', 'ARRANQUE ELECTRICO', 'RELAY ARRANQUE'),
    'KIT PIÑON ARRANQUE': ('SISTEMA ELECTRICO', 'ARRANQUE ELECTRICO', 'PIÑON ARRANQUE'),
    'BENDIX-ONE WAY': ('SISTEMA ELECTRICO', 'ARRANQUE ELECTRICO', 'BENDIX'),
    'PARTES ELETRICAS COMANDOS': ('SISTEMA ELECTRICO', 'LUCES Y COMANDOS', 'COMANDOS'),
    'SWICHES': ('SISTEMA ELECTRICO', 'LUCES Y COMANDOS', 'SWICHES'),
    'SWICH ENCENDIDO': ('SISTEMA ELECTRICO', 'LUCES Y COMANDOS', 'SWICH ENCENDIDO'),
    'KIT SWICH': ('SISTEMA ELECTRICO', 'LUCES Y COMANDOS', 'KIT SWICHES'),
    'FLASHER ELETRONICO': ('SISTEMA ELECTRICO', 'LUCES Y COMANDOS', 'FLASHER'),
    'LUCES LED': ('SISTEMA ELECTRICO', 'LUCES Y COMANDOS', 'STOP LED'),
    'BOMBILLOS': ('SISTEMA ELECTRICO', 'LUCES Y COMANDOS', 'STOP BOMBILLO'),
    'INDICADOR CAMBIOS': ('SISTEMA ELECTRICO', 'LUCES Y COMANDOS', 'INDICADOR CAMBIOS'),
    'PITO': ('SISTEMA ELECTRICO', 'SENSORES Y OTROS', 'PITO'),
    'SISTEMA ELECTRICO': ('SISTEMA ELECTRICO', 'CABLEADO', 'ARNES ELECTRICO'),
    'GUAYAS / VARIOS': ('SISTEMA ELECTRICO', 'CABLEADO', 'GUAYAS'),
    'CAJA VELOCIMETRO': ('SISTEMA ELECTRICO', 'SENSORES Y OTROS', 'CAJA VELOCIMETRO'),
    'PIÑON VELOCIMETRO': ('SISTEMA ELECTRICO', 'SENSORES Y OTROS', 'PIÑON VELOCIMETRO'),
    'CHOQUE ELECTRIC': ('SISTEMA ELECTRICO', 'SENSORES Y OTROS', 'CHOQUE ELECTRICO'),
    'CHOQUE ELETRICO': ('SISTEMA ELECTRICO', 'SENSORES Y OTROS', 'CHOQUE ELECTRICO'),
    # FALLBACK
    'BALINERAS ESPECIALES': ('MOTOR', 'TREN ALTERNATIVO', 'BALINERAS'),
    'KIT BALINERA MOTOR': ('MOTOR', 'TREN ALTERNATIVO', 'BALINERAS'),
    'TAPON DE TIEMPO': ('MOTOR', 'BLOQUE MOTOR', 'TAPON TIEMPO'),
    'CARCAZA VOLANTE': ('MOTOR', 'BLOQUE MOTOR', 'CARCASA'),
    'CANASTILLA': ('MOTOR', 'TREN ALTERNATIVO', 'CANASTILLA'),
    'IMPULSADORES': ('MOTOR', 'DISTRIBUCION', 'IMPULSORES'),
    'BASE C/BALANCINES': ('MOTOR', 'CULATA', 'BALANCINES'),
    'MOTOR DE CARGUERO': ('MOTOR', 'MOTOR COMPLETO', 'MOTOR COMPLETO'),
    'KIT RETENEDORES': ('ACCESORIOS Y OTROS', 'RETENEDORES', 'RETENEDORES'),
    'TAPA GASOLINA': ('ACCESORIOS Y OTROS', 'CARROCERIA', 'TAPA GASOLINA'),
    'MANIGUETA CON BASE COMPLETA': ('CHASIS Y FRENOS', 'FRENOS', 'MANIGUETA'),
    'Varios Motos': ('ACCESORIOS Y OTROS', 'VARIOS', 'VARIOS'),
    'Varios Carguero': ('ACCESORIOS Y OTROS', 'VARIOS', 'VARIOS')
}

# --- Palabras clave ---
MOTO_KEYWORDS = ['PULSAR', 'BWS', 'AGILITY', 'SCOOTER', 'NKD', 'FZ', 'LIBERO', 'BOXER', 'GS', 'GN', 'JET', 'EVO', 'TTR', 'AKT', 'YAMAHA', 'HONDA', 'SUZUKI', 'KYMCO', 'FLEX', 'CRIPTON', 'BEST', 'VIVA', 'BIZ']
MOTOCARGUERO_KEYWORDS = ['CARGUERO', '3W', 'AYCO', 'VAISAND', 'MOTOCARRO', 'TORITO', 'BAJAJ', 'ZH', 'CERONTE', 'SIGMA']
CAPITALIZE_WORDS = ['AKT', 'AYCO', 'KYMCO', 'BWS', 'NKD', 'SLR', 'TTR', 'CGR', 'CG', 'CDI', 'LED', 'OEM', 'KAIQI', 'PULSAR', 'FZ', 'GN', 'GS', 'BAJAJ', 'VAISAND', 'UM']
STOP_WORDS = ['CAJA', 'X10', 'JUEGO', 'KIT', 'PAR', 'UNIDAD', 'ORIGINAL', 'TIPO', 'OEM', 'KAIQI', 'REPUESTO', 'DALU', 'SMG', 'HLK', 'TWOM', 'KAY', 'CHO', 'KET', 'MN', 'MV', 'EOM', 'CTO', 'COMPL', 'REF', 'GENERICO', 'PARA', 'CON', 'DE']

# --- 2. Funciones de Limpieza y Formato ---
def clean_text_for_matching(text):
    text = str(text).upper()
    text = text.replace('Ã±', 'Ñ').replace('Ã', 'N')
    for word in STOP_WORDS:
        text = text.replace(word, '')
    text = re.sub(r'[^A-Z0-9\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

def format_title(text):
    text = str(text).title() 
    for word in CAPITALIZE_WORDS:
        text = re.sub(r'\b' + re.escape(word.title()) + r'\b', word, text, flags=re.IGNORECASE)
    # Corrección de caracteres
    text = text.replace('ã±', 'ñ').replace('ã¡', 'á').replace('ã©', 'é').replace('ã­', 'í').replace('ã³', 'ó').replace('ãº', 'ú')
    text = text.replace('Ã±', 'ñ').replace('Ã³', 'ó').replace('Ã¡', 'á').replace('Ã©', 'é').replace('Ã­', 'í').replace('Ãº', 'ú').replace('Ã‘', 'Ñ')
    return text

def get_tipo_vehiculo(desc):
    desc_upper = str(desc).upper()
    if any(keyword in desc_upper for keyword in MOTOCARGUERO_KEYWORDS):
        return "MOTOCARGUERO"
    if any(keyword in desc_upper for keyword in MOTO_KEYWORDS):
        return "MOTO"
    return "MOTOCARGUERO" # Default

# --- 3. Cargar Bases de Datos ---
try:
    print("1. Cargando inventario KAIQI (420 productos)...")
    df_kaiqi = pd.read_csv(KAIQI_INVENTARIO, sep=';', dtype=str, encoding='utf-8-sig')
    
    print("2. Cargando base de datos de competencia (904 productos)...")
    df_competencia = pd.read_csv(COMPETENCIA_DB, dtype=str)
    
    print("   -> Pre-procesando esencias de Competencia...")
    df_competencia['query_clean'] = df_competencia['Nombre_Externo'].apply(clean_text_for_matching)
    choices = df_competencia['query_clean'].dropna().tolist()
    choice_map = {}
    for i, row in df_competencia.iterrows():
        choice_map[row['query_clean']] = (row['Nombre_Externo'], row['Imagen_Externa'])

except Exception as e:
    print(f"❌ Error fatal cargando archivos: {e}")
    exit()

print(f"3. Iniciando Enriquecimiento y Propagación de Taxonomía...")

# Preparamos el DF KAIQI con las columnas finales
df_kaiqi['CODIGO NEW'] = ""
df_kaiqi['Descripcion_Rica'] = ""
df_kaiqi['Nivel_Confianza'] = 0
df_kaiqi['Sistema Principal'] = ""
df_kaiqi['Subsistema'] = ""
df_kaiqi['Componente'] = ""
df_kaiqi['Tipo Vehiculo'] = ""

matches_taxonomia = 0
matches_fuzzy = 0
codigo_new_counters = {}

# --- 4. Bucle de Enriquecimiento (Los 420 productos) ---
for index, row in df_kaiqi.iterrows():
    sku = str(row['SKU'])
    categoria_kaiqi_orig = str(row['Categoria']).upper().strip()
    
    # --- PASO A: PROPAGAR TAXONOMÍA (LÓGICA ENCICLOPEDIA) ---
    if categoria_kaiqi_orig in TAXONOMY_MAP:
        matches_taxonomia += 1
        mapa = TAXONOMY_MAP[categoria_kaiqi_orig]
        df_kaiqi.at[index, 'Sistema Principal'] = mapa[0]
        df_kaiqi.at[index, 'Subsistema'] = mapa[1]
        df_kaiqi.at[index, 'Componente'] = mapa[2]
    else:
        # Fallback (Si KAIQI tiene una categoría rara no mapeada)
        df_kaiqi.at[index, 'Sistema Principal'] = "ACCESORIOS Y OTROS"
        df_kaiqi.at[index, 'Subsistema'] = "VARIOS"
        df_kaiqi.at[index, 'Componente'] = categoria_kaiqi_orig.title()

    # --- PASO B: ENRIQUECER DESCRIPCIÓN (FUZZY MATCH) ---
    query = clean_text_for_matching(f"{row['Categoria']} {row['Descripcion']}")
    best_match = process.extractOne(query, choices, scorer=fuzz.token_set_ratio, score_cutoff=85)
    
    desc_final = ""
    if best_match:
        matches_fuzzy += 1
        nombre_esencia_match, score = best_match[0], best_match[1]
        desc_rica = choice_map[nombre_esencia_match][0]
        
        desc_final = format_title(desc_rica)
        df_kaiqi.at[index, 'Descripcion_Rica'] = desc_final
        df_kaiqi.at[index, 'Nivel_Confianza'] = score
    else:
        desc_final = format_title(row['Descripcion'])
        df_kaiqi.at[index, 'Descripcion_Rica'] = desc_final
        
    # --- PASO C: REFINAR TIPO VEHICULO ---
    df_kaiqi.at[index, 'Tipo Vehiculo'] = get_tipo_vehiculo(desc_final)
    
    # --- PASO D: GENERAR CODIGO NEW (PREFIJOS) ---
    pref1 = df_kaiqi.at[index, 'Sistema Principal'][:3].upper()
    pref2 = df_kaiqi.at[index, 'Subsistema'][:3].upper()
    pref3 = df_kaiqi.at[index, 'Componente'][:3].upper()
    
    pref_full = f"{pref1}-{pref2}-{pref3}"
    if pref_full not in codigo_new_counters:
        codigo_new_counters[pref_full] = 0
    codigo_new_counters[pref_full] += 1
    
    df_kaiqi.at[index, 'CODIGO NEW'] = f"{pref_full}-{codigo_new_counters[pref_full]:03d}"

# --- 5. LIMPIEZA Y GUARDADO FINAL ---
print("5. Guardando archivo final...")

columnas_finales = [
    'CODIGO NEW', 'SKU', 'Descripcion_Rica', 'Precio',
    'Sistema Principal', 'Subsistema', 'Componente', 'Tipo Vehiculo',
    'Categoria', 'Descripcion' # Dejamos las originales como referencia
]
df_final = df_kaiqi[columnas_finales]
df_final = df_final.rename(columns={'Descripcion_Rica': 'Descripcion'})

df_final.to_csv(OUTPUT_INVENTARIO_ENRIQUECIDO, index=False, sep=';', encoding='utf-8-sig')

print("\n" + "="*50)
print(f"✅ ¡PROYECTO DE TAXONOMÍA FINALIZADO!")
print(f"   -> {OUTPUT_INVENTARIO_ENRIQUECIDO}")
print(f"   -> {len(df_final)} productos procesados.")
print(f"   -> {matches_taxonomia} productos mapeados con la taxonomía de la Enciclopedia.")
print(f"   -> {matches_fuzzy} descripciones enriquecidas desde la competencia.")
print("="*50)