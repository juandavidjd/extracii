import pandas as pd
import os
import re

# --- CONFIGURACIÓN ---
PROJECT_DIR = r'C:\KAIQI_PROYECTO_FINAL'
SHOPIFY_FILE = os.path.join(PROJECT_DIR, 'Shopify_Import_FINAL.csv')

# Palabras para forzar mayúsculas (las mismas de antes)
CAPITALIZE_WORDS = ['AKT', 'AYCO', 'KYMCO', 'BWS', 'NKD', 'SLR', 'TTR', 'CGR', 'CG', 'CDI', 'LED', 'OEM', 'KAIQI', 'PULSAR', 'FZ', 'GN', 'GS', 'BAJAJ', 'VAISAND', 'UM']

print("--- SCRIPT DE PULIDO FINAL (V9 - Estética) ---")

# --- Función de Limpieza y Formato Profesional ---
def polish_description(text):
    text = str(text)
    
    # 1. Corregir caracteres de encoding (por si acaso)
    text = text.replace('Ã±', 'ñ').replace('Ã³', 'ó').replace('Ã¡', 'á').replace('Ã©', 'é').replace('Ã­', 'í').replace('Ãº', 'ú').replace('Ã‘', 'Ñ')
    
    # 2. Armonizar caracteres: Reemplazar /()*+ por un espacio
    text = re.sub(r'[/\()+*-]', ' ', text)
    
    # 3. Quitar cualquier otro carácter que no sea letra, número o espacio
    text = re.sub(r'[^A-Z0-9\sñáéíóú]', '', text, flags=re.IGNORECASE)
    
    # 4. Aplicar formato "Título" (ej: "Culata De Motor")
    text = text.title()
    
    # 5. Forzar mayúsculas de marcas (ej: "Culata De AKT")
    for word in CAPITALIZE_WORDS:
        text = re.sub(r'\b' + re.escape(word.title()) + r'\b', word, text, flags=re.IGNORECASE)
    
    # 6. Armonizar espacios: colapsar múltiples espacios en uno solo
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

# --- 1. Cargar el archivo de Shopify ---
try:
    print(f"1. Cargando {SHOPIFY_FILE} para pulir...")
    df = pd.read_csv(SHOPIFY_FILE, sep=';', encoding='utf-8-sig', dtype=str)
    print("   -> Archivo cargado.")

except Exception as e:
    print(f"❌ Error fatal cargando archivo: {e}")
    exit()

# --- 2. Aplicar Pulido ---
print("2. Aplicando limpieza de estética a Títulos, HTML y Tags...")

# Columnas que verá el cliente
cols_to_polish = ['Title', 'Body (HTML)', 'Image Alt Text', 'Tags']

for col in cols_to_polish:
    if col in df.columns:
        df[col] = df[col].apply(polish_description)
    else:
        print(f"   -> Advertencia: No se encontró la columna {col}")

# --- 3. Guardar (Sobrescribir) el archivo ---
print(f"3. Guardando archivo pulido: {SHOPIFY_FILE}")
try:
    df.to_csv(SHOPIFY_FILE, index=False, sep=';', encoding='utf-8-sig')
except Exception as e:
    print(f"   -> ❌ ERROR AL GUARDAR. ¿Tienes el archivo abierto en Excel? Ciérralo y reintenta.")
    exit()

print("\n" + "="*50)
print(f"✅ ¡PULIDO COMPLETO!")
print(f"   -> {SHOPIFY_FILE} ha sido actualizado y está listo.")
print("="*50)