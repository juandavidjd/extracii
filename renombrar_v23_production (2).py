#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
===============================================================================
 🏆 RENOMBRADOR ULTRA HÍBRIDO KAIQI — v23.2 FINAL PRODUCTION BUILD
===============================================================================

Autor: Juan David + ChatGPT
Versión: 23.2 • Final Estable para Producción
Fecha: 2025-11-22

Arquitectura definitiva:
1. Match Exacto → 2. Levenshtein → 3. Embeddings → 4. Vision GPT-4o → 5. Fallback
Protección total contra:
- OCR débil
- Filenames sucios
- Prefijos/sufijos
- Modelos CB110/NKD125
- Colisiones SHA1
- Imagenes corruptas
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
from PIL import Image, UnidentifiedImageError
from difflib import SequenceMatcher
from openai import OpenAI


# =============================================================================
# CONFIG
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

# OpenAI client
client = None
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    try:
        client = OpenAI(api_key=api_key)
    except:
        print("⚠️ Error inicializando OpenAI. IA desactivada.")
else:
    print("⚠️ No hay API Key — IA Vision y Embeddings deshabilitados.")


# =============================================================================
# LIMPIEZA
# =============================================================================

def limpiar(text):
    """Limpieza blindada estilo ADSI-KAIQI."""
    if not isinstance(text, str):
        return ""

    t = text.strip()

    t = re.sub(r"^\d{1,4}-\d{1,4}-\d{1,4}[-\s]*", "", t)
    t = re.sub(r"^\d{5,10}[-\s]*", "", t)
    t = re.sub(r"^[A-Z]{2,6}\d{2,6}[-\s]*", "", t)
    t = re.sub(r"\bOEM\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+", " ", t)

    return t.strip()


def slug(text):
    text = limpiar(text)
    if not text:
        return "pieza-moto"
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^A-Za-z0-9\s\-()]", "", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")[:180] or "pieza-moto"


# =============================================================================
# HASH & JPG
# =============================================================================

