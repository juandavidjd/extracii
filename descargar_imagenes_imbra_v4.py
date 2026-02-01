import os
import csv
import requests
from slugify import slugify
import time

# -------------------------------
# CONFIGURACIÓN DE RUTAS
# -------------------------------
BASE_DIR = r"C:\auteco\IMBRA_v27"
CSV_FULL = os.path.join(BASE_DIR, "02_csv", "IMBRA_FULL.csv")
CSV_IMAGES = os.path.join(BASE_DIR, "02_csv", "IMBRA_IMAGES.csv")
IMG_OUT = os.path.join(BASE_DIR, "01_imagenes")

# Crear carpeta de salida
os.makedirs(IMG_OUT, exist_ok=True)

# -------------------------------
# Cargar categorías desde IMBRA_FULL
# -------------------------------
def load_categories():
    categories = {}
    try:
        with open(CSV_FULL, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku = row.get("sku", "").strip()
                categoria = row.get("categoria", "SIN_CATEGORIA").strip()
                if sku:
                    categories[sku] = categoria
        print(f"✔ Categorías cargadas: {len(categories)}")
    except Exception as e:
        print(f"❌ Error leyendo IMBRA_FULL.csv: {e}")
    return categories

# -------------------------------
# Descargar imagen con reintentos
# -------------------------------
def download_image(url, out_path):
    tries = 0
    while tries < 3:
        try:
            r = requests.get(url, timeout=12)
            if r.status_code == 200:
                with open(out_path, "wb") as f:
                    f.write(r.content)
                return True
            else:
                print(f"⚠ Código HTTP {r.status_code} en descarga.")
        except Exception as e:
            print(f"⚠ Error: {e}")
        tries += 1
        time.sleep(1.5)
    return False

# -------------------------------
# MAIN
# -------------------------------
def main():

    print("\n🚀 MÓDULO B — Descarga AUTOMÁTICA de Imágenes FULL IMBRA v4\n")

    # Cargar categorías
    categories = load_categories()

    # Verificar archivo de imágenes
    if not os.path.exists(CSV_IMAGES):
        print(f"❌ No existe archivo de imágenes: {CSV_IMAGES}")
        return

    # Leer IMBRA_IMAGES.csv
    try:
        with open(CSV_IMAGES, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
    except Exception as e:
        print(f"❌ Error leyendo IMBRA_IMAGES.csv: {e}")
        return

    print(f"📥 Total imágenes detectadas: {len(reader)}\n")

    for i, row in enumerate(reader, start=1):

        sku = row.get("sku", "").strip()
        handle = row.get("handle", "").strip()
        url = row.get("imagen", "").strip()

        if not url or "cdn" not in url:
            print(f"{i}/{len(reader)} → ⚠ URL inválida para SKU: {sku}")
            continue

        # Categoría del SKU
        categoria = categories.get(sku, "SIN_CATEGORIA")
        categoria = categoria.replace(" ", "_").replace("/", "-")

        # Crear carpeta de categoría
        out_dir = os.path.join(IMG_OUT, categoria)
        os.makedirs(out_dir, exist_ok=True)

        filename = f"{slugify(handle)}_{sku}.jpg"
        out_path = os.path.join(out_dir, filename)

        # Si ya existe → saltar
        if os.path.exists(out_path):
            print(f"{i}/{len(reader)} → ⏭ Ya existe: {filename}")
            continue

        print(f"{i}/{len(reader)} → 🔽 Descargando {filename}")

        ok = download_image(url, out_path)
        if not ok:
            print(f"   ❌ Error descargando → {url}")
        else:
            print(f"   ✔ Guardado")

    print("\n🎉 DESCARGA COMPLETA")
    print(f"📂 Imágenes guardadas en: {IMG_OUT}\n")


if __name__ == "__main__":
    main()
