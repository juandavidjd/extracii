import pandas as pd
import os
import re
import urllib.parse

# --- CONFIGURACIÓN ---
INPUT_FILE = 'Inventario_KAIQI_Shopify_Ready.csv'
HTML_FILE = 'Asistente_Maestro_Busqueda.html'

# Palabras basura para limpiar la búsqueda
STOP_WORDS = [
    'CAJA', 'X10', 'X 10', 'JUEGO', 'KIT', 'PAR', 'UNIDAD', 'ORIGINAL', 'TIPO', 'OEM', 'KAIQI', 
    'REPUESTO', 'DALU', 'SMG', 'HLK', 'TWOM', 'KAY', 'CHO', 'KET', 'MN', 'MV', 'EOM', 'CTO', 'COMPL',
    'X 3', 'X 6', 'PCS'
]

print("--- GENERANDO ASISTENTE DE BÚSQUEDA MAESTRO ---")

try:
    df = pd.read_csv(INPUT_FILE)
    # Filtrar solo los que aún no tienen imagen
    mask_missing = (df['Imagen'].isna()) | (df['Imagen'] == '') | (df['Imagen'] == 'Sin Imagen')
    missing = df[mask_missing].copy()
except Exception as e:
    print(f"Error leyendo {INPUT_FILE}: {e}")
    exit()

def construir_query(row):
    desc = str(row['Descripcion']).upper()
    cat = str(row['Categoria']).upper().replace('REPUESTOS VARIOS', '')
    
    for word in STOP_WORDS:
        desc = desc.replace(word, '')
    
    desc = re.sub(r'[^A-Z0-9\s]', ' ', desc)
    query = f"{cat} {desc} MOTO"
    query = re.sub(r'\s+', ' ', query).strip()
    
    # Codificar para URL
    return urllib.parse.quote_plus(query)

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
a.btn-ayco{background:#D9232D;}
a.btn-vaisand{background:#278FE1;}
a.btn-japan{background:#333;}
a.btn-leo{background:#E07B00;}
a.btn-carguero{background:#F3A600; color:#000;}
</style></head><body>
<h1>Asistente de Búsqueda Visual (Todas las Fuentes)</h1>
<p>Revisa las fotos. Si encuentras la correcta, clic derecho "Guardar imagen como..." y usa el nombre <b>SKU.jpg</b></p>
<table><tr><th>SKU (Nombre)</th><th>Categoría</th><th>Descripción KAIQI</th><th>Acciones</th></tr>"""

for index, row in missing.iterrows():
    sku = str(row['SKU'])
    desc = str(row['Descripcion'])
    cat = str(row['Categoria'])
    
    query_url = construir_query(row)
    
    # Enlaces
    link_google = f"https://www.google.com/search?q={query_url}&tbm=isch"
    link_ayco = f"https://ayco.com.co/repuestos/?jsf=epro-archive-products&s={query_url}"
    link_vaisand = f"https://vaisand.com/repuestos?search={query_url}"
    link_japan = f"https://www.industriasjapan.com/productos?q={query_url}"
    link_leo = f"https://industriasleo.com/shop/?s={query_url}"
    link_carguero_pdf = "https://www.carguerostore.com/wp-content/uploads/2024/05/Catalogo-carguero-store_2024_compressed.pdf"
    
    html += f"<tr><td class='sku'>{sku}.jpg</td><td class='cat'>{cat}</td><td>{desc}</td>"
    html += f"<td>"
    html += f" <a href='{link_google}' target='_blank' class='btn btn-google'>Google</a>"
    html += f" <a href='{link_ayco}' target='_blank' class='btn btn-ayco'>AYCO</a>"
    html += f" <a href='{link_vaisand}' target='_blank' class='btn btn-vaisand'>Vaisand</a>"
    html += f" <a href='{link_japan}' target='_blank' class='btn btn-japan'>Japan</a>"
    html += f" <a href='{link_leo}' target='_blank' class='btn btn-leo'>Leo</a>"
    html += f" <a href='{link_carguero_pdf}' target='_blank' class='btn btn-carguero'>(Abrir PDF)</a>"
    html += f"</td></tr>"

html += "</table></body></html>"

with open(HTML_FILE, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n✅ LISTO: Abre el archivo '{HTML_FILE}' en tu navegador.")