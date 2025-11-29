import csv
import time
import re
import sys
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException


BASE_URL = "https://www.motofichas.com"

def create_driver(headless: bool = False) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--remote-debugging-pipe") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--start-maximized")
    
    try:
        driver = webdriver.Chrome(options=options)
        return driver
    except Exception as e:
        print(f"\nERROR AL ABRIR CHROME: {e}")
        print("💡 Solución: Actualiza tu ChromeDriver o cierra ventanas de Chrome abiertas.")
        sys.exit(1)

def parse_text_body(text):
    mapped = {}
    patterns = {
        "Displacement (ccm)": r"(?:cilindrada|cubica|displacement)[\s\S]{0,20}?(\d+(?:[.,]\d+)?)",
        "Power (hp)": r"(?:potencia|power|cv)[\s\S]{0,20}?(\d+(?:[.,]\d+)?)",
        "Torque (Nm)": r"(?:par\s|torque)[\s\S]{0,20}?(\d+(?:[.,]\d+)?)",
        "Dry weight (kg)": r"(?:peso|weight)[\s\S]{0,20}?(\d{2,3})",
        "Seat height (mm)": r"(?:asiento|seat)[\s\S]{0,20}?(\d{3,4})",
        "Fuel capacity (lts)": r"(?:depósito|tanque|capacity)[\s\S]{0,20}?(\d+(?:[.,]\d+)?)",
    }
    text_lower = text.lower()
    for field, pattern in patterns.items():
        match = re.search(pattern, text_lower)
        if match:
            val = match.group(1).replace(',', '.')
            mapped[field] = val

    if "gasolina" in text_lower: mapped["Fuel control"] = "Gasoline"
    if "eléctrico" in text_lower: mapped["Transmission type"] = "Electric" if "moto eléctrica" in text_lower else "Chain"
    return mapped

def map_html_rows(rows_data):
    mapped = {}
    key_map = {
        "cilindrada": "Displacement (ccm)", "potencia": "Power (hp)", "par": "Torque (Nm)",
        "peso": "Dry weight (kg)", "altura del asiento": "Seat height (mm)",
        "altura asiento": "Seat height (mm)", "capacidad": "Fuel capacity (lts)",
        "depósito": "Fuel capacity (lts)", "refrigeración": "Cooling system",
        "transmisión": "Transmission type", "cambio": "Gearbox", "marchas": "Gearbox",
        "ciclo": "Engine stroke", "cilindros": "Engine cylinder", "motor": "Engine cylinder"
    }
    for label, value in rows_data:
        label_lower = label.lower()
        val_clean = value.replace('\n', ' ').strip()
        for k_es, k_en in key_map.items():
            if k_es in label_lower:
                if k_en in ["Displacement (ccm)", "Power (hp)", "Torque (Nm)", "Fuel capacity (lts)", "Dry weight (kg)", "Seat height (mm)"]:
                    nums = re.findall(r"(\d+[.,]?\d*)", val_clean)
                    if nums: mapped[k_en] = nums[0].replace(',', '.')
                else:
                    mapped[k_en] = val_clean
                break
    return mapped


def get_valid_brand_input():
    while True:
        brand = input("\nIntroduce la marca: ").strip().lower()
        if brand:
            return brand
        print("Por favor, escribe algo.")

def verify_brand_exists(driver, brand_name):

    target_url = f"{BASE_URL}/marcas/{brand_name}"
    print(f"Conectando a {target_url}...")
    try:
        driver.get(target_url)
        time.sleep(2)

        potential_models = driver.find_elements(By.CSS_SELECTOR, f"a[href*='/marcas/{brand_name}/']")
        if len(potential_models) > 0:
            print(f"Marca '{brand_name}' validada.")
            return True
        else:
            print(f"No se encontraron modelos para '{brand_name}'.")
            return False
    except Exception as e:
        print(f"Error verificando marca: {e}")
        return False

