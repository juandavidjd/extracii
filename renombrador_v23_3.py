#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=================================================================================
 🏆 RENOMBRADOR ULTRA HÍBRIDO KAIQI — v23.3 ENTERPRISE API EDITION
=================================================================================

Incluye:
✔ Motor v23.2 (núcleo estable)
✔ API FastAPI (procesamiento remoto)
✔ Dashboard Web listo para:

   - Procesar carpetas
   - Ver logs
   - Subir imágenes
   - Renombrar individualmente

✔ CLI (command line interface)
✔ Listo para empaquetar .EXE (PyInstaller)

=================================================================================
"""

import os
import re
import json
import base64
import shutil
import hashlib
import unicodedata
import argparse
import uvicorn
import numpy as np
import pandas as pd
from difflib import SequenceMatcher
from fastapi import FastAPI, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from PIL import Image, UnidentifiedImageError
from openai import OpenAI


# =============================================================================
# CONFIG GENERAL
# =============================================================================

BASE = r"C:\img"

RUTAS_ENTRADA_DEFAULT = [
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
LOG_PATH = os.path.join(BASE, "log_renombrado_v23_3.csv")
CACHE_VISION = os.path.join(BASE, "vision_cache_v23_3.json")
EMB_PATH = os.path.join(BASE, "embeddings_v23_3.npz")

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

# Cliente OpenAI
client = None
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    try:
        client = OpenAI(api_key=api_key)
    except:
        print("⚠️ Error inicializando OpenAI — Vision/Embeddings OFF.")
else:
    print("⚠️ OPENAI_API_KEY no existe — Vision/Embeddings OFF.")


# =============================================================================
# UTILIDADES
# =============================================================================

def limpiar(text):
    """Limpieza blindada ADSI."""
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
    t = limpiar(text)
    if not t:
        return "pieza-moto"
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^A-Za-z0-9\s\-()]", "", t)
    t = re.sub(r"\s+", "-", t)
    t = re.sub(r"-+", "-", t)
    return t.strip("-")[:180] or "pieza-moto"


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
    except:
        return False


def evitar_conflicto(dir_base, filename):
    base, ext = os.path.splitext(filename)
    n = 2
    candidate = filename
    while os.path.exists(os.path.join(dir_base, candidate)):
        candidate = f"{base}-v{n}{ext}"
        n += 1
    return candidate


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
# IA — Vision y Embeddings
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
                {"role": "system",
                 "content": "Eres experto en repuestos de motos. Devuelve SOLO el nombre comercial rico."},
                {"role": "user",
                 "content": [
                     {"type": "text", "text": "Identifica este repuesto:"},
                     {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]}
            ],
            max_tokens=50
        )

        name = resp.choices[0].message.content.strip()
        cache[sha] = name
        save_cache(cache)
        return name
    except:
        return ""


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
        except:
            pass
    return np.array(out)


def resolver_emb(fn, vecs, textos):
    if client is None or vecs is None:
        return ""
    q = limpiar(os.path.splitext(fn)[0])
    if len(q) < 3:
        return ""
    try:
        r = client.embeddings.create(
            model="text-embedding-3-small",
            input=[q]
        )
        qv = np.array(r.data[0].embedding)
        sims = np.dot(vecs, qv) / (np.linalg.norm(vecs, axis=1) * np.linalg.norm(qv))
        idx = int(np.argmax(sims))
        if sims[idx] >= 0.50:
            return textos[idx]
    except:
        return ""
    return ""


# =============================================================================
# CARGA CSV/EXCEL
# =============================================================================

def load_csv(path):
    try: return pd.read_csv(path, encoding="utf-8")
    except: pass
    try: return pd.read_csv(path, encoding="latin-1")
    except: return pd.DataFrame()


def load_excel(path):
    rows = []
    if not os.path.exists(path):
        return rows
    try:
        df = pd.read_excel(path)
        col_img = next((c for c in df.columns if "IMAGEN" in c or "VER IMAGEN" in c), None)
        col_desc = next((c for c in df.columns if "DESCRIP" in c), None)

        for _, r in df.iterrows():
            d = limpiar(str(r.get(col_desc, "")).strip())
            if col_img:
                img = str(r.get(col_img, "")).strip().lower()
                if img and len(d) > 3:
                    rows.append((img, d))
            else:
                if len(d) > 3:
                    rows.append((d.lower(), d))
    except:
        pass
    return rows


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
# API FASTAPI
# =============================================================================

app = FastAPI(title="Renombrador KAIQI v23.3 API")

@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <h1>KAIQI Renombrador v23.3</h1>
    <p>API funcionando correctamente.</p>
    <ul>
        <li><a href="/dashboard">Dashboard Web</a></li>
    </ul>
    """