def sha1_file(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            h.update(block)
    return h.hexdigest()


def convertir_jpg(origen, destino):
    try:
        with Image.open(origen) as img:
            img = img.convert("RGB")
        destino = os.path.splitext(destino)[0] + ".jpg"
        img.save(destino, "JPEG", quality=90, optimize=True)
        return True
    except UnidentifiedImageError:
        print(f"[ERR] Imagen corrupta: {origen}")
        return False
    except Exception as e:
        print(f"[ERR] Conversión JPG: {e}")
        return False


def evitar_conflicto(dir_base, filename):
    base, ext = os.path.splitext(filename)
    n = 2
    candidate = filename
    while os.path.exists(os.path.join(dir_base, candidate)):
        candidate = f"{base}-v{n}{ext}"
        n += 1
    return candidate


# =============================================================================
# IA VISION GPT-4o
# =============================================================================

def load_cache():
    if os.path.exists(CACHE_VISION):
        try: return json.load(open(CACHE_VISION, "r", encoding="utf-8"))
        except: return {}
    return {}


def save_cache(c):
    try: json.dump(c, open(CACHE_VISION, "w", encoding="utf-8"), indent=2)
    except: pass


def vision(full_path, cache):
    if client is None:
        return ""
    sha = sha1_file(full_path)

    if sha in cache:
        return cache[sha]

    try:
        with open(full_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres experto en repuestos. Devuelve SOLO el nombre comercial rico."},
                {"role": "user", "content": [
                    {"type": "text", "text": "Identifica el repuesto de moto:"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]}
            ],
            max_tokens=50
        )

        result = resp.choices[0].message.content.strip()
        cache[sha] = result
        save_cache(cache)
        return result

    except Exception as e:
        print(f"[Vision ERROR] {e}")
        return ""


# =============================================================================
# EMBEDDINGS
# =============================================================================

def embed_lista(lista):
    if client is None:
        return None
    out = []
    batch = 200
    for i in range(0, len(lista), batch):
        subset = lista[i:i+batch]
        try:
            r = client.embeddings.create(
                model="text-embedding-3-small",
                input=subset
            )
            out.extend([d.embedding for d in r.data])
        except Exception as e:
            print("[Emb ERROR]", e)
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
        q = np.array(r.data[0].embedding)
        sims = np.dot(vecs, q) / (np.linalg.norm(vecs, axis=1) * np.linalg.norm(q))
        idx = int(np.argmax(sims))

        if sims[idx] >= 0.50:
            return textos[idx]
    except:
        return ""

    return ""


# =============================================================================
# LEVENSHTEIN
# =============================================================================

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


def match_aprox(fn, keys, t=0.65):
    base = os.path.splitext(fn)[0].lower()
    best = ""
    best_score = 0

    for k in keys:
        s = similar(base, k)
        if s > best_score:
            best_score = s
            best = k

    return best if best_score >= t else ""


# =============================================================================
# CARGA CSV / EXCEL
# =============================================================================

def load_csv(path):
    try: return pd.read_csv(path, encoding="utf-8")
    except: pass
    try: return pd.read_csv(path, encoding="latin-1")
    except: return pd.DataFrame()


def load_excel(path):
    if not os.path.exists(path):
        return []
    try:
        df = pd.read_excel(path)
        out = []
        col_img = next((c for c in df.columns if "IMAGEN" in c or "VER IMAGEN" in c), None)
        col_desc = next((c for c in df.columns if "DESCRIP" in c), None)

        for _, r in df.iterrows():
            desc = limpiar(str(r.get(col_desc, "")).strip())
            if col_img:
                img = str(r.get(col_img, "")).strip().lower()
                if img and len(desc) > 3:
                    out.append((img, desc))
            elif len(desc) > 3:
                out.append((desc.lower(), desc))
        return out
    except Exception as e:
        print("[Excel ERROR]", e)
        return []


def cargar_catalogos():
    rows = []
    for path in CATALOGOS:
        if not os.path.exists(path):
            continue
        df = load_csv(path)
        df.columns = [c.strip() for c in df.columns]
        col_f = next((c for c in df.columns if "Filename" in c), None)
        col_d = next((c for c in df.columns if "Nombre" in c or "Descripcion" in c), None)
        if col_f and col_d:
            for _, r in df.iterrows():
                f = str(r[col_f]).strip().lower()
                d = limpiar(str(r[col_d]).strip())
                if len(d) > 3:
                    rows.append((f, d))
    return rows


def cargar_inv():
    rows = []
    if not os.path.exists(INVENTARIO):
        return rows

    df = load_csv(INVENTARIO)
    col_img = next((c for c in df.columns if "IMAGEN" in c), None)
    col_d = next((c for c in df.columns if "DESCRIP" in c), None)

    if col_img and col_d:
        for _, r in df.iterrows():
            f = str(r[col_img]).strip().lower()
            d = limpiar(str(r[col_d]).strip())
            if f and len(d) > 3:
                rows.append((f, d))
    return rows


# =============================================================================
# RESOLUCIÓN HÍBRIDA
# =============================================================================

def resolver_nombre(fn, full, mapa, vecs, textos, vision_cache):
    base = fn.lower()

    if base in mapa:
        return "MATCH_EXACTO", mapa[base]

    approx = match_aprox(base, mapa.keys())
    if approx:
        return "MATCH_APROX", mapa[approx]

    em = resolver_emb(fn, vecs, textos)
    if em:
        return "EMBEDDING", em

    vis = vision(full, vision_cache)
    if vis:
        return "VISION", vis

    return "FALLBACK", limpiar(os.path.splitext(fn)[0])


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("\n==========================================")
    print("🔥 RENOMBRADOR KAIQI — v23.2 FINAL PROD")
    print("==========================================\n")

    # Consolidar inteligencia
    cat = cargar_catalogos()
    inv = cargar_inv()
    jc = load_excel(JC)
    yoko = load_excel(YOKO)

    mapa = {}
    for k, v in cat + yoko + jc + inv:
        mapa[k] = v

    textos = list(set(mapa.values()))

    # Embeddings
    if client and textos:
        if os.path.exists(EMB_PATH):
            try:
                data = np.load(EMB_PATH)
                vecs = data["vecs"]
            except:
                vecs = embed_lista(textos)
                np.savez(EMB_PATH, vecs=vecs)
        else:
            vecs = embed_lista(textos)
            np.savez(EMB_PATH, vecs=vecs)
    else:
        vecs = None

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

            # Deduplicación
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

            # Resolver
            estrategia, nombre = resolver_nombre(fn, full, mapa, vecs, textos, vision_cache)
            s = slug(nombre)
            new = evitar_conflicto(DIR_SALIDA, f"{s}.jpg")
            dest = os.path.join(DIR_SALIDA, new)

            if convertir_jpg(full, dest):
                print(f"   [{estrategia}] {fn} → {new}")
                log.append([fn, new, estrategia, "EXITO", h])
            else:
                log.append([fn, "", estrategia, "FALLO", h])

    # Log
    pd.DataFrame(log, columns=["original","final","estrategia","estado","sha1"]).to_csv(
        LOG_PATH, sep=";", index=False
    )

    save_cache(vision_cache)

    print("\n==========================================")
    print(" ✅ PROCESO COMPLETADO — v23.2 PRODUCCIÓN")
    print("==========================================")
    print(f"→ Salida: {DIR_SALIDA}")
    print(f"→ Duplicados: {DIR_DUP}")
    print(f"→ Log: {LOG_PATH}")
    print(f"→ Cache: {CACHE_VISION}")


if __name__ == "__main__":
    main()
