import os
import pandas as pd
import re
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN ---
PROJECT_DIR = r'C:\KAIQI_PROYECTO_FINAL'
HTML_DIR = os.path.join(PROJECT_DIR, 'html_fuentes')
OUTPUT_CSV = os.path.join(PROJECT_DIR, 'Base_Datos_Fuentes_HTML.csv') # Archivo temporal

print("--- SCRIPT 2a: MINERÍA DE FUENTES HTML (Mercado Libre) ---")

if not os.path.exists(HTML_DIR):
    print(f"❌ Error: No se encontró la carpeta '{HTML_DIR}'.")
    exit()

productos_encontrados = []

def limpiar_texto(texto):
    if not texto: return ""
    texto = texto.replace('Ã±', 'ñ').replace('Ã³', 'ó').replace('Ã¡', 'á').replace('Ã©', 'é').replace('Ã­', 'í').replace('Ãº', 'ú').replace('Ã‘', 'Ñ')
    return re.sub(r'\s+', ' ', texto).strip().upper()

# Recorremos todos los archivos HTML
for filename in os.listdir(HTML_DIR):
    if filename.endswith(".html") or filename.endswith(".htm"):
        filepath = os.path.join(HTML_DIR, filename)
        print(f"Procesando: {filename}...")
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                soup = BeautifulSoup(f, 'html.parser')
                
                # --- LÓGICA DE EXTRACCIÓN (Mercado Libre) ---
                # 1. Encontrar todos los contenedores de producto
                items = soup.find_all('li', class_='ui-search-layout__item')
                
                for item in items:
                    # 2. Encontrar el Título
                    titulo_tag = item.find('a', class_='poly-component__title')
                    nombre = titulo_tag.get_text() if titulo_tag else None
                    
                    # 3. Encontrar la Imagen
                    img_tag = item.find('img', class_='poly-component__picture')
                    src = img_tag.get('data-src') or img_tag.get('src') if img_tag else None
                    
                    if nombre and src:
                        nombre_limpio = limpiar_texto(nombre)
                        img_filename = os.path.basename(src.split('?')[0]) # Limpiar URL
                        
                        productos_encontrados.append({
                            'Nombre_Externo': nombre_limpio,
                            'Imagen_Externa': img_filename, # Solo el nombre del archivo
                            'URL_Origen': src # URL Completa
                        })
                            
        except Exception as e:
            print(f"   Error leyendo {filename}: {e}")

# Guardar resultado
if productos_encontrados:
    df_externo = pd.DataFrame(productos_encontrados)
    df_externo = df_externo.drop_duplicates(subset=['Nombre_Externo'])
    df_externo.to_csv(OUTPUT_CSV, index=False)
    print("\n" + "="*40)
    print(f"✅ MINERÍA COMPLETADA. Se encontraron {len(df_externo)} productos nuevos.")
    print(f"Nueva base de datos guardada en: {OUTPUT_CSV}")
    print("="*40)
else:
    print("⚠️ No se encontraron productos. Revisa que los HTML tengan contenido.")