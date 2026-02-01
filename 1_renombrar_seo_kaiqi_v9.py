#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1_renombrar_seo_kaiqi_v9.py

Renombrador SEO robusto para IMAGENES_KAIQI_MAESTRAS usando:
- Nombres de archivo existentes (prioridad cuando traen fitment rico)
- Múltiples bases locales en C:\img:
    * Inventario_FINAL_CON_TAXONOMIA.csv
    * LISTA DE PRECIOS NOVIEMBRE 13 2025 TRABAJO JC.xlsx
    * LISTA DE PRECIOS  YOKOMAR ACTUALIZADA 2025.xlsx
    * Base_Datos_Store.csv
    * Base_Datos_Leo.csv
    * Base_Datos_Japan.csv
    * Base_Datos_Vaisand.csv
- Vision gpt-4o SOLO como apoyo cuando no hay buena información local.

Principios clave v9:
- Si el nombre original ya tiene fitment rico (marcas/modelos/años/cilindraje):
    -> se respeta y solo se limpia (sin IA y sin sobrescribir).
- Las bases locales sirven para reforzar DESCRIPCION / COMPONENTE / SISTEMA / etc.
- IA solo se usa para nombres pobres (tipo IMG_1234, 103017501.png) cuando no hay match local.
- NO se marcan duplicados falsos; si dos imágenes generan el mismo slug, se versionan con -v2, -v3, etc.
- Se genera un log detallado en C:\img\LOGS\log_renombrado_seo_v9.csv

Requisitos:
- Python 3.9+
- Paquetes: pandas, openpyxl, openai (nuevo cliente OpenAI), unicodedata
- Variable de entorno OPENAI_API_KEY configurada para usar Vision gpt-4o
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
LOG_CSV = os.path.join(LOG_DIR, "log_renombrado_seo_v9.csv")

# Umbrales / parámetros
MIN_RICH_TOKENS = 6  # mínimo de tokens para considerar un nombre "rico"
BRAND_KEYWORDS = [
    "akt", "bajaj", "yamaha", "honda", "suzuki", "tvs", "ktm", "hero",
    "boxer", "pulsar", "apache", "nkd", "dominar", "gixxer", "cb", "cbf",
    "dr", "xr", "xre", "crypton", "libero", "viva", "st", "dinamic",
]

# Cliente OpenAI (opcional, solo si hay API key)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client: Optional[OpenAI] = None
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)


# ============================================================
# UTILIDADES BÁSICAS
# ============================================================

def slugify(text: str) -> str:
    """Convierte texto a slug SEO: minúsculas, sin acentos, sin ñ, con guiones."""
    if not isinstance(text, str):
        text = str(text or "")
    text = text.strip()
    if not text:
        return ""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("ñ", "n")
    text = text.lower()
    # Solo letras, números, espacios y guiones
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")


def encode_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def file_hash(path: str) -> str:
    """Hash SHA1 del archivo para detectar duplicados reales."""
    sha = hashlib.sha1()
    with open(path, "rb") as f:
        while True:
            block = f.read(65536)
            if not block:
                break
            sha.update(block)
    return sha.hexdigest()


def read_csv_smart(path: str) -> pd.DataFrame:
    """Intenta leer CSV probando separador ';' y luego ','."""
    if not os.path.exists(path):
        return pd.DataFrame()
    for sep in [";", ","]:
        try:
            df = pd.read_csv(path, sep=sep, encoding="utf-8", on_bad_lines="warn")
            return df
        except Exception:
            continue
    # último intento sin especificar
    try:
        return pd.read_csv(path, encoding="utf-8", on_bad_lines="warn")
    except Exception:
        return pd.DataFrame()


# ============================================================
# DETECCIÓN DE NOMBRES RICOS / POBRES
# ============================================================

def extraer_tokens_crudos(nombre_sin_ext: str) -> List[str]:
    """Extrae tokens alfanuméricos conservando guiones internos (ej: '1-11-131')."""
    nombre_sin_ext = nombre_sin_ext.lower()
    tokens = re.findall(r"[a-z0-9-]+", nombre_sin_ext)
    # quitar tokens muy cortos irrelevantes
    return [t for t in tokens if len(t) >= 2]


def es_nombre_rico(nombre_sin_ext: str) -> bool:
    """Heurística para detectar si el nombre trae fitment rico.

    Criterios:
    - Mínimo de tokens
    - Contiene palabras de marca/modelo o varios números (años/cilindraje)
    """
    tokens = extraer_tokens_crudos(nombre_sin_ext)
    if len(tokens) < MIN_RICH_TOKENS:
        return False

    # detectar palabras de marca/modelo
    hay_marca = any(tok in BRAND_KEYWORDS for tok in tokens)

    # contar tokens numéricos (años, cilindraje, códigos)
    numeric_tokens = [t for t in tokens if re.fullmatch(r"\d{2,4}", t)]

    if hay_marca and len(numeric_tokens) >= 1:
        return True
    if len(numeric_tokens) >= 2:
        return True

    return False


