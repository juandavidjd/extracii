import pandas as pd
import re
import os

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\scrap" # Cambiar a C:\img si moviste el archivo
ARCHIVO_ENTRADA = "CATALOGO NOVIEMBRE V01-2025 NF.xlsx"
ARCHIVO_SALIDA = "Base_Datos_Catalogo_Noviembre_DEEP_MINED.csv"

ruta_entrada = os.path.join(BASE_DIR, ARCHIVO_ENTRADA)
ruta_salida = os.path.join(BASE_DIR, ARCHIVO_SALIDA)

def limpiar_precio(texto):
    if pd.isna(texto): return 0
    # Quitar todo lo que no sea número
    t = re.sub(r'[^\d]', '', str(texto))
    try:
        val = int(t)
        # Filtro heurístico: Un repuesto no vale $1 ni $10. 
        # Asumimos precios > 500 pesos colombianos.
        return val if val > 500 else 0
    except:
        return 0

def limpiar_texto(texto):
    if pd.isna(texto): return ""
    t = str(texto).replace('\n', ' ').replace('\r', '')
    return " ".join(t.split()).strip()

def es_codigo(texto):
    # Patrón: 5 o 6 dígitos, empezando por 0 (común en este catálogo)
    # O formato COD: XXXX
    texto = str(texto).strip()
    match = re.search(r'(?:^|[\s:])(0\d{4,5})(?:$|[\s])', texto)
    if match:
        return match.group(1)
    return None

