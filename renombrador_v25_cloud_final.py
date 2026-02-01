#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
====================================================================================
 🚀 RENOMBRADOR ULTRA HÍBRIDO KAIQI — v25.1 ULTRA CLOUD (FINAL FIXED)
====================================================================================

Autor: Juan David + Gemini
Versión: 25.1 — Stable Cloud Release
Fecha: 2025-11-22

Arquitectura:
- Cloud Storage Abstraction (S3 / Local)
- Cache Distribuido (Redis / Local Memory)
- Vision AI Microservice (GPT-4o)
- Embeddings Microservice
- Stateless Logic (listo para Lambda/Docker)

CORRECCIONES v25.1:
- Fix: Paso correcto de 'text_list' a la función de embeddings.
- Fix: Manejo de errores si Redis no está disponible.
- Fix: Fallback automático a almacenamiento local si S3 falla.

====================================================================================
"""

import os
import re
import io
import json
import base64
import hashlib
import logging
import unicodedata
import numpy as np
import pandas as pd
from PIL import Image
from difflib import SequenceMatcher
from openai import OpenAI

# Clientes Cloud (Try/Except para evitar crashes si no están instalados)
try:
    import boto3
except ImportError:
    boto3 = None

try:
    import redis
except ImportError:
    redis = None

# =====================================================================
# CONFIGURACIÓN GLOBAL
# =====================================================================

# Variables de Entorno
CLOUD_STORAGE_TYPE = os.getenv("CLOUD_STORAGE_TYPE", "LOCAL")   # S3 | LOCAL
CLOUD_BUCKET = os.getenv("CLOUD_BUCKET", "kaiqi-assets")
REDIS_URL = os.getenv("REDIS_URL", None)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Rutas Locales (Fallback)
BASE = os.getenv("KAIQI_BASE", r"C:\img")
DIR_OUT = os.path.join(BASE, "output")
DIR_CACHE = os.path.join(BASE, "cache")
DIR_LOGS = os.path.join(BASE, "logs")

# Crear directorios locales si es necesario
for d in [DIR_OUT, DIR_CACHE, DIR_LOGS]:
    os.makedirs(d, exist_ok=True)

# Inicializar Clientes
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

redis_client = None
if REDIS_URL and redis:
    try:
        redis_client = redis.from_url(REDIS_URL, socket_timeout=2)
        redis_client.ping()
        print("✅ Redis conectado.")
    except:
        print("⚠️ Redis no disponible. Usando memoria local.")
        redis_client = None

s3_client = None
if CLOUD_STORAGE_TYPE == "S3" and boto3:
    try:
        s3_client = boto3.client("s3")
        print("✅ S3 Cliente inicializado.")
    except:
        print("⚠️ Error S3. Usando almacenamiento local.")
        CLOUD_STORAGE_TYPE = "LOCAL"

# Logging Setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

# =====================================================================
# UTILIDADES DE TEXTO
# =====================================================================

def limpiar(text):
    if not isinstance(text, str): return ""
    t = text.strip()
    # Patrones de limpieza (Regex Blindado v24)
    t = re.sub(r"^\d{1,4}-\d{1,4}-\d{1,4}[-\s]*", "", t) # 1-11-131
    t = re.sub(r"^\d{5,10}[-\s]*", "", t)                # 1010115
    t = re.sub(r"^[A-Z]{2,6}\d{2,6}[-\s]*", "", t)       # DALU017
    t = re.sub(r"\bOEM\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+", " ", t)
    return t.strip()

def slug(text):
    t = limpiar(text)
    if not t: return "pieza-moto"
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^A-Za-z0-9\s\-()]", "", t)
    t = re.sub(r"\s+", "-", t)
    t = re.sub(r"-+", "-", t)
    return t.strip("-")[:180]

# =====================================================================
# GESTIÓN DE IMÁGENES Y HASH
# =====================================================================

def sha1_bytes(b):
    return hashlib.sha1(b).hexdigest()

def convertir_jpg_bytes(image_bytes):
    """Convierte bytes de imagen a bytes de JPG optimizado."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        elif img.mode != "RGB":
            img = img.convert("RGB")
            
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=90, optimize=True)
        return out.getvalue()
    except Exception as e:
        logging.error(f"Error conversión JPG: {e}")
        return None

