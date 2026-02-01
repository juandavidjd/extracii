#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
===============================================================================
 🏆 RENOMBRADOR ULTRA HÍBRIDO KAIQI — v23.1 FINAL STABLE
===============================================================================

Autor: Juan David + Gemini
Versión: 23.1 (Corregida Sintaxis API)
Fecha: 2025-11-22

CORRECCIONES APLICADAS:
1. Fix API OpenAI: Se reemplazó 'client.responses' (inválido) por 'client.chat.completions'.
2. Estabilidad: Manejo de errores robusto en carga de Excel y Vision.
3. Arquitectura: Match Exacto > Aproximado > Embeddings > Vision > Fallback.

===============================================================================
"""

import os
import re
import json
import base64
import shutil
import hashlib
import unicodedata
import numpy as np
import pandas as pd
from PIL import Image
from difflib import SequenceMatcher
from openai import OpenAI

# =============================================================================
# CONFIGURACIÓN GENERAL
# =============================================================================

BASE = r"C:\img"

RUTAS_ENTRADA = [
    os.path.join(BASE, "FOTOS_COMPETENCIA_BARA"),
    os.path.join(BASE, "FOTOS_COMPETENCIA_JAPAN"),
    os.path.join(BASE, "FOTOS_COMPETENCIA_KAIQI"),
    os.path.join(BASE, "FOTOS_COMPETENCIA_LEO"),
    os.path.join(BASE, "FOTOS_COMPETENCIA_STORE"),
    os.path.join(BASE, "FOTOS_COMPETENCIA_VAISAND"),
    os.path.join(BASE, "IMAGENES_KAIQI_MAESTRAS"),
]

DIR_SALIDA = os.path.join(BASE, "IMAGENES_RENOMBRADAS_v23")
DIR_DUP = os.path.join(BASE, "IMAGENES_DUPLICADOS_v23")

LOG_PATH = os.path.join(BASE, "log_renombrado_v23.csv")
CACHE_VISION = os.path.join(BASE, "vision_cache_v23.json")
EMB_PATH = os.path.join(BASE, "embeddings_v23.npz")

os.makedirs(DIR_SALIDA, exist_ok=True)
os.makedirs(DIR_DUP, exist_ok=True)

# Bases de inteligencia
CATALOGOS = [
    os.path.join(BASE, "catalogo_kaiqi_imagenes_bara.csv"),
    os.path.join(BASE, "catalogo_kaiqi_imagenes_japan.csv"),
    os.path.join(BASE, "catalogo_kaiqi_imagenes_kaiqi.csv"),
    os.path.join(BASE, "catalogo_kaiqi_imagenes_leo.csv"),
    os.path.join(BASE, "catalogo_kaiqi_imagenes_store.csv"),
    os.path.join(BASE, "catalogo_kaiqi_imagenes_vaisand.csv"),
]

INVENTARIO = os.path.join(BASE, "Inventario_FINAL_CON_TAXONOMIA.csv")
JC = os.path.join(BASE, "LISTA DE PRECIOS NOVIEMBRE 13 2025 TRABAJO JC.xlsx")
YOKO = os.path.join(BASE, "LISTA DE PRECIOS  YOKOMAR ACTUALIZADA 2025.xlsx")

# Cliente OpenAI
client = None
try:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        client = OpenAI(api_key=api_key)
    else:
        print("⚠️  ADVERTENCIA: No se detectó OPENAI_API_KEY. IA Vision/Embeddings deshabilitados.")
except Exception as e:
    print(f"⚠️  Error inicializando OpenAI: {e}")


# =============================================================================
# UTILIDADES DE LIMPIEZA
# =============================================================================

def limpiar(text):
    """Limpia códigos basura al inicio protegiendo modelos (CB110, NKD, etc)."""
    if not isinstance(text, str):
        return ""

    t = text.strip()

    # 1-11-131-
    t = re.sub(r"^\d{1,4}-\d{1,4}-\d{1,4}[-\s]*", "", t)
    # 1010115
    t = re.sub(r"^\d{5,10}\s*", "", t)
    # DALU017 (Anclado al inicio ^)
    t = re.sub(r"^[A-Z]{2,5}\d{2,6}[-\s]*", "", t)
    # OEM
    t = re.sub(r"\bOEM\b", "", t, flags=re.IGNORECASE)
    
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def slug(text):
    """Slug SEO 100% válido y limpio."""
    text = limpiar(text)
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^A-Za-z0-9\s\-()]", "", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")[:180]


# =============================================================================
# HASH & JPG
# =============================================================================

def sha1_file(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk: break
            h.update(chunk)
    return h.hexdigest()


def convertir_jpg(origen, destino):
    try:
        with Image.open(origen) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            elif img.mode != "RGB":
                img = img.convert("RGB")
            
            # Forzar extensión .jpg en destino si no la tiene
            if not destino.lower().endswith(".jpg"):
                destino = os.path.splitext(destino)[0] + ".jpg"
                
            img.save(destino, "JPEG", quality=90, optimize=True)
        return True
    except:
        return False


def evitar_conflicto(dir_base, fn):
    base, ext = os.path.splitext(fn)
    candidate = fn
    n = 2
    while os.path.exists(os.path.join(dir_base, candidate)):
        candidate = f"{base}-v{n}{ext}"
        n += 1
    return candidate


# =============================================================================
# IA VISION (SINTAXIS CORREGIDA)
# =============================================================================

def load_cache():
    if os.path.exists(CACHE_VISION):
        try:
            return json.load(open(CACHE_VISION, "r", encoding="utf-8"))
        except:
            return {}
    return {}


def save_cache(c):
    try:
        json.dump(c, open(CACHE_VISION, "w", encoding="utf-8"), indent=2)
    except: pass


def vision(path, cache):
    """Identificación visual con GPT-4o (Sintaxis Correcta)."""
    if client is None:
        return ""

    sha = sha1_file(path)
    if sha in cache:
        return cache[sha]

    try:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

        # --- CORRECCIÓN CRÍTICA AQUÍ ---
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "Eres experto en repuestos de motos. Devuelve SOLO el nombre comercial rico en español."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Identifica este repuesto. Sin códigos. Ej: 'Cilindro Kit AKT 125 NKD'."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                    ]
                }
            ],
            max_tokens=60
        )
        # -------------------------------

        name = resp.choices[0].message.content.strip()
        cache[sha] = name
        save_cache(cache)
        return name

    except Exception as e:
        print(f"   [ERR] Vision API: {e}")
        return ""


# =============================================================================
# EMBEDDINGS
# =============================================================================

def embed_lista(lista):
    if client is None:
        return None

    out = []
    batch = 250
    for i in range(0, len(lista), batch):
        subset = lista[i:i+batch]
        try:
            resp = client.embeddings.create(
                model="text-embedding-3-small",
                input=subset
            )
            out.extend([d.embedding for d in resp.data])
        except Exception as e:
            print(f"   [ERR] Embeddings: {e}")

    return np.array(out)


def resolver_emb(fn, vecs, textos):
    if client is None or vecs is None:
        return ""

    query = limpiar(os.path.splitext(fn)[0])
    if len(query) < 3:
        return ""

    try:
        r = client.embeddings.create(
            model="text-embedding-3-small",
            input=[query]
        )
        v = np.array(r.data[0].embedding)
        sims = np.dot(vecs, v) / (np.linalg.norm(vecs, axis=1) * np.linalg.norm(v))
        idx = np.argmax(sims)

        if sims[idx] >= 0.52: # Umbral ajustado
            return textos[idx]
    except:
        pass

    return ""


# =============================================================================
# LEVENSHTEIN MATCH (Aproximado)
# =============================================================================

def similar(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def match_aprox(fn, keys, threshold=0.66):
    base = os.path.splitext(fn)[0].lower()
    best = ""
    best_score = 0
    
    # Optimización: solo comparar strings de longitud similar
    l_base = len(base)
    candidates = [k for k in keys if abs(len(k) - l_base) < 6]

    for k in candidates:
        s = similar(base, k)
        if s > best_score:
            best_score = s
            best = k

    if best_score >= threshold:
        return best
    return ""


# =============================================================================
# CARGA DE DATOS
# =============================================================================

def load_df(path):
    try: return pd.read_csv(path, encoding="utf-8")
    except:
        try: return pd.read_csv(path, encoding="latin-1")
        except: return pd.DataFrame()


def cargar_catalogos():
    rows = []
    for path in CATALOGOS:
        if not os.path.exists(path): continue
        df = load_df(path)
        df.columns = [c.strip() for c in df.columns]
        col_f = next((c for c in df.columns if "Filename" in c), None)
        col_d = next((c for c in df.columns if "Nombre" in c or "Descripcion" in c or "Identificacion" in c), None)
        if col_f and col_d:
            for _, r in df.iterrows():
                f = str(r[col_f]).strip().lower()
                d = limpiar(str(r[col_d]).strip())
                if len(d) > 3: rows.append((f, d))
    return rows


def cargar_inv():
    if not os.path.exists(INVENTARIO): return []
    df = load_df(INVENTARIO)
    col_img = next((c for c in df.columns if "IMAGEN" in c), None)
    col_d = next((c for c in df.columns if "DESCRIP" in c), None)
    rows = []
    if col_img and col_d:
        for _, r in df.iterrows():
            f = str(r[col_img]).strip().lower()
            d = limpiar(str(r[col_d]).strip())
            if f and len(d) > 3: rows.append((f, d))
    return rows


def cargar_excel(path):
    rows = []
    if not os.path.exists(path): return rows
    try:
        df = pd.read_excel(path)
        col_ver = next((c for c in df.columns if "VER IMAGEN" in c), None)
        col_d = next((c for c in df.columns if "DESCRIP" in c), None)

        for _, r in df.iterrows():
            desc = limpiar(str(r[col_d]).strip()) if col_d else ""
            if col_ver:
                img = str(r[col_ver]).strip().lower()
                if img and len(desc) > 3: rows.append((img, desc))
            elif len(desc) > 3:
                rows.append((desc.lower(), desc))
    except: pass
    return rows


# =============================================================================
# RESOLUCIÓN DE NOMBRE FINAL
# =============================================================================

def resolver_nombre(fn, full, mapa, vecs, textos, vision_cache):
    base = fn.lower()

    # 1. Match Exacto
    if base in mapa:
        return "MATCH_EXACTO", mapa[base]

    # 2. Match Aproximado (typos)
    # Usamos las llaves del mapa como candidatos
    approx = match_aprox(base, list(mapa.keys()))
    if approx:
        return "MATCH_APROX", mapa[approx]

    # 3. Embedding
    em = resolver_emb(fn, vecs, textos)
    if em:
        return "EMBEDDING", em

    # 4. Vision
    vis = vision(full, vision_cache)
    if vis:
        return "VISION", vis

    # 5. Fallback
    return "FALLBACK", limpiar(os.path.splitext(fn)[0])


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("\n=======================================")
    print(" 🚀 RENOMBRADOR KAIQI v23.1 — STABLE")
    print("=======================================\n")

    # Cargar datos humanos
    cat = cargar_catalogos()
    inv = cargar_inv()
    jc = cargar_excel(JC)
    yoko = cargar_excel(YOKO)

    # Prioridad: Inventario → JC → Yoko → Catálogos
    mapa = {}
    for k, v in cat + yoko + jc + inv:
        mapa[k] = v

    textos = list(set(mapa.values()))
    print(f"→ Referencias humanas cargadas: {len(textos)}")

    # Embeddings
    if client and textos:
        if os.path.exists(EMB_PATH):
            print("→ Cargando embeddings cacheados...")
            try:
                d = np.load(EMB_PATH)
                vecs = d["vecs"]
            except:
                print("→ Error cache, regenerando...")
                vecs = embed_lista(textos)
                np.savez(EMB_PATH, vecs=vecs)
        else:
            print("→ Generando embeddings (costo API)...")
            vecs = embed_lista(textos)
            np.savez(EMB_PATH, vecs=vecs)
    else:
        vecs = None

    # Cache Vision
    vision_cache = load_cache()

    log = []
    hashes = {}

    for folder in RUTAS_ENTRADA:
        if not os.path.exists(folder):
            continue

        print(f"\n>>> Carpeta: {os.path.basename(folder)}")

        for fn in os.listdir(folder):
            if not fn.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                continue

            full = os.path.join(folder, fn)

            # Deduplicación física
            try:
                h = sha1_file(full)
            except:
                continue

            if h in hashes:
                new = evitar_conflicto(DIR_DUP, fn)
                shutil.move(full, os.path.join(DIR_DUP, new))
                log.append([fn, new, "DUPLICADO", "MOVIDO", h])
                continue

            hashes[h] = fn

            # Resolver nombre
            estrategia, nombre = resolver_nombre(fn, full, mapa, vecs, textos, vision_cache)

            s = slug(nombre)
            if len(s) < 3:
                s = "pieza-generica-moto"

            new = evitar_conflicto(DIR_SALIDA, f"{s}.jpg")
            dest = os.path.join(DIR_SALIDA, new)

            if convertir_jpg(full, dest):
                print(f"   [{estrategia}] {fn} -> {new}")
                log.append([fn, new, estrategia, "EXITO", h])
            else:
                print(f"   [ERR] Conversión fallida: {fn}")
                log.append([fn, "", estrategia, "FALLO", h])

    # Log
    pd.DataFrame(log, columns=["original", "final", "estrategia", "estado", "sha1"]).to_csv(
        LOG_PATH, sep=";", index=False
    )

    save_cache(vision_cache)

    print("\n=======================================")
    print(" ✅ RENOMBRADO COMPLETO — v23.1")
    print("=======================================")
    print(f" → Salida: {DIR_SALIDA}")
    print(f" → Duplicados: {DIR_DUP}")
    print(f" → Log: {LOG_PATH}")
    print(f" → Cache Vision: {CACHE_VISION}")


if __name__ == "__main__":
    main()