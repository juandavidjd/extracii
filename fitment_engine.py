#!/usr/bin/env python3
"""
ODI M6.2 - Fitment Engine
Motor de búsqueda semántica para IND_MOTOS
"""

import os
import json
import re
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

DATA_DIR = os.environ.get('IND_MOTOS_DATA_DIR', '/app/data')
TAXONOMY_PATH = os.environ.get('TAXONOMY_PATH', f'{DATA_DIR}/taxonomy_motos_v1.json')
FITMENT_PATH = os.environ.get('FITMENT_PATH', f'{DATA_DIR}/fitment_master_v1.json')
MAX_RESULTS = int(os.environ.get('M62_MAX_RESULTS', '10'))

# =============================================================================
# SINÓNIMOS REGIONALES (Normalización Semántica)
# =============================================================================

SINONIMOS = {
    # Bujía
    "vela": "bujia",
    "velas": "bujia",
    "chispa": "bujia",
    
    # Frenos
    "balata": "pastilla de freno",
    "balatas": "pastilla de freno",
    "zapata": "banda de freno",
    "zapatas": "banda de freno",
    "fricciones": "pastilla de freno",
    
    # Transmisión
    "pacha": "sprocket",
    "pachas": "sprocket",
    "piñon": "sprocket",
    "piñones": "sprocket",
    "catalina": "sprocket trasero",
    "kit de arrastre": "kit transmision",
    "kit arrastre": "kit transmision",
    "kit de traccion": "kit transmision",
    
    # Rodamientos
    "balinera": "rodamiento",
    "balineras": "rodamiento",
    "rolinera": "rodamiento",
    "rolineras": "rodamiento",
    "ruliman": "rodamiento",
    "rulimanes": "rodamiento",
    
    # Cadena
    "cadenilla": "cadena",
    
    # Clutch/Embrague
    "cloche": "embrague",
    "croche": "embrague",
    "clutch": "embrague",
    
    # Otros
    "farola": "faro",
    "direccional": "luz direccional",
    "direccionales": "luz direccional",
    "pito": "bocina",
    "claxon": "bocina",
    "guaya": "cable",
    "guayas": "cable",
    "manigueta": "manija",
    "manubrio": "manillar",
    "espejos": "espejo",
    "retrovisores": "espejo",
    "retrovisor": "espejo",
}

# =============================================================================
# ALIAS DE MARCAS (Detección de marca en consulta)
# =============================================================================

MARCAS_ALIAS = {
    # Bajaj
    "pulsar": "BAJAJ",
    "boxer": "BAJAJ",
    "discover": "BAJAJ",
    "dominar": "BAJAJ",
    "platino": "BAJAJ",
    "ct100": "BAJAJ",
    "ct 100": "BAJAJ",
    
    # Honda
    "cb": "HONDA",
    "cbf": "HONDA",
    "cgl": "HONDA",
    "xr": "HONDA",
    "navi": "HONDA",
    "dio": "HONDA",
    "pcx": "HONDA",
    "click": "HONDA",
    "wave": "HONDA",
    "splendor": "HONDA",
    
    # Yamaha
    "fz": "YAMAHA",
    "fazer": "YAMAHA",
    "ybr": "YAMAHA",
    "szr": "YAMAHA",
    "sz": "YAMAHA",
    "crypton": "YAMAHA",
    "xtz": "YAMAHA",
    "nmax": "YAMAHA",
    "bws": "YAMAHA",
    "libero": "YAMAHA",
    
    # Suzuki
    "gn": "SUZUKI",
    "gsx": "SUZUKI",
    "gixxer": "SUZUKI",
    "ax": "SUZUKI",
    "ax100": "SUZUKI",
    "ax 100": "SUZUKI",
    "best": "SUZUKI",
    "viva": "SUZUKI",
    
    # AKT
    "akt": "AKT",
    "ak": "AKT",
    "nkd": "AKT",
    "tt": "AKT",
    "flex": "AKT",
    "dynamic": "AKT",
    
    # TVS
    "tvs": "TVS",
    "apache": "TVS",
    "sport": "TVS",
    
    # Auteco
    "victory": "VICTORY",
    "advance": "VICTORY",
    
    # KTM
    "duke": "KTM",
    "rc": "KTM",
    
    # Kawasaki
    "ninja": "KAWASAKI",
    "versys": "KAWASAKI",
    "z": "KAWASAKI",
    
    # Hero
    "hero": "HERO",
    "splendor": "HERO",
    "eco": "HERO",
    "deluxe": "HERO",
    
    # Kymco
    "agility": "KYMCO",
    "fly": "KYMCO",
    "twist": "KYMCO",
}

# =============================================================================
# DATOS EN MEMORIA
# =============================================================================

