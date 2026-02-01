import pandas as pd
import os

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\img"
ARCHIVO_ENTRADA = os.path.join(BASE_DIR, "Inventario_Cliente_NF_GOLDEN.csv")
ARCHIVO_SALIDA = os.path.join(BASE_DIR, "Inventario_Cliente_NF_PLATINUM.csv")

def limpieza_platinum():
    print("--- PULIDO FINAL (PLATINUM) ---")
    
    if not os.path.exists(ARCHIVO_ENTRADA):
        print(f"❌ No encuentro: {ARCHIVO_ENTRADA}")
        return

    # Cargar
    try:
        df = pd.read_csv(ARCHIVO_ENTRADA, sep=';', encoding='utf-8-sig', on_bad_lines='skip')
    except:
        # Fallback encoding
        df = pd.read_csv(ARCHIVO_ENTRADA, sep=';', encoding='latin-1', on_bad_lines='skip')

    total_inicial = len(df)
    print(f"📦 Total Inicial: {total_inicial}")

    # 1. Eliminar filas donde 'Imagen_Final' esté vacía
    # Esto borra todos los textos sueltos que no son productos
    df_limpio = df.dropna(subset=['Imagen_Final'])
    
    # 2. Eliminar filas donde 'Imagen_Final' no parezca una imagen
    # (Debe terminar en .jpg, .jpeg, .png)
    df_limpio = df_limpio[df_limpio['Imagen_Final'].str.contains(r'\.(jpg|jpeg|png|webp)$', case=False, na=False)]

    # 3. Eliminar filas residuales de encabezados
    # A veces queda texto como "COD. DESCRIPCION" en la columna descripción
    df_limpio = df_limpio[~df_limpio['Descripcion'].str.contains("COD. DESCRIPCION", case=False, na=False)]

    # 4. Resetear índice
    df_limpio.reset_index(drop=True, inplace=True)

    total_final = len(df_limpio)
    eliminados = total_inicial - total_final
    
    # Guardar
    df_limpio.to_csv(ARCHIVO_SALIDA, index=False, sep=',', encoding='utf-8-sig')

    print("\n" + "="*50)
    print(f"✨ LIMPIEZA PLATINUM COMPLETADA")
    print(f"   Basura Eliminada: {eliminados}")
    print(f"   Productos Perfectos: {total_final}")
    print(f"   Archivo Final: {os.path.basename(ARCHIVO_SALIDA)}")
    print("="*50)

if __name__ == "__main__":
    limpieza_platinum()