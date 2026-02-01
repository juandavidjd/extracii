import os
import shutil
import base64
import json
import csv
import re
import unicodedata
from openai import OpenAI

# ==========================================
# 🔧 CONFIGURACIÓN
# ==========================================
BASE_DIR        = r"C:\img"
IMAGE_DIR       = os.path.join(BASE_DIR, "IMAGENES_KAIQI_MAESTRAS")  # carpeta ya filtrada por el clasificador
OUTPUT_DIR      = IMAGE_DIR  # renombrar en la misma carpeta

DIR_DUPLICADOS  = os.path.join(BASE_DIR, "IMAGENES_DUPLICADAS")
DIR_LOGS        = os.path.join(BASE_DIR, "LOGS")

LOG_RENAME_CSV  = os.path.join(DIR_LOGS, "log_renombrado_kaiqi_v2.csv")

MODEL_VISION    = "gpt-4o"  # Vision 4o
NUM_EXTS        = (".jpg", ".jpeg", ".png", ".webp")

# Cliente IA – usa tu API key desde la variable de entorno OPENAI_API_KEY
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ==========================================
# 🧠 PROMPT RENOMBRADO SEO
# ==========================================
PROMPT_RENOMBRE = """
Actúas como experto en catálogo de repuestos de moto y naming SEO.

Tu tarea es proponer un NOMBRE BASE (slug) para el archivo de imagen de un repuesto de moto, siguiendo estas reglas EXACTAS:

1) FORMATO SEO
   - Solo minúsculas.
   - Separador siempre guion medio "-".
   - Sin acentos ni caracteres especiales (ñ -> n, á -> a, etc.).
   - Nada de espacios, nada de barras, nada de puntos dentro del nombre base.

2) USO DEL NOMBRE ORIGINAL:
   - Si el nombre de archivo ORIGINAL ya es DESCRIPTIVO (por ejemplo: "110 Bob Encendido C-70 PLATINO", "BANDA_DE_FRENO_PARA_MOTOS_1010115"):
        * NO debes resumirlo ni reemplazarlo por algo genérico.
        * Debes conservar TODAS las palabras útiles y números relevantes que trae.
        * Solo límpialo: quita tildes, convierte a minúsculas y reemplaza espacios, guiones y guiones bajos por un solo "-".
        * Ejemplo:
            original: "110 Bob Encendido C-70 PLATINO"
            slug_base: "110-bob-encendido-c-70-platino"
   - Un nombre se considera DESCRIPTIVO si:
        * Tiene varias palabras reales (en español) o
        * Contiene términos claros de repuesto (banda, freno, bob, encendido, pastilla, manigueta, cilindro, disco, pedal, etc.).

3) NOMBRES BASURA / CÓDIGOS:
   - Si el nombre de archivo es genérico o poco útil (por ejemplo solo números, códigos largos mezclados, "IMG_1234", "D_NQ_NP_626199-MLA74548978406_022024-O"):
        * IGNORA ese texto como base.
        * Crea un nombre nuevo basado en lo que ves en la imagen: componente y, si lo identificas, la marca y modelo de moto.
        * Ejemplos de nombres válidos:
            "bobina-encendido-ax-100",
            "banda-freno-trasera-boxer-ct100",
            "cruceta-de-cardan",
            "pastillas-freno-delantero-nkd-125".

4) MARCA + MODELO:
   - Si detectas claramente MARCA + MODELO + COMPONENTE:
        * Estructura recomendada: "componente-marca-modelo"
        * Ejemplo: "banda-freno-trasera-suzuki-ax-115".
   - Si NO detectas modelo ni marca:
        * Usa algo como "componente-universal" o una descripción corta del componente.

5) NÚMEROS DE MOLDE
   - No agregues números de molde típicos (ej: 54410, 16B01) al slug SEO.
   - Sí puedes usar códigos cortos o referencias si forman parte clara del nombre ORIGINAL descriptivo, pero no inventes ni refuerces números de molde que solo veas grabados.

6) RESPUESTA OBLIGATORIA EN JSON:
   Devuelve SOLO un objeto JSON con esta estructura:

   {
     "usa_nombre_original": true/false,
     "slug_base": "nombre-seo-sin-extension",
     "motivo": "explicacion breve",
     "componente": "ej: bobina de encendido, banda de freno, pastillas de freno, cruceta de cardan, etc.",
     "marca_moto": "ej: honda, yamaha, bajaj, suzuki, akt, etc. o null si no se ve",
     "modelo_moto": "ej: ax 115, boxer ct 100, nkd 125, etc. o null si no se ve",
     "es_nombre_basura": true/false
   }

- "usa_nombre_original" debe ser true si consideras que el nombre original ya era descriptivo y solo aplicaste limpieza SEO.
- "es_nombre_basura" debe ser true si el nombre original era tipo código, solo números o irrelevante.

NO escribas nada fuera del JSON.
"""


