import pandas as pd
import re
import os

# --- CONFIGURACIÓN DE ARCHIVOS ---
INPUT_FILE = 'Base_Datos_Competencia_Maestra.csv' 
OUTPUT_FILE = 'Base_Datos_Competencia_Maestra_ULTRA_LIMPIA.csv'

# --- LISTA DE EXCLUSIÓN (Filtro de Marcas de Carros/Ruido) ---
EXCLUSION_KEYWORDS = [
    'CHEVROLET', 'TOYOTA', 'NISSAN', 'FORD', 'MAZDA', 'KIA', 'HYUNDAI', 'RENAULT',
    'SPARK', 'SAIL', 'DODGE', 'MITSUBISHI', 'JEEP', 
    'CAMIONETA', 'AUTOMOVIL', 'SUV', 'HOGAR', 'COCINA', 'ESCRITORIO'
]

# --- LISTA DE INCLUSIÓN (Filtro de Enciclopedia/Componentes KAIQI) ---
# Términos técnicos validados del mapa de taxonomía V8
KAIQI_COMPONENTS = [
    'CULATA', 'EMPAQUE', 'VALVULA', 'GUIA', 'SELLO', 'BALANCIN', 'ARBOL', 'CADENILLA', 'TENSOR', 
    'CILINDRO', 'PISTON', 'ANILLO', 'BIELA', 'CIGÜEÑAL', 'CARBURADOR', 'CONECTOR', 'BAQUELA', 
    'FILTRO', 'LLAVE GASOLINA', 'BOMBA', 'RADIADOR', 'VENTILADOR', 'TERMOSTATO', 'TANQUE', 
    'SENSOR', 'TAPA', 'PRENSA', 'DISCO', 'CLUTCH', 'EJE', 'CRANK', 'PEDAL', 'MOFLE', 
    'PASTILLAS', 'BANDAS', 'MORDAZA', 'TREN', 'AMORTIGUADOR', 'CUNA', 'MANUBRIO', 'GUARDABARRO', 
    'ESPEJO', 'CHAPA', 'SOPORTE', 'RIN', 'CAMPANA', 'HORQUILLA', 'SELECTOR', 'DIFERENCIAL', 
    'REVERSA', 'PIÑON', 'CRUCETA', 'VARIADOR', 'CORREA', 'ZAPATA', 'CENTRIFUGO', 'RODILLO', 
    'ANTIVIBRANTE', 'CDI', 'BOBINA', 'CAPUCHON', 'BUJIA', 'ESTATOR', 'VOLANTE', 'REGULADOR', 
    'ESCOBILLA', 'RELAY', 'BENDIX', 'COMANDO', 'SWICH', 'FLASHER', 'LUZ', 'BOMBILLO', 
    'INDICADOR', 'PITO', 'ARNES', 'GUAYA', 'VELOCIMETRO', 'CHOQUE', 'BALINERA', 'RETENEDOR',
    'CANASTILLA', 'IMPULSOR', 'MANIGUETA'
]

# --- FUNCIÓN DE UTILIDAD: LIMPIEZA DE NOMBRES DE COLUMNAS ---
def clean_column_names(df):
    """Limpia los nombres de las columnas de espacios, saltos de línea y BOM."""
    df.columns = df.columns.str.replace(r'\s+', ' ', regex=True).str.strip()
    df.columns = df.columns.str.strip('\ufeff') # Quitar BOM (Byte Order Mark)
    return df

def clean_and_filter():
    print(f"1. Cargando archivo: {INPUT_FILE}")
    df_comp = None
    
    # --- LECTURA ROBUSTA: INTENTAR ; LUEGO , ---
    for delimiter in [';', ',']:
        try:
            # Leer con el delimitador actual, forzando la primera fila como header
            df_comp = pd.read_csv(INPUT_FILE, delimiter=delimiter, encoding='utf-8')
            # Intentar limpiar columnas inmediatamente después de la carga
            df_comp = clean_column_names(df_comp)
            # Intentar acceder a la columna clave. Si falla, probar el siguiente delimitador
            if 'Nombre_Externo' in df_comp.columns:
                print(f"   -> Delimitador '{delimiter}' detectado con éxito.")
                break
            else:
                df_comp = None # Reiniciar si la columna no se encuentra
        except Exception:
            df_comp = None # Continuar si la lectura falla
            
    if df_comp is None:
        print(f"❌ ERROR FATAL: No se pudo cargar '{INPUT_FILE}'. Confirma que el archivo existe y que los delimitadores son ';' o ','.")
        return

    initial_count = len(df_comp)
    
    # --- APLICAR FILTROS ---
    print(f"2. Aplicando filtros de Exclusión (Carros) e Inclusión (Enciclopedia)...")

    # Crear columna limpia para la comparación (si no existe, lo cual no debería ocurrir aquí)
    if 'Nombre_Limpio' not in df_comp.columns:
        df_comp['Nombre_Limpio'] = df_comp['Nombre_Externo'].astype(str).str.upper()

    # PASO 1: FILTRO DE EXCLUSIÓN (Carros/Ruido)
    exclusion_pattern = '|'.join(EXCLUSION_KEYWORDS)
    df_comp_filtered = df_comp[~df_comp['Nombre_Limpio'].str.contains(exclusion_pattern, na=False)]
    
    # PASO 2: FILTRO DE INCLUSIÓN (Enciclopedia/Componentes)
    inclusion_pattern = '|'.join(KAIQI_COMPONENTS)
    df_comp_final = df_comp_filtered[df_comp_filtered['Nombre_Limpio'].str.contains(inclusion_pattern, na=False)]

    final_count = len(df_comp_final)
    
    # --- RESULTADOS Y GUARDADO ---
    print(f"3. Limpieza finalizada. Total inicial: {initial_count}. Total final: {final_count}")

    # Eliminar la columna temporal y guardar el archivo final
    df_comp_final = df_comp_final.drop(columns=['Nombre_Limpio'])
    df_comp_final.to_csv(OUTPUT_FILE, index=False)

    print(f"✅ ¡Archivo {OUTPUT_FILE} creado con éxito en tu ambiente local con {final_count} productos!")

if __name__ == "__main__":
    clean_and_filter()