#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
limpiar_imagenes_kaiqi_v2.py

Reclasifica todas las imágenes de FOTOS_COMPETENCIA usando los catálogos
'catalogo_kaiqi_imagenes data 1/2/3.csv' generados por IA.

Salida:
- C:\img\IMAGENES_KAIQI_MAESTRAS_V2
- C:\img\DESCARTADAS_NO_MOTO_V2
- C:\img\DESCARTADAS_TEXTOS_V2

ANTES DE EJECUTAR:
- Asegúrate de que TODAS las imágenes que quieras evaluar estén dentro de:
    C:\img\FOTOS_COMPETENCIA
  (incluyendo las que estaban en DESCARTADAS_* si quieres re-evaluarlas).
"""

import os
import shutil
import pandas as pd

# ==========================
# CONFIGURACIÓN BÁSICA
# ==========================

BASE_DIR = r"C:\img"
IMAGES_DIR = os.path.join(BASE_DIR, "FOTOS_COMPETENCIA")
DATA_DIR = os.path.join(BASE_DIR, "DATA")

# Archivos de catálogo IA
CATALOG_FILES = [
    os.path.join(DATA_DIR, "catalogo_kaiqi_imagenes data 1.csv"),
    os.path.join(DATA_DIR, "catalogo_kaiqi_imagenes data 2.csv"),
    os.path.join(DATA_DIR, "catalogo_kaiqi_imagenes data 3.csv"),
]

# Carpetas de salida
OUT_MAESTRAS = os.path.join(BASE_DIR, "IMAGENES_KAIQI_MAESTRAS_V2")
OUT_NO_MOTO = os.path.join(BASE_DIR, "DESCARTADAS_NO_MOTO_V2")
OUT_TEXTOS = os.path.join(BASE_DIR, "DESCARTADAS_TEXTOS_V2")

# Crear carpetas si no existen
for folder in [OUT_MAESTRAS, OUT_NO_MOTO, OUT_TEXTOS]:
    os.makedirs(folder, exist_ok=True)

# ==========================
# FUNCIONES AUXILIARES
# ==========================

def load_catalogs(files):
    """Carga y concatena todos los catálogos IA en un solo DataFrame."""
    dfs = []
    for f in files:
        if not os.path.exists(f):
            print(f"⚠️  No se encontró el archivo de catálogo: {f}")
            continue
        try:
            df = pd.read_csv(f, sep=";", encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(f, sep=";", encoding="latin-1")
        dfs.append(df)

    if not dfs:
        raise RuntimeError("No se pudo cargar ningún catálogo IA. Revisa rutas y nombres.")

    df_all = pd.concat(dfs, ignore_index=True)

    # Normalizar nombre de columna principal de archivo
    # Ajusta este nombre si en tus CSV aparece diferente (por ejemplo 'Archivo' o 'Nombre_archivo')
    if "Filename" not in df_all.columns:
        # Intento de detección automática
        for candidate in ["archivo", "nombre_archivo", "file", "imagen"]:
            if candidate in df_all.columns:
                df_all.rename(columns={candidate: "Filename"}, inplace=True)
                break

    if "Filename" not in df_all.columns:
        raise RuntimeError("No se encontró columna 'Filename' en los catálogos IA.")

    # Quitar duplicados por Filename, conservando el primero
    df_all = df_all.drop_duplicates(subset=["Filename"])

    return df_all


def es_no_moto(row):
    """Heurística para detectar imágenes que NO son de motos/motocargueros."""
    # Columna booleana principal (ajusta el nombre si en tu CSV es distinto)
    col_bool_candidates = ["Es_repuesto_moto", "es_repuesto_moto", "EsMoto", "es_moto"]
    es_moto = None
    for c in col_bool_candidates:
        if c in row:
            es_moto = row[c]
            break

    # Si explícitamente dice que no es repuesto de moto
    if es_moto is False:
        return True

    texto = (
        str(row.get("Tags", "")) + " " +
        str(row.get("Nombre_producto_sugerido", "")) + " " +
        str(row.get("Descripcion_visual", ""))
    ).lower()

    palabras_no_moto = [
        "carro", "camioneta", "camión", "bus", "autobús", "buseta",
        "juguete", "muñeco", "muñeca",
        "lavadora", "licuadora", "refrigerador", "nevera", "televisor", "tv",
        "logo", "logotipo", "banner", "publicidad", "flyer",
        "bicicleta", "bici",
    ]

    if any(p in texto for p in palabras_no_moto):
        return True

    # Si no encontramos nada que lo marque como no moto, devolvemos False
    return False


def tiene_texto_pesado(row):
    """Detecta imágenes que son más bien banners / piezas gráficas llenas de texto."""
    notas = str(row.get("Notas_textos_visibles", "")).lower()
    tags = str(row.get("Tags", "")).lower()
    nombre = str(row.get("Nombre_producto_sugerido", "")).lower()

    palabras_texto_pesado = [
        "banner", "publicidad", "promo", "oferta", "flyer",
        "texto grande", "texto promocional", "anuncio", "poster", "póster",
        "portada", "catálogo", "catalogo"
    ]

    if any(p in notas for p in palabras_texto_pesado):
        return True
    if any(p in tags for p in palabras_texto_pesado):
        return True
    if any(p in nombre for p in palabras_texto_pesado):
        return True

    return False


def es_repuesto_moto_confiable(row, min_score=0.80):
    """Determina si es un repuesto de moto/motocarguero aceptable para el banco maestro."""
    # Booleano principal de moto
    col_bool_candidates = ["Es_repuesto_moto", "es_repuesto_moto", "EsMoto", "es_moto"]
    es_moto = None
    for c in col_bool_candidates:
        if c in row:
            es_moto = row[c]
            break

    if es_moto is not True:
        return False

    # Score de clasificación
    score = None
    for c in ["Score_clasificacion", "score_clasificacion", "Confianza", "confidence"]:
        if c in row:
            try:
                score = float(row[c])
            except Exception:
                pass
            break

    if score is not None and score < min_score:
        return False

    # Tipo objeto (si existe)
    tipo = str(row.get("Tipo_objeto", "")).lower()
    if tipo and tipo not in ["repuesto_moto", "repuesto_motocarguero", "pieza_moto"]:
        # Si el tipo explícitamente dice otra cosa rara, mejor no lo metemos
        return False

    return True


def copiar_si_existe(src_folder, filename, dst_folder):
    """Copia filename desde src_folder a dst_folder si existe."""
    src_path = os.path.join(src_folder, filename)
    if not os.path.exists(src_path):
        print(f"   ⚠️  No se encontró la imagen en disco: {filename}")
        return False
    shutil.copy2(src_path, dst_folder)
    return True


# ==========================
# PROCESO PRINCIPAL
# ==========================

def main():
    if not os.path.exists(IMAGES_DIR):
        print(f"❌ No existe la carpeta de imágenes: {IMAGES_DIR}")
        return

    print("==============================================")
    print("  Limpieza/Reclasificación de imágenes KAIQI")
    print("==============================================\n")

    # 1) Cargar catálogos IA
    print("📥 Cargando catálogos IA...")
    df = load_catalogs(CATALOG_FILES)
    print(f"   → Registros en catálogos IA: {len(df)}")

    total_maestras = 0
    total_no_moto = 0
    total_textos = 0
    total_sin_archivo = 0

    # 2) Recorrer filas y clasificar
    for idx, row in df.iterrows():
        filename = str(row["Filename"])
        filename = filename.strip()

        if not filename:
            continue

        # Normalización mínima por si hay espacios raros
        # (No cambiamos el nombre en disco, solo nos aseguramos de no tener espacios extra)
        categoria = None

        if es_no_moto(row):
            categoria = "no_moto"
        elif tiene_texto_pesado(row):
            categoria = "texto"
        elif es_repuesto_moto_confiable(row, min_score=0.80):
            categoria = "maestra"
        else:
            # Si no entra en nada y no es claramente no-moto, por ahora lo mandamos a texto
            # o podríamos crear una carpeta 'REVISION_MANUAL'. Si prefieres eso, cambia aquí.
            categoria = "texto"

        if categoria == "no_moto":
            ok = copiar_si_existe(IMAGES_DIR, filename, OUT_NO_MOTO)
            if ok:
                total_no_moto += 1
            else:
                total_sin_archivo += 1

        elif categoria == "texto":
            ok = copiar_si_existe(IMAGES_DIR, filename, OUT_TEXTOS)
            if ok:
                total_textos += 1
            else:
                total_sin_archivo += 1

        elif categoria == "maestra":
            ok = copiar_si_existe(IMAGES_DIR, filename, OUT_MAESTRAS)
            if ok:
                total_maestras += 1
            else:
                total_sin_archivo += 1

    print("\n==================== RESUMEN ====================")
    print(f"✅ IMAGENES_KAIQI_MAESTRAS_V2 : {total_maestras}")
    print(f"🚫 DESCARTADAS_NO_MOTO_V2     : {total_no_moto}")
    print(f"📝 DESCARTADAS_TEXTOS_V2      : {total_textos}")
    print(f"⚠️  Registros sin archivo en disco: {total_sin_archivo}")
    print("================================================\n")
    print("Proceso terminado. Revisa las carpetas de salida en C:\\img")


if __name__ == "__main__":
    main()
