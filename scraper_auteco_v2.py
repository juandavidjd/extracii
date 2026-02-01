import os
import csv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

BASE_URL = "https://www.auteco.com.co/blog/post/manuales-de-partes-de-vehiculos-y-propietarios"
ROOT_DIR = r"C:\auteco"
PDF_DIR = os.path.join(ROOT_DIR, "pdfs_extraidos")

os.makedirs(PDF_DIR, exist_ok=True)

# Carpeta clasificadas por tipo
DESTINOS = {
    "manual": os.path.join(ROOT_DIR, "manuales"),
    "catalogo": os.path.join(ROOT_DIR, "catalogos"),
    "diagrama": os.path.join(ROOT_DIR, "diagramas"),
    "otro": os.path.join(ROOT_DIR, "otros")
}

for d in DESTINOS.values():
    os.makedirs(d, exist_ok=True)

CSV_PATH = os.path.join(ROOT_DIR, "inventario_auteco.csv")

# ============================================================
# SESIÓN GLOBAL CON HEADERS DE NAVEGADOR REAL
# ============================================================

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
    "Accept": "*/*",
    "Connection": "keep-alive",
    "Referer": "https://www.auteco.com.co/"
})

# ============================================================
# FUNCIONES DE UTILIDAD
# ============================================================

def es_pdf(url):
    return ".pdf" in url.lower()

def clasificar(nombre):
    n = nombre.lower()
    if "manual" in n or "man-" in n:
        return "manual"
    if "catalog" in n or "catálogo" in n or "catalogo" in n:
        return "catalogo"
    if "diagram" in n:
        return "diagrama"
    return "otro"

def limpiar_nombre(url):
    nombre = os.path.basename(urlparse(url).path)
    if not nombre.lower().endswith(".pdf"):
        nombre += ".pdf"
    return nombre

def extraer_pdfs(url):
    print(f"🔎 Extrayendo PDFs desde: {url}")
    resp = session.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    pdfs = []
    for a in soup.find_all("a", href=True):
        href = urljoin(url, a["href"])
        if es_pdf(href):
            pdfs.append(href)

    pdfs = list(set(pdfs))  # quitar duplicados
    print(f"📄 PDFs encontrados: {len(pdfs)}")
    return pdfs

# ============================================================
# DESCARGA CON REINTENTOS
# ============================================================

def descargar_pdf(url, intentos=3):
    nombre = limpiar_nombre(url)
    tipo = clasificar(nombre)
    destino = DESTINOS[tipo]
    ruta_local = os.path.join(destino, nombre)

    if os.path.exists(ruta_local):
        return (url, ruta_local, tipo, os.path.getsize(ruta_local), "EXISTENTE")

    for intento in range(1, intentos + 1):
        try:
            print(f"⬇ Descargando ({intento}/{intentos}): {nombre}")
            r = session.get(url, stream=True, timeout=25, allow_redirects=True)

            if r.status_code != 200:
                print(f"❌ HTTP {r.status_code} para {url}")
                continue

            with open(ruta_local, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            size = os.path.getsize(ruta_local)
            print(f"✔ Guardado: {ruta_local} ({size} bytes)")

            return (url, ruta_local, tipo, size, "OK")

        except Exception as e:
            print(f"⚠ Error intento {intento} en {url}: {e}")
            time.sleep(1)

    return (url, None, tipo, 0, "FALLÓ")

# ============================================================
# CSV
# ============================================================

def inicializar_csv():
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["url", "archivo_local", "tipo", "tamaño_bytes", "estado"])

def escribir_csv(info):
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(info)

# ============================================================
# MAIN (MULTI-HILO)
# ============================================================

def main():
    inicializar_csv()

    pdfs = extraer_pdfs(BASE_URL)

    print("\n🚀 Iniciando descargas con 8 hilos...\n")

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(descargar_pdf, url): url for url in pdfs}

        for future in as_completed(futures):
            result = future.result()
            escribir_csv(result)

    print("\n🎉 PROCESO COMPLETO")
    print(f"📁 Inventario generado en: {CSV_PATH}")
    print("📦 Carpetas finales:")
    for t, p in DESTINOS.items():
        print(f" - {t}: {p}")

# ============================================================
# EJECUTA
# ============================================================

if __name__ == "__main__":
    main()
