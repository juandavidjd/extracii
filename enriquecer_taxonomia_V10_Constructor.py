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
OUTPUT_LOG = os.path.join(PROJECT_DIR, 'Log_Enriquecimiento_V10.txt')

# --- 1. MAPA DE TAXONOMÍA (Basado en Enciclopedia y Categorías KAIQI) ---
TAXONOMY_MAP = {
    # SISTEMA: MOTOR
    'CULATA COMPLETA CON VALVULAS': ('MOTOR', 'CULATA', 'Culata Completa'),
    'EMPAQUES TAPA CULATIN ORING': ('MOTOR', 'CULATA', 'Empaque Tapa Culatin'),
    'KIT VALVULAS': ('MOTOR', 'CULATA', 'Valvulas'),
    'GUIA VALVULA': ('MOTOR', 'CULATA', 'Guias de Valvula'),
    'SELLOS DOBLE RESORTE VERDES': ('MOTOR', 'CULATA', 'Sellos de Valvula'),
    'BALANCIN SUPERIOR': ('MOTOR', 'CULATA', 'Balancines'),
    'BASE C/BALANCINES': ('MOTOR', 'CULATA', 'Balancines'),
    'ARBOL LEVAS': ('MOTOR', 'DISTRIBUCION', 'Arbol de Levas'),
    'CADENILLAS': ('MOTOR', 'DISTRIBUCION', 'Cadenilla'),
    'GUIA CADENILLA': ('MOTOR', 'DISTRIBUCION', 'Guias Cadenilla'),
    'TENSOR CADENILLA': ('MOTOR', 'DISTRIBUCION', 'Tensor Cadenilla'),
    'IMPULSADORES': ('MOTOR', 'DISTRIBUCION', 'Impulsores'),
    'KIT CILINDRO EOM': ('MOTOR', 'TREN ALTERNATIVO', 'Cilindro Completo'),
    'KIT PISTONES +ANILLOS': ('MOTOR', 'TREN ALTERNATIVO', 'Piston y Anillos'),
    'KIT ANILLOS': ('MOTOR', 'TREN ALTERNATIVO', 'Anillos'),
    'KIT BIELA+CANASTILLA': ('MOTOR', 'TREN ALTERNATIVO', 'Biela'),
    'CIGÜEÑAL+BALINERA': ('MOTOR', 'TREN ALTERNATIVO', 'Cigüeñal'),
    'CANASTILLA': ('MOTOR', 'TREN ALTERNATIVO', 'Canastilla'),
    'BALINERAS ESPECIALES': ('MOTOR', 'TREN ALTERNATIVO', 'Balineras'),
    'KIT BALINERA MOTOR': ('MOTOR', 'TREN ALTERNATIVO', 'Balineras'),
    'CARBURADORES': ('MOTOR', 'ALIMENTACION', 'Carburador'),
    'CONECTOR CARBURADOR': ('MOTOR', 'ALIMENTACION', 'Conector Carburador'),
    'BAQUELA CARBURADOR': ('MOTOR', 'ALIMENTACION', 'Baquela Carburador'),
    'FILTRO DE AIRE': ('MOTOR', 'ALIMENTACION', 'Filtro de Aire'),
    'CAJA FILTROS': ('MOTOR', 'ALIMENTACION', 'Caja Filtro'),
    'LLAVE GASOLINA': ('MOTOR', 'ALIMENTACION', 'Llave Gasolina'),
    'BOMBA ACEITE': ('MOTOR', 'LUBRICACION', 'Bomba de Aceite'),
    'FILTRO ACEITE': ('MOTOR', 'LUBRICACION', 'Filtro de Aceite'),
    'FILTRO CENTRIFUGO': ('MOTOR', 'LUBRICACION', 'Filtro Centrifugo'),
    'RADIADOR': ('MOTOR', 'REFRIGERACION', 'Radiador'),
    'VENTILADOR': ('MOTOR', 'REFRIGERACION', 'Ventilador'),
    'BASE VENTILADOR': ('MOTOR', 'REFRIGERACION', 'Base Ventilador'),
    'BOMBA AGUA': ('MOTOR', 'REFRIGERACION', 'Bomba de Agua'),
    'TERMOSTATO': ('MOTOR', 'REFRIGERACION', 'Termostato'),
    'TANQUE AGUA': ('MOTOR', 'REFRIGERACION', 'Tanque Auxiliar'),
    'TROMPO TEMPERATURA': ('MOTOR', 'REFRIGERACION', 'Sensor Temperatura'),
    'TAPAS REFRIGERANTE DE MOTOR': ('MOTOR', 'REFRIGERACION', 'Tapas Motor'),
    'PRENSA CLUTH CON DISCOS': ('MOTOR', 'EMBRAGUE', 'Prensa Clutch'),
    'DISCOS CLUTCH': ('MOTOR', 'EMBRAGUE', 'Discos Clutch'),
    'EJE CRANK COMPLETO': ('MOTOR', 'ARRANQUE MECANICO', 'Eje Crank'),
    'PEDAL CAMBIOS-CRANK- EJE SALIDA': ('MOTOR', 'ARRANQUE MECANICO', 'Pedal Crank'),
    'KIT EMPAQUES CTO': ('MOTOR', 'EMPAQUES', 'Juego Empaques Completo'),
    'EMPAQUES ANILLO EXOSTO': ('MOTOR', 'EMPAQUES', 'Empaque Exosto'),
    'KIT RETENEDORES MOTOR': ('MOTOR', 'EMPAQUES', 'Kit Retenedores'),
    'MOFLE': ('MOTOR', 'SISTEMA DE ESCAPE', 'Mofle'),
    'VALVULA PAIR': ('MOTOR', 'SISTEMA DE ESCAPE', 'Valvula PAIR'),
    'TAPON DE TIEMPO': ('MOTOR', 'BLOQUE MOTOR', 'Tapon Tiempo'),
    'CARCAZA VOLANTE': ('MOTOR', 'BLOQUE MOTOR', 'Carcasa'),
    'MOTOR DE CARGUERO': ('MOTOR', 'MOTOR COMPLETO', 'Motor Completo'),
    'PIÑON PRIMARIO': ('MOTOR', 'DISTRIBUCION', 'Piñon Primario'),
    # SISTEMA: CHASIS Y FRENOS
    'PASTILLAS DE FRENO DELANTERAS HLK': ('CHASIS Y FRENOS', 'FRENOS', 'Pastillas de Freno'),
    'BANDAS FRENO TRASERO': ('CHASIS Y FRENOS', 'FRENOS', 'Bandas de Freno'),
    'DISCO FRENO DELANTERO': ('CHASIS Y FRENOS', 'FRENOS', 'Disco de Freno'),
    'BOMBA FRENO -CILINDRO FRENO': ('CHASIS Y FRENOS', 'FRENOS', 'Bomba de Freno'),
    'CILINDRO FRENO TRASERO': ('CHASIS Y FRENOS', 'FRENOS', 'Cilindro de Freno'),
    'PERA FRENOS': ('CHASIS Y FRENOS', 'FRENOS', 'Pera de Freno'),
    'DEPOSITO LIQUIDO FRENO': ('CHASIS Y FRENOS', 'FRENOS', 'Deposito Liquido'),
    'KIT MORDAZA': ('CHASIS Y FRENOS', 'FRENOS', 'Mordaza'),
    'MANIGUETA CON BASE COMPLETA': ('CHASIS Y FRENOS', 'FRENOS', 'Manigueta'),
    'TREN DELANTERO CARGUERO': ('CHASIS Y FRENOS', 'SUSPENSION Y DIRECCION', 'Tren Delantero'),
    'SUSPENSION TRASERA': ('CHASIS Y FRENOS', 'SUSPENSION Y DIRECCION', 'Amortiguador'),
    'KIT CUNAS': ('CHASIS Y FRENOS', 'SUSPENSION Y DIRECCION', 'Cunas de Direccion'),
    'MANUBRIO': ('CHASIS Y FRENOS', 'SUSPENSION Y DIRECCION', 'Manubrio'),
    'GUARDA BARRO DELANTERO METALICO': ('CHASIS Y FRENOS', 'CARROCERIA', 'Guardabarro'),
    'ESPEJOS / VARIOS': ('CHASIS Y FRENOS', 'CARROCERIA', 'Espejos'),
    'CHAPAS COMPUERTA': ('CHASIS Y FRENOS', 'CARROCERIA', 'Chapas'),
    'SOPORTE MOTOR': ('CHASIS Y FRENOS', 'CARROCERIA', 'Soporte Motor'),
    'TAPA GASOLINA': ('CHASIS Y FRENOS', 'CARROCERIA', 'Tapa Gasolina'),
    'RIN': ('CHASIS Y FRENOS', 'RUEDAS', 'Rin'),
    'CAMPANA DELANTERA': ('CHASIS Y FRENOS', 'RUEDAS', 'Campana'),
    # SISTEMA: TRANSMISION
    'CAJA DE CAMBIOS': ('TRANSMISION', 'CAJA DE CAMBIOS', 'Caja de Cambios'),
    'KIT HORQUILLAS': ('TRANSMISION', 'CAJA DE CAMBIOS', 'Horquillas'),
    'EJE CAMBIOS': ('TRANSMISION', 'CAJA DE CAMBIOS', 'Eje de Cambios'),
    'PEDAL CAMBIOS': ('TRANSMISION', 'CAJA DE CAMBIOS', 'Pedal de Cambios'),
    'SELECTOR DE CAMBIOS': ('TRANSMISION', 'CAJA DE CAMBIOS', 'Selector'),
    'CAJA DIFERENCIAL': ('TRANSMISION', 'REVERSA Y DIFERENCIAL', 'Caja Diferencial'),
    'CAJA REVERSA': ('TRANSMISION', 'REVERSA Y DIFERENCIAL', 'Caja Reversa'),
    'CAJA DE CAMBIOS-REVERSA': ('TRANSMISION', 'REVERSA Y DIFERENCIAL', 'Piñones Reversa'),
    'PIÑON REVERSA': ('TRANSMISION', 'REVERSA Y DIFERENCIAL', 'Piñon Reversa'),
    'TOMA FUERZA': ('TRANSMISION', 'REVERSA Y DIFERENCIAL', 'Toma Fuerza'),
    'UNION REVERSA': ('TRANSMISION', 'REVERSA Y DIFERENCIAL', 'Union Reversa'),
    'KIT PIÑONES DELANTERO/TRASERO': ('TRANSMISION', 'TRANSMISION FINAL', 'Kit Arrastre'),
    'PIÑON SALIDA': ('TRANSMISION', 'TRANSMISION FINAL', 'Piñon Salida'),
    'CRUCETAS CARGUERO': ('TRANSMISION', 'TRANSMISION FINAL', 'Crucetas'),
    'EJE SALIDA': ('TRANSMISION', 'TRANSMISION FINAL', 'Eje Salida'),
    'PARTES DE SCOOTER-AGILLITY/DINAMIC': ('TRANSMISION', 'SCOOTER', 'Variador'),
    'CORREAS DISTRIBUCION': ('TRANSMISION', 'SCOOTER', 'Correa'),
    'ZAPATAS': ('TRANSMISION', 'SCOOTER', 'Zapatas Clutch Scooter'),
    'CENTRIFUGA': ('TRANSMISION', 'SCOOTER', 'Centrifugo'),
    'ROLEX': ('TRANSMISION', 'SCOOTER', 'Rodillos Variador'),
    'ANTIVIBRANTES': ('TRANSMISION', 'SCOOTER', 'Antivibrantes'),
    # SISTEMA: ELECTRICO
    'CDI': ('SISTEMA ELECTRICO', 'ENCENDIDO Y CARGA', 'CDI'),
    'BOBINA DE ALTA CON CAPUCHON': ('SISTEMA ELECTRICO', 'ENCENDIDO Y CARGA', 'Bobina de Alta'),
    'CAPUCHON BUJIA': ('SISTEMA ELECTRICO', 'ENCENDIDO Y CARGA', 'Capuchon Bujia'),
    'BUJIA': ('SISTEMA ELECTRICO', 'ENCENDIDO Y CARGA', 'Bujia'),
    'BOBINA PULSORA': ('SISTEMA ELECTRICO', 'ENCENDIDO Y CARGA', 'Bobina Pulsora'),
    'STATOR -CORONA ENCENDIDO': ('SISTEMA ELECTRICO', 'ENCENDIDO Y CARGA', 'Estator'),
    'VOLANTE': ('SISTEMA ELECTRICO', 'ENCENDIDO Y CARGA', 'Volante'),
    'REGULADOR': ('SISTEMA ELECTRICO', 'ENCENDIDO Y CARGA', 'Regulador'),
    'REGULADOR TRIFASICO': ('SISTEMA ELECTRICO', 'ENCENDIDO Y CARGA', 'Regulador Trifasico'),
    'MOTOR ARRANQUE': ('SISTEMA ELECTRICO', 'ARRANQUE ELECTRICO', 'Motor Arranque'),
    'ESCOBILLAS CON BASE': ('SISTEMA ELECTRICO', 'ARRANQUE ELECTRICO', 'Escobillas Arranque'),
    'RELAY UNIVERSAL': ('SISTEMA ELECTRICO', 'ARRANQUE ELECTRICO', 'Relay Arranque'),
    'KIT PIÑON ARRANQUE': ('SISTEMA ELECTRICO', 'ARRANQUE ELECTRICO', 'Piñon Arranque'),
    'BENDIX-ONE WAY': ('SISTEMA ELECTRICO', 'ARRANQUE ELECTRICO', 'Bendix'),
    'PARTES ELETRICAS COMANDOS': ('SISTEMA ELECTRICO', 'LUCES Y COMANDOS', 'Comandos'),
    'SWICHES': ('SISTEMA ELECTRICO', 'LUCES Y COMANDOS', 'Swiches'),
    'SWICH ENCENDIDO': ('SISTEMA ELECTRICO', 'LUCES Y COMANDOS', 'Swich Encendido'),
    'KIT SWICH': ('SISTEMA ELECTRICO', 'LUCES Y COMANDOS', 'Kit Swiches'),
    'FLASHER ELETRONICO': ('SISTEMA ELECTRICO', 'LUCES Y COMANDOS', 'Flasher'),
    'LUCES LED': ('SISTEMA ELECTRICO', 'LUCES Y COMANDOS', 'Stop Led'),
    'BOMBILLOS': ('SISTEMA ELECTRICO', 'LUCES Y COMANDOS', 'Stop Bombillo'),
    'INDICADOR CAMBIOS': ('SISTEMA ELECTRICO', 'LUCES Y COMANDOS', 'Indicador Cambios'),
    'PITO': ('SISTEMA ELECTRICO', 'SENSORES Y OTROS', 'Pito'),
    'SISTEMA ELECTRICO': ('SISTEMA ELECTRICO', 'CABLEADO', 'Arnes Electrico'),
    'GUAYAS / VARIOS': ('SISTEMA ELECTRICO', 'CABLEADO', 'Guayas'),
    'CAJA VELOCIMETRO': ('SISTEMA ELECTRICO', 'SENSORES Y OTROS', 'Caja Velocimetro'),
    'PIÑON VELOCIMETRO': ('SISTEMA ELECTRICO', 'SENSORES Y OTROS', 'Piñon Velocimetro'),
    'CHOQUE ELECTRIC': ('SISTEMA ELECTRICO', 'SENSORES Y OTROS', 'Choque Electrico'),
    'CHOQUE ELETRICO': ('SISTEMA ELECTRICO', 'SENSORES Y OTROS', 'Choque Electrico'),
    'KIT RETENEDORES': ('ACCESORIOS Y OTROS', 'RETENEDORES', 'Retenedores'),
    'BOMBA FRENO TRASERO UNIVERSAL': ('CHASIS Y FRENOS', 'FRENOS', 'Bomba de Freno')
}

