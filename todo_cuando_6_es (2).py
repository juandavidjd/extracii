import sqlite3
import pandas as pd
import os

# Configuración
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\todo_cuando_6_es.csv'

# Lista de tablas que contienen las combinaciones
tablas = [
    'cuando_6_es_unidad',
    'cuando_6_es_decena',
    'cuando_6_es_centena',
    'cuando_6_es_umil',
    'cuando_6_es_d_y_u',
    'cuando_6_es_c_y_u',
    'cuando_6_es_um_y_u',
    'cuando_6_es_c_y_d',
    'cuando_6_es_um_y_d',
    'cuando_6_es_um_y_c',
    'cuando_6_es_c_d_y_u',
    'cuando_6_es_um_c_d_y_u',
    'cuando_6_es_um_c_y_d',
    'cuando_6_es_um_c_y_u',
    'cuando_6_es_um_d_y_u'
]

# Conexión a la base de datos
conn = sqlite3.connect(DB_PATH)

# Lista para almacenar los DataFrames
dataframes = []

# Cargar y almacenar los datos de cada tabla
for tabla in tablas:
    try:
        df = pd.read_sql_query(f"SELECT * FROM {tabla}", conn)
        df['origen'] = tabla  # Añadir columna de origen
        dataframes.append(df)
    except Exception as e:
        print(f"⚠️ Error al procesar {tabla}: {e}")

# Concatenar todos los DataFrames si hay alguno válido
if dataframes:
    df_total = pd.concat(dataframes, ignore_index=True)
    df_total.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')
    print(f"✅ Archivo generado con todas las combinaciones: {OUTPUT_FILE}")
else:
    print("❌ No se generó el archivo. No se encontraron tablas válidas.")

# Cierre de conexión
conn.close()
