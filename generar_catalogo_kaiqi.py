#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import json
import base64
from io import BytesIO
from PIL import Image
import pandas as pd
from openai import OpenAI

# ============================================
# CONFIGURACIÓN AJUSTADA A TU COMPUTADOR
# ============================================

IMAGE_FOLDER = r"C:\img\FOTOS_COMPETENCIA"
OUTPUT_CSV = "catalogo_repuestos_IA.csv"
DESCARTES_CSV = "imagenes_descartadas_no_moto.csv"

OPENAI_MODEL = "gpt-4o-mini"   # rápido + económico

# ============================================
# INSTRUCCIONES DEL EXPERTO PARA LA IA
# ============================================

SCHEMA_INSTRUCCIONES = """
Eres un experto en repuestos para MOTOS y MOTOCARGUEROS.

Debes devolver SOLO un JSON con esta estructura:

{
  "Es_Moto_o_Motocarguero": true/false,
  "Tipo_Vehiculo_Detectado": "moto | motocarguero | carro | camioneta | bus | bicicleta | juguete | electrodomestico | desconocido",
  "Identificacion_Repuesto": "string",
  "Caracteristicas_Observadas": "string",
  "Compatibilidad_Probable": "string",
  "Funcion_Mecanica": "string",
  "Nombre_Comercial_Sugerido": "string",
  "Componente_Taxonomia_Sugerido": "string",
  "Sistema_Vehiculo_Sugerido": "string",
  "Es_Motocarguero": true/false,
  "Tiene_Marcaciones_Grabadas": true/false,
  "Texto_Marcaciones_Detectado": "string",
  "Sugerir_Borrado_Marcaciones": true/false,
  "Observaciones_Extra": "string"
}

Reglas:

- Si NO es moto/motocarguero, devuelve "Es_Moto_o_Motocarguero": false.
- Detecta textos grabados (JAPAN, 2, 54410, etc.) PERO no los uses en el nombre comercial.
- No devuelvas nada fuera del objeto JSON.
"""

# ============================================
# UTILIDADES
# ============================================

def encode_image(image_path: str) -> str | None:
    try:
        with Image.open(image_path) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"[ERROR al abrir {image_path}] {e}")
        return None


def get_ai_response(base64_image: str, filename: str) -> dict | None:
    try:
        client = OpenAI()

        prompt = f"Analiza esta imagen. Archivo: {filename}. Devuelve SOLO el JSON según formato."

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SCHEMA_INSTRUCCIONES},
                {"role": "user",
                 "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url",
                     "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                        "detail": "low"
                     }}
                ]}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )

        return json.loads(response.choices[0].message.content.strip())

    except Exception as e:
        print(f"[ERROR IA en archivo {filename}] {e}")
        return None

# ============================================
# PROCESO PRINCIPAL
# ============================================

def generate_catalog():
    print("\n=============================================")
    print(" Iniciando catalogación de 2844 imágenes...")
    print("=============================================\n")

    archivos = [
        f for f in os.listdir(IMAGE_FOLDER)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    if not archivos:
        print("❌ No hay imágenes para procesar.")
        return

    catalogo = []
    descartes = []

    for i, fname in enumerate(sorted(archivos), start=1):
        ruta = os.path.join(IMAGE_FOLDER, fname)
        print(f"[{i}/{len(archivos)}] Procesando → {fname}")

        b64 = encode_image(ruta)
        if not b64:
            descartes.append({"Filename": fname, "Motivo": "No se pudo abrir"})
            continue

        data = get_ai_response(b64, fname)

        if not data:
            descartes.append({"Filename": fname, "Motivo": "Error IA"})
            continue

        data["Filename_Original"] = fname

        if not data.get("Es_Moto_o_Motocarguero", False):
            print("  → ❌ DESCARTADA (no es moto/motocarguero)")
            descartes.append({
                "Filename": fname,
                "Motivo": "No es moto/motocarguero",
                "Tipo_Vehiculo_Detectado": data.get("Tipo_Vehiculo_Detectado", "")
            })
            continue

        print("  → ✅ OK: Pieza válida de moto/motocarguero")
        catalogo.append(data)

    # -----------------------------------------
    # Guardar catálogo
    # -----------------------------------------
    if catalogo:
        df = pd.DataFrame(catalogo)
        salida_catalogo = os.path.join(IMAGE_FOLDER, OUTPUT_CSV)
        df.to_csv(salida_catalogo, sep=";", index=False, encoding="utf-8-sig")

        print("\n=============================================")
        print(f"✅ Catálogo generado correctamente:")
        print(f"   {salida_catalogo}")
        print(f"   Total piezas válidas: {len(df)}")
        print("=============================================\n")

    # -----------------------------------------
    # Guardar descartados
    # -----------------------------------------
    if descartes:
        df_disc = pd.DataFrame(descartes)
        salida_descartes = os.path.join(IMAGE_FOLDER, DESCARTES_CSV)
        df_disc.to_csv(salida_descartes, sep=";", index=False, encoding="utf-8-sig")

        print("📄 Archivo de descartes:")
        print(f"    {salida_descartes}")
        print(f"    Total descartados: {len(df_disc)}")

    print("\nProceso COMPLETO.\n")

# ============================================

if __name__ == "__main__":
    generate_catalog()