# ==========================================
# 🔧 UTILIDADES
# ==========================================
def setup_dirs():
    os.makedirs(DIR_DUPLICADOS, exist_ok=True)
    os.makedirs(DIR_LOGS, exist_ok=True)


def encode_image(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return None


def is_image_file(name: str) -> bool:
    return name.lower().endswith(NUM_EXTS)


def normalize_slug(slug: str) -> str:
    """
    Normaliza un slug:
    - minúsculas
    - sin tildes
    - solo [a-z0-9-]
    - colapsa guiones múltiples
    """
    slug = slug.strip().lower()

    # quitar tildes
    slug = unicodedata.normalize("NFD", slug)
    slug = "".join(c for c in slug if unicodedata.category(c) != "Mn")

    # reemplazar separadores por guion
    slug = re.sub(r"[\s_/]+", "-", slug)

    # dejar solo a-z0-9- 
    slug = re.sub(r"[^a-z0-9-]", "-", slug)

    # colapsar guiones
    slug = re.sub(r"-+", "-", slug).strip("-")

    return slug


def nombre_original_descriptivo(stem: str) -> bool:
    """
    Heurística para saber si el nombre original ya es descriptivo.
    - Contiene varias palabras
    - Y contiene términos típicos de repuestos
    """
    s = stem.lower().replace("_", " ").replace("-", " ")
    tokens = s.split()
    if len(tokens) >= 3:
        # Palabras clave típicas
        keywords = [
            "banda", "freno", "pastilla", "pastillas",
            "bob", "bobina", "encendido",
            "cilindro", "manigueta", "pedal", "eje",
            "estator", "piñon", "piston", "disco",
            "varilla", "guaya", "cdi", "regulador",
            "biela", "suspension", "amortiguador"
        ]
        if any(k in s for k in keywords):
            return True

    return False


def analizar_para_renombrar(path: str, filename: str) -> dict | None:
    """
    Llama a Vision 4o para decidir el slug SEO,
    respetando el nombre original si ya es descriptivo.
    """
    img64 = encode_image(path)
    if not img64:
        return None

    stem, _ = os.path.splitext(filename)

    try:
        resp = client.chat.completions.create(
            model=MODEL_VISION,
            messages=[
                {
                    "role": "system",
                    "content": "Eres un experto en repuestos de moto y SEO. Respondes solo con JSON válido."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": PROMPT_RENOMBRE + f"\n\nNombre de archivo original (sin ruta): '{stem}'"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img64}",
                                "detail": "low"
                            }
                        }
                    ]
                }
            ],
            temperature=0.0,
            max_tokens=300
        )

        content = resp.choices[0].message.content.strip()
        # Limpieza por si viniera con ```json
        content = content.replace("```json", "").replace("```", "").strip()
        data = json.loads(content)

        # Normalizar slug_base con nuestra función robusta
        raw_slug = data.get("slug_base", "").strip()
        if not raw_slug:
            return None

        data["slug_base"] = normalize_slug(raw_slug)

        # Si el modelo no detectó bien que el nombre ya era descriptivo,
        # usamos nuestra propia heurística como refuerzo:
        if nombre_original_descriptivo(stem) and data.get("es_nombre_basura", False):
            # forzamos uso del nombre original
            data["usa_nombre_original"] = True
            data["slug_base"] = normalize_slug(stem)

        # Si dice que usa nombre original pero el slug no se parece, lo re-generamos desde stem
        if data.get("usa_nombre_original"):
            data["slug_base"] = normalize_slug(stem)

        return data

    except Exception as e:
        print(f"   [ERROR IA] {filename} → {e}")
        return None


