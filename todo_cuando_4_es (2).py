import sqlite3
import pandas as pd
import os

# Configuración de rutas
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\todo_cuando_4_es.csv'

# Lista de tablas a incluir
tablas = [
    'cuando_4_es_unidad',
    'cuando_4_es_decena',
    'cuando_4_es_centena',
    'cuando_4_es_umil',
    'cuando_4_es_d_y_u',
    'cuando_4_es_c_y_u',
    'cuando_4_es_um_y_u',
    'cuando_4_es_c_y_d',
    'cuando_4_es_um_y_d',
    'cuando_4_es_um_y_c',
    'cuando_4_es_c_d_y_u',
    'cuando_4_es_um_c_d_y_u',
    'cuando_4_es_um_c_y_d',
    'cuando_4_es_um_c_y_u',
    'cuando_4_es_um_d_y_u',
]

# Conexión a la base de datos
conn = sqlite3.connect(DB_PATH)

# Lista para almacenar DataFrames
dfs = []

for tabla in tablas:
    try:
        df = pd.read_sql_query(f"SELECT * FROM {tabla}", conn)
        df["origen"] = tabla  # Añadir columna para saber de qué tabla vino
        dfs.append(df)
    except Exception as e:
        print(f"⚠️ Error al procesar {tabla}: {e}")

# Unir todos los DataFrames y eliminar duplicados
if dfs:
    combinado = pd.concat(dfs, ignore_index=True).drop_duplicates()
    combinado.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')
    print(f"✅ Archivo generado con todas las combinaciones: {OUTPUT_FILE}")
else:
    print("❌ No se pudo generar el archivo: ninguna tabla fue leída correctamente.")

# Cerrar conexión
conn.close()