# Palabras clave
MOTO_KEYWORDS = ['PULSAR', 'BWS', 'AGILITY', 'SCOOTER', 'NKD', 'FZ', 'LIBERO', 'BOXER', 'GS', 'GN', 'JET', 'EVO', 'TTR', 'AKT', 'YAMAHA', 'HONDA', 'SUZUKI', 'KYMCO', 'FLEX', 'CRIPTON', 'BEST', 'VIVA', 'BIZ']
MOTOCARGUERO_KEYWORDS = ['CARGUERO', '3W', 'AYCO', 'VAISAND', 'MOTOCARRO', 'TORITO', 'BAJAJ', 'ZH', 'CERONTE', 'SIGMA']
CAPITALIZE_WORDS = ['AKT', 'AYCO', 'KYMCO', 'BWS', 'NKD', 'SLR', 'TTR', 'CGR', 'CG', 'CDI', 'LED', 'OEM', 'KAIQI', 'PULSAR', 'FZ', 'GN', 'GS', 'BAJAJ', 'VAISAND', 'UM']
STOP_WORDS = [
    'CAJA', 'X10', 'JUEGO', 'KIT', 'PAR', 'UNIDAD', 'ORIGINAL', 'TIPO', 'OEM', 'KAIQI', 
    'REPUESTO', 'DALU', 'SMG', 'HLK', 'TWOM', 'KAY', 'CHO', 'KET', 'MN', 'MV', 'EOM', 'CTO', 
    'COMPL', 'REF', 'GENERICO', 'PARA', 'CON', 'DE'
]