def limpiar_prefijo_codigo(nombre_sin_ext: str) -> Tuple[str, Optional[str]]:
    """Si el nombre inicia con un prefijo tipo '1-11-131-' lo separa y devuelve
    (resto, prefijo). Si no, devuelve (nombre_original, None).
    """
    # trabajamos con crudo, no slugificado aún
    m = re.match(r"^([0-9]+(?:-[0-9]+)+)-(.*)$", nombre_sin_ext)
    if m:
        prefijo = m.group(1)
        resto = m.group(2).lstrip("-")
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
        if any(k in cu for k in ["COD", "CÓD", "REF", "SKU", "REFERENCIA"]):
            cols.append(c)
    return cols


def detectar_columnas_descripcion(df: pd.DataFrame) -> List[str]:
    if df.empty:
        return []
    cols = []
    for c in df.columns:
        cu = str(c).strip().upper()
        if any(k in cu for k in ["DESC", "PRODUCTO", "NOMBRE"]):
            cols.append(c)
    return cols


def cargar_inventario() -> Dict[str, Record]:
    """Carga Inventario_FINAL_CON_TAXONOMIA.csv como fuente de taxonomía."""
    if not os.path.exists(INVENTARIO_CSV):
        print(f"⚠ No se encontró inventario: {INVENTARIO_CSV}")
        return {}

    df = read_csv_smart(INVENTARIO_CSV)
    if df.empty:
        print("⚠ Inventario vacío o ilegible.")
        return {}

    records: Dict[str, Record] = {}
    # columnas típicas
    codigo_cols = []
    for candidate in ["CODIGO NEW", "CODIGO_NEW", "CODIGO", "SKU", "ID_MASTER"]:
        if candidate in df.columns:
            codigo_cols.append(candidate)
    if not codigo_cols:
        # fallback: detectar automáticamente
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
    """Carga un Excel genérico (JC, Yokomar) como diccionario codigo -> record."""
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
    """Carga un CSV genérico (Store, Leo, Japan, Vaisand) como diccionario codigo -> record."""
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
        """Busca en todos los catálogos si algún token coincide con un código.
        Prioridad: INV > JC > YOKO > STORE > LEO > JAPAN > VAISAND
        """
        # Filtrar tokens más largos para evitar ruido
        cand = [t for t in tokens if len(t) >= 3]
        # buscamos códigos exactos en orden de prioridad
        for t in cand:
            t_l = t.lower()
            if t_l in self.inv:
                return self.inv[t_l]
        for t in cand:
            t_l = t.lower()
            if t_l in self.jc:
                return self.jc[t_l]
        for t in cand:
            t_l = t.lower()
            if t_l in self.yoko:
                return self.yoko[t_l]
        for t in cand:
            t_l = t.lower()
            if t_l in self.store:
                return self.store[t_l]
        for t in cand:
            t_l = t.lower()
            if t_l in self.leo:
                return self.leo[t_l]
        for t in cand:
            t_l = t.lower()
            if t_l in self.japan:
                return self.japan[t_l]
        for t in cand:
            t_l = t.lower()
            if t_l in self.vaisand:
                return self.vaisand[t_l]
        return None


# ============================================================
# IA VISION 4o (USO RESTRINGIDO A CASOS POBRES)
# ============================================================

VISION_PROMPT = """
Actúa como experto en catálogo técnico de repuestos para moto y motocarro.

Se te dará una imagen de una pieza y, opcionalmente, el nombre de archivo.
Solo debes ayudar cuando el nombre de archivo es pobre (tipo IMG_1234, 103017501).

Reglas:
- NO inventes marcas comerciales raras ni nombres de proveedor (no uses 'gaju', 'leo', 'yoko', etc.).
- NO pongas fechas ni cosas como '09-10-2023'.
- Usa un lenguaje técnico limpio, corto y directo.
- El nombre sugerido debe describir componente, tipo de vehículo y algo de fitment genérico.

Devuelve SOLO un JSON con este esquema EXACTO:
{
  "nombre_base_seo": "string (sin extensión, ejemplo: 'pastillas-freno-delanteras-scooter-125-150cc')",
  "componente": "string (nombre técnico del repuesto)",
  "marca_moto": "string o '' si genérico",
  "modelo_moto": "string o '' si genérico",
  "cilindraje": "string o '' (ej: '125', '100-125')",
  "es_motocarguero": false,
  "numeros_molde": "string con códigos grabados visibles o '' si nada claro"
}
"""