# ==========================================
# 🚀 MAIN RENOMBRADOR
# ==========================================
def main():
    setup_dirs()

    if not os.path.isdir(IMAGE_DIR):
        print(f"❌ Carpeta de imágenes no encontrada: {IMAGE_DIR}")
        return

    files = [f for f in os.listdir(IMAGE_DIR) if is_image_file(f)]
    files.sort()

    if not files:
        print("⚠ No se encontraron imágenes en IMAGENES_KAIQI_MAESTRAS.")
        return

    print("==============================================")
    print("  🔥 Renombrador SEO KAIQI (Vision 4o)")
    print("==============================================")
    print(f"📁 Carpeta origen: {IMAGE_DIR}")
    print(f"📸 Imágenes a procesar: {len(files)}")
    print()

    used_slugs = set()
    log_rows = []

    for idx, fname in enumerate(files, start=1):
        old_path = os.path.join(IMAGE_DIR, fname)
        stem, ext = os.path.splitext(fname)

        print(f"[{idx}/{len(files)}] Analizando para renombrar → {fname}")

        data = analizar_para_renombrar(old_path, fname)
        if not data:
            print(f"   ⚠ No se pudo obtener slug, se deja con su nombre original.")
            log_rows.append({
                "old_filename": fname,
                "new_filename": fname,
                "status": "SIN_CAMBIO_ERROR_IA",
                "motivo": "No se obtuvo respuesta de IA",
                "componente": "",
                "marca_moto": "",
                "modelo_moto": ""
            })
            continue

        slug_base = data.get("slug_base", "").strip()
        componente = data.get("componente", "")
        marca_moto = data.get("marca_moto", "")
        modelo_moto = data.get("modelo_moto", "")
        motivo = data.get("motivo", "")

        if not slug_base:
            print("   ⚠ Slug vacío, se deja nombre original.")
            log_rows.append({
                "old_filename": fname,
                "new_filename": fname,
                "status": "SIN_CAMBIO_SLUG_VACIO",
                "motivo": "Slug vacío tras normalización",
                "componente": componente,
                "marca_moto": marca_moto,
                "modelo_moto": modelo_moto
            })
            continue

        # Nuevo nombre completo (misma extensión)
        new_name = slug_base + ext.lower()
        new_path = os.path.join(IMAGE_DIR, new_name)

        # Duplicados por slug_base
        if slug_base in used_slugs or os.path.exists(new_path):
            # mover a carpeta de duplicados
            dup_path = os.path.join(DIR_DUPLICADOS, fname)
            shutil.move(old_path, dup_path)
            print(f"   ⚠ Slug duplicado → movido a DUPLICADOS: {dup_path}")

            log_rows.append({
                "old_filename": fname,
                "new_filename": "",
                "status": "DUPLICADO",
                "motivo": f"Slug '{slug_base}' ya usado, revisar manualmente.",
                "componente": componente,
                "marca_moto": marca_moto,
                "modelo_moto": modelo_moto
            })
            continue

        # Renombrar en sitio
        try:
            os.rename(old_path, new_path)
            used_slugs.add(slug_base)
            print(f"   ✅ Nuevo nombre: {new_name}")

            log_rows.append({
                "old_filename": fname,
                "new_filename": new_name,
                "status": "RENOMBRADO",
                "motivo": motivo,
                "componente": componente,
                "marca_moto": marca_moto,
                "modelo_moto": modelo_moto
            })
        except Exception as e:
            print(f"   ❌ Error al renombrar: {e}")
            log_rows.append({
                "old_filename": fname,
                "new_filename": fname,
                "status": "ERROR_RENAME",
                "motivo": str(e),
                "componente": componente,
                "marca_moto": marca_moto,
                "modelo_moto": modelo_moto
            })

    # Guardar CSV maestro
    with open(LOG_RENAME_CSV, "w", newline="", encoding="utf-8-sig") as csvfile:
        fieldnames = ["old_filename", "new_filename", "status", "motivo", "componente", "marca_moto", "modelo_moto"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        for row in log_rows:
            writer.writerow(row)

    print("\n===============================")
    print("   PROCESO DE RENOMBRE LISTO")
    print("===============================")
    print(f"📄 Log de renombrado: {LOG_RENAME_CSV}")
    print(f"📂 Duplicados (para revisar): {DIR_DUPLICADOS}")
    print("===============================")


if __name__ == "__main__":
    main()
