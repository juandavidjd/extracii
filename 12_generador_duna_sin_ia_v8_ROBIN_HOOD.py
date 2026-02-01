import os
import pandas as pd
import re
from difflib import SequenceMatcher

# ================= CONFIGURACIÓN =================
BASE_DIR = r"C:\img"

# Archivos
ARCHIVO_RICO_FUENTE = os.path.join(BASE_DIR, "catalogo_kaiqi_imagenes_Bara.csv")
ARCHIVO_POBRE_DESTINO = os.path.join(BASE_DIR, "catalogo_kaiqi_imagenes_DUNA.csv") # El que generó la v5
ARCHIVO_SALIDA = os.path.join(BASE_DIR, "catalogo_kaiqi_imagenes_DUNA_ENRIQUECIDO.csv")

# Diccionario de Reglas (Por si no hay match con Bara)
# Palabras clave -> (Sistema, Subsistema, Función)
REGLAS_EXPERTO = {
    "BOMBILLO": ("Eléctrico", "Iluminación", "Proveer iluminación"),
    "FAROLA": ("Eléctrico", "Iluminación", "Iluminación frontal"),
    "STOP": ("Eléctrico", "Iluminación", "Señalización trasera"),
    "DIRECCIONAL": ("Eléctrico", "Iluminación", "Señalización de giro"),
    "LLANTA": ("Chasis", "Ruedas", "Tracción y contacto"),
    "NEUMATICO": ("Chasis", "Ruedas", "Cámara de aire"),
    "AMORTIGUADOR": ("Suspensión", "Trasera/Delantera", "Absorber impactos"),
    "BATERIA": ("Eléctrico", "Energía", "Almacenamiento de carga"),
    "CARBURADOR": ("Motor", "Admisión", "Mezcla aire-combustible"),
    "CILINDRO": ("Motor", "Potencia", "Cámara de combustión"),
    "PISTON": ("Motor", "Potencia", "Compresión"),
    "EMPAQUE": ("Motor", "Sellado", "Evitar fugas"),
    "RETEN": ("Motor", "Sellado", "Retención de fluidos"),
    "GUAYA": ("Control", "Mandos", "Accionamiento mecánico"),
    "ESPEJO": ("Chasis", "Carrocería", "Visibilidad trasera"),
    "MANIGUETA": ("Control", "Manubrio", "Accionamiento freno/clutch"),
    "BALINERA": ("Transmisión", "Rodamientos", "Reducir fricción"),
    "KIT ARRASTRE": ("Transmisión", "Final", "Transmitir potencia a rueda"),
    "CADENA": ("Transmisión", "Final", "Tracción"),
    "PIÑON": ("Transmisión", "Engranajes", "Transmisión de movimiento"),
    "BANDAS": ("Frenos", "Tambor", "Frenado por fricción"),
    "PASTILLAS": ("Frenos", "Disco", "Frenado hidráulico"),
    "DISCO": ("Frenos", "Disco", "Superficie de frenado"),
    "CLUTCH": ("Motor", "Embrague", "Conexión motor-caja")
}

# ================= UTILIDADES =================
def similitud(a, b):
    return SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio()

def cargar_fuente_rica():
    print("📚 Cargando Conocimiento de BARA...")
    if not os.path.exists(ARCHIVO_RICO_FUENTE):
        print("   ❌ No encuentro el archivo Bara. Usaré solo reglas.")
        return []
    
    try:
        # Intentar leer Bara
        try: df = pd.read_csv(ARCHIVO_RICO_FUENTE, sep=';', encoding='utf-8-sig')
        except: df = pd.read_csv(ARCHIVO_RICO_FUENTE, sep=';', encoding='latin-1')
        
        conocimiento = []
        for _, row in df.iterrows():
            conocimiento.append({
                "nombre": str(row.get('Nombre_Comercial_Catalogo', '')),
                "sistema": str(row.get('Sistema', '')),
                "sub": str(row.get('SubSistema', '')),
                "func": str(row.get('Funcion', '')),
                "carac": str(row.get('Caracteristicas_Observadas', '')),
                "tags": str(row.get('Tags_Sugeridos', ''))
            })
        return conocimiento
    except Exception as e:
        print(f"   ⚠️ Error leyendo Bara: {e}")
        return []