def analizar_con_vision(path: str, nombre_sin_ext: str) -> Dict[str, Any]:
    """Llama a Vision 4o SOLO si hay API key; si no, devuelve estructura vacía."""
    if client is None:
        return {
            "nombre_base_seo": "",
            "componente": "",
            "marca_moto": "",
            "modelo_moto": "",
            "cilindraje": "",
            "es_motocarguero": False,
            "numeros_molde": "",
        }

    img64 = encode_image(path)
    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.0,
            max_tokens=300,
            messages=[
                {
                    "role": "system",
                    "content": "Eres un experto en repuestos. Respondes SOLO JSON válido."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": VISION_PROMPT + f"\nNombre de archivo: {nombre_sin_ext}"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img64}",
                                "detail": "high",
                            },
                        },
                    ],
                },
            ],
        )
        txt = resp.choices[0].message.content.strip()
        txt = txt.replace("```json", "").replace("```", "").strip()
        data = json.loads(txt)
        # normalizar campos faltantes
        for k in [
            "nombre_base_seo",
            "componente",
            "marca_moto",
            "modelo_moto",
            "cilindraje",
            "es_motocarguero",
            "numeros_molde",
        ]:
            if k not in data:
                data[k] = "" if k != "es_motocarguero" else False
        return data
    except Exception as e:
        print(f"[IA ERROR] {os.path.basename(path)} -> {e}")
        return {
            "nombre_base_seo": "",
            "componente": "",
            "marca_moto": "",
            "modelo_moto": "",
            "cilindraje": "",
            "es_motocarguero": False,
            "numeros_molde": "",
        }


# ============================================================
# CONSTRUCCIÓN DEL SLUG FINAL
# ============================================================


def construir_slug_desde_record(rec: Record) -> str:
    """Arma un slug base desde un record local (código + descripción + marca/modelo/cilindraje)."""
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


def construir_slug_final(
    estrategia: str,
    nombre_sin_ext: str,
    prefijo_codigo: Optional[str],
    rec: Optional[Record],
    ia_data: Optional[Dict[str, Any]],
) -> Tuple[str, str, str, str, str, str]:
    """Devuelve (slug_final, fuente_principal, codigo_usado, desc_usada, ia_nombre, ia_componente).

    Estrategias:
    - RICO_ORIGINAL: se respeta el nombre (limpio), sin IA, sin sobrescribir.
    - MATCH_xxx: se usa record local como base y se respeta fitment si lo hay.
    - IA_SOLO: se usa IA porque no hay nada más.
    """

    ia_nombre = ""
    ia_comp = ""
    codigo_usado = ""
    desc_usada = ""
    fuente = estrategia

    if estrategia == "RICO_ORIGINAL":
        # limpiamos prefijo tipo 1-11-131- si existe, y usamos el resto tal cual
        base_sin_prefijo, pref = limpiar_prefijo_codigo(nombre_sin_ext)
        if prefijo_codigo is None and pref is not None:
            prefijo_codigo = pref
        slug_base = slugify(base_sin_prefijo)
        if not slug_base:
            slug_base = slugify(nombre_sin_ext)
        # opcional: agregar código al final si queremos mantenerlo
        # Por ahora seguimos tu instrucción: dejar tal cual sin el prefijo.
        return slug_base or "sin-nombre", fuente, "", base_sin_prefijo, "", ""

    if estrategia.startswith("MATCH_") and rec is not None:
        codigo_usado = rec.get("codigo", "")
        desc_usada = rec.get("descripcion", "")
        base_slug_rec = construir_slug_desde_record(rec)

        # Si el nombre original también es rico, damos preferencia a su fitment
        # pero complementamos con descripción local.
        base_sin_prefijo, pref = limpiar_prefijo_codigo(nombre_sin_ext)
        if prefijo_codigo is None and pref is not None:
            prefijo_codigo = pref

        if es_nombre_rico(nombre_sin_ext):
            # combinamos: fitment original + pieza desde record
            fitment_slug = slugify(base_sin_prefijo)
            combined = f"{fitment_slug}-{base_slug_rec}" if base_slug_rec not in fitment_slug else fitment_slug
            slug_final = combined
        else:
            slug_final = base_slug_rec

        return slug_final or "sin-nombre", fuente, codigo_usado, desc_usada, "", ""

    # IA_SOLO o fallback con IA
    if ia_data is None:
        ia_data = {}
    ia_nombre = slugify(ia_data.get("nombre_base_seo", ""))
    ia_comp = ia_data.get("componente", "")

    if ia_nombre:
        slug_final = ia_nombre
    else:
        # fallback: usar nombre_sin_ext limpio
        slug_final = slugify(nombre_sin_ext)

    return slug_final or "sin-nombre", "IA_SOLO", "", "", ia_nombre, ia_comp


