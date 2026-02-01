#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1_renombrar_seo_kaiqi_v10_fixed.py

CORRECCIÓN: Se agrega soporte para columna 'ID_MASTER' en la detección automática.
"""

import os
import re
import csv
import json
import base64
import hashlib
import unicodedata
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
from openai import OpenAI

# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

BASE_DIR = r"C:\img"
IMAGE_DIR = os.path.join(BASE_DIR, "IMAGENES_KAIQI_MAESTRAS")

INVENTARIO_CSV = os.path.join(BASE_DIR, "Inventario_FINAL_CON_TAXONOMIA.csv")
JC_XLSX = os.path.join(BASE_DIR, "LISTA DE PRECIOS NOVIEMBRE 13 2025 TRABAJO JC.xlsx")
YOKO_XLSX = os.path.join(BASE_DIR, "LISTA DE PRECIOS  YOKOMAR ACTUALIZADA 2025.xlsx")
STORE_CSV = os.path.join(BASE_DIR, "Base_Datos_Store.csv")
LEO_CSV = os.path.join(BASE_DIR, "Base_Datos_Leo.csv")
JAPAN_CSV = os.path.join(BASE_DIR, "Base_Datos_Japan.csv")
VAISAND_CSV = os.path.join(BASE_DIR, "Base_Datos_Vaisand.csv")

LOG_DIR = os.path.join(BASE_DIR, "LOGS")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_CSV = os.path.join(LOG_DIR, "log_renombrado_seo_v10_fixed.csv")

# Parámetros de heurística
MIN_RICH_TOKENS = 5

BRAND_KEYWORDS = [
    "akt", "bajaj", "yamaha", "honda", "suzuki", "tvs", "ktm", "hero",
    "boxer", "pulsar", "apache", "nkd", "dominar", "gixxer", "cb", "cbf",
    "dr", "xr", "xre", "crypton", "libero", "viva", "st", "dinamic",
]

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client: Optional[OpenAI] = None
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)


# ============================================================
# UTILIDADES BÁSICAS
# ============================================================

def slugify(text: str) -> str:
    if not isinstance(text, str):
        text = str(text or "")
    text = text.strip()
    if not text:
        return ""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("ñ", "n")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")


def encode_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def file_hash(path: str) -> str:
    sha = hashlib.sha1()
    with open(path, "rb") as f:
        while True:
            block = f.read(65536)
            if not block:
                break
            sha.update(block)
    return sha.hexdigest()


def read_csv_smart(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    for sep in [";", ","]:
        try:
            df = pd.read_csv(path, sep=sep, encoding="utf-8", on_bad_lines="warn")
            return df
        except Exception:
            continue
    try:
        return pd.read_csv(path, encoding="utf-8", on_bad_lines="warn")
    except Exception:
        return pd.DataFrame()


# ============================================================
# DETECCIÓN DE NOMBRES RICOS / POBRES
# ============================================================

def extraer_tokens_crudos(nombre_sin_ext: str) -> List[str]:
    if not isinstance(nombre_sin_ext, str):
        nombre_sin_ext = str(nombre_sin_ext or "")
    text = nombre_sin_ext.lower()
    text = text.replace("_", " ").replace("-", " ")
    tokens = re.findall(r"[a-z0-9]+", text)
    return tokens


def es_nombre_rico(nombre_sin_ext: str) -> bool:
    tokens = extraer_tokens_crudos(nombre_sin_ext)
    if len(tokens) >= 12:
        return True

    if len(tokens) < MIN_RICH_TOKENS:
        return False

    hay_marca = any(tok in BRAND_KEYWORDS for tok in tokens)
    numeric_tokens = [t for t in tokens if re.fullmatch(r"\d{2,4}", t)]

    if hay_marca and len(numeric_tokens) >= 1:
        return True
    if len(numeric_tokens) >= 2:
        return True

    return False


def limpiar_prefijo_codigo(nombre_sin_ext: str) -> Tuple[str, Optional[str]]:
    m = re.match(r"^([0-9]+(?:-[0-9]+)+)[-_](.*)$", nombre_sin_ext, flags=re.IGNORECASE)
    if m:
        prefijo = m.group(1)
        resto = m.group(2).lstrip("-_ ")
        return resto, prefijo
    return nombre_sin_ext, None


# ============================================================
# CARGA DE BASES Y MAPEO DE CÓDIGOS/DESCRIPCIONES
# ============================================================

Record = Dict[str, Any]


def detectar_columnas_codigo(df: pd.DataFrame) -> List[str]:
    if df.empty:
        return []
    cols = []
    for c in df.columns:
        cu = str(c).strip().upper()
        # CORRECCIÓN: Agregado ID_MASTER e ID para tus archivos específicos
        if any(k in cu for k in ["COD", "CÓD", "REF", "SKU", "REFERENCIA", "ITEM", "ID_MASTER", "ID"]):
            cols.append(c)
    return cols


def detectar_columnas_descripcion(df: pd.DataFrame) -> List[str]:
    if df.empty:
        return []
    cols = []
    for c in df.columns:
        cu = str(c).strip().upper()
        if any(k in cu for k in ["DESC", "DESCRIP", "PRODUCTO", "NOMBRE", "DETALLE"]):
            cols.append(c)
    return cols


def cargar_inventario() -> Dict[str, Record]:
    if not os.path.exists(INVENTARIO_CSV):
        print(f"⚠ No se encontró inventario: {INVENTARIO_CSV}")
        return {}

    df = read_csv_smart(INVENTARIO_CSV)
    if df.empty:
        print("⚠ Inventario vacío o ilegible.")
        return {}

    records: Dict[str, Record] = {}
    codigo_cols = []
    for candidate in ["CODIGO NEW", "CODIGO_NEW", "CODIGO", "SKU", "ID_MASTER"]:
        if candidate in df.columns:
            codigo_cols.append(candidate)
    if not codigo_cols:
        codigo_cols = detectar_columnas_codigo(df)

    desc_col = None
    for candidate in ["DESCRIPCION", "DESCRIPCIÓN"]:
        if candidate in df.columns:
            desc_col = candidate
            break
    if desc_col is None:
        desc_candidates = detectar_columnas_descripcion(df)
        desc_col = desc_candidates[0] if desc_candidates else None

    for _, row in df.iterrows():
        codigo = None
        for c in codigo_cols:
            val = str(row.get(c, "")).strip()
            if val and val.lower() != "nan":
                codigo = val
                break
        if not codigo:
            continue

        desc = str(row.get(desc_col, "")).strip() if desc_col else ""
        rec: Record = {
            "source": "INV",
            "codigo": codigo,
            "descripcion": desc,
            "marca": str(row.get("MARCA", "") or "").strip(),
            "modelo": str(row.get("MODELO", "") or "").strip(),
            "cilindraje": str(row.get("CILINDRAJE", "") or "").strip(),
        }
        records[codigo.lower()] = rec

    print(f"Inventario: {len(records)} registros cargados.")
    return records


def cargar_excel_generico(path: str, source_name: str) -> Dict[str, Record]:
    if not os.path.exists(path):
        print(f"⚠ No se encontró {source_name}: {path}")
        return {}

    try:
        df = pd.read_excel(path)
    except Exception as e:
        print(f"⚠ Error leyendo {source_name}: {e}")
        return {}

    if df.empty:
        print(f"⚠ {source_name} vacío.")
        return {}

    codigo_cols = detectar_columnas_codigo(df)
    desc_cols = detectar_columnas_descripcion(df)

    if not codigo_cols or not desc_cols:
        print(f"⚠ {source_name}: no se detectaron columnas de código/descripcion claras.")
        return {}

    codigo_col = codigo_cols[0]
    desc_col = desc_cols[0]

    records: Dict[str, Record] = {}
    for _, row in df.iterrows():
        cod = str(row.get(codigo_col, "")).strip()
        if not cod or cod.lower() == "nan":
            continue
        desc = str(row.get(desc_col, "")).strip()
        rec: Record = {
            "source": source_name,
            "codigo": cod,
            "descripcion": desc,
            "marca": "",
            "modelo": "",
            "cilindraje": "",
        }
        records[cod.lower()] = rec

    print(f"{source_name}: {len(records)} registros cargados.")
    return records


def cargar_csv_generico(path: str, source_name: str) -> Dict[str, Record]:
    if not os.path.exists(path):
        print(f"⚠ No se encontró {source_name}: {path}")
        return {}

    df = read_csv_smart(path)
    if df.empty:
        print(f"⚠ {source_name} vacío o ilegible.")
        return {}

    codigo_cols = detectar_columnas_codigo(df)
    desc_cols = detectar_columnas_descripcion(df)

    if not codigo_cols or not desc_cols:
        print(f"⚠ {source_name}: no se detectaron columnas de código/descripcion claras.")
        # Intento de debug
        print(f"   Columnas disponibles: {list(df.columns)}")
        return {}

    codigo_col = codigo_cols[0]
    desc_col = desc_cols[0]

    records: Dict[str, Record] = {}
    for _, row in df.iterrows():
        cod = str(row.get(codigo_col, "")).strip()
        if not cod or cod.lower() == "nan":
            continue
        desc = str(row.get(desc_col, "")).strip()
        rec: Record = {
            "source": source_name,
            "codigo": cod,
            "descripcion": desc,
            "marca": "",
            "modelo": "",
            "cilindraje": "",
        }
        records[cod.lower()] = rec

    print(f"{source_name}: {len(records)} registros cargados.")
    return records


# ============================================================
# BUSQUEDA DE MATCH POR CÓDIGO EN ARCHIVOS
# ============================================================

class Catalogos:
    def __init__(self) -> None:
        self.inv = cargar_inventario()
        self.jc = cargar_excel_generico(JC_XLSX, "JC")
        self.yoko = cargar_excel_generico(YOKO_XLSX, "YOKO")
        self.store = cargar_csv_generico(STORE_CSV, "STORE")
        self.leo = cargar_csv_generico(LEO_CSV, "LEO")
        self.japan = cargar_csv_generico(JAPAN_CSV, "JAPAN")
        self.vaisand = cargar_csv_generico(VAISAND_CSV, "VAISAND")

    def buscar_por_tokens(self, tokens: List[str]) -> Optional[Record]:
        cand = [t for t in tokens if len(t) >= 3]
        for t in cand:
            t_l = t.lower()
            if t_l in self.inv: return self.inv[t_l]
        for t in cand:
            t_l = t.lower()
            if t_l in self.jc: return self.jc[t_l]
        for t in cand:
            t_l = t.lower()
            if t_l in self.yoko: return self.yoko[t_l]
        for t in cand:
            t_l = t.lower()
            if t_l in self.store: return self.store[t_l]
        for t in cand:
            t_l = t.lower()
            if t_l in self.leo: return self.leo[t_l]
        for t in cand:
            t_l = t.lower()
            if t_l in self.japan: return self.japan[t_l]
        for t in cand:
            t_l = t.lower()
            if t_l in self.vaisand: return self.vaisand[t_l]
        return None


# ============================================================
# IA VISION 4o (USO RESTRINGIDO)
# ============================================================

VISION_PROMPT = """
Actúa como experto en catálogo técnico de repuestos para moto y motocarro.
Devuelve SOLO un JSON con este esquema EXACTO:
{
  "nombre_base_seo": "string",
  "componente": "string",
  "marca_moto": "string",
  "modelo_moto": "string",
  "cilindraje": "string",
  "es_motocarguero": false,
  "numeros_molde": "string"
}
"""

def analizar_con_vision(path: str, nombre_sin_ext: str) -> Dict[str, Any]:
    if client is None:
        return {}

    img64 = encode_image(path)
    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.0,
            max_tokens=300,
            messages=[
                {"role": "system", "content": "Eres un experto en repuestos. Respondes SOLO JSON válido."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": VISION_PROMPT + f"\nNombre de archivo: {nombre_sin_ext}"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img64}", "detail": "high"}},
                    ],
                },
            ],
        )
        txt = resp.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(txt)
        return data
    except Exception as e:
        print(f"[IA ERROR] {os.path.basename(path)} -> {e}")
        return {}


# ============================================================
# CONSTRUCCIÓN DEL SLUG FINAL
# ============================================================

def construir_slug_desde_record(rec: Record) -> str:
    partes = [
        rec.get("descripcion", ""),
        rec.get("marca", ""),
        rec.get("modelo", ""),
        rec.get("cilindraje", ""),
    ]
    txt = " ".join([p for p in partes if p])
    s = slugify(txt)
    if not s:
        s = slugify(rec.get("codigo", ""))
    return s or "sin-nombre"


def construir_slug_rico_desde_nombre(nombre_sin_ext: str) -> Tuple[str, str, str]:
    base_sin_prefijo, prefijo = limpiar_prefijo_codigo(nombre_sin_ext)
    slug_base = slugify(base_sin_prefijo)
    if not slug_base:
        slug_base = slugify(nombre_sin_ext)
    return slug_base or "sin-nombre", base_sin_prefijo, prefijo or ""


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    print("\n============================================")
    print("  🔧 RENOMBRAR SEO KAIQI v10.1 (FIXED HEADERS)")
    print("============================================\n")

    if not os.path.isdir(IMAGE_DIR):
        raise NotADirectoryError(f"No existe la carpeta de imágenes: {IMAGE_DIR}")

    catalogos = Catalogos()

    files = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
    print(f"📸 Imágenes detectadas: {len(files)}\n")

    used_slugs: Dict[str, int] = {}
    hash_seen: Dict[str, str] = {}
    log_rows: List[List[Any]] = []

    for fname in files:
        src_path = os.path.join(IMAGE_DIR, fname)
        base_name, ext = os.path.splitext(fname)
        ext = ext.lower()

        # Hash
        try:
            h = file_hash(src_path)
        except Exception as e:
            print(f"[ERROR HASH] {fname} -> {e}")
            continue

        if h in hash_seen:
            original = hash_seen[h]
            slug_dup = slugify(os.path.splitext(original)[0]) or "duplicado"
            if slug_dup in used_slugs:
                used_slugs[slug_dup] += 1
                slug_dup_final = f"{slug_dup}-dup{used_slugs[slug_dup]}"
            else:
                used_slugs[slug_dup] = 1
                slug_dup_final = f"{slug_dup}-dup1"
            new_name = f"{slug_dup_final}{ext}"
            dst_path = os.path.join(IMAGE_DIR, new_name)
            try:
                os.rename(src_path, dst_path)
                estado = "DUP_REAL_RENOMBRADO"
            except Exception as e:
                estado = f"ERROR_RENOMBRANDO_DUP:{e}"
            print(f"[DUP REAL] {fname} -> {new_name}")
            log_rows.append([fname, new_name, slug_dup_final, "DUPLICADO_REAL", "DUPLICADO_REAL", "", "", "", "", "", "", "", "", estado])
            continue
        else:
            hash_seen[h] = fname

        nombre_sin_ext = base_name
        tokens = extraer_tokens_crudos(nombre_sin_ext)

        estrategia = ""
        fuente_principal = ""
        codigo_usado = ""
        desc_usada = ""
        ia_nombre = ""

        # 1) Rico
        if es_nombre_rico(nombre_sin_ext):
            slug_final, desc_base, prefijo = construir_slug_rico_desde_nombre(nombre_sin_ext)
            estrategia = "RICO_ORIGINAL"
            fuente_principal = "NOMBRE_ARCHIVO"
            desc_usada = desc_base
        else:
            # 2) Match local
            rec = catalogos.buscar_por_tokens(tokens)
            if rec is not None:
                fuente_principal = rec.get("source", "CATALOGO")
                estrategia = f"MATCH_{fuente_principal}"
                codigo_usado = rec.get("codigo", "")
                desc_usada = rec.get("descripcion", "")
                slug_final = construir_slug_desde_record(rec)
            else:
                # 3) IA
                estrategia = "IA_SOLO"
                fuente_principal = "IA"
                ia_data = analizar_con_vision(src_path, nombre_sin_ext)
                ia_nombre = slugify(ia_data.get("nombre_base_seo", ""))
                if ia_nombre:
                    slug_final = ia_nombre
                else:
                    slug_final = slugify(nombre_sin_ext) or "sin-nombre"

        # Colisiones slug
        slug_base = slug_final
        if slug_base in used_slugs:
            used_slugs[slug_base] += 1
            slug_final = f"{slug_base}-v{used_slugs[slug_base]}"
        else:
            used_slugs[slug_base] = 1

        new_fname = f"{slug_final}{ext}"
        dst_path = os.path.join(IMAGE_DIR, new_fname)

        if os.path.abspath(src_path) == os.path.abspath(dst_path):
            estado = "SIN_CAMBIO"
        else:
            try:
                os.rename(src_path, dst_path)
                estado = "RENOMBRADO"
            except Exception as e:
                estado = f"ERROR_RENOMBRANDO:{e}"

        print(f"[{estado}] {fname} -> {new_fname} | estrategia={estrategia}")

        log_rows.append([fname, new_fname, slug_final, estrategia, fuente_principal, codigo_usado, desc_usada, ia_nombre, "", "", "", "", "", estado])

    # Guardar log
    with open(LOG_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["archivo_original", "archivo_nuevo", "slug_final", "estrategia", "fuente_principal", "codigo_usado", "descripcion_usada", "ia_nombre", "ia_comp", "ia_marca", "ia_modelo", "ia_cilindraje", "ia_numeros", "estado"])
        for row in log_rows:
            if len(row) < 14:
                row = list(row) + [""] * (14 - len(row))
            writer.writerow(row)

    print("\n✅ Renombrado SEO v10.1 finalizado.")
    print(f"   → Log: {LOG_CSV}")


if __name__ == "__main__":
    main()