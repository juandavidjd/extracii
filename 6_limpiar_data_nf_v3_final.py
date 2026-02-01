import pandas as pd
import os
import re

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\img"
ARCHIVO_ENTRADA = os.path.join(BASE_DIR, "Inventario_Cliente_NF_FINAL_CLEAN.csv")
ARCHIVO_SALIDA = os.path.join(BASE_DIR, "Inventario_Cliente_NF_GOLDEN.csv")

# Lista negra de "Falsos Productos" (Atributos que parecen nombres)
PALABRAS_PROHIBIDAS = [
    "ROJO AZUL", "NEGRO ROJO", "AZUL BLANCO", "DORADO", "PLATEADO", 
    "VERDE", "AMARILLO", "NARANJA", "GRIS", "TRASERO", "DELANTERO",
    "DERECHO", "IZQUIERDO", "JUEGO", "KIT", "PAR", "UND", "UNIDAD"
]

def limpieza_final():
    print("--- LIMPIEZA FINAL (PULIDO) DATA NF ---")
    
    if not os.path.exists(ARCHIVO_ENTRADA):
        print(f"❌ No encuentro: {ARCHIVO_ENTRADA}")
        return

    # Cargar con separador ; que detectamos en el análisis
    try:
        df = pd.read_csv(ARCHIVO_ENTRADA, sep=';', encoding='utf-8-sig', on_bad_lines='skip')
    except:
        df = pd.read_csv(ARCHIVO_ENTRADA, sep=';', encoding='latin-1', on_bad_lines='skip')

    # Eliminar columnas vacías extrañas (Unnamed)
    df = df.dropna(axis=1, how='all')
    
    total_inicial = len(df)
    print(f"📦 Total Inicial: {total_inicial}")

    # 1. Filtro de Longitud Estricto
    # Un nombre de repuesto real difícilmente tiene menos de 10 letras
    # Ej: "BUJIA C70" tiene 9. Seamos cuidadosos. 
    # "ROJO AZUL" tiene 9. Vamos a subir la vara a 10 o filtrar contenido exacto.
    
    # Filtramos filas donde la descripción sea EXACTAMENTE una combinación de colores o atributos
    # Regex para detectar si la cadena es SOLO colores/atributos
    patron_basura = r'^(' + '|'.join(PALABRAS_PROHIBIDAS) + r')[\s\d]*$'
    
    df_limpio = df[~df['Descripcion'].str.match(patron_basura, case=False, na=False)]
    
    # 2. Filtro de Longitud General (Eliminar < 8 chars)
    df_limpio = df_limpio[df_limpio['Descripcion'].str.len() > 7]

    # 3. Filtro de URLs residuales
    df_limpio = df_limpio[~df_limpio['Descripcion'].str.contains("http", case=False, na=False)]

    total_final = len(df_limpio)
    eliminados = total_inicial - total_final
    
    # Guardar el GOLDEN RECORD
    df_limpio.to_csv(ARCHIVO_SALIDA, index=False, sep=',', encoding='utf-8-sig') # Coma para estándar

    print("\n" + "="*50)
    print(f"✨ LIMPIEZA FINAL COMPLETADA")
    print(f"   Basura 'Fina' Eliminada: {eliminados}")
    print(f"   Productos Golden: {total_final}")
    print(f"   Archivo Final: {os.path.basename(ARCHIVO_SALIDA)}")
    print("="*50)

if __name__ == "__main__":
    limpieza_final()