import json
import os

BASE_DIR = r"C:\SRM_ADSI\00_docs"
INDEX_PATH = os.path.join(BASE_DIR, "docs_index.json")
OUTPUT_HTML = os.path.join(BASE_DIR, "panel_documentos.html")

def load_docs_index():
    if not os.path.exists(INDEX_PATH):
        print("❌ No se encontró docs_index.json")
        return []

    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def build_html(data):

    counts = {}
    for item in data:
        cat = item["category"]
        counts[cat] = counts.get(cat, 0) + 1

    # HTML HEADER
    html = """
<!DOCTYPE html>
<html lang='es'>
<head>
<meta charset='UTF-8'>
<title>SRM_ADSI – Panel Documental</title>

<style>
body {
    font-family: Arial, sans-serif;
    background: #f7f7f7;
    margin: 0;
    padding: 20px;
}
h1 {
    text-align: center;
    color: #222;
}
.category-box {
    display: inline-block;
    padding: 10px 20px;
    margin: 5px;
    border-radius: 6px;
    background: #fff;
    border: 1px solid #ccc;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
}
th, td {
    padding: 8px;
    border-bottom: 1px solid #ddd;
}
tr:hover {
    background: #eee;
}
.search-box {
    width: 40%;
    padding: 10px;
    margin: 20px auto;
    display: block;
    font-size: 16px;
}
</style>

<script>
function searchDocs() {
    let input = document.getElementById("search").value.toLowerCase();
    let rows = document.getElementsByClassName("doc-row");

    for (let row of rows) {
        let text = row.innerText.toLowerCase();
        row.style.display = text.includes(input) ? "" : "none";
    }
}
</script>
</head>

<body>

<h1>📚 Panel Documental — SRM_ADSI</h1>

<input id="search" class="search-box" placeholder="Buscar documento..." onkeyup="searchDocs()">

<div>
"""

    # CONTADORES
    for cat, count in counts.items():
        html += f"<div class='category-box'><b>{cat}</b>: {count}</div>"

    html += """
</div>

<table>
<thead>
<tr>
    <th>Documento</th>
    <th>Categoría</th>
    <th>Ruta</th>
</tr>
</thead>
<tbody>
"""

    # FILAS
    for item in data:
        filename = item["file"]
        category = item["category"]

        # Convertir ruta a formato URL seguro
        path = item["new_path"].replace("\\", "/")
        url = "file:///" + path

        row = """
<tr class="doc-row">
    <td>{}</td>
    <td>{}</td>
    <td><a href="{}" target="_blank">📄 Abrir</a></td>
</tr>
""".format(filename, category, url)

        html += row

    # FOOTER
    html += """
</tbody>
</table>

</body>
</html>
"""

    return html

def generate_panel():
    data = load_docs_index()
    if not data:
        return

    html = build_html(data)

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    print("=============================================")
    print(" ✔ PANEL DOCUMENTAL GENERADO")
    print(f" ✔ Archivo: {OUTPUT_HTML}")
    print("=============================================")

if __name__ == "__main__":
    generate_panel()
