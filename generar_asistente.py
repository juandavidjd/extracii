import pandas as pd
import os

INPUT_FILE = 'Inventario_KAIQI_Shopify_Ready.csv'
HTML_FILE = 'Asistente_Busqueda_Manual.html'

df = pd.read_csv(INPUT_FILE)
mask_missing = (df['Imagen'].isna()) | (df['Imagen'] == '') | (df['Imagen'] == 'Sin Imagen')
missing = df[mask_missing]

html = """<html><head><style>
body{font-family:sans-serif;} table{border-collapse:collapse;width:100%;} 
td,th{border:1px solid #ddd;padding:8px;} tr:nth-child(even){background-color:#f2f2f2;}
a.btn{background:#4CAF50;color:white;padding:5px 10px;text-decoration:none;border-radius:3px;}
</style></head><body>
<h2>Asistente de Búsqueda Manual - KAIQI</h2>
<p>Guarda las imágenes en la carpeta 'imagenes' con el nombre exacto del SKU.</p>
<table><tr><th>SKU (Nombre Archivo)</th><th>Descripción</th><th>Acción</th></tr>"""

for index, row in missing.iterrows():
    sku = str(row['SKU'])
    desc = str(row['Descripcion']).replace('"', '')
    query = f"{desc} repuesto moto".replace(' ', '+')
    link = f"https://www.google.com/search?q={query}&tbm=isch"
    
    html += f"<tr><td><b>{sku}.jpg</b></td><td>{desc}</td>"
    html += f"<td><a href='{link}' target='_blank' class='btn'>Buscar en Google</a></td></tr>"

html += "</table></body></html>"

with open(HTML_FILE, "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ Abre el archivo {HTML_FILE} en tu navegador.")