# ============================================================
# MAIN
# ============================================================


def main() -> None:
    print("\n============================================")
    print("  🔧 RENOMBRAR SEO KAIQI v9 (robusto)")
    print("============================================\n")

    if not os.path.isdir(IMAGE_DIR):
        raise NotADirectoryError(f"No existe la carpeta de imágenes: {IMAGE_DIR}")

    catalogos = Catalogos()

    files = [
        f
        for f in os.listdir(IMAGE_DIR)
        if os.path.isfile(os.path.join(IMAGE_DIR, f))
        and f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    ]

    print(f"📸 Imágenes detectadas en IMAGENES_KAIQI_MAESTRAS: {len(files)}\n")

    used_slugs: Dict[str, int] = {}
    hash_seen: Dict[str, str] = {}
    log_rows: List[List[Any]] = []

    for fname in files:
        src_path = os.path.join(IMAGE_DIR, fname)
        base_name, ext = os.path.splitext(fname)
        ext = ext.lower()

        # Hash para detectar duplicados reales (misma imagen exacta)
        try:
            h = file_hash(src_path)
        except Exception as e:
            print(f"[ERROR HASH] {fname} -> {e}")
            log_rows.append([
                fname,
                fname,
                "",
                "ERROR_HASH",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                str(e),
            ])
            continue

        if h in hash_seen:
            # Duplicado real, no lo eliminamos pero lo versionamos
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
            print(f"[DUP REAL] {fname} -> {new_name} (igual a {original})")
            log_rows.append([
                fname,
                new_name,
                "",
                "DUPLICADO_REAL",
                "",
                slug_dup_final,
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                estado,
            ])
            continue
        else:
            hash_seen[h] = fname

        nombre_sin_ext = base_name
        tokens = extraer_tokens_crudos(nombre_sin_ext)

        # 1) Si el nombre es rico, lo respetamos y solo lo limpiamos.
        if es_nombre_rico(nombre_sin_ext):
            slug_final, fuente, codigo_usado, desc_usada, ia_nombre, ia_comp = construir_slug_final(
                "RICO_ORIGINAL", nombre_sin_ext, None, None, None
            )
            estrategia = "RICO_ORIGINAL"
            ia_nombre = ia_nombre or ""
            ia_comp = ia_comp or ""
        else:
            # 2) Intentamos match en catálogos locales por código
            rec = catalogos.buscar_por_tokens(tokens)
            if rec is not None:
                fuente_label = f"MATCH_{rec.get('source', '')}"
                slug_final, fuente, codigo_usado, desc_usada, ia_nombre, ia_comp = construir_slug_final(
                    fuente_label, nombre_sin_ext, None, rec, None
                )
                estrategia = fuente_label
            else:
                # 3) Nombre pobre + sin match local -> usar IA como apoyo
                ia_data = analizar_con_vision(src_path, nombre_sin_ext)
                slug_final, fuente, codigo_usado, desc_usada, ia_nombre, ia_comp = construir_slug_final(
                    "IA_SOLO", nombre_sin_ext, None, None, ia_data
                )
                estrategia = "IA_SOLO"

        # Resolver colisiones de slug (sin usar carpeta duplicados)
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

        log_rows.append([
            fname,
            new_fname,
            slug_final,
            estrategia,
            fuente,
            codigo_usado if "codigo_usado" in locals() else "",
            desc_usada if "desc_usada" in locals() else "",
            ia_nombre,
            ia_comp,
            "",
            "",
            "",
            "",
            estado,
        ])

    # Guardar log
    with open(LOG_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow([
            "archivo_original",
            "archivo_nuevo",
            "slug_final",
            "estrategia",
            "fuente_principal",
            "codigo_usado",
            "descripcion_usada",
            "ia_nombre_base_seo",
            "ia_componente",
            "ia_marca",
            "ia_modelo",
            "ia_cilindraje",
            "ia_numeros_molde",
            "estado",
        ])
        for row in log_rows:
            # completar a 14 columnas por seguridad
            if len(row) < 14:
                row = list(row) + [""] * (14 - len(row))
            writer.writerow(row)

    print("\n✅ Renombrado SEO v9 finalizado.")
    print(f"   → Log: {LOG_CSV}")


if __name__ == "__main__":
    main()
