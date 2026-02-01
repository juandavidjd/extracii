import pandas as pd
import os
import re
import urllib.parse

# --- CONFIGURACIÓN ---
INPUT_FILE = 'Inventario_KAIQI_Shopify_Ready.csv'
HTML_FILE = 'Asistente_Maestro_FINAL.html'
ID_TIENDA_AKT_MELI = "206900898" # ID Oficial de la tienda AKT Repuestos

# Palabras basura para limpiar la búsqueda
STOP_WORDS = [
    'CAJA', 'X10', 'X 10', 'JUEGO', 'KIT', 'PAR', 'UNIDAD', 'ORIGINAL', 'TIPO', 'OEM', 'KAIQI', 
    'REPUESTO', 'DALU', 'SMG', 'HLK', 'TWOM', 'KAY', 'CHO', 'KET', 'MN', 'MV', 'EOM', 'CTO', 'COMPL',
    'X 3', 'X 6', 'PCS'
]

print("--- GENERANDO ASISTENTE DE BÚSQUEDA DEFINITIVO (CON MELI) ---")

try:
    df = pd.read_csv(INPUT_FILE)
    # Filtrar solo los que aún no tienen imagen
    mask_missing = (df['Imagen'].isna()) | (df['Imagen'] == '') | (df['Imagen'] == 'Sin Imagen')
    missing = df[mask_missing].copy()
except Exception as e:
    print(f"Error leyendo {INPUT_FILE}: {e}")
    exit()

def construir_query_url(row, separador='-'):
    desc = str(row['Descripcion']).upper()
    cat = str(row['Categoria']).upper().replace('REPUESTOS VARIOS', '')
    
    for word in STOP_WORDS:
        desc = desc.replace(word, '')
    
    desc = re.sub(r'[^A-Z0-9\s]', ' ', desc)
    query = f"{cat} {desc} MOTO"
    query = re.sub(r'\s+', ' ', query).strip()
    
    # Mercado Libre usa guiones (-)
    # Google usa más (+)
    return query.replace(' ', separador)

html = """<html><head><style>
body{font-family:sans-serif; padding:15px;} 
table{border-collapse:collapse;width:100%; margin-top:15px;} 
td,th{border:1px solid #ddd;padding:10px; text-align:left;} 
tr:nth-child(even){background-color:#f9f9f9;}
.sku{font-weight:bold; color:#333; font-size:1.1em;}
.cat{color:#666; font-size:0.9em; text-transform:uppercase;}
a.btn{
    background:#444; color:white; padding:5px 8px; text-decoration:none; 
    border-radius:4px; display:inline-block; margin:2px; font-size:0.9em;
}
a.btn-google{background:#4CAF50;}
a.btn-meli{background:#FFE600; color:#3483FA; border:1px solid #3483FA; font-weight:bold;} /* Color Meli */
a.btn-ayco{background:#D9232D;}
a.btn-vaisand{background:#278FE1;}
a.btn-japan{background:#333;}
a.btn-leo{background:#E07B00;}
</style></head><body>
<h1>Asistente de Búsqueda Visual (KAIQI + Fuentes Oficiales)</h1>
<p>Revisa las fotos. Si encuentras la correcta, clic derecho "Guardar imagen como..." y usa el nombre <b>SKU.jpg</b></p>
<table><tr><th>SKU (Nombre)</th><th>Categoría</th><th>Descripción KAIQI</th><th>Acciones</th></tr>"""

for index, row in missing.iterrows():
    sku = str(row['SKU'])
    desc = str(row['Descripcion'])
    cat = str(row['Categoria'])
    
    # Query para Google (con +)
    query_google = construir_query_url(row, separador='+')
    # Query para Meli (con -)
    query_meli = construir_query_url(row, separador='-')
    
    # Enlaces
    link_google = f"https://www.google.com/search?q={query_google}&tbm=isch"
    # --- ENLACE MÁGICO ---
    # Busca el repuesto PERO solo dentro de la tienda AKT Oficial
    link_meli = f"https://listado.mercadolibre.com.co/{query_meli}_CustId_{ID_TIENDA_AKT_MELI}"
    # ---
    link_ayco = f"https://ayco.com.co/repuestos/?jsf=epro-archive-products&s={query_google}"
    link_vaisand = f"https://vaisand.com/repuestos?search={query_google}"
    link_japan = f"https://www.industriasjapan.com/productos?q={query_google}"
    
    html += f"<tr><td class='sku'>{sku}.jpg</td><td class='cat'>{cat}</td><td>{desc}</td>"
    html += f"<td>"
    html += f" <a href='{link_meli}' target='_blank' class='btn btn-meli'>Meli (AKT)</a>"
    html += f" <a href='{link_google}' target='_blank' class='btn btn-google'>Google</a>"
    html += f" <a href='{link_ayco}' target='_blank' class='btn btn-ayco'>AYCO</a>"
    html += f" <a href='{link_vaisand}' target='_blank' class='btn btn-vaisand'>Vaisand</a>"
    html += f" <a href='{link_japan}' target='_blank' class='btn btn-japan'>Japan</a>"
    html += f"</td></tr>"

html += "</table></body></html>"

with open(HTML_FILE, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n✅ LISTO: Abre el archivo '{HTML_FILE}' en tu navegador.")