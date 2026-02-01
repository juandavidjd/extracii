import pandas as pd

# Nombre del archivo corregido
FILE_FIXED = 'LISTADO_KAIQI_CORREGIDO.csv'

print("--- VERIFICACIÓN DE REGISTROS CORREGIDOS ---\n")

try:
    # Leemos el archivo corregido
    df = pd.read_csv(FILE_FIXED, sep=';', header=None, encoding='latin-1', dtype=str)
    df.columns = ['Vacio', 'SKU', 'Descripcion', 'Categoria', 'Precio']
    
    # Filtramos los SKUs que terminan en -A o -B
    mask = df['SKU'].str.endswith(('-A', '-B'), na=False)
    df_filtered = df[mask]
    
    # Mostramos en formato tabla
    print(df_filtered[['SKU', 'Descripcion', 'Precio']].to_string(index=False))
    
except Exception as e:
    print(f"Error leyendo el archivo: {e}")