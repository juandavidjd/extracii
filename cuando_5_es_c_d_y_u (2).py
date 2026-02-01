import sqlite3
import pandas as pd

# Rutas de configuración
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\cuando_5_es_c_d_y_u.csv'
TABLE_NAME = 'sexto_resumen_matriz_aslu'

# Conexión a la base de datos
conn = sqlite3.connect(DB_PATH)

# Consulta SQL para filtrar c_5, d_5 y u_5 = 1
query = f"""
    SELECT fecha, numero, c_5, d_5, u_5
    FROM {TABLE_NAME}
    WHERE c_5 = 1 AND d_5 = 1 AND u_5 = 1
"""

# Ejecutar consulta y exportar resultados
df = pd.read_sql_query(query, conn)
df.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')

# Cierre de la conexión
conn.close()

print(f"✅ Archivo generado: {OUTPUT_FILE}")
