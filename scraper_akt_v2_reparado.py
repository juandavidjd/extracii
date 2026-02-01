import requests
from bs4 import BeautifulSoup
import os
import time
from urllib.parse import urljoin

# --- NUEVAS LIBRERÍAS ---
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
# ------------------------

# --- CONFIGURACIÓN ---
START_URL = "https://www.aktmotos.com/servicio-tecnico-de-motos/catalogo-de-partes"
BASE_URL = "https://www.aktmotos.com"
OUTPUT_DIR = "manuales_akt"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

print(f"--- INICIANDO DESCARGA V2 (MODO REFORZADO) ---")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- 1. INICIAR SELENIUM (VERSIÓN REFORZADA) ---
try:
    print("Configurando opciones de Chrome...")
    options = Options()
    # Descomenta la siguiente línea si quieres que corra oculto (a veces evita crashes)
    # options.add_argument('--headless') 
    
    # --- Opciones de Estabilidad (CRÍTICAS) ---
    options.add_argument('--disable-gpu') # Desactiva la tarjeta gráfica
    options.add_argument('--no-sandbox') # Requerido para algunos sistemas Windows
    options.add_argument('--disable-dev-shm-usage') # Reduce uso de memoria
    options.add_argument('--log-level=3') # Limpia la consola de errores
    
    print("Instalando/Verificando el driver exacto para tu Chrome...")
    # Usa webdriver-manager para instalar el driver correcto
    s = Service(ChromeDriverManager().install())
    
    print("Iniciando navegador...")
    # Pasa el servicio (s) y las opciones (options)
    driver = webdriver.Chrome(service=s, options=options)
    
    print("Navegador listo.")
    
    driver.get(START_URL)
    
    # Esperar a que la lista de motos cargue
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.elementor-post__card"))
    )
    print("Página de catálogo cargada. Buscando motos...")

    # Encontrar todos los enlaces a las motos
    moto_elements = driver.find_elements(By.CSS_SELECTOR, "a.elementor-post__thumbnail__link")
    links_motos = set()
    
    for link in moto_elements:
        href = link.get_attribute('href')
        if href and '/motos/' in href:
            links_motos.add(href)
            
    print(f"   ✅ Se encontraron {len(links_motos)} páginas de motos para analizar.")

except Exception as e:
    print(f"   ❌ Error crítico con Selenium: {e}")
    if 'driver' in locals():
        driver.quit()
    exit()


# --- 2. VISITAR CADA MOTO Y DESCARGAR PDFS ---
# (Esta parte es idéntica a la anterior y debería funcionar)
total_descargados = 0
if not links_motos:
    print("   🛑 No se encontraron enlaces de motos.")
    driver.quit()
    exit()

for i, url_moto in enumerate(links_motos):
    print(f"\n[{i+1}/{len(links_motos)}] Analizando: {url_moto.split('/')[-2].upper()}...")
    
    try:
        driver.get(url_moto)
        time.sleep(2) 
        moto_soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        pdfs_encontrados = 0
        
        for link in moto_soup.find_all('a', href=True):
            link_text = link.get_text(strip=True).lower()
            
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
        
    time.sleep(1) 

driver.quit()

print("\n" + "="*40)
print(f"PROCESO FINALIZADO")
print(f"Total PDFs descargados: {total_descargados}")
print(f"Archivos guardados en: {OUTPUT_DIR}")
print("="*40)