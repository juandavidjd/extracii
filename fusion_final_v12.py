import pandas as pd
import os
import re
import json
from thefuzz import fuzz
from thefuzz import process

# ==============================
# CONFIGURACIÓN
# ==============================
PROJECT_DIR = r'C:\KAIQI_PROYECTO_FINAL'
IMAGE_SOURCE_DIR = os.path.join(PROJECT_DIR, 'FOTOS_COMPETENCIA')
IMAGE_OUTPUT_DIR = os.path.join(PROJECT_DIR, 'IMAGENES_PARA_SHOPIFY')

# Archivos de Entrada
FILE_MASTER = 'Inventario_FINAL_CON_TAXONOMIA.csv'
FILE_AI_CATALOG = 'catalogo_kaiqi_imagenes.csv'

# Archivos de Salida
OUTPUT_SHOPIFY = 'Shopify_Import_Definitivo_V12.csv'
OUTPUT_BAT_RENAME = 'renombrar_imagenes.bat'

# Umbral de Coincidencia (0-100)
SCORE_CUTOFF = 60  # Un poco más flexible ya que cruzamos descripciones humanas vs IA

# ==============================
# FUNCIONES DE UTILIDAD
# ==============================

def clean_text(text):
    """Limpia texto para mejorar el matching."""
    if not isinstance(text, str): return ""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return " ".join(text.split())

def parse_fitment_json(json_str):
    """Convierte el string JSON de la IA en un texto legible de aplicaciones."""
    try:
        if not json_str or pd.isna(json_str): return ""
        data = json.loads(json_str)
        apps = []
        for item in data:
            marca = item.get('marca', '').replace('GENERICA', '').strip()
            modelo = item.get('modelo', '').replace('GENERICA', '').strip()
            cc = item.get('cilindraje', '').replace('desconocido', '').strip()
            
            # Construir string tipo "Suzuki GN 125"
            partes = [p for p in [marca, modelo, cc] if p]
            if partes:
                apps.append(" ".join(partes))
        
        # Eliminar duplicados y unir
        return ", ".join(list(set(apps)))
    except:
        return ""

def generate_seo_handle(title):
    """Genera un handle tipo URL."""
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    return slug.strip('-')

# ==============================
# PROCESO PRINCIPAL
# ==============================

