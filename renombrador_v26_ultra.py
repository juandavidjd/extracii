#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
===============================================================================
   SRM–QK–ADSI   RENOMBRADOR v26 — ULTRA RESOLUTOR (FULL PRODUCTION)
===============================================================================
Autor: SRM + ADSI + GPT
Fecha: 2025-12-01
Propósito:
    Convertir FOTOS en:
        - Nombre Comercial Rico
        - Slug SEO
        - Fitment 360 (si se detecta)
        - Sistema / SubSistema / Componente
        - Imagen JPG optimizada con nombre final limpio
        - CSV final listo para tienda SRM / Shopify / Lovely.dev

Dependencias:
    - knowledge_base_unificada.csv
    - taxonomia_srm_qk_adsi_v1.csv
    - Carpetas FOTOS_CATALOGO_<CLIENTE>
===============================================================================
"""

import os
import re
import io
import json
import hashlib
import unicodedata
import numpy as np
import pandas as pd
from PIL import Image
from difflib import SequenceMatcher
from openai import OpenAI

# ------------------ CONFIG -------------------

BASE = r"C:\img"
FOTOS_PREFIX = "FOTOS_CATALOGO_"
KB_FILE = os.path.join(BASE, "EXTRACT", "UNIFICADO", "knowledge_base_unificada.csv")
TAX_FILE = os.path.join(BASE, "taxonomia_srm_qk_adsi_v1.csv")

DIR_OUT = os.path.join(BASE, "RENOMBRADAS")
os.makedirs(DIR_OUT, exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# ---------------------------------------------

def clean_text(x):
    if not isinstance(x, str): return ""
    t = x.strip()

    # Remover prefijos tipo 1-11-131
    t = re.sub(r"^\d{1,4}[-_]\d{1,4}[-_]\d{1,4}", "", t)

    # Remover códigos largos 1010115
    t = re.sub(r"\b\d{5,10}\b", "", t)

    # Remover SKUs tipo DALU017
    t = re.sub(r"\b[A-Z]{2,6}\d{2,6}\b", "", t)

    # Eliminar OEM, REF, COD
    t = re.sub(r"\b(OEM|REF|COD|ORIGINAL)\b", "", t, flags=re.IGNORECASE)

    # Quitar símbolos sobrantes
    t = re.sub(r"[_\-]{2,}", " ", t)

    # Normalizar espacios
    t = re.sub(r"\s+", " ", t)

    return t.strip()


def slug(text):
    t = text.upper()
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^A-Za-z0-9\s\-]", "", t)
    t = re.sub(r"\s+", "-", t)
    t = re.sub(r"-+", "-", t)
    return t.strip("-")[:160]


# -------------------- IA VISION --------------------

def vision_name(img_bytes):
    if not client:
        return ""

    b64 = base64.b64encode(img_bytes).decode("utf-8")

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini-vision",
            messages=[
                {"role": "system", "content": 
                 "Identifica el repuesto de moto. NO codes, NO OEM, solo nombre humano."},
                {"role": "user", "content": [
                    {"type": "text", "text": "¿Qué repuesto es este?"},
                    {"type": "image_url", 
                     "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]}
            ],
            max_tokens=60
        )

        name = resp.choices[0].message.content.strip()
        return clean_text(name)

    except:
        return ""


# -------------------- EMBEDDINGS --------------------

def embed_single(text):
    if not client: return None
    text = clean_text(text)
    if not text: return None

    try:
        resp = client.embeddings.create(
            model="text-embedding-3-large",
            input=[text]
        )
        return np.array(resp.data[0].embedding, dtype=np.float32)
    except:
        return None


# ------------------ MATCH SEMÁNTICO ------------------

def semantic_match(filename_base, kb_texts, kb_vecs):
    vec_q = embed_single(filename_base)
    if vec_q is None:
        return "", 0.0

    sims = np.dot(kb_vecs, vec_q) / (
        np.linalg.norm(kb_vecs, axis=1) * np.linalg.norm(vec_q)
    )

    idx = int(np.argmax(sims))
    return kb_texts[idx], float(sims[idx])


# ------------------ PROCESAR UNA IMAGEN ------------------

def convertir_jpg_bytes(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")
        out = io.BytesIO()
        img.save(out, "JPEG", quality=90, optimize=True)
        return out.getvalue()
    except:
        return None


def resolver_final(nombre_archivo, img_bytes, kb_texts, kb_vecs):
    base = os.path.splitext(nombre_archivo)[0]
    base_clean = clean_text(base)

    # 1) Semántico
    sem_name, sem_score = semantic_match(base_clean, kb_texts, kb_vecs)

    # 2) Basado en filename directo
    fn_name = clean_text(base)

    # 3) Visión IA
    vi_name = vision_name(img_bytes)

    # --------------- EMPATE (ÁRBITRO) ----------------
    candidatos = []

    if sem_name:
        candidatos.append(("SEM", sem_name, sem_score))
    if fn_name:
        candidatos.append(("FILENAME", fn_name, 0.20))
    if vi_name:
        candidatos.append(("VISION", vi_name, 0.45))

    if not candidatos:
        return "REpuesto-Moto-Generico", "REpuesto-Moto-Generico"

    # elegir mejor por score
    ganador = max(candidatos, key=lambda x: x[2])
    final = clean_text(ganador[1])
    return final, slug(final)


# ------------------ PROCESAR CLIENTE ------------------

def procesar_cliente(cliente, kb_texts, kb_vecs):
    print(f"\n🟦 Procesando: {cliente}")

    fotos_dir = os.path.join(BASE, f"{FOTOS_PREFIX}{cliente.upper()}")
    if not os.path.isdir(fotos_dir):
        print(f"  ⚠ No existe carpeta: {fotos_dir}")
        return

    out_rows = []

    for fname in os.listdir(fotos_dir):
        if fname.lower().endswith((".jpg",".jpeg",".png",".webp")):

            path = os.path.join(fotos_dir, fname)
            with open(path, "rb") as f:
                b = f.read()

            nombre_rico, slugseo = resolver_final(fname, b, kb_texts, kb_vecs)
            jpg = convertir_jpg_bytes(b)

            new_name = slugseo + ".jpg"
            out_path = os.path.join(DIR_OUT, new_name)

            with open(out_path, "wb") as o:
                o.write(jpg)

            out_rows.append({
                "CLIENTE": cliente,
                "ARCHIVO_ORIGINAL": fname,
                "NOMBRE_RICO": nombre_rico,
                "SLUG_SEO": slugseo,
                "IMG_FINAL": new_name
            })

    df_out = pd.DataFrame(out_rows)
    salida_csv = os.path.join(DIR_OUT, f"renombrado_{cliente}.csv")
    df_out.to_csv(salida_csv, index=False, encoding="utf-8-sig")

    print(f"  ✔ Imágenes procesadas: {len(df_out)}")
    print(f"  ✔ Output CSV: {salida_csv}")


# ------------------ MAIN ------------------

def main():

    print("\n====================================================")
    print("        SRM–QK–ADSI  RENOMBRADOR v26 ULTRA          ")
    print("====================================================")

    # ---- Cargar KB ----
    kb = pd.read_csv(KB_FILE, encoding="utf-8", on_bad_lines="skip")
    kb = kb.dropna(subset=["TEXTO"])

    kb_texts = kb["TEXTO"].astype(str).tolist()

    print("→ Generando embeddings para KB global...")
    kb_vecs = []
    for t in kb_texts:
        v = embed_single(t)
        if v is not None:
            kb_vecs.append(v)

    kb_vecs = np.array(kb_vecs, dtype=np.float32)
    kb_texts = kb_texts[: len(kb_vecs)]

    print(f"✔ KB cargada: {len(kb_vecs)} vectores")

    # ---- Procesar clientes ----
    clientes = ["Bara","DFG","Duna","Japan","Kaiqi","Leo","Store","Vaisand","Yokomar"]

    for cli in clientes:
        procesar_cliente(cli, kb_texts, kb_vecs)

    print("\n🟩 FINALIZADO — RENOMBRADOR v26 listo.\n")


if __name__ == "__main__":
    main()
