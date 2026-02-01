import pandas as pd
import os
import glob
import shutil

# --- CONFIGURACIÓN ---
# Directorios a buscar
DIRECTORIOS = [r'C:\merge', r'C:\KAIQI_PROYECTO_FINAL']
PROJECT_DIR = r'C:\KAIQI_PROYECTO_FINAL'

OUTPUT_CSV = os.path.join(PROJECT_DIR, 'Base_Datos_Competencia_Maestra.csv')
OUTPUT_IMG_DIR = os.path.join(PROJECT_DIR, 'FOTOS_COMPETENCIA')

if not os.path.exists(OUTPUT_IMG_DIR):
    os.makedirs(OUTPUT_IMG_DIR)

print("--- SCRIPT 2 (V2): CONSOLIDACIÓN TOTAL (Merge + Fuentes HTML) ---")

# --- 1. CONSOLIDAR BASES DE DATOS (CSV) ---
print(f"1. Buscando archivos 'Base_Datos_...' en {DIRECTORIOS}")
csv_files = []
for d in DIRECTORIOS:
    csv_files.extend(glob.glob(os.path.join(d, 'Base_Datos_*.csv')))

if not csv_files:
    print(f"❌ ¡Error! No se encontraron archivos 'Base_Datos_'.")
    exit()

print(f"   -> Encontrados {len(csv_files)} archivos CSV para unificar:")
all_dataframes = []
for f in csv_files:
    print(f"   -> Procesando {os.path.basename(f)}")
    df = pd.read_csv(f)
    all_dataframes.append(df)
        
df_maestro = pd.concat(all_dataframes)
df_maestro = df_maestro.drop_duplicates(subset=['Nombre_Externo', 'Imagen_Externa'])
df_maestro = df_maestro.dropna(subset=['Nombre_Externo', 'Imagen_Externa'])
df_maestro.to_csv(OUTPUT_CSV, index=False)
print(f"\n✅ Base de datos de competencia MAESTRA creada: {OUTPUT_CSV} ({len(df_maestro)} productos únicos)")

# --- 2. CONSOLIDAR CARPETAS DE IMÁGENES ---
print(f"\n2. Copiando imágenes a {OUTPUT_IMG_DIR}...")
img_folders = []
# 1. Carpetas 'imagenes_*' de C:\merge
for d in os.listdir(r'C:\merge'):
    if d.startswith('imagenes_') and os.path.isdir(os.path.join(r'C:\merge', d)):
        img_folders.append(os.path.join(r'C:\merge', d))
# 2. Carpetas '_files' de C:\KAIQI_PROYECTO_FINAL\html_fuentes
html_fuentes_dir = os.path.join(PROJECT_DIR, 'html_fuentes')
if os.path.exists(html_fuentes_dir):
    for d in os.listdir(html_fuentes_dir):
        if d.endswith('_files') and os.path.isdir(os.path.join(html_fuentes_dir, d)):
            img_folders.append(os.path.join(html_fuentes_dir, d))

if not img_folders:
    print(f"❌ ¡Error! No se encontraron carpetas de imágenes.")
    exit()
    
total_copied = 0
for folder in img_folders:
    print(f"   -> Copiando desde {folder}...")
    for root, dirs, files in os.walk(folder):
        for img_file in files:
            # Solo copiar archivos de imagen
            if img_file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                source_path = os.path.join(root, img_file)
                dest_path = os.path.join(OUTPUT_IMG_DIR, img_file)
                
                if not os.path.exists(dest_path):
                    try:
                        shutil.copy2(source_path, dest_path)
                        total_copied += 1
                    except Exception:
                        pass # Ignorar archivos que no se pueden copiar
                
print(f"\n✅ {total_copied} imágenes nuevas copiadas a FOTOS_COMPETENCIA.")
print("--- SCRIPT 2 TERMINADO. Listo para el SCRIPT 3 (Enriquecimiento). ---")