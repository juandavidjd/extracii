import pandas as pd
import os

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\img"
ARCHIVO_ENTRADA = os.path.join(BASE_DIR, "Inventario_Cliente_NF_Docx_Mejorado.csv")
ARCHIVO_SALIDA = os.path.join(BASE_DIR, "Inventario_Cliente_NF_FINAL_CLEAN.csv")

# Palabras que identifican a los "Stickers" o Basura
PALABRAS_BASURA = [
    "Teléfonos:", "Despachos:", "MARCA REGISTRADA", "Guadalajara de Buga", 
    "S S REPUESTOS", "Cartera:", "Ventas:", "$", "Página"
]

def limpiar_nf():
    print("--- INICIANDO LIMPIEZA DE DATA NF (ARMVALLE) ---")
    
    if not os.path.exists(ARCHIVO_ENTRADA):
        print(f"❌ No encuentro: {ARCHIVO_ENTRADA}")
        # Intenta buscarlo en C:\scrap por si acaso no lo moviste
        alt_path = r"C:\scrap\Inventario_Cliente_NF_Docx_Mejorado.csv"
        if os.path.exists(alt_path):
            print(f"   ✅ Encontrado en scrap, usándolo...")
            df = pd.read_csv(alt_path, sep=';', quotechar='"', encoding='utf-8-sig')
        else:
            return
    else:
        df = pd.read_csv(ARCHIVO_ENTRADA, sep=';', quotechar='"', encoding='utf-8-sig')

    total_inicial = len(df)
    print(f"📦 Registros Iniciales: {total_inicial}")

    # 1. Filtro por Palabras Basura
    # Creamos una expresión regular que busca cualquiera de las palabras basura
    patron = '|'.join([re.escape(p) for p in PALABRAS_BASURA])
    import re
    
    # Mantenemos solo las filas que NO contienen basura
    # Usamos na=False para que no falle si hay celdas vacías
    df_limpio = df[~df['Descripcion'].str.contains(patron, case=False, na=False)]
    
    # 2. Filtro por Longitud (Descripciones muy cortas suelen ser errores)
    df_limpio = df_limpio[df_limpio['Descripcion'].str.len() > 10]

    total_final = len(df_limpio)
    eliminados = total_inicial - total_final
    
    # Guardar
    df_limpio.to_csv(ARCHIVO_SALIDA, index=False, encoding='utf-8-sig')

    print("\n" + "="*50)
    print(f"✅ LIMPIEZA COMPLETADA")
    print(f"   Basura Eliminada (Stickers): {eliminados}")
    print(f"   Productos Reales Listos: {total_final}")
    print(f"   Archivo Limpio: {os.path.basename(ARCHIVO_SALIDA)}")
    print("="*50)

if __name__ == "__main__":
    limpiar_nf()