import pandas as pd
import re
import os

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\scrap"
ARCHIVO_ENTRADA = "CATALOGO NOVIEMBRE V01-2025 NF.xlsx"
ARCHIVO_SALIDA = "Base_Datos_Catalogo_Noviembre_REFINED.csv"

ruta_entrada = os.path.join(BASE_DIR, ARCHIVO_ENTRADA)
ruta_salida = os.path.join(BASE_DIR, ARCHIVO_SALIDA)

def limpiar_precio(texto):
    """Limpia símbolos y puntos de precios."""
    if pd.isna(texto): return 0
    t = str(texto).replace('$', '').replace('.', '').replace(',', '').replace(' ', '')
    try:
        return int(t)
    except:
        return 0

def limpiar_texto(texto):
    """Elimina saltos de línea y espacios extra."""
    if pd.isna(texto): return ""
    t = str(texto).replace('\n', ' ').replace('\r', '')
    return " ".join(t.split()).strip()

def limpiar_catalogo_v2():
    print(f"--- LIMPIEZA MAESTRA V2 (CORRECCIÓN PRECIOS): {ARCHIVO_ENTRADA} ---")
    
    if not os.path.exists(ruta_entrada):
        print(f"❌ No encuentro {ruta_entrada}")
        return

    try:
        print("   ⏳ Leyendo archivo Excel...")
        dict_dfs = pd.read_excel(ruta_entrada, sheet_name=None, header=None)
        df = pd.concat(dict_dfs.values(), ignore_index=True)
        print(f"   ✅ Excel cargado. Total filas: {len(df)}")
    except Exception as e:
        print(f"❌ Error leyendo Excel: {e}")
        return

    productos_limpios = []
    categoria_actual = "GENERAL"
    
    print("   🔍 Analizando filas con lógica financiera...")
    
    for index, row in df.iterrows():
        valores = [str(v).strip() for v in row.values if pd.notna(v) and str(v).strip() != '']
        
        if not valores: continue
        
        # 1. DETECTAR CATEGORÍA
        if len(valores) == 1 and len(valores[0]) > 4 and valores[0].isupper() and not re.search(r'\d', valores[0]):
            categoria_actual = valores[0]
            continue

        # 2. DETECTAR PRODUCTO
        codigo = ""
        descripcion = ""
        precio_final = 0
        
        # Buscar código (0xxxx o 5 dígitos)
        for v in valores:
            if re.match(r'^0\d{4,5}$', v) or re.match(r'^\d{5}$', v):
                codigo = v
                break
        
        if codigo:
            # Remover código de la lista para analizar el resto
            otros_valores = [v for v in valores if v != codigo]
            
            # Buscar Precio (El número más alto o con $)
            candidatos_precio = []
            candidatos_texto = []
            
            for v in otros_valores:
                # Si tiene $ es precio seguro
                if '$' in v:
                    candidatos_precio.append(limpiar_precio(v))
                # Si es solo números, evaluamos
                elif re.match(r'^[\d\.,]+$', v):
                    valor = limpiar_precio(v)
                    # Filtro Anti-Cantidad: Si es < 500 pesos, probablemente es cantidad (X1, X10) o basura
                    if valor > 500: 
                        candidatos_precio.append(valor)
                else:
                    # Es texto (descripción o empaque X1)
                    if not re.match(r'^X\d+$', v, re.IGNORECASE): # Ignorar "X1", "X10"
                        candidatos_texto.append(v)
            
            # Elegir el mejor precio (el mayor encontrado)
            if candidatos_precio:
                precio_final = max(candidatos_precio)
            
            # Elegir la mejor descripción (la más larga)
            if candidatos_texto:
                # A veces la descripción se parte en dos celdas, las unimos
                # Pero cuidado con mezclar con "UND", "PAR"
                desc_parts = [t for t in candidatos_texto if len(t) > 3]
                descripcion = " ".join(desc_parts)
                descripcion = limpiar_texto(descripcion)
            
            if descripcion and precio_final > 0:
                productos_limpios.append({
                    "Codigo": codigo,
                    "Descripcion": descripcion,
                    "Precio": precio_final,
                    "Categoria_Inferida": categoria_actual,
                    "Fuente": "CATALOGO_NOVIEMBRE_XLSX_V2"
                })

    # Guardar
    if productos_limpios:
        df_final = pd.DataFrame(productos_limpios)
        df_final.drop_duplicates(subset=['Codigo'], inplace=True)
        
        df_final.to_csv(ruta_salida, index=False, sep=';', encoding='utf-8-sig')
        
        print("\n" + "="*50)
        print(f"✅ LIMPIEZA V2 COMPLETADA")
        print(f"   Productos Válidos (Con Precio): {len(df_final)}")
        print(f"   Archivo Mejorado: {ARCHIVO_SALIDA}")
        print("="*50)
    else:
        print("⚠️ No se encontraron productos válidos.")

if __name__ == "__main__":
    limpiar_catalogo_v2()