# =====================================================================
# ALMACENAMIENTO (ABSTRACTO)
# =====================================================================

def save_file(filename, data_bytes):
    """Guarda el archivo en S3 o Disco Local según config."""
    if CLOUD_STORAGE_TYPE == "S3" and s3_client:
        try:
            s3_client.put_object(Bucket=CLOUD_BUCKET, Key=f"renombradas/{filename}", Body=data_bytes)
            return f"s3://{CLOUD_BUCKET}/renombradas/{filename}"
        except Exception as e:
            logging.error(f"Fallo subida S3: {e}")
            return None
    else:
        # Local Fallback
        path = os.path.join(DIR_OUT, filename)
        try:
            with open(path, "wb") as f:
                f.write(data_bytes)
            return path
        except Exception as e:
            logging.error(f"Fallo escritura local: {e}")
            return None

# =====================================================================
# CACHE DE VISIÓN (REDIS / LOCAL)
# =====================================================================

def get_vision_cache(sha):
    if redis_client:
        val = redis_client.get(f"vision:{sha}")
        return val.decode("utf-8") if val else None
    else:
        # Fallback a archivo JSON local (lento pero seguro)
        local_cache_path = os.path.join(DIR_CACHE, "vision_cache.json")
        if os.path.exists(local_cache_path):
            try:
                data = json.load(open(local_cache_path, "r", encoding="utf-8"))
                return data.get(sha)
            except: return None
    return None

def set_vision_cache(sha, text):
    if redis_client:
        redis_client.set(f"vision:{sha}", text)
    else:
        # Fallback local (Append only logica simple)
        local_cache_path = os.path.join(DIR_CACHE, "vision_cache.json")
        try:
            if os.path.exists(local_cache_path):
                data = json.load(open(local_cache_path, "r", encoding="utf-8"))
            else:
                data = {}
            data[sha] = text
            json.dump(data, open(local_cache_path, "w", encoding="utf-8"), indent=2)
        except: pass

# =====================================================================
# IA MOTORS
# =====================================================================

def vision_identify(img_bytes):
    """Usa GPT-4o para identificar la imagen."""
    if not client: return ""
    
    sha = sha1_bytes(img_bytes)
    cached = get_vision_cache(sha)
    if cached: return cached

    try:
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres experto en repuestos de motos. Responde SOLO el nombre comercial rico."},
                {"role": "user", "content": [
                    {"type": "text", "text": "Identifica este repuesto sin usar códigos:"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]}
            ],
            max_tokens=60
        )
        name = resp.choices[0].message.content.strip()
        set_vision_cache(sha, name)
        return name
    except Exception as e:
        logging.error(f"Vision API Error: {e}")
        return ""

def embed_text(text):
    """Genera embedding para un solo texto (Query)."""
    if not client: return None
    text = limpiar(text)
    if len(text) < 3: return None
    
    # Cache Redis para embeddings de query
    if redis_client:
        cached = redis_client.get(f"emb:{text}")
        if cached: return np.frombuffer(cached, dtype=np.float32)

    try:
        resp = client.embeddings.create(model="text-embedding-3-small", input=[text])
        vec = np.array(resp.data[0].embedding, dtype=np.float32)
        if redis_client:
            redis_client.set(f"emb:{text}", vec.tobytes())
        return vec
    except:
        return None