def enriquecer_duna():
    print("\n🚀 INICIANDO ENRIQUECIMIENTO 'ROBIN HOOD' (Sin IA)...")
    
    # 1. Cargar Duna (El Pobre)
    if not os.path.exists(ARCHIVO_POBRE_DESTINO):
        print("❌ No encuentro el catálogo Duna base.")
        return

    try:
        df_duna = pd.read_csv(ARCHIVO_POBRE_DESTINO, sep=';', encoding='utf-8-sig')
    except:
        print("❌ Error leyendo Duna base.")
        return

    # 2. Cargar Bara (El Rico)
    base_conocimiento = cargar_fuente_rica()
    
    resultados = []
    stats = {"match_bara": 0, "match_regla": 0, "sin_datos": 0}

    print(f"🔍 Procesando {len(df_duna)} productos de Duna...")

    for idx, row in df_duna.iterrows():
        nombre_duna = str(row.get('Identificacion_Repuesto', '')).upper()
        
        # Datos a rellenar
        sistema = "General"
        subsistema = ""
        funcion = ""
        carac = ""
        tags = ""
        origen_dato = "NADA"

        # ESTRATEGIA A: Buscar Gemelo en Bara
        mejor_match = None
        mejor_score = 0
        
        # Solo buscamos si tenemos base de conocimiento (optimización: buscar solo si hay palabras clave comunes)
        # Para hacerlo rápido en local, hacemos barrido simple o optimizado
        # Optimización: Buscar solo si comparten la primera palabra
        palabra_clave = nombre_duna.split()[0] if nombre_duna else ""
        
        candidatos = [c for c in base_conocimiento if palabra_clave in c['nombre'].upper()]
        
        for cand in candidatos:
            score = similitud(nombre_duna, cand['nombre'])
            if score > mejor_score:
                mejor_score = score
                mejor_match = cand
        
        if mejor_match and mejor_score > 0.65: # Si se parecen más del 65%
            sistema = mejor_match['sistema']
            subsistema = mejor_match['sub']
            funcion = mejor_match['func']
            carac = mejor_match['carac']
            tags = mejor_match['tags']
            origen_dato = f"BARA ({(mejor_score*100):.0f}%)"
            stats["match_bara"] += 1
        
        else:
            # ESTRATEGIA B: Reglas de Experto (Regex)
            encontrado = False
            for key, val in REGLAS_EXPERTO.items():
                if key in nombre_duna:
                    sistema = val[0]
                    subsistema = val[1]
                    funcion = val[2]
                    carac = f"Repuesto tipo {key} estándar."
                    tags = f"{key}, {sistema}, Repuesto Moto"
                    origen_dato = "REGLA_EXPERTA"
                    stats["match_regla"] += 1
                    encontrado = True
                    break
            
            if not encontrado:
                stats["sin_datos"] += 1
                carac = "Pendiente de clasificación manual."

        # Actualizar Fila
        row['Sistema'] = sistema
        row['SubSistema'] = subsistema
        row['Funcion'] = funcion
        row['Caracteristicas_Observadas'] = carac
        row['Tags_Sugeridos'] = tags
        # row['Origen_Datos'] = origen_dato # Opcional para debug

        resultados.append(row)
        
        if idx % 100 == 0: print(f"   ... {idx}/{len(df_duna)}", end="\r")

    # 3. Guardar
    df_final = pd.DataFrame(resultados)
    df_final.to_csv(ARCHIVO_SALIDA, index=False, sep=';', encoding='utf-8-sig')
    
    print("\n" + "="*50)
    print(f"✅ ENRIQUECIMIENTO COMPLETADO")
    print(f"   Total: {len(df_final)}")
    print(f"   Rellenados con Bara: {stats['match_bara']}")
    print(f"   Rellenados con Reglas: {stats['match_regla']}")
    print(f"   Vacíos: {stats['sin_datos']}")
    print(f"   Archivo Rico: {os.path.basename(ARCHIVO_SALIDA)}")
    print("="*50)

if __name__ == "__main__":
    enriquecer_duna()