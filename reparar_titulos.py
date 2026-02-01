import pandas as pd
import os
import re

# --- CONFIGURACIÓN ---
PROJECT_DIR = r'C:\KAIQI_PROYECTO_FINAL'
INPUT_FILE = os.path.join(PROJECT_DIR, 'Inventario_FINAL_CON_TAXONOMIA.csv')
OUTPUT_FILE = os.path.join(PROJECT_DIR, 'Inventario_FINAL_CON_TAXONOMIA.csv') # Sobrescribimos para corregir

# Palabras para forzar mayúsculas
CAPITALIZE_WORDS = ['AKT', 'AYCO', 'KYMCO', 'BWS', 'NKD', 'SLR', 'TTR', 'CGR', 'CG', 'CDI', 'LED', 'OEM', 'KAIQI', 'PULSAR', 'FZ', 'GN', 'GS', 'BAJAJ', 'VAISAND', 'UM', '3W', 'CTO', 'MN', 'MV']

print("--- SCRIPT DE RESTAURACIÓN Y LIMPIEZA (Corrección de Error) ---")

def polish_text(text):
    if pd.isna(text): return ""
    text = str(text)
    # 1. Corregir encoding
    text = text.replace('Ã±', 'ñ').replace('Ã³', 'ó').replace('Ã¡', 'á').replace('Ã©', 'é').replace('Ã­', 'í').replace('Ãº', 'ú').replace('Ã‘', 'Ñ')
    # 2. Reemplazar caracteres separadores por espacios
    text = re.sub(r'[/\()+*-]', ' ', text)
    # 3. Quitar caracteres extraños
    text = re.sub(r'[^A-Z0-9\sñáéíóú\.]', '', text, flags=re.IGNORECASE)
    # 4. Formato Título
    text = text.title()
    # 5. Corregir Marcas
    for word in CAPITALIZE_WORDS:
        text = re.sub(r'\b' + re.escape(word.title()) + r'\b', word, text, flags=re.IGNORECASE)
    # 6. Espacios
    text = re.sub(r'\s+', ' ', text).strip()
    return text

try:
    print(f"1. Cargando {INPUT_FILE}...")
    df = pd.read_csv(INPUT_FILE, sep=';', encoding='utf-8-sig', dtype=str)
    
    print(f"   -> Total productos: {len(df)}")
    
    # Verificamos que exista la columna original
    col_original = 'Descripcion.1'
    if col_original not in df.columns:
        print("⚠️ ¡ALERTA! No encuentro 'Descripcion.1'. Buscando 'Descripcion_Original_KAIQI'...")
        if 'Descripcion_Original_KAIQI' in df.columns:
            col_original = 'Descripcion_Original_KAIQI'
        else:
             # Si no está, usamos 'Descripcion' asumiendo que es lo que hay, pero limpiamos
             col_original = 'Descripcion'
    
    print(f"   -> Restaurando datos desde: {col_original}")

    count_restaurados = 0
    for index, row in df.iterrows():
        # 1. Obtener datos originales
        desc_original = str(row[col_original])
        componente = str(row['Componente'])
        
        # 2. Limpiar la descripción original
        desc_limpia = polish_text(desc_original)
        componente_limpio = polish_text(componente)
        
        # 3. Construir Título Inteligente
        # Si la descripción original YA contiene el componente, no lo repetimos
        # Ej: Componente="Motor", Desc="Motor de Carguero" -> "Motor de Carguero" (No "Motor Motor de Carguero")
        if componente_limpio.lower() in desc_limpia.lower():
            titulo_final = desc_limpia
        else:
            titulo_final = f"{componente_limpio} {desc_limpia}"
            
        # 4. Asignar
        df.at[index, 'Descripcion'] = titulo_final
        count_restaurados += 1
        
    print(f"2. Guardando archivo corregido...")
    df.to_csv(OUTPUT_FILE, index=False, sep=';', encoding='utf-8-sig')
    
    print("\n" + "="*50)
    print(f"✅ RESTAURACIÓN COMPLETADA")
    print(f"   -> Se corrigieron {count_restaurados} descripciones usando tu data original.")
    print(f"   -> Los textos ahora están limpios y legibles (sin / - *).")
    print(f"   -> Archivo: {OUTPUT_FILE}")
    print("="*50)

except Exception as e:
    print(f"❌ Error: {e}")