@app.get("/status")
def status():
    return {"status": "ok", "engine": "v23.3", "ia_enabled": client is not None}


@app.post("/rename-file")
async def api_rename_file(file: UploadFile):
    """Procesa un archivo enviado por HTTP."""
    original_path = os.path.join(BASE, "_temp_upload_" + file.filename)
    with open(original_path, "wb") as f:
        f.write(await file.read())

    # Reusar lógica v23.2
    vision_cache = load_cache()
    sha = sha1_file(original_path)

    # Resolver nombre
    cat = cargar_catalogos()
    inv = cargar_inv()
    jc = load_excel(JC)
    yoko = load_excel(YOKO)

    mapa = {}
    for k, v in cat + yoko + jc + inv:
        mapa[k] = v
    textos = list(set(mapa.values()))

    if os.path.exists(EMB_PATH):
        vecs = np.load(EMB_PATH)["vecs"]
    else:
        vecs = None

    estrategia, nombre = resolver_nombre(file.filename, original_path, mapa, vecs, textos, vision_cache)
    sl = slug(nombre)
    new_fn = evitar_conflicto(DIR_SALIDA, sl + ".jpg")

    destino = os.path.join(DIR_SALIDA, new_fn)
    convertir_jpg(original_path, destino)

    return {
        "original": file.filename,
        "final": new_fn,
        "estrategia": estrategia
    }


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    """Mini dashboard HTML."""
    return """
    <html><body>
    <h1>KAIQI Renombrador v23.3 — Dashboard</h1>
    <p>Subir una imagen para renombrar:</p>
    <form action="/rename-file" enctype="multipart/form-data" method="post">
      <input type="file" name="file"/>
      <input type="submit" value="Procesar"/>
    </form>
    </body></html>
    """


@app.post("/rename-folder")
def api_rename_folder(folder_path: str):
    """Procesa una carpeta remota."""
    if not os.path.exists(folder_path):
        return {"error": "Folder no existe."}

    res = rename_folder(folder_path)
    return {"procesado": len(res), "detalles": res}


# =============================================================================
# FUNCIÓN PRINCIPAL (LOOP LOCAL)
# =============================================================================

def rename_folder(folder):
    """Procesa una carpeta completa (para CLI y API)."""
    vision_cache = load_cache()

    # Cargar inteligencia
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
                vecs = np.load(EMB_PATH)["vecs"]
            except:
                vecs = embed_lista(textos)
                np.savez(EMB_PATH, vecs=vecs)
        else:
            vecs = embed_lista(textos)
            np.savez(EMB_PATH, vecs=vecs)
    else:
        vecs = None

    resultados = []
    hashes = {}

    for fn in os.listdir(folder):
        if not fn.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            continue

        full = os.path.join(folder, fn)

        try:
            sha = sha1_file(full)
        except:
            continue

        if sha in hashes:
            new = evitar_conflicto(DIR_DUP, fn)
            shutil.move(full, os.path.join(DIR_DUP, new))
            resultados.append([fn, new, "DUPLICADO"])
            continue

        hashes[sha] = fn

        estrategia, nombre = resolver_nombre(fn, full, mapa, vecs, textos, vision_cache)
        sl = slug(nombre)
        new = evitar_conflicto(DIR_SALIDA, f"{sl}.jpg")
        destino = os.path.join(DIR_SALIDA, new)

        convertir_jpg(full, destino)

        resultados.append([fn, new, estrategia])

    save_cache(vision_cache)
    return resultados


# =============================================================================
# CLI
# =============================================================================

def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", help="Carpeta a procesar")
    parser.add_argument("--api", action="store_true", help="Levanta API FastAPI")
    args = parser.parse_args()

    if args.api:
        uvicorn.run("renombrador_v23_3:app", host="0.0.0.0", port=8080, reload=True)
        return

    folder = args.folder or BASE
    print("Procesando carpeta:", folder)
    res = rename_folder(folder)
    print("Total procesados:", len(res))


if __name__ == "__main__":
    cli()
