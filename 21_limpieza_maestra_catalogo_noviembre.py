import pandas as pd
import re
import os

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\scrap" # O C:\img si moviste el archivo
ARCHIVO_ENTRADA = "CATALOGO NOVIEMBRE V01-2025 NF.xlsx"
ARCHIVO_SALIDA = "Base_Datos_Catalogo_Noviembre_CLEAN.csv"

ruta_entrada = os.path.join(BASE_DIR, ARCHIVO_ENTRADA)
ruta_salida = os.path.join(BASE_DIR, ARCHIVO_SALIDA)

def limpiar_catalogo_noviembre():
    print(f"--- LIMPIANDO CATÁLOGO MAESTRO: {ARCHIVO_ENTRADA} ---")
    
    if not os.path.exists(ruta_entrada):
        print(f"❌ No encuentro {ruta_entrada}")
        return

    # Leer Excel (Leemos todas las hojas porque el usuario dijo que tiene 166 tablas)
    # Si es un solo archivo con muchas hojas, esto las une.
    try:
        print("   ⏳ Leyendo archivo Excel (esto puede tardar)...")
        # Leer todas las hojas a la vez (sheet_name=None devuelve un dict de dataframes)
        dict_dfs = pd.read_excel(ruta_entrada, sheet_name=None, header=None)
        
        # Unir todas las hojas en un solo DataFrame gigante
        df = pd.concat(dict_dfs.values(), ignore_index=True)
        print(f"   ✅ Excel cargado. Total filas crudas: {len(df)}")
        
    except Exception as e:
        print(f"❌ Error leyendo Excel: {e}")
        return

    productos_limpios = []
    categoria_actual = "GENERAL"
    
    # Iterar filas
    print("   🔍 Procesando y limpiando datos...")
    for index, row in df.iterrows():
        # Convertir fila a lista de strings limpios
        valores = [str(v).strip() for v in row.values if pd.notna(v) and str(v).strip() != '']
        
        if not valores: continue
        
        # DETECTAR CATEGORÍA (Heurística: Texto en mayúscula solo en la primera columna)
        if len(valores) == 1 and len(valores[0]) > 4 and valores[0].isupper() and not re.search(r'\d', valores[0]):
            categoria_actual = valores[0]
            continue

        # DETECTAR PRODUCTO
        codigo = ""
        descripcion = ""
        precio = ""
        
        # Buscar código (0xxxx o xxxxx)
        for v in valores:
            # Patrones comunes de códigos en este catálogo (empiezan con 0, longitud 5)
            if re.match(r'^0\d{4}$', v) or re.match(r'^\d{5}$', v):
                codigo = v
                break
        
        if codigo:
            # Remover el código para no confundir
            otros_valores = [v for v in valores if v != codigo]
            
            desc_candidatos = [v for v in otros_valores if len(v) > 5 and not re.search(r'\$\s*\d', v)]
            precio_candidatos = [v for v in otros_valores if re.search(r'\d', v) and (len(v) < 10 or '$' in v)]
            
            if desc_candidatos:
                # Tomamos el texto más largo como descripción
                descripcion = max(desc_candidatos, key=len)
            
            if precio_candidatos:
                # Limpiar precio
                p = precio_candidatos[-1]
                precio = re.sub(r'[^\d]', '', p)
            
            if descripcion:
                productos_limpios.append({
                    "Codigo": codigo,
                    "Descripcion": descripcion,
                    "Precio": precio,
                    "Categoria_Inferida": categoria_actual,
                    "Fuente": "CATALOGO_NOVIEMBRE_XLSX"
                })

    # Guardar
    if productos_limpios:
        df_final = pd.DataFrame(productos_limpios)
        # Eliminar duplicados exactos
        df_final.drop_duplicates(subset=['Codigo'], inplace=True)
        
        df_final.to_csv(ruta_salida, index=False, sep=';', encoding='utf-8-sig')
        
        print("\n" + "="*50)
        print(f"✅ LIMPIEZA COMPLETADA")
        print(f"   Productos Rescatados: {len(df_final)}")
        print(f"   Archivo Limpio: {ARCHIVO_SALIDA}")
        print("="*50)
    else:
        print("⚠️ No se encontraron productos válidos.")

if __name__ == "__main__":
    limpiar_catalogo_noviembre()