fitment_data = []
taxonomy_data = {}
index_by_marca = {}
index_by_component = {}
stats = {
    "total_products": 0,
    "loaded_at": None,
    "queries_served": 0
}

# =============================================================================
# FUNCIONES DE CARGA
# =============================================================================

def load_data():
    """Carga los datos de fitment y taxonomía"""
    global fitment_data, taxonomy_data, stats
    
    try:
        # Cargar fitment
        with open(FITMENT_PATH, 'r', encoding='utf-8') as f:
            fitment_data = json.load(f)
        
        # Cargar taxonomía
        with open(TAXONOMY_PATH, 'r', encoding='utf-8') as f:
            taxonomy_data = json.load(f)
        
        stats["total_products"] = len(fitment_data)
        stats["loaded_at"] = datetime.now().isoformat()
        
        # Construir índices
        build_indexes()
        
        print(f"✅ Datos cargados: {stats['total_products']} productos")
        return True
        
    except Exception as e:
        print(f"❌ Error cargando datos: {e}")
        return False

def build_indexes():
    """Construye índices para búsqueda rápida"""
    global index_by_marca, index_by_component
    
    index_by_marca = {}
    index_by_component = {}
    
    for i, product in enumerate(fitment_data):
        # Índice por marca
        if 'fitment' in product and 'canonical' in product['fitment']:
            for fit in product['fitment']['canonical']:
                marca = fit.get('marca', 'GENERICA').upper()
                if marca not in index_by_marca:
                    index_by_marca[marca] = []
                index_by_marca[marca].append(i)
        
        # Índice por componente
        if 'taxonomy' in product:
            component = product['taxonomy'].get('component', '').lower()
            if component:
                if component not in index_by_component:
                    index_by_component[component] = []
                index_by_component[component].append(i)
    
    print(f"📊 Índices: {len(index_by_marca)} marcas, {len(index_by_component)} componentes")

# =============================================================================
# FUNCIONES DE NORMALIZACIÓN
# =============================================================================

def normalizar_query(texto):
    """Normaliza el texto de búsqueda aplicando sinónimos"""
    texto = texto.lower().strip()
    
    # Aplicar sinónimos
    for sinonimo, canonico in SINONIMOS.items():
        texto = re.sub(r'\b' + sinonimo + r'\b', canonico, texto)
    
    return texto

def detectar_marca(texto):
    """Detecta la marca mencionada en el texto"""
    texto_lower = texto.lower()
    
    # Buscar en alias
    for alias, marca in MARCAS_ALIAS.items():
        if alias in texto_lower:
            return marca
    
    # Buscar marcas directamente
    marcas_directas = ["HONDA", "YAMAHA", "SUZUKI", "BAJAJ", "AKT", "TVS", 
                       "VICTORY", "KTM", "KAWASAKI", "HERO", "KYMCO", "AUTECO"]
    for marca in marcas_directas:
        if marca.lower() in texto_lower:
            return marca
    
    return None

def extraer_cilindraje(texto):
    """Extrae el cilindraje del texto"""
    # Patrones: 150cc, 150 cc, 150CC, NS200, 200NS
    patterns = [
        r'(\d{2,3})\s*cc',
        r'(\d{2,3})cc',
        r'ns\s*(\d{2,3})',
        r'(\d{2,3})\s*ns',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, texto.lower())
        if match:
            return match.group(1)
    
    return None

def extraer_keywords(texto):
    """Extrae palabras clave relevantes"""
    # Remover palabras comunes
    stopwords = {'para', 'de', 'la', 'el', 'los', 'las', 'un', 'una', 'tienen', 
                 'hay', 'busco', 'necesito', 'quiero', 'precio', 'cuanto', 'cuesta',
                 'pa', 'pal', 'ese', 'esa', 'esos', 'esas', 'me', 'te', 'se'}
    
    palabras = re.findall(r'\b\w+\b', texto.lower())
    keywords = [p for p in palabras if p not in stopwords and len(p) > 2]
    
    return keywords

# =============================================================================
# FUNCIÓN DE BÚSQUEDA PRINCIPAL
# =============================================================================

