import os
from PIL import Image, UnidentifiedImageError

# --- CONFIGURACIÓN ---
INPUT_DIR = 'imagenes_descargadas'

print("--- INICIANDO AUDITORÍA Y REPARACIÓN DE IMÁGENES ---")

if not os.path.exists(INPUT_DIR):
    print(f"Error: No existe la carpeta {INPUT_DIR}")
    exit()

corruptas = 0
reparadas = 0
total = 0

for filename in os.listdir(INPUT_DIR):
    filepath = os.path.join(INPUT_DIR, filename)
    
    # Saltamos si es carpeta
    if os.path.isdir(filepath):
        continue
        
    total += 1
    
    try:
        # Intentamos abrir la imagen
        with Image.open(filepath) as img:
            # Verificar formato real
            real_format = img.format
            
            # Si es válida, la forzamos a ser un JPG estándar
            # Convertimos a RGB (para quitar transparencia de PNG que rompe JPGs)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Sobrescribimos el archivo con un JPG limpio y nuevo
            img.save(filepath, "JPEG", quality=90)
            reparadas += 1
            print(f"✅ [OK] {filename} (Era {real_format} -> Ahora JPG)")

    except (UnidentifiedImageError, OSError):
        # Si falla al abrir, es un archivo basura (HTML o corrupto)
        print(f"❌ [BORRANDO] {filename} - Archivo corrupto o no es imagen.")
        try:
            os.remove(filepath)
            corruptas += 1
        except:
            print("   Error al borrar archivo.")

print("\n" + "="*40)
print(f"RESUMEN DE REPARACIÓN:")
print(f"Total procesadas: {total}")
print(f"✅ Imágenes validadas/reparadas: {reparadas}")
print(f"🗑️ Archivos basura eliminados: {corruptas}")
print("="*40)
print("Ahora tu carpeta 'imagenes_descargadas' tiene solo JPGs válidos.")