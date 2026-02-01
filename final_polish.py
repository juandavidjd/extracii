import pandas as pd
import numpy as np

# --- CONFIGURACIÓN ---
INPUT_FILE = 'Inventario_KAIQI_Maestro_Final.csv'
OUTPUT_FILE = 'Inventario_KAIQI_Shopify_Ready.csv'
CLOUDINARY_BASE = "https://res.cloudinary.com/dhegu1fzm/image/upload/"

print("--- INICIANDO LIMPIEZA FINAL Y GENERACIÓN DE URLs ---")

# 1. CARGAR EL ARCHIVO MAESTRO
print(f"1. Leyendo {INPUT_FILE}...")
try:
    df = pd.read_csv(INPUT_FILE)
except FileNotFoundError:
    print(f"❌ Error: No se encuentra el archivo {INPUT_FILE}. Asegúrate de haber corrido el paso anterior.")
    exit()

# 2. LIMPIEZA DE DESCRIPCIONES (Quitar espacios extra)
print("2. Puliendo descripciones (eliminando espacios basura)...")

def limpiar_espacios(texto):
    if pd.isna(texto): return ""
    # ' '.join(texto.split()) hace magia: convierte "HOLA    MUNDO  " en "HOLA MUNDO"
    return ' '.join(str(texto).split())

# Aplicamos la limpieza a la columna Descripcion
df['Descripcion'] = df['Descripcion'].apply(limpiar_espacios)


# 3. GENERACIÓN DE URLs DE CLOUDINARY
print("3. Generando enlaces de imágenes...")

def generar_url(row):
    # Filtros: Solo generamos URL si es Existente o Huérfano, Y si tiene un nombre de imagen válido
    grupos_con_imagen = ['Existente (Actualizado)', 'Huérfano (Solo en Shopify)']
    imagen = str(row['Imagen']).strip()
    
    if row['Origen_Dato'] in grupos_con_imagen and imagen.lower() != 'sin imagen' and imagen != 'nan':
        # Concatenamos la base con el nombre del archivo
        return f"{CLOUDINARY_BASE}{imagen}"
    
    return "" # Dejamos vacío para los productos nuevos sin foto

df['Imagen_URL'] = df.apply(generar_url, axis=1)


# 4. EXPORTAR ARCHIVO FINAL
print(f"4. Guardando archivo definitivo: {OUTPUT_FILE}...")
# Reordenamos las columnas para que Imagen_URL quede visible
cols = ['SKU', 'Descripcion', 'Precio', 'Categoria', 'Imagen', 'Imagen_URL', 'Origen_Dato']
df_final = df[cols]

df_final.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')

print("\n" + "="*50)
print(f"✅ PROCESO TERMINADO. Archivo listo: {OUTPUT_FILE}")
print("="*50)

# Muestra de validación
print("\nEjemplo de cómo quedó (Primeras 3 filas con URL):")
con_url = df_final[df_final['Imagen_URL'] != ''].head(3)
print(con_url[['SKU', 'Descripcion', 'Imagen_URL']].to_string(index=False))

print("\nEjemplo de limpieza de texto (Primeras 3 filas):")
print(df_final[['SKU', 'Descripcion']].head(3).to_string(index=False))