def main():
    print("--- INICIANDO FUSIÓN FINAL V12 (MASTER + IA) ---")

    # 1. Cargar Archivos
    print("1. Cargando bases de datos...")
    try:
        df_master = pd.read_csv(FILE_MASTER, sep=';', encoding='utf-8-sig')
        print(f"   -> Maestro KAIQI cargado: {len(df_master)} productos.")
        
        df_ai = pd.read_csv(FILE_AI_CATALOG, sep=';', encoding='utf-8-sig')
        print(f"   -> Catálogo IA cargado: {len(df_ai)} imágenes analizadas.")
    except Exception as e:
        print(f"❌ Error cargando archivos: {e}")
        return

    # 2. Preparar Datos para Matching
    print("2. Indexando datos de IA para búsqueda...")
    
    # Crear una columna de "Texto Rico" en la data de IA para buscar contra ella
    # Combinamos: Identificación del Repuesto + Características + Compatibilidad Texto
    df_ai['Search_Text'] = df_ai['Identificacion_Repuesto'].fillna('') + " " + \
                           df_ai['Compatibilidad_Probable_Texto'].fillna('') + " " + \
                           df_ai['Tags_Sugeridos'].fillna('')
    
    df_ai['Search_Clean'] = df_ai['Search_Text'].apply(clean_text)
    
    # Diccionario para búsqueda rápida: {Search_Clean: Index_AI}
    # Usamos una lista de las descripciones limpias para thefuzz
    ai_choices = df_ai['Search_Clean'].tolist()
    
    # 3. Fusión (Loop Maestro)
    print("3. Ejecutando emparejamiento (Matching)...")
    
    shopify_rows = []
    rename_commands = [f'mkdir "{IMAGE_OUTPUT_DIR}" 2>nul'] # Comando para crear carpeta si no existe

    matches_found = 0

    for idx, row in df_master.iterrows():
        sku = str(row['SKU'])
        desc_master = str(row['Descripcion'])
        desc_clean = clean_text(desc_master)
        
        # --- MATCHING ---
        # Buscamos la descripción de KAIQI dentro de la "inteligencia" de la IA
        best_match = process.extractOne(desc_clean, ai_choices, scorer=fuzz.token_set_ratio, score_cutoff=SCORE_CUTOFF)
        
        fitment_text = ""
        image_filename = ""
        match_score = 0
        ai_title = ""

        if best_match:
            match_string, match_score, match_idx = best_match
            ai_row = df_ai.iloc[match_idx]
            
            matches_found += 1
            
            # Extraer datos de la IA
            raw_filename = ai_row['Filename_Original']
            fitment_text = parse_fitment_json(ai_row['Compatibilidad_Probable_JSON'])
            if not fitment_text: # Fallback al texto si el JSON falló
                fitment_text = str(ai_row['Compatibilidad_Probable_Texto'])
            
            ai_title = str(ai_row['Nombre_Comercial_Catalogo'])

            # --- GENERAR NOMBRE DE IMAGEN SEO ---
            # Formato: nombre-producto-aplicacion_SKU.jpg
            base_name = f"{desc_master} {fitment_text}".strip()
            seo_name = generate_seo_handle(base_name)
            # Limitar longitud para no romper Windows
            seo_name = seo_name[:100] 
            final_image_name = f"{seo_name}_{sku}.jpg"
            
            image_filename = final_image_name # Para el CSV
            
            # Comando BAT para copiar y renombrar
            source_path = os.path.join(IMAGE_SOURCE_DIR, raw_filename)
            dest_path = os.path.join(IMAGE_OUTPUT_DIR, final_image_name)
            
            # Usamos 'copy' en lugar de 'ren' para mantener el original por seguridad
            cmd = f'copy "{source_path}" "{dest_path}"'
            rename_commands.append(cmd)

        # --- CONSTRUCCIÓN DE DATOS SHOPIFY ---
        
        # Título Final: KAIQI Descripción + Fitment (si existe)
        final_title = desc_master
        if fitment_text and len(fitment_text) > 3:
             final_title = f"{desc_master} para {fitment_text}"
        
        # Limpieza final del título (Capitalización)
        final_title = final_title.title().replace(' Para ', ' para ').replace(' De ', ' de ')

        shopify_rows.append({
            "Handle": generate_seo_handle(final_title),
            "Title": final_title,
            "Body (HTML)": f"<p>{final_title}.</p><p><strong>Compatibilidad:</strong> {fitment_text}</p><p><strong>Calidad:</strong> Premium</p>",
            "Vendor": "KAIQI",
            "Type": row['Componente'],
            "Tags": f"{row['Sistema Principal']}, {row['Subsistema']}, {row['Componente']}, {fitment_text}",
            "Published": "TRUE",
            "Option1 Name": "Title",
            "Option1 Value": "Default Title",
            "Variant SKU": sku,
            "Variant Grams": 500,
            "Variant Inventory Qty": 10,
            "Variant Price": row.get('Precio', 0),
            "Image Src": image_filename, # El nombre nuevo
            "Image Position": 1 if image_filename else "",
            "Image Alt Text": final_title,
            "Status": "active",
            "KAIQI_MATCH_SCORE": match_score # Para auditoría
        })

    # 4. Guardar Resultados
    print("4. Guardando archivos finales...")
    
    # CSV Shopify
    df_shopify = pd.DataFrame(shopify_rows)
    df_shopify.to_csv(OUTPUT_SHOPIFY, index=False, sep=',', encoding='utf-8-sig')
    
    # BAT Renombrado
    with open(OUTPUT_BAT_RENAME, 'w', encoding='ansi') as f: # 'ansi' es mejor para consola Windows
        f.write("@echo off\n")
        f.write(f'echo Iniciando copia y renombrado de {matches_found} imagenes...\n')
        for cmd in rename_commands:
            f.write(cmd + "\n")
        f.write("echo Proceso completado.\n")
        f.write("pause")

    print("\n" + "="*60)
    print(f"✅ PROYECTO COMPLETADO")
    print(f"   -> Total Productos KAIQI Procesados: {len(df_master)}")
    print(f"   -> Imágenes/Fitment Encontrados (Matches): {matches_found}")
    print(f"   -> Archivo Importación Shopify: {OUTPUT_SHOPIFY}")
    print(f"   -> Script de Imágenes: {OUTPUT_BAT_RENAME}")
    print("============================================================")
    print("\n👉 INSTRUCCIÓN FINAL:")
    print(f"1. Ve a la carpeta {PROJECT_DIR}")
    print(f"2. Haz doble clic en '{OUTPUT_BAT_RENAME}' para organizar tus fotos.")
    print("3. Sube el CSV a Shopify.")

if __name__ == "__main__":
    main()