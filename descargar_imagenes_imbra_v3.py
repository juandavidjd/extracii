import os
import csv
import requests
from time import sleep
from pathlib import Path
import glob

# ==========================================================
# CONFIGURACIÓN
# ==========================================================

BASE_DIR = r"C:\auteco"  # Buscaremos ahí todo

def buscar(archivo):
    """Busca el archivo en TODO C:\auteco (recursivo)."""
    print(f"🔎 Buscando {archivo} en {BASE_DIR} ...")
    rutas = glob.glob(os.path.join(BASE_DIR, "**", archivo), recursive=True)
    if rutas:
        print(f"   ✔ Encontrado: {rutas[0]}")
        return rutas[0]
    else:
        print(f"   ❌ No encontrado: {archivo}")
        return None


# Buscar archivos reales
CSV_PRODUCTOS = buscar("IMBRA_FULL.csv")
CSV_IMAGENES = buscar("IMBRA_IMAGENES.csv")

if not CSV_PRODUCTOS or not CSV_IMAGENES:
    print("\n❌ Error: No se encontraron los CSV necesarios.")
    print("Debes asegurarte que IMBRA_FULL.csv e IMBRA_IMAGENES.csv están dentro de C:\\auteco")
    exit()


# Carpeta donde guardaremos imágenes
OUTPUT_DIR = os.path.join(BASE_DIR, "IMBRA_v27", "imagenes")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==========================================================
# CARGAR MAPA DE IMÁGENES
# ==========================================================

imagenes_por_handle = {}

print("\n📥 Cargando listado de imágenes...\n")

with open(CSV_IMAGENES, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        handle = row.get("handle", "").strip()
        url = row.get("url_imagen", "").strip()
        if handle and url:
            imagenes_por_handle.setdefault(handle, []).append(url)

print(f"✔ Se cargaron {len(imagenes_por_handle)} handles con imágenes.")


# ==========================================================
# UTILIDAD PARA DESCARGAR
# ==========================================================

def descargar_imagen(url, destino):
    try:
        r = requests.get(url, timeout=12)
        if r.status_code == 200:
            with open(destino, "wb") as f:
                f.write(r.content)
            print(f"   ✔ Guardada: {destino}")
            return True
        print(f"   ❌ HTTP {r.status_code}: {url}")
    except Exception as e:
        print(f"   ❌ Error descargando {url}: {e}")
    return False


# ==========================================================
# PROCESAR PRODUCTOS
# ==========================================================

print("\n🚀 INICIANDO DESCARGA DE IMÁGENES IMBRA v3 (auto-detect)\n")

with open(CSV_PRODUCTOS, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)

    for row in reader:

        handle = row["handle"]
        categoria = row["categoria"].replace("/", "-")
        titulo = row["titulo"].replace("/", "-")

        carpeta = os.path.join(OUTPUT_DIR, categoria, handle)
        Path(carpeta).mkdir(parents=True, exist_ok=True)

        print(f"\n📦 {titulo}")
        print(f"🔎 Handle: {handle}")

        urls = imagenes_por_handle.get(handle, [])

        if not urls:
            print("   ⚠ No hay imágenes asociadas.")
            continue

        # Descargar cada imagen del producto
        for i, url in enumerate(urls, start=1):

            ext = ".jpg"
            if ".png" in url.lower(): ext = ".png"
            if ".webp" in url.lower(): ext = ".webp"

            destino = os.path.join(carpeta, f"{handle}_{i}{ext}")

            if os.path.exists(destino):
                print(f"   ↪ Ya existe: {destino}")
                continue

            descargar_imagen(url, destino)
            sleep(0.2)

print("\n🎉 DESCARGA COMPLETA")
print(f"📂 Imágenes guardadas en: {OUTPUT_DIR}")
