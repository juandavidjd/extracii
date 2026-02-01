import sqlite3
import pandas as pd
import os

# Configuración
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\todo_cuando_5_es.csv'

# Listado de tablas que contienen las combinaciones
tablas = [
    'cuando_5_es_unidad',
    'cuando_5_es_decena',
    'cuando_5_es_centena',
    'cuando_5_es_umil',
    'cuando_5_es_d_y_u',
    'cuando_5_es_c_y_u',
    'cuando_5_es_um_y_u',
    'cuando_5_es_c_y_d',
    'cuando_5_es_um_y_d',
    'cuando_5_es_um_y_c',
    'cuando_5_es_c_d_y_u',
    'cuando_5_es_um_c_d_y_u',
    'cuando_5_es_um_c_y_d',
    'cuando_5_es_um_c_y_u',
    'cuando_5_es_um_d_y_u'
]

# Conexión a la base de datos
conn = sqlite3.connect(DB_PATH)

# Lista para almacenar los DataFrames cargados
dataframes = []

# Cargar cada tabla si existe
for tabla in tablas:
    try:
        query = f"SELECT * FROM {tabla}"
        df = pd.read_sql_query(query, conn)
        df['origen'] = tabla  # Agrega columna de origen para trazabilidad
        dataframes.append(df)
        print(f"✅ Tabla añadida: {tabla}")
    except Exception as e:
        print(f"⚠️ Error al procesar {tabla}: {e}")

# Combinar todos los DataFrames
if dataframes:
    df_final = pd.concat(dataframes, ignore_index=True).drop_duplicates()
    df_final.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')
    print(f"\n✅ Archivo generado con todas las combinaciones: {OUTPUT_FILE}")
else:
    print("❌ No se generó el archivo. No se encontró ninguna tabla válida.")

# Cerrar conexión
conn.close()
