import sqlite3
import pandas as pd

# Rutas de configuración
DB_PATH = r'C:\RadarPremios\radar_premios.db'
OUTPUT_FILE = r'C:\RadarPremios\data\limpio\cuando_6_es_um_c_y_u.csv'
TABLE_NAME = 'septimo_resumen_matriz_aslu'

# Conexión a la base de datos
conn = sqlite3.connect(DB_PATH)

# Consulta SQL
query = f"""
    SELECT fecha, numero, um_6, c_6, u_6
    FROM {TABLE_NAME}
    WHERE um_6 = 1 AND c_6 = 1 AND u_6 = 1
"""

# Ejecutar consulta y exportar a CSV
df = pd.read_sql_query(query, conn)
df.to_csv(OUTPUT_FILE, sep='\t', index=False, encoding='utf-8')

# Cierre de conexión
conn.close()

print(f"✅ Archivo generado: {OUTPUT_FILE}")