def limpiar_catalogo_v3_profundo():
    print(f"--- MINERÍA PROFUNDA EXCEL v3: {ARCHIVO_ENTRADA} ---")
    
    if not os.path.exists(ruta_entrada):
        print(f"❌ No encuentro {ruta_entrada}")
        return

    try:
        print("   ⏳ Cargando todas las hojas del Excel...")
        dict_dfs = pd.read_excel(ruta_entrada, sheet_name=None, header=None)
        df = pd.concat(dict_dfs.values(), ignore_index=True)
        print(f"   ✅ Excel cargado. Filas totales: {len(df)}")
    except Exception as e:
        print(f"❌ Error leyendo Excel: {e}")
        return

    productos = []
    categoria_actual = "GENERAL"
    
    # Variables de estado para "mirar atrás"
    ultimo_codigo = ""
    ultima_desc = ""
    
    print("   🔍 Escaneando celdas en busca de patrones...")

    for index, row in df.iterrows():
        valores = [str(v).strip() for v in row.values if pd.notna(v) and str(v).strip() != '']
        if not valores: continue

        # 1. DETECTAR CATEGORÍA
        # Si la fila tiene un solo texto largo en mayúsculas y sin números
        if len(valores) == 1 and len(valores[0]) > 5 and valores[0].isupper() and not re.search(r'\d', valores[0]):
            categoria_actual = valores[0]
            continue

        # 2. ESCANEO DE LA FILA
        codigo_fila = ""
        precio_fila = 0
        textos_fila = []
        
        for v in valores:
            # A. Buscar Código
            cod = es_codigo(v)
            if cod:
                codigo_fila = cod
                # Si la celda tiene más texto que el código, es parte de la descripción
                # Ej: "KIT 04500" -> Desc: "KIT"
                resto = v.replace(cod, "").replace("COD", "").replace(":", "").strip()
                if len(resto) > 3:
                    textos_fila.append(resto)
                continue # Ya procesamos esta celda como código
            
            # B. Buscar Precio
            # Prioridad a celdas con "$"
            if '$' in v:
                p = limpiar_precio(v)
                if p > 0: precio_fila = p
            # Si son solo números y parece precio
            elif re.match(r'^[\d\.,]+$', v):
                p = limpiar_precio(v)
                if p > 500: # Evitar capturar "Cantidad: 1"
                    # Si ya tenemos precio, nos quedamos con el mayor (a veces ponen precio unitario y total)
                    precio_fila = max(precio_fila, p)
            else:
                # C. Es Texto / Descripción
                # Ignorar textos basura comunes
                if v.upper() not in ['PRECIO', 'UND', 'X1', 'X10', 'IMAGEN', 'FOTO', 'EMPAQUE']:
                    textos_fila.append(v)

        # 3. LÓGICA DE FUSIÓN Y RESCATE
        
        # Caso A: Fila Completa (Código + Precio)
        if codigo_fila and precio_fila > 0:
            desc = " ".join(textos_fila)
            # Si no hay descripción en la fila, usar la última vista (raro, pero posible en tablas malformadas)
            if not desc and ultima_desc: desc = ultima_desc
            
            productos.append({
                "Codigo": codigo_fila,
                "Descripcion": desc,
                "Precio": precio_fila,
                "Categoria": categoria_actual,
                "Metodo": "FILA_COMPLETA"
            })
            ultimo_codigo = codigo_fila
            ultima_desc = desc

        # Caso B: Tengo Código pero NO Precio (Mirar siguiente fila en próxima iteración o usar lógica de "Header")
        elif codigo_fila and precio_fila == 0:
            # Guardamos este código "pendiente" en memoria para la siguiente vuelta?
            # Mejor: Lo guardamos con precio 0 y descripción. Si la siguiente fila es solo precio, actualizamos.
            desc = " ".join(textos_fila)
            if not desc and ultima_desc: desc = ultima_desc # Heredar descripción anterior si es una variante
            
            productos.append({
                "Codigo": codigo_fila,
                "Descripcion": desc,
                "Precio": 0, # Pendiente
                "Categoria": categoria_actual,
                "Metodo": "CODIGO_SIN_PRECIO"
            })
            ultimo_codigo = codigo_fila
            if desc: ultima_desc = desc
            
        # Caso C: Tengo Precio pero NO Código (¿Pertenece al anterior?)
        elif not codigo_fila and precio_fila > 0:
            # Si la fila anterior fue "CODIGO_SIN_PRECIO", este precio es suyo.
            if productos and productos[-1]['Precio'] == 0:
                productos[-1]['Precio'] = precio_fila
                productos[-1]['Metodo'] = "PRECIO_RESCATADO"
                # Si esta fila tenía texto, agregarlo a la descripción del anterior
                if textos_fila:
                    productos[-1]['Descripcion'] += " " + " ".join(textos_fila)
            
            # O puede ser una variante del producto anterior (mismo nombre, diferente precio/medida)
            elif productos and ultima_desc:
                # Asumimos que es variante del último producto visto
                # Pero necesitamos un código único. Si no hay, no podemos venderlo.
                # Lo ignoramos por seguridad a menos que encontremos un patrón de código implícito.
                pass

        # Caso D: Solo texto (Descripción multilínea)
        elif not codigo_fila and not precio_fila and textos_fila:
            texto = " ".join(textos_fila)
            if len(texto) > 10:
                # Si el último producto tiene descripción corta o vacía, le sumamos esto
                if productos:
                    productos[-1]['Descripcion'] += " " + texto

    # 4. LIMPIEZA FINAL DE RESULTADOS
    df_final = pd.DataFrame(productos)
    
    if not df_final.empty:
        # Eliminar duplicados de código (quedarse con el último o el más completo)
        df_final.drop_duplicates(subset=['Codigo'], keep='last', inplace=True)
        
        # Limpiar espacios en descripciones
        df_final['Descripcion'] = df_final['Descripcion'].apply(lambda x: limpiar_texto(x))
        
        # Filtrar los que quedaron sin descripción válida
        df_final = df_final[df_final['Descripcion'].str.len() > 3]

        df_final.to_csv(ruta_salida, index=False, sep=';', encoding='utf-8-sig')
        
        print("\n" + "="*50)
        print(f"✅ MINERÍA PROFUNDA COMPLETADA")
        print(f"   Productos Extraídos: {len(df_final)}")
        print(f"   Precios Rescatados (fusión de filas): {len(df_final[df_final['Metodo']=='PRECIO_RESCATADO'])}")
        print(f"   Archivo: {ARCHIVO_SALIDA}")
        print("="*50)
    else:
        print("⚠️ No se pudo extraer data estructurada.")

if __name__ == "__main__":
    limpiar_catalogo_v3_profundo()