def buscar_productos(query_text):
    """Búsqueda semántica de productos"""
    
    # Normalizar query
    query_normalizado = normalizar_query(query_text)
    
    # Extraer información
    marca_detectada = detectar_marca(query_text)
    cilindraje = extraer_cilindraje(query_text)
    keywords = extraer_keywords(query_normalizado)
    
    resultados = []
    indices_candidatos = set()
    
    # Filtrar por marca si se detectó
    if marca_detectada and marca_detectada in index_by_marca:
        indices_candidatos = set(index_by_marca[marca_detectada])
        # Agregar genéricos también
        if 'GENERICA' in index_by_marca:
            indices_candidatos.update(index_by_marca['GENERICA'])
    else:
        # Sin marca, buscar en todo
        indices_candidatos = set(range(len(fitment_data)))
    
    # Buscar en candidatos
    for idx in indices_candidatos:
        product = fitment_data[idx]
        score = 0
        
        # Match por keywords en título
        title_lower = product.get('title', '').lower()
        for kw in keywords:
            if kw in title_lower:
                score += 10
        
        # Match por componente
        component = product.get('taxonomy', {}).get('component', '').lower()
        for kw in keywords:
            if kw in component:
                score += 15
        
        # Match por sistema
        system = product.get('taxonomy', {}).get('system', '').lower()
        for kw in keywords:
            if kw in system:
                score += 5
        
        # Match por cilindraje
        if cilindraje and 'fitment' in product:
            for fit in product['fitment'].get('canonical', []):
                if str(cilindraje) in str(fit.get('cilindraje', '')):
                    score += 20
        
        # Si hay score, agregar resultado
        if score > 0:
            resultados.append({
                'product': product,
                'score': score,
                'marca_match': marca_detectada
            })
    
    # Ordenar por score
    resultados.sort(key=lambda x: (-x['score'], -x['product'].get('confidence', 0)))
    
    return resultados[:MAX_RESULTS], {
        'query_original': query_text,
        'query_normalizado': query_normalizado,
        'marca_detectada': marca_detectada,
        'cilindraje': cilindraje,
        'keywords': keywords
    }

# =============================================================================
# FORMATEO DE RESPUESTA
# =============================================================================

def formatear_respuesta(resultados, meta):
    """Formatea la respuesta para el usuario"""
    
    if not resultados:
        return {
            "status": "not_found",
            "message": f"No encontré productos para '{meta['query_original']}'",
            "answer": f"🔍 No encontré productos que coincidan con tu búsqueda. ¿Podrías darme más detalles como la marca o modelo de tu moto?",
            "results": [],
            "meta": meta
        }
    
    # Formatear resultados
    items = []
    for r in resultados:
        p = r['product']
        items.append({
            "sku_ref": p.get('sku_ref', ''),
            "title": p.get('title', ''),
            "price": p.get('price', 0),
            "price_formatted": f"${p.get('price', 0):,} COP".replace(",", "."),
            "client": p.get('client', ''),
            "confidence": p.get('confidence', 0),
            "taxonomy": p.get('taxonomy', {}),
            "compatibility": extraer_compatibilidad(p)
        })
    
    # Generar respuesta humanizada
    main = items[0]
    answer = f"✅ Sí tenemos: {main['title']}\n"
    answer += f"💰 Precio: {main['price_formatted']}\n"
    answer += f"🏍️ Compatible: {main['compatibility']}"
    
    if len(items) > 1:
        answer += f"\n\n📦 También encontré {len(items)-1} opciones más."
    
    return {
        "status": "success",
        "results_count": len(items),
        "main_result": main,
        "results": items,
        "answer": answer,
        "meta": meta
    }

def extraer_compatibilidad(product):
    """Extrae texto de compatibilidad"""
    if 'fitment' not in product:
        return "Consultar"
    
    fits = product['fitment'].get('canonical', [])[:3]
    compat = []
    for f in fits:
        marca = f.get('marca', '')
        modelo = f.get('modelo', '')
        compat.append(f"{marca} {modelo}".strip())
    
    return ", ".join(compat) if compat else "Consultar"

# =============================================================================
# ENDPOINTS
# =============================================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        "status": "ok",
        "service": "M6.2 Fitment Engine",
        "version": "1.0.0",
        "stats": stats,
        "indexes": {
            "marcas": len(index_by_marca),
            "componentes": len(index_by_component)
        }
    })

@app.route('/fitment/query', methods=['POST'])
def fitment_query():
    """Endpoint principal de búsqueda"""
    global stats
    
    try:
        data = request.get_json() or {}
        query = data.get('q', data.get('query', ''))
        
        if not query:
            return jsonify({
                "status": "error",
                "message": "Se requiere el parámetro 'q' con la consulta"
            }), 400
        
        # Buscar
        resultados, meta = buscar_productos(query)
        stats["queries_served"] += 1
        
        # Formatear respuesta
        response = formatear_respuesta(resultados, meta)
        response["query_id"] = f"M6-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/fitment/brands', methods=['GET'])
def get_brands():
    """Lista las marcas indexadas"""
    return jsonify({
        "status": "ok",
        "brands": list(index_by_marca.keys()),
        "count": len(index_by_marca)
    })

@app.route('/fitment/reload', methods=['POST'])
def reload_data():
    """Recarga los datos"""
    success = load_data()
    return jsonify({
        "status": "ok" if success else "error",
        "message": "Datos recargados" if success else "Error recargando datos"
    })

# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("🚀 Iniciando M6.2 Fitment Engine...")
    load_data()
    app.run(host='0.0.0.0', port=8802, debug=False)
