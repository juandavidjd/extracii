import pandas as pd
import re
import os

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\scrap"
ARCHIVO_ENTRADA = "CATALOGO NOVIEMBRE V01-2025 NF.xlsx"

OUT_OK = "Base_Datos_Catalogo_REFINED.csv"
OUT_INCOMP = "Base_Datos_Catalogo_INCOMPLETOS.csv"
OUT_FRAG = "Base_Datos_Catalogo_FRAGMENTS.csv"
OUT_DEBUG = "Base_Datos_Catalogo_DEBUG.csv"

ruta_entrada = os.path.join(BASE_DIR, ARCHIVO_ENTRADA)

# ------------------ UTILIDADES ------------------ #

def limpiar_precio(t):
    if pd.isna(t): 
        return None
    s = str(t).replace("$", "").replace(" ", "").replace(".", "").replace(",", "")
    return int(s) if s.isdigit() else None

def es_codigo(s):
    if not isinstance(s, str):
        s = str(s).strip()
    patrones = [
        r"^0\d{4,5}$",
        r"^\d{5}$",
        r"^[A-Z]{1,3}\d{3,5}$",
        r"^[A-Z0-9]{4,8}$"
    ]
    return any(re.match(p, s) for p in patrones)

def limpiar_texto(tx):
    if pd.isna(tx): return ""
    return " ".join(str(tx).replace("\n"," ").replace("\r"," ").split()).strip()

def es_categoria(tx):
    if not isinstance(tx, str):
        return False
    if re.search(r"\d", tx): return False
    if len(tx.strip()) < 4: return False
    if len(tx.strip().split()) <= 5: 
        return True
    return False


# ------------------ PROCESADOR FULL ------------------ #

def limpiar_catalogo_v4_full():
    print("\n--- LIMPIEZA MAESTRA V4 (FULL EXTRACTION) ---")
    print(f"Archivo: {ruta_entrada}")

    if not os.path.exists(ruta_entrada):
        print(f"❌ No existe {ruta_entrada}")
        return

    print("   ⏳ Leyendo Excel...")
    try:
        data = pd.concat(pd.read_excel(ruta_entrada, sheet_name=None, header=None, dtype=str).values(),
                         ignore_index=True)
        print(f"   ✔ Filas cargadas: {len(data)}")
    except Exception as e:
        print(f"❌ Error leyendo: {e}")
        return

    categoria_actual = "GENERAL"
    codigo_actual = None
    buffer_desc = []
    precio_encontrado = None

    productos_ok = []
    incompletos = []
    fragments = []
    debug_log = []

    print("   🔍 Procesando filas...")

    for idx, row in data.iterrows():
        valores = [str(v).strip() for v in row.values if pd.notna(v) and str(v).strip()]

        debug_log.append({"Fila": idx, "Valores": valores})

        if not valores:
            continue

        # Detectar categorías
        if len(valores) == 1 and es_categoria(valores[0]):
            categoria_actual = valores[0].upper()
            continue

        codigo_fila = None
        precio_fila = None
        textos = []

        for v in valores:
            if es_codigo(v):
                codigo_fila = v
            else:
                p = limpiar_precio(v)
                if p and p > 500:
                    precio_fila = p
                else:
                    if not re.match(r"^X\d+$", v, re.IGNORECASE):
                        textos.append(v)

        # Si aparece nuevo código → cerrar anterior
        if codigo_fila:
            if codigo_actual:
                if precio_encontrado:
                    productos_ok.append({
                        "Codigo": codigo_actual,
                        "Descripcion": limpiar_texto(" ".join(buffer_desc)),
                        "Precio": precio_encontrado,
                        "Categoria": categoria_actual
                    })
                else:
                    incompletos.append({
                        "Codigo": codigo_actual,
                        "Descripcion": limpiar_texto(" ".join(buffer_desc)),
                        "Categoria": categoria_actual,
                        "Precio": 0
                    })

            codigo_actual = codigo_fila
            buffer_desc = []
            precio_encontrado = None

        # Acumular descripciones
        if textos:
            buffer_desc.extend(textos)

        # Si aparece precio → cerrar producto completo
        if precio_fila:
            precio_encontrado = precio_fila

            if codigo_actual:
                productos_ok.append({
                    "Codigo": codigo_actual,
                    "Descripcion": limpiar_texto(" ".join(buffer_desc)),
                    "Precio": precio_encontrado,
                    "Categoria": categoria_actual
                })

                # Reset
                codigo_actual = None
                buffer_desc = []
                precio_encontrado = None
            else:
                # Precio sin código → fragmento útil
                fragments.append({
                    "Tipo": "PRECIO_SIN_CODIGO",
                    "Fila": idx,
                    "Valores": valores
                })

        # Si la fila no tiene nada clasificable → guardar como fragmento
        if not codigo_fila and not precio_fila and textos:
            fragments.append({
                "Tipo": "TEXTO_SUELTO",
                "Fila": idx,
                "Valores": textos,
                "Categoria": categoria_actual
            })

    # Exportar resultados
    print("\n📦 Exportando archivos...")

    pd.DataFrame(productos_ok).drop_duplicates("Codigo").to_csv(
        os.path.join(BASE_DIR, OUT_OK), sep=";", index=False, encoding="utf-8-sig"
    )

    pd.DataFrame(incompletos).to_csv(
        os.path.join(BASE_DIR, OUT_INCOMP), sep=";", index=False, encoding="utf-8-sig"
    )

    pd.DataFrame(fragments).to_csv(
        os.path.join(BASE_DIR, OUT_FRAG), sep=";", index=False, encoding="utf-8-sig"
    )

    pd.DataFrame(debug_log).to_csv(
        os.path.join(BASE_DIR, OUT_DEBUG), sep=";", index=False, encoding="utf-8-sig"
    )

    print("✔ COMPLETADO")
    print(f"   Productos completos: {len(productos_ok)}")
    print(f"   Productos incompletos: {len(incompletos)}")
    print(f"   Fragmentos útiles: {len(fragments)}")
    print(f"   Debug rows: {len(debug_log)}")


if __name__ == "__main__":
    limpiar_catalogo_v4_full()
