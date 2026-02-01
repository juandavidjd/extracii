import pandas as pd
import os
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURACIÓN ---
# Estas son las URLS de filtro que usa AYCO
CATEGORIAS_A_MINAR = {
    "Motor": "https://ayco.com.co/repuestos/?jsf=epro-archive-products&tax=product_cat:27",
    "Caja_Velocidades": "https://ayco.com.co/repuestos/?jsf=epro-archive-products&tax=product_cat:24",
    "Transmision": "https://ayco.com.co/repuestos/?jsf=epro-archive-products&tax=product_cat:28",
    "Electrico": "https://ayco.com.co/repuestos/?jsf=epro-archive-products&tax=product_cat:26",
    "Chasis": "https://ayco.com.co/repuestos/?jsf=epro-archive-products&tax=product_cat:25",
    "Accesorios": "https://ayco.com.co/repuestos/?jsf=epro-archive-products&tax=product_cat:23"
}

OUTPUT_DIR = "imagenes_ayco"
OUTPUT_CSV = "Base_Datos_AYCO.csv"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

print(f"--- INICIANDO SCRAPER SELENIUM PARA AYCO ---")
print("Se abrirá una ventana de Chrome. No la cierres...")

# Iniciar el navegador
driver = webdriver.Chrome()
driver.implicitly_wait(5) # Espera 5 seg si no encuentra algo

productos_ayco = []
total_descargadas = 0

try:
    # 1. Loop por cada CATEGORÍA
    for cat_nombre, cat_url in CATEGORIAS_A_MINAR.items():
        print(f"\n--- 📂 Iniciando Categoría: {cat_nombre} ---")
        driver.get(cat_url)
        time.sleep(3) # Espera extra para que el JS cargue productos
        
        pagina = 1
        
        # 2. Loop de Paginación (mientras exista el botón "Siguiente")
        while True:
            print(f"  📄 Procesando Página {pagina}...")
            
            # --- AQUÍ LA ESTRUCTURA REAL DE AYCO ---
            items = driver.find_elements(By.CSS_SELECTOR, 'div.jet-woo-products__item')
            
            if not items:
                print("     No se encontraron productos en esta página.")
                break # Salir del loop de paginación

            encontrados_pag = 0
            
            for item in items:
                try:
                    name_tag = item.find_element(By.CSS_SELECTOR, 'h5.jet-woo-products__item-title')
                    nombre = name_tag.text.strip()
                    
                    img_tag = item.find_element(By.CSS_SELECTOR, 'img')
                    img_url = img_tag.get_attribute('src')

                    if img_url and nombre:
                        filename = re.sub(r'[\\/*?:"<>|]', '', nombre) + ".jpg"
                        filepath = os.path.join(OUTPUT_DIR, filename)
                        
                        productos_ayco.append({
                            'Nombre_Externo': nombre.upper(),
                            'Imagen_Externa': filename,
                            'URL_Origen': img_url
                        })
                        
                        if not os.path.exists(filepath):
                            # Descarga con 'requests' (más rápido que Selenium)
                            img_data = requests.get(img_url, timeout=5).content
                            with open(filepath, 'wb') as f:
                                f.write(img_data)
                            encontrados_pag += 1
                except Exception:
                    continue 
            
            print(f"     ✅ {encontrados_pag} imágenes nuevas extraídas.")
            total_descargadas += encontrados_pag
            
            # --- Lógica de Paginación ---
            try:
                # Buscar el botón "siguiente" (flecha)
                next_button = driver.find_element(By.CSS_SELECTOR, 'a.page-numbers.next')
                
                # Scroll para asegurar que el botón es clickeable
                driver.execute_script("arguments[0].scrollIntoView();", next_button)
                time.sleep(0.5)
                
                next_button.click()
                print("     Pasando a página siguiente...")
                pagina += 1
                time.sleep(3) # Espera crucial para que cargue la nueva página
            except:
                # Si no hay botón "next", es la última página
                print("     🛑 Fin de la categoría.")
                break

except Exception as e:
    print(f"   ❌ Error crítico: {e}")
finally:
    driver.quit() # Cerrar la ventana de Chrome

# Guardar Base de Datos Externa
df = pd.DataFrame(productos_ayco)
df = df.drop_duplicates(subset=['Nombre_Externo'])
df.to_csv(OUTPUT_CSV, index=False)

print("\n" + "="*40)
print(f"PROCESO FINALIZADO")
print(f"Total productos recolectados: {len(df)}")
print(f"Imágenes guardadas en: {OUTPUT_DIR}")
print(f"Base de datos creada: {OUTPUT_CSV}")
print("="*40)