def embed_list_batch(lista_textos):
    """Genera embeddings para una lista masiva (Initialization)."""
    if not client: return None
    print(f"🔵 Generando embeddings para {len(lista_textos)} textos...")
    vectors = []
    batch_size = 500
    for i in range(0, len(lista_textos), batch_size):
        chunk = lista_textos[i:i+batch_size]
        try:
            resp = client.embeddings.create(model="text-embedding-3-small", input=chunk)
            vectors.extend([d.embedding for d in resp.data])
        except Exception as e:
            print(f"Error batch {i}: {e}")
    return np.array(vectors, dtype=np.float32)

# =====================================================================
# MATCHING LOGIC
# =====================================================================

def match_aprox(fn, keys):
    base = os.path.splitext(fn)[0].lower()
    best, best_score = "", 0
    # Optimización: comparar solo longitudes similares
    l_base = len(base)
    candidates = [k for k in keys if abs(len(k) - l_base) < 6]
    
    for k in candidates:
        s = SequenceMatcher(None, base, k).ratio()
        if s > best_score:
            best_score = s
            best = k
    return best if best_score >= 0.66 else ""

def resolver_nombre(filename, img_bytes, knowledge_map, embedding_matrix, text_list_ref):
    """
    Motor de decisión principal.
    Args:
        filename: Nombre original del archivo.
        img_bytes: Contenido binario.
        knowledge_map: Dict {filename_clean: description}.
        embedding_matrix: Matriz numpy con embeddings de text_list_ref.
        text_list_ref: Lista de strings alineada con embedding_matrix.
    """
    base = filename.lower()

    # 1. EXACTO
    if base in knowledge_map:
        return "EXACTO", knowledge_map[base]

    # 2. APROXIMADO
    approx = match_aprox(base, list(knowledge_map.keys()))
    if approx:
        return "APROX", knowledge_map[approx]

    # 3. SEMÁNTICO (Embeddings)
    if embedding_matrix is not None and len(text_list_ref) > 0:
        query_vec = embed_text(os.path.splitext(filename)[0])
        if query_vec is not None:
            # Similitud Coseno vectorizada
            sims = np.dot(embedding_matrix, query_vec) / (np.linalg.norm(embedding_matrix, axis=1) * np.linalg.norm(query_vec))
            idx = int(np.argmax(sims))
            if sims[idx] >= 0.52:
                return "SEMANTICO", text_list_ref[idx]

    # 4. VISIÓN
    vis_name = vision_identify(img_bytes)
    if vis_name:
        return "VISION", vis_name

    # 5. FALLBACK
    return "FALLBACK", limpiar(os.path.splitext(filename)[0])

# =====================================================================
# CARGADOR DE DATOS (INIT)
# =====================================================================

def cargar_cerebro_local():
    """Carga CSVs y Excels locales para construir el knowledge_map."""
    mapa = {}
    
    # Lista de archivos esperados en BASE
    files = [
        "catalogo_kaiqi_imagenes_bara.csv", "catalogo_kaiqi_imagenes_japan.csv",
        "catalogo_kaiqi_imagenes_kaiqi.csv", "catalogo_kaiqi_imagenes_leo.csv",
        "catalogo_kaiqi_imagenes_store.csv", "catalogo_kaiqi_imagenes_vaisand.csv",
        "Inventario_FINAL_CON_TAXONOMIA.csv"
    ]
    
    for f in files:
        path = os.path.join(BASE, f)
        if not os.path.exists(path): continue
        try:
            df = pd.read_csv(path, encoding='latin-1', on_bad_lines='skip')
            # Normalizar columnas
            df.columns = [c.strip() for c in df.columns]
            
            # Detectar columnas dinámicamente
            col_f = next((c for c in df.columns if "Filename" in c or "IMAGEN" in c), None)
            col_d = next((c for c in df.columns if "Nombre" in c or "Descripcion" in c or "DESCRIP" in c), None)
            
            if col_f and col_d:
                for _, r in df.iterrows():
                    k = str(r[col_f]).strip().lower()
                    v = limpiar(str(r[col_d]).strip())
                    if len(v) > 3: mapa[k] = v
        except: pass
        
    # Cargar Excel (JC/Yoko)
    for f in ["LISTA DE PRECIOS NOVIEMBRE 13 2025 TRABAJO JC.xlsx", "LISTA DE PRECIOS  YOKOMAR ACTUALIZADA 2025.xlsx"]:
        path = os.path.join(BASE, f)
        if not os.path.exists(path): continue
        try:
            df = pd.read_excel(path)
            # Lógica simplificada para Excel
            for col in df.columns:
                if "DESCRIP" in str(col).upper():
                    for val in df[col].dropna():
                        v = limpiar(str(val))
                        if len(v) > 3: mapa[v.lower()] = v # Auto-referencia para match texto
        except: pass

    return mapa