# --- 2. Funciones de Limpieza y Formato ---
def clean_text_for_matching(text):
    text = str(text).upper()
    text = text.replace('Ã±', 'Ñ').replace('Ã', 'N')
    for word in STOP_WORDS:
        text = text.replace(word, '')
    text = re.sub(r'[^A-Z0-9\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

def polish_text(text):
    text = str(text)
    # 1. Corregir encoding (importante)
    text = text.replace('Ã±', 'ñ').replace('Ã³', 'ó').replace('Ã¡', 'á').replace('Ã©', 'é').replace('Ã­', 'í').replace('Ãº', 'ú').replace('Ã‘', 'Ñ')
    text = text.replace('ã±', 'ñ').replace('ã¡', 'á').replace('ã©', 'é').replace('ã­', 'í').replace('ã³', 'ó').replace('ãº', 'ú')
    
    # 2. Armonizar caracteres: Reemplazar /()*+ por un espacio
    text = re.sub(r'[/\()+*-]', ' ', text)
    
    # 3. Quitar cualquier otro carácter que no sea letra, número o espacio
    text = re.sub(r'[^A-Z0-9\sñáéíóú]', '', text, flags=re.IGNORECASE)
    
    # 4. Aplicar formato "Título"
    text = text.title()
    
    # 5. Forzar mayúsculas de marcas
    for word in CAPITALIZE_WORDS:
        text = re.sub(r'\b' + re.escape(word.title()) + r'\b', word, text, flags=re.IGNORECASE)
    
    # 6. Armonizar espacios
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def get_tipo_vehiculo(desc, default):
    if default and default not in ["N/A", ""]:
        return default
    desc_upper = str(desc).upper()
    if any(keyword in desc_upper for keyword in MOTOCARGUERO_KEYWORDS):
        return "MOTOCARGUERO"
    if any(keyword in desc_upper for keyword in MOTO_KEYWORDS):
        return "MOTO"
    return "MOTOCARGUERO" # Default

# --- 3. Cargar Bases de Datos ---
try:
    log_file = open(OUTPUT_LOG, 'w', encoding='utf-8')
    print("--- SCRIPT V11: Constructor de Taxonomía y Estética ---")
    
    print("1. Cargando inventario KAIQI (420 productos)...")
    df_kaiqi = pd.read_csv(KAIQI_INVENTARIO, sep=';', dtype=str, encoding='utf-8-sig')
    
    print("2. Cargando 'Catálogo de Perfección' (110 productos)...")
    try:
        df_perfeccion = pd.read_csv(CATALOGO_PERFECCION, sep=';', encoding='latin-1', dtype=str)
    except:
        df_perfeccion = pd.read_csv(CATALOGO_PERFECCION, sep=',', encoding='latin-1', dtype=str)
        
    df_perfeccion = df_perfeccion.applymap(lambda x: str(x).replace('Ã±', 'ñ').replace('Ã³', 'ó').replace('Ã¡', 'á').replace('Ã©', 'é').replace('Ã­', 'í').replace('Ãº', 'ú').replace('Ã‘', 'Ñ'))
    
    # --- CREAR EL MAPA DE TAXONOMÍA (EL CEREBRO) ---
    tax_map = {}
    df_perfeccion_limpio = df_perfeccion.dropna(subset=['CATEGORIA_NORM', 'SISTEMA PRINCIPAL'])
    for index, row in df_perfeccion_limpio.iterrows():
        cat_norm = str(row['CATEGORIA_NORM']).upper().strip()
        if cat_norm not in tax_map:
            tax_map[cat_norm] = (
                row['SISTEMA PRINCIPAL'], row['SUBSISTEMA'], row['COMPONENTE'], row['TIPO VEHICULO']
            )
    print(f"   -> Mapa de Taxonomía (Perfección) creado con {len(tax_map)} reglas.")

    print(f"3. Cargando base de datos de competencia ({os.path.basename(COMPETENCIA_DB)})...")
    df_competencia = pd.read_csv(COMPETENCIA_DB, dtype=str)
    
    print(f"   -> Pre-procesando esencias de Competencia ({len(df_competencia)} productos)...")
    df_competencia['query_clean'] = df_competencia['Nombre_Externo'].apply(clean_text_for_matching)
    choices = df_competencia['query_clean'].dropna().tolist()
    choice_map = {}
    for i, row in df_competencia.iterrows():
        choice_map[row['query_clean']] = row['Nombre_Externo'] # Solo necesitamos el nombre

except Exception as e:
    print(f"❌ Error fatal cargando archivos: {e}")
    log_file.close()
    exit()

print(f"4. Iniciando Enriquecimiento y Propagación...")

# Preparamos el DF KAIQI con las columnas finales
df_kaiqi['CODIGO NEW'] = ""
df_kaiqi['Descripcion_Rica'] = ""
df_kaiqi['Nivel_Confianza'] = 0
# Borramos las columnas de taxonomía viejas (si existían) para re-poblarlas
df_kaiqi['Sistema Principal'] = ""
df_kaiqi['Subsistema'] = ""
df_kaiqi['Componente'] = ""
df_kaiqi['Tipo Vehiculo'] = ""

matches_taxonomia_perfecta = 0
matches_taxonomia_fallback = 0
matches_desc_rica = 0
codigo_new_counters = {}

# --- 4. Bucle de Enriquecimiento (Los 420 productos) ---
for index, row in df_kaiqi.iterrows():
    sku = str(row['SKU'])
    categoria_kaiqi_orig = str(row['Categoria']).upper().strip()
    desc_kaiqi_orig = str(row['Descripcion'])
    
    # --- PASO A: PROPAGAR TAXONOMÍA (LÓGICA HÍBRIDA) ---
    sistema, subsistema, componente, tipo_vehiculo = "ACCESORIOS Y OTROS", "VARIOS", categoria_kaiqi_orig.title(), "N/A"
    
    # Intento 1: Buscar en el mapa de perfección (tu catalogo.csv)
    if categoria_kaiqi_orig in tax_map:
        matches_taxonomia_perfecta += 1
        mapa = tax_map[categoria_kaiqi_orig]
        sistema, subsistema, componente, tipo_vehiculo = mapa[0], mapa[1], mapa[2], mapa[3]
    # Intento 2: Buscar en el mapa de la Enciclopedia (si el primero falla)
    elif categoria_kaiqi_orig in TAXONOMY_MAP:
        matches_taxonomia_fallback += 1
        mapa = TAXONOMY_MAP[categoria_kaiqi_orig]
        sistema, subsistema, componente = mapa[0], mapa[1], mapa[2]
    
    df_kaiqi.at[index, 'Sistema Principal'] = sistema
    df_kaiqi.at[index, 'Subsistema'] = subsistema
    df_kaiqi.at[index, 'Componente'] = componente

    # --- PASO B: ENRIQUECER DESCRIPCIÓN (LÓGICA V9) ---
    query = clean_text_for_matching(f"{categoria_kaiqi_orig} {desc_kaiqi_orig}")
    best_match = process.extractOne(query, choices, scorer=fuzz.token_set_ratio, score_cutoff=85)
    
    desc_final_raw = ""
    if best_match:
        # Intento 1: Usar la descripción rica de la competencia
        matches_fuzzy += 1
        nombre_esencia_match, score = best_match[0], best_match[1]
        desc_final_raw = choice_map[nombre_esencia_match]
        df_kaiqi.at[index, 'Nivel_Confianza'] = score
    else:
        # Intento 2 (Fallback): Construir la descripción
        # Usamos el COMPONENTE (de la taxonomía) + la descripción KAIQI original
        desc_final_raw = f"{componente} {desc_kaiqi_orig}"
        
    # --- PASO C: PULIDO ESTÉTICO ---
    desc_final_pulida = polish_text(desc_final_raw)
    df_kaiqi.at[index, 'Descripcion_Rica'] = desc_final_pulida
        
    # --- PASO D: REFINAR TIPO VEHICULO ---
    df_kaiqi.at[index, 'Tipo Vehiculo'] = get_tipo_vehiculo(desc_final_pulida, tipo_vehiculo)
    
    # --- PASO E: GENERAR CODIGO NEW (PREFIJOS) ---
    pref1 = str(df_kaiqi.at[index, 'Sistema Principal'])[:3].upper()
    pref2 = str(df_kaiqi.at[index, 'Subsistema'])[:3].upper()
    pref3 = str(df_kaiqi.at[index, 'Componente'])[:3].upper()
    
    # Limpiar prefijos de caracteres no-alfabéticos
    pref1 = re.sub(r'[^A-Z]', '', pref1)
    pref2 = re.sub(r'[^A-Z]', '', pref2)
    pref3 = re.sub(r'[^A-Z]', '', pref3)
    
    pref_full = f"{pref1}-{pref2}-{pref3}"
    if pref_full not in codigo_new_counters:
        codigo_new_counters[pref_full] = 0
    codigo_new_counters[pref_full] += 1
    
    df_kaiqi.at[index, 'CODIGO NEW'] = f"{pref_full}-{codigo_new_counters[pref_full]:03d}"

# --- 5. LIMPIEZA Y GUARDADO FINAL ---
print("5. Guardando archivo final (sin imágenes)...")

columnas_finales = [
    'CODIGO NEW', 'SKU', 'Descripcion_Rica', 'Precio',
    'Sistema Principal', 'Subsistema', 'Componente', 'Tipo Vehiculo',
    'Categoria', 'Descripcion' # Dejamos las originales como referencia
]
df_final = df_kaiqi[columnas_finales]
df_final = df_final.rename(columns={
    'Descripcion_Rica': 'Descripcion', 
    'Descripcion':'Descripcion_Original_KAIQI', 
    'Categoria':'Categoria_Original_KAIQI'
})

# Aplicar pulido final a las columnas de taxonomía
df_final['Sistema Principal'] = df_final['Sistema Principal'].apply(polish_text)
df_final['Subsistema'] = df_final['Subsistema'].apply(polish_text)
df_final['Componente'] = df_final['Componente'].apply(polish_text)
df_final['Tipo Vehiculo'] = df_final['Tipo Vehiculo'].apply(polish_text)


df_final.to_csv(OUTPUT_INVENTARIO_ENRIQUECIDO, index=False, sep=';', encoding='utf-8-sig')

log_file.write(f"PROCESO V11 FINALIZADO\n")
log_file.write(f"Total productos procesados: {len(df_final)}\n")
log_file.write(f"Mapeos de Taxonomía (catalogo.csv): {matches_taxonomia_perfecta}\n")
log_file.write(f"Mapeos de Taxonomía (Enciclopedia): {matches_taxonomia_fallback}\n")
log_file.write(f"Descripciones Enriquecidas (Competencia): {matches_fuzzy}\n")
log_file.close()

print("\n" + "="*50)
print(f"✅ ¡PROYECTO DE TAXONOMÍA FINALIZADO!")
print(f"   -> {OUTPUT_INVENTARIO_ENRIQUECIDO}")
print(f"   -> {len(df_final)} productos procesados.")
print(f"   -> {matches_taxonomia_perfecta} productos mapeados con tu 'catalogo.csv'.")
print(f"   -> {matches_taxonomia_fallback} productos mapeados con la 'Enciclopedia'.")
print(f"   -> {matches_fuzzy} descripciones enriquecidas desde la competencia.")
print(f"   -> {len(df_final) - matches_fuzzy} descripciones construidas y pulidas.")
print("="*50)