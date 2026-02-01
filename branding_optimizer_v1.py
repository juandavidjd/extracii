#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
branding_optimizer_v1.py
SRM–QK–ADSI — Sistema de Branding Automatizado
------------------------------------------------
Toma los logos originales desde C:/img,
los optimiza, limpia fondo, recorta, centra y genera:

- logos_optimizados/
- palettes_detectadas/
- backgrounds/

Compatible con:
- Pipeline SRM v2.1
- Lovely.dev UI generator
"""

import os
import json
import numpy as np
from PIL import Image, ImageOps, ImageFilter
from sklearn.cluster import KMeans

# -----------------------------------------
# CONFIGURACIONES
# -----------------------------------------
BASE_DIR = r"C:/SRM_ADSI/08_branding"
LOGOS_ORIGINALES = os.path.join(BASE_DIR, "logos_originales")
LOGOS_OPTIMIZADOS = os.path.join(BASE_DIR, "logos_optimizados")
PALETTES_DIR = os.path.join(BASE_DIR, "palettes_detectadas")
BACKGROUNDS_DIR = os.path.join(BASE_DIR, "backgrounds")

FUENTE_LOGOS = r"C:/img"

CLIENTES = [
    "DFG",
    "Duna",
    "Japan",
    "Kaiqi",
    "Leo",
    "Vaisand",
    "Yokomar",
    "Bara",
    "Store",
]

# Tamaños finales
SIZE_SMALL = 64
SIZE_MEDIUM = 512
SIZE_LARGE = 1024


# -----------------------------------------
# FUNCIONES UTILITARIAS
# -----------------------------------------

def asegurar_directorio(path):
    if not os.path.exists(path):
        os.makedirs(path)


def cargar_imagen(path):
    img = Image.open(path).convert("RGBA")
    return img


def eliminar_fondo(im):
    """
    Algoritmo sencillo basado en diferencia de color (color spill)
    Sirve para logos con fondo blanco/negro dependiendo del histograma.
    """
    # Convertir a numpy
    data = np.array(im)
    r, g, b, a = np.rollaxis(data, axis=-1)

    # Detectar si el fondo es blanco o negro por promedio del borde
    borde = np.concatenate([
        data[0, :, :3],
        data[-1, :, :3],
        data[:, 0, :3],
        data[:, -1, :3]
    ])
    avg = borde.mean()

    # Fondo blanco
    if avg > 200:
        mask = (r > 200) & (g > 200) & (b > 200)
    # Fondo negro
    else:
        mask = (r < 50) & (g < 50) & (b < 50)

    data[mask] = [0, 0, 0, 0]
    return Image.fromarray(data)


def recortar_transparente(img):
    """
    Quita todo el espacio transparente alrededor.
    """
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    return img


def redimensionar(img, size):
    """
    Redimensiona manteniendo proporción.
    """
    return ImageOps.contain(img, (size, size))


def extraer_paleta(img, k=5):
    """
    Extrae la paleta principal usando KMeans.
    """
    img_small = img.resize((200, 200))
    arr = np.array(img_small)
    arr = arr.reshape((-1, 4))

    # Filtrar solo pixeles visibles
    arr = arr[arr[:, 3] > 0][:, :3]

    kmeans = KMeans(n_clusters=k, n_init=10)
    kmeans.fit(arr)

    colores = kmeans.cluster_centers_.astype(int)

    hex_colors = []
    for c in colores:
        hex_colors.append('#%02x%02x%02x' % tuple(c))

    return hex_colors


def generar_background_degradado(color1, color2, size=(1920, 1080)):
    img = Image.new("RGB", size, color1)
    top = np.array(Image.new("RGB", size, color1))
    bottom = np.array(Image.new("RGB", size, color2))

    arr = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    for y in range(size[1]):
        alpha = y / size[1]
        arr[y] = (1 - alpha) * top[y] + alpha * bottom[y]

    return Image.fromarray(arr)


# -----------------------------------------
# PROCESO PRINCIPAL
# -----------------------------------------

def procesar_cliente(cliente):
    print(f"→ Procesando {cliente}...")

    origen = os.path.join(FUENTE_LOGOS, f"{cliente}.png")

    if not os.path.exists(origen):
        print(f"  ⚠ No existe: {origen}")
        return

    # Copiar original
    destino_original = os.path.join(LOGOS_ORIGINALES, f"{cliente}.png")
    Image.open(origen).save(destino_original)

    # Optimizar
    img = cargar_imagen(origen)
    img = eliminar_fondo(img)
    img = recortar_transparente(img)

    # Guardar tamaños
    out512 = redimensionar(img, SIZE_MEDIUM)
    out1024 = redimensionar(img, SIZE_LARGE)
    out64 = redimensionar(img, SIZE_SMALL)

    out512.save(os.path.join(LOGOS_OPTIMIZADOS, f"{cliente}_logo_512.png"))
    out1024.save(os.path.join(LOGOS_OPTIMIZADOS, f"{cliente}_logo_1024.png"))
    out64.save(os.path.join(LOGOS_OPTIMIZADOS, f"{cliente}_favicon_64.png"))

    # Paleta
    paleta = extraer_paleta(img)
    with open(os.path.join(PALETTES_DIR, f"{cliente}_palette.json"), "w") as f:
        json.dump({"cliente": cliente, "palette": paleta}, f, indent=4)

    # Background
    if len(paleta) >= 2:
        bg = generar_background_degradado(paleta[0], paleta[1])
        bg.save(os.path.join(BACKGROUNDS_DIR, f"{cliente}_background.jpg"))

    print(f"  ✔ OK — {cliente}")


def main():
    print("\n==========================================")
    print(" SRM–QK–ADSI — BRANDING OPTIMIZER v1")
    print("==========================================\n")

    # Crear estructura
    asegurar_directorio(BASE_DIR)
    asegurar_directorio(LOGOS_ORIGINALES)
    asegurar_directorio(LOGOS_OPTIMIZADOS)
    asegurar_directorio(PALETTES_DIR)
    asegurar_directorio(BACKGROUNDS_DIR)

    for c in CLIENTES:
        procesar_cliente(c)

    print("\n==========================================")
    print(" ✔ Branding Optimizado COMPLETADO")
    print(" Archivos en: C:/SRM_ADSI/08_branding/")
    print("==========================================\n")


if __name__ == "__main__":
    main()
