import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
import re
from urllib.parse import urljoin

# --- CONFIGURACIÓN ---
START_URL = "https://www.aktmotos.com/servicio-tecnico-de-motos/catalogo-de-partes"
BASE_URL = "https://www.aktmotos.com"
OUTPUT_DIR = "manuales_akt"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

print(f"--- INICIANDO DESCARGA DE MANUALES Y CATÁLOGOS AKT ---")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- 1. OBTENER LISTA DE MOTOS ---
print(f"Buscando todas las motos en: {START_URL}")
try:
    response = requests.get(START_URL, headers=headers, timeout=10)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    links_motos = set() # Usamos un 'set' para evitar duplicados
    
    # Buscamos todos los enlaces en la página
    for link in soup.find_all('a', href=True):
        href = link['href']
        # Filtramos solo los que parecen ser una página de moto
        if '/motos/' in href and href.startswith(BASE_URL):
            links_motos.add(href)
            
    print(f"   ✅ Se encontraron {len(links_motos)} páginas de motos para analizar.")

except Exception as e:
    print(f"   ❌ Error crítico cargando la página principal: {e}")
    exit()


# --- 2. VISITAR CADA MOTO Y DESCARGAR PDFS ---
total_descargados = 0
if not links_motos:
    print("   🛑 No se encontraron enlaces de motos. Revisar estructura de AKT.")
    exit()

for i, url_moto in enumerate(links_motos):
    print(f"\n[{i+1}/{len(links_motos)}] Analizando: {url_moto.split('/')[-2].upper()}...") # Muestra el nombre de la moto
    
    try:
        moto_page = requests.get(url_moto, headers=headers, timeout=10)
        moto_soup = BeautifulSoup(moto_page.content, 'html.parser')
        
        pdfs_encontrados = 0
        
        # Buscamos enlaces que contengan el texto de descarga
        for link in moto_soup.find_all('a', href=True):
            link_text = link.get_text(strip=True).lower()
            
            if "catálogo de partes" in link_text or "manual de propietario" in link_text or "manual de servicio" in link_text:
                
                pdf_url = link['href']
                
                # Asegurarse que la URL es completa
                if not pdf_url.startswith('http'):
                    pdf_url = urljoin(BASE_URL, pdf_url) # Une la base con el link relativo
                
                # Solo descargar si es un PDF
                if not pdf_url.lower().endswith('.pdf'):
                    continue
                    
                # Obtener nombre del archivo (ej: CP-NKD-125.pdf)
                pdf_name = os.path.basename(pdf_url)
                filepath = os.path.join(OUTPUT_DIR, pdf_name)
                
                if not os.path.exists(filepath):
                    print(f"   -> Descargando: {pdf_name}...")
                    pdf_data = requests.get(pdf_url, headers=headers, timeout=15).content
                    with open(filepath, 'wb') as f:
                        f.write(pdf_data)
                    pdfs_encontrados += 1
                    total_descargados += 1
                else:
                    print(f"   -> Ya existe: {pdf_name}")

        if pdfs_encontrados == 0:
            print("   -> No se encontraron PDFs en esta página.")
            
    except Exception as e:
        print(f"   ❌ Error analizando {url_moto}: {e}")
        
    time.sleep(1) # Pausa respetuosa

print("\n" + "="*40)
print(f"PROCESO FINALIZADO")
print(f"Total PDFs descargados: {total_descargados}")
print(f"Archivos guardados en: {OUTPUT_DIR}")
print("="*40)