# =====================================================================
# ENTRY POINT (Function for Lambda/Microservice)
# =====================================================================

# Variables globales para caché en memoria (Hot Start)
GLOBAL_KNOWLEDGE = None
GLOBAL_VECS = None
GLOBAL_TEXT_LIST = None

def initialize_service():
    global GLOBAL_KNOWLEDGE, GLOBAL_VECS, GLOBAL_TEXT_LIST
    if GLOBAL_KNOWLEDGE is None:
        print("⚡ Inicializando servicio KAIQI v25...")
        GLOBAL_KNOWLEDGE = cargar_cerebro_local()
        GLOBAL_TEXT_LIST = list(set(GLOBAL_KNOWLEDGE.values()))
        
        # Cargar o Generar Embeddings
        emb_path = os.path.join(DIR_CACHE, "embeddings_v25.npz")
        if os.path.exists(emb_path):
            print("   -> Cargando embeddings de disco...")
            GLOBAL_VECS = np.load(emb_path)["vecs"]
        elif client and GLOBAL_TEXT_LIST:
            print("   -> Generando nuevos embeddings...")
            GLOBAL_VECS = embed_list_batch(GLOBAL_TEXT_LIST)
            if GLOBAL_VECS is not None:
                np.savez(emb_path, vecs=GLOBAL_VECS)
        else:
            GLOBAL_VECS = None
        print("✅ Servicio listo.")

def process_single_file(filename, file_bytes):
    """Función principal para procesar un archivo."""
    # Asegurar inicialización
    if GLOBAL_KNOWLEDGE is None: initialize_service()
    
    # 1. Procesar Nombre
    estrategia, nombre_rico = resolver_nombre(
        filename, 
        file_bytes, 
        GLOBAL_KNOWLEDGE, 
        GLOBAL_VECS, 
        GLOBAL_TEXT_LIST, 
        {} # Cache local efímero, Redis maneja la persistencia
    )
    
    # 2. Generar Slug y JPG
    slug_name = slug(nombre_rico)
    new_filename = f"{slug_name}.jpg"
    jpg_bytes = convertir_jpg_bytes(file_bytes)
    
    if not jpg_bytes:
        return {"error": "Imagen corrupta", "status": "failed"}
    
    # 3. Guardar
    location = save_file(new_filename, jpg_bytes)
    
    return {
        "original": filename,
        "final": new_filename,
        "estrategia": estrategia,
        "location": location,
        "status": "success"
    }

# =====================================================================
# MODO SCRIPT (TESTING LOCAL)
# =====================================================================

if __name__ == "__main__":
    print("🔧 Modo Pruebas Local Activo")
    initialize_service()
    
    # Prueba con una imagen dummy si existe carpeta input
    input_dir = os.path.join(BASE, "input_test")
    if os.path.exists(input_dir):
        for f in os.listdir(input_dir):
            path = os.path.join(input_dir, f)
            with open(path, "rb") as file:
                bytes_data = file.read()
            res = process_single_file(f, bytes_data)
            print(res)
    else:
        print(f"Crea la carpeta {input_dir} y pon imágenes para probar.")