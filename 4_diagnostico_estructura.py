import requests
from bs4 import BeautifulSoup
import re

URL = "https://armvalle.com/?page_id=394"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def diagnosticar():
    print(f"--- DIAGNOSTICANDO: {URL} ---")
    try:
        r = requests.get(URL, headers=HEADERS, timeout=15)
    except Exception as e:
        print(f"Error conectando: {e}")
        return

    soup = BeautifulSoup(r.text, 'html.parser')
    
    # Buscar todas las imágenes
    imgs = soup.find_all('img')
    print(f"Total imágenes encontradas: {len(imgs)}")
    
    count = 0
    print("\n--- MUESTRA DE ESTRUCTURA (Primeras 10 imágenes relevantes) ---")
    
    for img in imgs:
        src = img.get('src', '')
        # Ignorar iconos pequeños, pixels, logos
        if 'logo' in src or 'icon' in src or 'pixel' in src:
            continue
            
        # Obtener padres para entender la estructura
        padres = []
        curr = img.parent
        for _ in range(3): # Subir 3 niveles
            if curr:
                name = curr.name
                classes = curr.get('class', [])
                padres.append(f"{name}.{'.'.join(classes)}")
                curr = curr.parent
            else:
                break
        
        print(f"\nIMAGEN: {src.split('/')[-1]}")
        print(f"   Jerarquía: {' > '.join(padres)}")
        
        # Buscar texto cercano
        texto_cerca = img.find_parent(['div', 'tr', 'li'])
        if texto_cerca:
            txt = texto_cerca.get_text(" ", strip=True)[:50]
            print(f"   Texto cercano: {txt}...")
            
        count += 1
        if count >= 10: break

if __name__ == "__main__":
    diagnosticar()