def get_brand_model_links(driver, brand_name):
    print(f"Escaneando catálogo de {brand_name.upper()}...")
    for _ in range(3):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)

    selector = f"a[href*='/marcas/{brand_name}/']"
    anchors = driver.find_elements(By.CSS_SELECTOR, selector)
    links = set()
    forbidden = ["125cc", "a-2", "a-1", "carnet", "precio", "fotos", "videos", "prueba", "opiniones", "ofertas", "seguros", "concesionarios", "noticias", "scooter", "naked", "sport", "trail", "custom", "turismo", "competicion"]

    for a in anchors:
        href = a.get_attribute("href")
        if not href: continue
        href = href.split('#')[0].split('?')[0]
        segment = href.rstrip('/').split('/')[-1]
        if segment in forbidden: continue
        if len(segment) < 3 or any(f"/{bad}" in href for bad in forbidden): continue
        links.add(href)

    valid = list(links)
    print(f"URLs detectadas: {len(valid)}")
    return valid

def scrape_single_model(driver, url, brand_name):
    print(f"Procesando: {url}")
    driver.get(url)
    
    try:
        WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button"))).click()
    except: pass

    driver.execute_script("window.scrollTo(0, 400);")
    try:

        candidates = driver.find_elements(By.XPATH, "//*[contains(text(), 'Ficha') or contains(text(), 'Técnica') or contains(text(), 'Datos')]")
        for c in candidates:
            if c.tag_name in ['a', 'li', 'button', 'span', 'div']:
                try:
                    driver.execute_script("arguments[0].click();", c)
                    time.sleep(0.5) 
                    break
                except: pass
        time.sleep(1.5) 
    except: pass

    final_data = {
        "Brand": brand_name.capitalize(), "Model": "Unknown", "Year": "Unknown", "Category": "Unknown",
        "URL": url
    }

    rows = []
    try:
        html_rows = driver.find_elements(By.CSS_SELECTOR, "tr, li.data-item, dl")
        for r in html_rows:
            txt = r.text.replace('\n', ':')
            if ':' in txt:
                parts = txt.split(':')
                if len(parts) >= 2: rows.append((parts[0], parts[1]))
    except: pass
    final_data.update(map_html_rows(rows))

    if "Power (hp)" not in final_data or "Displacement (ccm)" not in final_data:
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            final_data.update({k: v for k, v in parse_text_body(body_text).items() if k not in final_data})
        except: pass

    title = driver.title
    year_match = re.search(r'(202[3-5])', title) or re.search(r'(202[3-5])', url)
    
    if year_match:
        final_data["Year"] = int(year_match.group(1))
    else:
        print("No es modelo 2023-2025.")
        return None

    if final_data["Model"] == "Unknown":
        final_data["Model"] = title.split('-')[0].split('|')[0].strip()

    if not final_data.get("Power (hp)") and not final_data.get("Displacement (ccm)"):
        print("   [FAIL] Datos vacíos.")
        return None

    print(f"   [OK] {final_data['Model']} ({final_data['Year']})")
    return final_data

def main():
    
    brand_name = get_valid_brand_input()
    
    print("\nIniciando navegador blindado...")
    driver = create_driver(headless=False)

    try:
        if not verify_brand_exists(driver, brand_name):
            print("La marca no parece correcta o no tiene modelos. Intenta de nuevo.")
            return

        links = get_brand_model_links(driver, brand_name)
        if not links:
            print("No hay links para procesar.")
            return

        all_rows = []
        for i, link in enumerate(links):
            print(f"--- ({i+1}/{len(links)}) ---")
            try:
                d = scrape_single_model(driver, link, brand_name)
                if d: all_rows.append(d)
            except WebDriverException:
                print("Navegador cerrado o error crítico.")
                driver.quit()
                driver = create_driver(headless=False) 
            except Exception as e:
                print(f"Error leve en {link}: {e}")

        if all_rows:
            csv_filename = f"motos_motofichas_{brand_name}_2023_2025.csv"
            output_path = Path(__file__).resolve().parent / csv_filename
            
            keys = [
                "Brand", "Model", "Year", "Category",
                "Displacement (ccm)", "Power (hp)", "Torque (Nm)",
                "Fuel capacity (lts)", "Dry weight (kg)", "Seat height (mm)",
                "Cooling system", "Transmission type", "Gearbox",
                "Engine stroke", "Engine cylinder", "URL"
            ]
            
            with output_path.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=keys)
                w.writeheader()
                for row in all_rows:
                    safe_row = {k: row.get(k, "Unknown") for k in keys}
                    w.writerow(safe_row)
            
            print(f"\n{len(all_rows)} motos guardadas en: {output_path.name}")
        else:
            print("\nNo se extrajeron motos.")

    finally:
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    main()