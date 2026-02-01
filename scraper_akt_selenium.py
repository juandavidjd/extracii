import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
import re
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURACIÓN ---
START_URL = "https://www.aktmotos.com/servicio-tecnico-de-motos/catalogo-de-partes"
BASE_URL = "https://www.aktmotos.com"
OUTPUT_DIR = "manuales_akt"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

print(f"--- INICIANDO DESCARGA SELENIUM DE MANUALES AKT ---")
print("Se abrirá una ventana de Chrome. No la cierres...")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- 1. INICIAR SELENIUM Y OBTENER LISTA DE MOTOS ---
try:
    driver = webdriver.Chrome()
    driver.get(START_URL)
    
    # Esperar a que la lista de motos cargue
    # Esperamos por la "caja" que contiene las motos
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.elementor-post__card"))
    )
    print("Página de catálogo cargada. Buscando motos...")

    # Encontrar todos los enlaces a las motos
    moto_elements = driver.find_elements(By.CSS_SELECTOR, "a.elementor-post__thumbnail__link")
    links_motos = set() # Usamos un 'set' para evitar duplicados
    
    for link in moto_elements:
        href = link.get_attribute('href')
        if href and '/motos/' in href:
            links_motos.add(href)
            
    print(f"   ✅ Se encontraron {len(links_motos)} páginas de motos para analizar.")

except Exception as e:
    print(f"   ❌ Error crítico con Selenium: {e}")
    driver.quit()
    exit()


# --- 2. VISITAR CADA MOTO Y DESCARGAR PDFS ---
total_descargados = 0
if not links_motos:
    print("   🛑 No se encontraron enlaces de motos.")
    driver.quit()
    exit()

for i, url_moto in enumerate(links_motos):
    print(f"\n[{i+1}/{len(links_motos)}] Analizando: {url_moto.split('/')[-2].upper()}...")
    
    try:
        # Usamos el mismo driver para ir a la página de la moto
        driver.get(url_moto)
        # Esperar a que carguen los botones de descarga
        time.sleep(2) 
        
        # Obtenemos el HTML ya renderizado por el navegador
        moto_soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        pdfs_encontrados = 0
        
        for link in moto_soup.find_all('a', href=True):
            link_text = link.get_text(strip=True).lower()
            
            # Buscamos los textos clave
            if "catálogo de partes" in link_text or "manual de propietario" in link_text or "manual de servicio" in link_text:
                
                pdf_url = link['href']
                
                if not pdf_url.startswith('http'):
                    pdf_url = urljoin(BASE_URL, pdf_url)
                
                if not pdf_url.lower().endswith('.pdf'):
                    continue
                    
                pdf_name = os.path.basename(pdf_url)
                filepath = os.path.join(OUTPUT_DIR, pdf_name)
                
                if not os.path.exists(filepath):
                    print(f"   -> Descargando: {pdf_name}...")
                    # Usamos requests para la descarga (es más estable para archivos)
                    pdf_data = requests.get(pdf_url, headers=headers, timeout=20).content
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
        
    time.sleep(1) # Pausa entre motos

# Cerrar el navegador
driver.quit()

print("\n" + "="*40)
print(f"PROCESO FINALIZADO")
print(f"Total PDFs descargados: {total_descargados}")
print(f"Archivos guardados en: {OUTPUT_DIR}")
print("="*40)