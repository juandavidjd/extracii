import pandas as pd
import os
import re

INPUT_FILE = 'Inventario_KAIQI_Shopify_Ready.csv'
HTML_FILE = 'Asistente_Busqueda_Mejorado.html'

df = pd.read_csv(INPUT_FILE)
mask_missing = (df['Imagen'].isna()) | (df['Imagen'] == '') | (df['Imagen'] == 'Sin Imagen')
missing = df[mask_missing]

STOP_WORDS = [
    'CAJA', 'X10', 'X 10', 'JUEGO', 'KIT', 'PAR', 'UNIDAD', 'ORIGINAL', 'TIPO', 'OEM', 'KAIQI', 
    'REPUESTO', 'DALU', 'SMG', 'HLK', 'TWOM', 'KAY', 'CHO', 'KET', 'MN', 'MV', 'EOM', 'CTO', 'COMPL',
    'X 3', 'X 6', 'PCS'
]

def construir_query_url(row):
    desc = str(row['Descripcion']).upper()
    cat = str(row['Categoria']).upper()
    
    for word in STOP_WORDS:
        desc = desc.replace(word, '')
    
    desc = re.sub(r'[^A-Z0-9\s]', ' ', desc)
    cat = cat.replace('REPUESTOS VARIOS', '')
    
    query = f"{cat} {desc} MOTO"
    query = re.sub(r'\s+', ' ', query).strip()
    return query.replace(' ', '+') # Formato URL

html = """<html><head><style>
body{font-family:sans-serif; padding:20px;} 
table{border-collapse:collapse;width:100%; margin-top:20px;} 
td,th{border:1px solid #ddd;padding:10px; text-align:left;} 
tr:nth-child(even){background-color:#f9f9f9;}
tr:hover{background-color:#f1f1f1;}
.sku{font-weight:bold; color:#333;}
.cat{color:#666; font-size:0.9em; text-transform:uppercase;}
a.btn{background:#007bff;color:white;padding:8px 15px;text-decoration:none;border-radius:4px; display:inline-block;}
a.btn:hover{background:#0056b3;}
</style></head><body>
<h1>Asistente de Búsqueda Visual (Lógica Mejorada)</h1>
<p>Guarda la imagen como: <b>SKU.jpg</b></p>
<table><tr><th>SKU (Nombre Archivo)</th><th>Categoría</th><th>Descripción Original</th><th>Acción</th></tr>"""

for index, row in missing.iterrows():
    sku = str(row['SKU'])
    desc = str(row['Descripcion'])
    cat = str(row['Categoria'])
    query_url = construir_query_url(row)
    link = f"https://www.google.com/search?q={query_url}&tbm=isch"
    
    html += f"<tr><td class='sku'>{sku}.jpg</td><td class='cat'>{cat}</td><td>{desc}</td>"
    html += f"<td><a href='{link}' target='_blank' class='btn'>Buscar Imagen</a></td></tr>"

html += "</table></body></html>"

with open(HTML_FILE, "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ LISTO: Abre el archivo '{HTML_FILE}' en tu navegador.")