import os
import csv
import requests
from time import sleep
from pathlib import Path

# ============================================
# CONFIGURACIÓN
# ============================================
BASE_DIR = r"C:\auteco\imbra_store"
CSV_PRODUCTOS = os.path.join(BASE_DIR, "IMBRA_FULL.csv")
CSV_IMAGENES = os.path.join(BASE_DIR, "IMBRA_IMAGENES.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "imagenes")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================
# CARGAR URLs DE IMÁGENES AGRUPADAS POR HANDLE
# ============================================

imagenes_por_handle = {}

with open(CSV_IMAGENES, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        handle = row.get("handle", "").strip()
        url = row.get("url_imagen", "").strip()
        if not handle or not url:
            continue

        if handle not in imagenes_por_handle:
            imagenes_por_handle[handle] = []
        imagenes_por_handle[handle].append(url)


# ============================================
# DESCARGAR IMAGEN
# ============================================

def descargar_imagen(url, ruta_destino):
    try:
        r = requests.get(url, timeout=12)
        if r.status_code == 200:
            with open(ruta_destino, "wb") as img_file:
                img_file.write(r.content)
            print(f"   ✔ Imagen descargada: {ruta_destino}")
            return True
        else:
            print(f"   ❌ Error HTTP {r.status_code}: {url}")
            return False
    except Exception as e:
        print(f"   ❌ Error descargando {url}: {e}")
        return False


# ============================================
# DESCARGA PARA CADA PRODUCTO
# ============================================

print("\n🚀 INICIANDO DESCARGA DE IMÁGENES IMBRA v2\n")

with open(CSV_PRODUCTOS, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)

    for row in reader:
        handle = row["handle"]
        titulo = row["titulo"].replace("/", "-")
        categoria = row["categoria"].replace("/", "-")

        # Carpeta destino organizada por categoría
        carpeta = os.path.join(OUTPUT_DIR, categoria, handle)
        Path(carpeta).mkdir(parents=True, exist_ok=True)

        print(f"\n📦 Producto: {titulo}")
        print(f"🔎 Handle: {handle}")

        urls = imagenes_por_handle.get(handle, [])

        if not urls:
            print("   ⚠ SIN IMÁGENES DISPONIBLES")
            continue

        # Descargar todas las imágenes del producto
        for i, url in enumerate(urls, start=1):
            extension = ".jpg"

            # Intentar detectar extensión real
            if ".png" in url.lower():
                extension = ".png"
            if ".jpeg" in url.lower():
                extension = ".jpeg"
            if ".webp" in url.lower():
                extension = ".webp"

            nombre_archivo = f"{handle}_{i}{extension}"
            destino = os.path.join(carpeta, nombre_archivo)

            if os.path.exists(destino):
                print(f"   ↪ Ya existe, saltando: {destino}")
                continue

            descargar_imagen(url, destino)
            sleep(0.2)  # Anti-bloqueo del servidor


print("\n🎉 PROCESO COMPLETADO")
print(f"📂 Carpeta final de imágenes: {OUTPUT_DIR}")
