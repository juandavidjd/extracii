import pandas as pd
import os
import re  # <--- Faltaba esto, vital para el filtro

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\img"
SCRAP_DIR = r"C:\scrap"

NOMBRE_ARCHIVO = "Inventario_Cliente_NF_Docx_Mejorado.csv"
ARCHIVO_SALIDA = os.path.join(BASE_DIR, "Inventario_Cliente_NF_FINAL_CLEAN.csv")

# Palabras que identifican a los "Stickers" o Basura
PALABRAS_BASURA = [
    "Teléfonos:", "Despachos:", "MARCA REGISTRADA", "Guadalajara de Buga", 
    "S S REPUESTOS", "Cartera:", "Ventas:", "Página", "Carrera"
]

def cargar_csv_robusto(ruta):
    """Intenta cargar con UTF-8, si falla usa Latin-1."""
    try:
        print(f"   Intentando leer {ruta} con UTF-8...")
        return pd.read_csv(ruta, sep=';', quotechar='"', encoding='utf-8-sig')
    except UnicodeDecodeError:
        print(f"   ⚠️ UTF-8 falló. Intentando con Latin-1 (ANSI)...")
        return pd.read_csv(ruta, sep=';', quotechar='"', encoding='latin-1')
    except Exception as e:
        print(f"   ❌ Error de lectura: {e}")
        return None

def limpiar_nf():
    print("--- INICIANDO LIMPIEZA DE DATA NF (ARMVALLE) V2 ---")
    
    # 1. Buscar el archivo (en img o en scrap)
    ruta_final = os.path.join(BASE_DIR, NOMBRE_ARCHIVO)
    if not os.path.exists(ruta_final):
        ruta_scrap = os.path.join(SCRAP_DIR, NOMBRE_ARCHIVO)
        if os.path.exists(ruta_scrap):
            print(f"   ✅ Archivo encontrado en: {ruta_scrap}")
            ruta_final = ruta_scrap
        else:
            print(f"❌ NO ENCUENTRO EL ARCHIVO: {NOMBRE_ARCHIVO}")
            print(f"   Por favor muévelo a C:\\img o C:\\scrap")
            return

    # 2. Cargar DataFrame
    df = cargar_csv_robusto(ruta_final)
    if df is None: return

    total_inicial = len(df)
    print(f"📦 Registros Iniciales: {total_inicial}")

    # 3. Filtro por Palabras Basura (Regex)
    # Escapamos caracteres especiales para evitar errores de regex
    patron = '|'.join([re.escape(p) for p in PALABRAS_BASURA])
    
    # Filtramos filas que NO (~) contienen el patrón
    # 'na=False' trata los valores vacíos como "no match" para no borrar de más
    df_limpio = df[~df['Descripcion'].str.contains(patron, case=False, na=False, regex=True)]
    
    # 4. Filtro por Longitud y Precios Sueltos
    # Eliminamos filas que empiezan con "$" (son precios sueltos del PDF)
    df_limpio = df_limpio[~df_limpio['Descripcion'].str.strip().str.startswith('$')]
    
    # Eliminamos descripciones muy cortas (menos de 8 caracteres)
    df_limpio = df_limpio[df_limpio['Descripcion'].str.len() > 8]

    total_final = len(df_limpio)
    eliminados = total_inicial - total_final
    
    # 5. Guardar Resultado Limpio
    df_limpio.to_csv(ARCHIVO_SALIDA, index=False, encoding='utf-8-sig')

    print("\n" + "="*50)
    print(f"✅ LIMPIEZA COMPLETADA")
    print(f"   Registros Eliminados (Ruido): {eliminados}")
    print(f"   Productos Reales Listos: {total_final}")
    print(f"   Archivo Guardado: {ARCHIVO_SALIDA}")
    print("="*50)

if __name__ == "__main__":
    limpiar_nf()