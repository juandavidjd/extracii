#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M6.2 Fitment Engine — Motor de Búsqueda Semántica Industrial
ODI-ADSI v17.0

Funciones:
- Carga taxonomía y catálogo fitment
- Normaliza consultas con sinónimos regionales
- Busca compatibilidades por marca/modelo/componente
- Responde en lenguaje natural
"""

import json
import os
import re
from typing import List, Dict, Optional
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# ============================================================
# CONFIGURACIÓN
# ============================================================

DATA_DIR = os.environ.get('IND_MOTOS_DATA_DIR', '/app/data')
TAXONOMY_PATH = os.environ.get('TAXONOMY_PATH', f'{DATA_DIR}/taxonomy_motos_v1.json')
FITMENT_PATH = os.environ.get('FITMENT_PATH', f'{DATA_DIR}/fitment_master_v1.json')
MAX_RESULTS = int(os.environ.get('M62_MAX_RESULTS', 5))

# ============================================================
# SINÓNIMOS REGIONALES (Jerga → Canónico)
# ============================================================

SINONIMOS = {
    # Frenos
    "vela": "bujia",
    "balata": "pastilla de freno",
    "zapata": "banda de freno",
    "fricciones": "pastilla de freno",
    
    # Transmisión
    "pacha": "sprocket",
    "catalina": "sprocket",
    "kit de traccion": "kit arrastre",
    "kit arrastre": "kit arrastre",
    "cadenilla": "cadena de tiempo",
    
    # Motor
    "empaque": "junta",
    "reten": "sello",
    "balinera": "rodamiento",
    "rolinera": "rodamiento",
    
    # Eléctrico
    "bombillo": "foco",
    "foco": "bombillo",
    "pito": "claxon",
    
    # Coloquial
    "eso que para": "pastilla de freno",
    "lo de frenar": "pastilla de freno",
    "pa frenar": "pastilla de freno",
}

# Marcas normalizadas
MARCAS_ALIAS = {
    "pulsar": "BAJAJ",
    "boxer": "BAJAJ", 
    "discover": "BAJAJ",
    "dominar": "BAJAJ",
    "platino": "BAJAJ",
    "cb": "HONDA",
    "cbf": "HONDA",
    "xr": "HONDA",
    "nxr": "HONDA",
    "cg": "HONDA",
    "eco": "HONDA",
    "splendor": "HONDA",
    "fz": "YAMAHA",
    "ybr": "YAMAHA",
    "xtz": "YAMAHA",
    "mt": "YAMAHA",
    "r15": "YAMAHA",
    "gn": "SUZUKI",
    "gixxer": "SUZUKI",
    "gsx": "SUZUKI",
    "ax": "SUZUKI",
    "best": "SUZUKI",
    "nkd": "AKT",
    "akt": "AKT",
    "tt": "AKT",
    "cr4": "AKT",
    "flex": "AKT",
    "apache": "TVS",
    "ntorq": "TVS",
    "agility": "KYMCO",
    "fly": "KYMCO",
}


class FitmentEngine:
    """Motor de búsqueda semántica para repuestos de motos"""
    
    def __init__(self):
        self.taxonomy = {}
        self.catalog = []
        self.index_by_brand = {}
        self.index_by_component = {}
        self.stats = {
            "total_items": 0,
            "brands": set(),
            "components": set(),
            "load_time": None
        }
        self._load_data()
    
    def _load_data(self):
        """Carga taxonomía y catálogo en memoria"""
        start = datetime.now()
        
        # Cargar taxonomía
        if os.path.exists(TAXONOMY_PATH):
            try:
                with open(TAXONOMY_PATH, 'r', encoding='utf-8') as f:
                    self.taxonomy = json.load(f)
                print(f"[M6.2] Taxonomía cargada: {len(self.taxonomy)} sistemas")
            except Exception as e:
                print(f"[M6.2] Error cargando taxonomía: {e}")
        
        # Cargar catálogo fitment
        if os.path.exists(FITMENT_PATH):
            try:
                with open(FITMENT_PATH, 'r', encoding='utf-8') as f:
                    self.catalog = json.load(f)
                self._build_indexes()
                print(f"[M6.2] Catálogo cargado: {len(self.catalog)} productos")
            except Exception as e:
                print(f"[M6.2] Error cargando catálogo: {e}")
        
        self.stats["load_time"] = (datetime.now() - start).total_seconds()
        self.stats["total_items"] = len(self.catalog)
    
    def _build_indexes(self):
        """Construye índices para búsqueda rápida"""
        for item in self.catalog:
            # Índice por marca
            fitment = item.get("fitment", {})
            canonical = fitment.get("canonical", []) or fitment.get("inferred", [])
            
            for fit in canonical:
                if isinstance(fit, dict):
                    marca = fit.get("marca", "").upper()
                    if marca:
                        self.stats["brands"].add(marca)
                        if marca not in self.index_by_brand:
                            self.index_by_brand[marca] = []
                        self.index_by_brand[marca].append(item)
            
            # Índice por componente
            taxonomy = item.get("taxonomy", {})
            component = taxonomy.get("component", "").lower()
            if component:
                self.stats["components"].add(component)
                if component not in self.index_by_component:
                    self.index_by_component[component] = []
                self.index_by_component[component].append(item)
    
    def normalize_query(self, query: str) -> str:
        """Normaliza consulta aplicando sinónimos"""
        query = query.lower().strip()
        
        # Aplicar sinónimos
        for slang, canonical in SINONIMOS.items():
            if slang in query:
                query = query.replace(slang, canonical)
        
        return query
    
    def extract_brand(self, query: str) -> Optional[str]:
        """Extrae marca de la consulta"""
        query_lower = query.lower()
        
        for alias, brand in MARCAS_ALIAS.items():
            if alias in query_lower:
                return brand
        
        return None
    
    def extract_cc(self, query: str) -> Optional[str]:
        """Extrae cilindraje de la consulta"""
        # Buscar patrones como "200cc", "150", "200ns"
        patterns = [
            r'(\d{2,3})\s*cc',
            r'(\d{2,3})\s*ns',
            r'(\d{2,3})\s*st',
            r'\b(\d{2,3})\b'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                cc = match.group(1)
                if 50 <= int(cc) <= 1000:  # Rango válido para motos
                    return cc
        
        return None
    
    def search(self, user_query: str) -> List[Dict]:
        """Búsqueda principal"""
        normalized = self.normalize_query(user_query)
        brand = self.extract_brand(user_query)
        cc = self.extract_cc(user_query)
        
        keywords = normalized.split()
        results = []
        seen_skus = set()
        
        # Estrategia 1: Buscar por marca si se detectó
        if brand and brand in self.index_by_brand:
            for item in self.index_by_brand[brand]:
                if self._matches(item, keywords, cc):
                    sku = item.get("sku_ref", "")
                    if sku not in seen_skus:
                        results.append(item)
                        seen_skus.add(sku)
                        if len(results) >= MAX_RESULTS:
                            break
        
        # Estrategia 2: Búsqueda general si no hay suficientes resultados
        if len(results) < MAX_RESULTS:
            for item in self.catalog:
                sku = item.get("sku_ref", "")
                if sku in seen_skus:
                    continue
                    
                if self._matches(item, keywords, cc):
                    results.append(item)
                    seen_skus.add(sku)
                    if len(results) >= MAX_RESULTS:
                        break
        
        return results
    
    def _matches(self, item: Dict, keywords: List[str], cc: Optional[str]) -> bool:
        """Verifica si un item coincide con los criterios"""
        # Construir texto de búsqueda
        title = item.get("title", "").lower()
        sku = item.get("sku_ref", "").lower()
        taxonomy = item.get("taxonomy", {})
        component = taxonomy.get("component", "").lower()
        system = taxonomy.get("system", "").lower()
        
        fitment = item.get("fitment", {})
        canonical = fitment.get("canonical", []) or fitment.get("inferred", [])
        fitment_text = " ".join([
            f"{f.get('marca', '')} {f.get('modelo', '')} {f.get('cilindraje', '')}"
            for f in canonical if isinstance(f, dict)
        ]).lower()
        
        search_text = f"{title} {sku} {component} {system} {fitment_text}"
        
        # Verificar keywords
        match_count = 0
        for kw in keywords:
            if len(kw) >= 2 and kw in search_text:
                match_count += 1
        
        # Al menos 50% de keywords deben coincidir
        if len(keywords) > 0 and match_count / len(keywords) < 0.5:
            return False
        
        # Filtrar por cilindraje si se especificó
        if cc:
            if cc not in search_text and f"{cc}cc" not in search_text:
                # Verificar rangos (ej: 125-200)
                range_match = False
                for fit in canonical:
                    if isinstance(fit, dict):
                        cil = fit.get("cilindraje", "")
                        if "-" in str(cil):
                            try:
                                low, high = map(int, str(cil).split("-"))
                                if low <= int(cc) <= high:
                                    range_match = True
                                    break
                            except:
                                pass
                        elif str(cc) in str(cil):
                            range_match = True
                            break
                
                if not range_match:
                    return False
        
        return match_count > 0
    
    def format_response(self, results: List[Dict], query: str) -> Dict:
        """Formatea respuesta para el usuario"""
        if not results:
            return {
                "status": "not_found",
                "message": f"No encontré repuestos para: {query}",
                "suggestion": "Intenta con otra marca o modelo. Ej: 'pastillas Pulsar 200'"
            }
        
        # Formatear primer resultado como respuesta principal
        main = results[0]
        price = main.get("price", 0)
        price_str = f"${price:,.0f} COP" if price > 0 else "Consultar precio"
        
        taxonomy = main.get("taxonomy", {})
        fitment = main.get("fitment", {})
        canonical = fitment.get("canonical", []) or fitment.get("inferred", [])
        
        # Construir lista de compatibilidades
        compat_list = []
        for fit in canonical[:3]:
            if isinstance(fit, dict):
                marca = fit.get("marca", "")
                modelo = fit.get("modelo", "")
                if marca and modelo:
                    compat_list.append(f"{marca} {modelo}")
        
        compat_str = ", ".join(compat_list) if compat_list else "Varias motos"
        
        return {
            "status": "success",
            "count": len(results),
            "main_result": {
                "title": main.get("title", "Repuesto"),
                "sku": main.get("sku_ref", ""),
                "price": price,
                "price_formatted": price_str,
                "system": taxonomy.get("system", ""),
                "component": taxonomy.get("component", ""),
                "compatibility": compat_str,
                "confidence": main.get("confidence", 0.5)
            },
            "answer": f"✅ Sí tenemos: {main.get('title', 'Repuesto')}\n💰 Precio: {price_str}\n🏍️ Compatible: {compat_str}",
            "alternatives": [
                {
                    "title": r.get("title", ""),
                    "price": r.get("price", 0),
                    "sku": r.get("sku_ref", "")
                }
                for r in results[1:4]
            ]
        }


# ============================================================
# INSTANCIA GLOBAL
# ============================================================

engine = FitmentEngine()


# ============================================================
# ENDPOINTS
# ============================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        "status": "ok",
        "service": "M6.2 Fitment Engine",
        "version": "1.0.0",
        "fitment_items": engine.stats["total_items"],
        "brands_indexed": len(engine.stats["brands"]),
        "components_indexed": len(engine.stats["components"]),
        "load_time_seconds": engine.stats["load_time"]
    })


@app.route('/fitment/query', methods=['POST'])
def query():
    """Endpoint principal de búsqueda"""
    data = request.json or {}
    user_query = data.get("q", data.get("query", ""))
    
    if not user_query:
        return jsonify({
            "status": "error",
            "message": "Falta el parámetro 'q' con la consulta"
        }), 400
    
    results = engine.search(user_query)
    response = engine.format_response(results, user_query)
    
    # Agregar metadata
    response["query_received"] = user_query
    response["query_normalized"] = engine.normalize_query(user_query)
    response["timestamp"] = datetime.now().isoformat()
    
    return jsonify(response)


@app.route('/fitment/brands', methods=['GET'])
def list_brands():
    """Lista marcas indexadas"""
    return jsonify({
        "brands": sorted(list(engine.stats["brands"])),
        "count": len(engine.stats["brands"])
    })


@app.route('/fitment/reload', methods=['POST'])
def reload_data():
    """Recarga datos (para actualizaciones)"""
    global engine
    engine = FitmentEngine()
    return jsonify({
        "status": "reloaded",
        "items": engine.stats["total_items"]
    })


# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    port = int(os.environ.get('M62_PORT', 8802))
    print(f"[M6.2] Fitment Engine iniciando en puerto {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)
