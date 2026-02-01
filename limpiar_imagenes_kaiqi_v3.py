import os
import base64
import json
import shutil
import time
from openai import OpenAI
from PIL import Image

# ============================
# CONFIGURACIÓN
# ============================

INPUT_FOLDER = r"C:\img\FOTOS_COMPETENCIA"
OUTPUT_BASE = r"C:\img"

FOLDER_MAESTRAS = os.path.join(OUTPUT_BASE, "IMAGENES_KAIQI_MAESTRAS")
FOLDER_EDITAR = os.path.join(OUTPUT_BASE, "IMAGENES_PARA_EDITAR_TEXTO")
FOLDER_DESCARTADAS = os.path.join(OUTPUT_BASE, "DESCARTADAS_NO_MOTO")
FOLDER_LOGS = os.path.join(OUTPUT_BASE, "LOGS")

CSV_SALIDA = os.path.join(OUTPUT_BASE, "analisis_360_kaiqi.csv")

os.makedirs(FOLDER_MAESTRAS, exist_ok=True)
os.makedirs(FOLDER_EDITAR, exist_ok=True)
os.makedirs(FOLDER_DESCARTADAS, exist_ok=True)
os.makedirs(FOLDER_LOGS, exist_ok=True)

# ============================
# IA CONFIG
# ============================

client = OpenAI()

VISION_MODEL_LITE = "gpt-4o-mini"   # Paso 1 — filtro primario (rápido)
VISION_MODEL_FULL = "gpt-4o"        # Paso 2 — análisis 360°


# ============================
# UTILIDADES
# ============================

def encode_image(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except:
        return None


def vision_call(model, image_b64, prompt):
    try:
        res = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Eres un analista experto en repuestos de motocicletas."},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                ]}
            ],
            max_tokens=1000
        )
        return res.choices[0].message.content
    except Exception as e:
        return None


# ============================
# PROCESO
# ============================

def procesar_imagen(archivo):
    ruta = os.path.join(INPUT_FOLDER, archivo)
    img64 = encode_image(ruta)
    if not img64:
        return None, "ERROR: No se pudo leer la imagen."

    print(f"\n📸 Analizando '{archivo}' (filtro inicial)…")

    # -------------------------------------
    # 1. Filtro rápido con Vision Mini
    # -------------------------------------

    prompt_lite = """
    Clasifica la imagen SOLO respondiendo JSON:
    {
      "es_moto_o_motocarguero": "si/no",
      "tiene_texto_grabado_en_pieza": "si/no",
      "nivel_texto": "ninguno/leve/medio/fuerte",
      "es_basura_o_no_repuesto": "si/no"
    }
    """

    lite_raw = vision_call(VISION_MODEL_LITE, img64, prompt_lite)
    if not lite_raw:
        return None, "ERROR IA Lite"

    try:
        lite = json.loads(lite_raw)
    except:
        return None, "ERROR JSON Lite"

    # -------------------------------------
    # Filtro de descarte
    # -------------------------------------

    if lite.get("es_basura_o_no_repuesto") == "si" or lite.get("es_moto_o_motocarguero") == "no":
        shutil.move(ruta, os.path.join(FOLDER_DESCARTADAS, archivo))
        return None, "DESCARTADA"

    # -------------------------------------
    # 2. Vision 4o — análisis 360°
    # -------------------------------------

    print(f"🔍 Vision Full 4o '{archivo}'…")

    prompt_full = f"""
    Realiza análisis 360° profesional. Usa este formato JSON EXACTO:

    {json.dumps({
        "es_moto_o_motocarguero": "",
        "motivo_si_no": "",
        "tipo_repuesto_probable": "",
        "descripcion_pieza": "",
        "sistema": "",
        "sub_sistema": "",
        "materiales": "",
        "marca_grabada_detectada": "",
        "nivel_texto_grabado": "",
        "accion_recomendada": "",
        "compatibilidad_probable": [{
            "marca": "",
            "modelos": [],
            "cilindraje": "",
            "grado_confianza": ""
        }],
        "nombre_comercial_sugerido": "",
        "notas_calidad": "",
        "clasificacion_final": "",
        "motivo_clasificacion": ""
    })}
    SOLO responde JSON válido, sin texto extra.
    """

    full_raw = vision_call(VISION_MODEL_FULL, img64, prompt_full)
    if not full_raw:
        return None, "ERROR IA Full"

    try:
        full = json.loads(full_raw)
    except:
        return None, "ERROR JSON Full"

    # -------------------------------------
    # Clasificación final
    # -------------------------------------

    texto = full.get("nivel_texto_grabado", "ninguno")

    if texto in ["medio", "fuerte"]:
        destino = FOLDER_EDITAR
        full["clasificacion_final"] = "para_editar"
    else:
        destino = FOLDER_MAESTRAS
        full["clasificacion_final"] = "maestra"

    shutil.copy(ruta, os.path.join(destino, archivo))

    return full, "OK"


# ============================
# MAIN
# ============================

def main():
    archivos = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

    print("\n==============================================")
    print("  🔥 Limpieza/Reclasificación KAIQI Vision 4o")
    print("==============================================")
    print(f"Total imágenes por procesar: {len(archivos)}")

    registros = []

    for idx, archivo in enumerate(archivos, start=1):
        print(f"\n[{idx}/{len(archivos)}] → {archivo}")

        datos, estado = procesar_imagen(archivo)

        if datos:
            datos["archivo"] = archivo
            registros.append(datos)

        time.sleep(0.4)  # anti-rate limit

    # Guardar CSV
    import pandas as pd
    df = pd.DataFrame(registros)
    df.to_csv(CSV_SALIDA, index=False, encoding="utf-8-sig")

    print("\n==============================================")
    print("   🎉 PROCESO FINALIZADO")
    print("==============================================")
    print(f"Carpeta MAESTRAS:      {FOLDER_MAESTRAS}")
    print(f"Carpeta EDITAR:        {FOLDER_EDITAR}")
    print(f"Carpeta DESCARTADAS:   {FOLDER_DESCARTADAS}")
    print(f"CSV técnico 360°:      {CSV_SALIDA}")


if __name__ == "__main__":
    main()
