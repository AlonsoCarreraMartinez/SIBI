import csv
import time
import re
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

BASE_URL = "https://www.motofichas.com"
YAMAHA_URL = f"{BASE_URL}/marcas/yamaha"

OUTPUT_CSV = Path(__file__).resolve().parent / "motos_motofichas_yamaha_2023_2025.csv"


def create_driver(headless: bool = False) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")

    # Hacernos pasar por un navegador normal
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def slow_scroll(driver, steps: int = 8, pause: float = 1.0):
    """Bajamos poco a poco para que carguen más modelos."""
    for _ in range(steps):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)


def get_yamaha_model_links(driver):
    print(f"[INFO] Entrando a {YAMAHA_URL}")
    driver.get(YAMAHA_URL)

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
    except TimeoutException:
        print("[ERROR] No cargó la página de Yamaha")
        return []

    # Hacemos scroll para que aparezcan más tarjetas
    slow_scroll(driver, steps=10, pause=1.0)

    # Cogemos cualquier enlace que apunte a /marcas/yamaha/<algo>
    links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/marcas/yamaha/']")
    urls = set()

    for a in links:
        href = (a.get_attribute("href") or "").strip()
        if not href:
            continue

        # Normalizamos
        if href.endswith("/"):
            href = href[:-1]

        # Nos quedamos con rutas tipo /marcas/yamaha/mt-03-2025
        if "/marcas/yamaha" in href and href != YAMAHA_URL:
            # Evitar enlaces con anclas, etc.
            if "#" in href:
                href = href.split("#", 1)[0]
            urls.add(href)

    urls = sorted(urls)
    print(f"[INFO] URLs de modelos Yamaha detectadas: {len(urls)}")
    return urls


def extract_number(text):
    """Devuelve el primer número (int o float) encontrado en un texto."""
    if not text:
        return "Unknown"
    # Sustituimos comas por puntos para decimales
    t = text.replace(",", ".")
    m = re.search(r"(\d+(\.\d+)?)", t)
    if not m:
        return "Unknown"
    num = m.group(1)
    # Si es decimal, lo dejamos como está; si no, int
    if "." in num:
        return float(num)
    return int(num)


def parse_year_from_table(rows):
    for label, value in rows:
        if "año" in label.lower():
            y = extract_number(value)
            if isinstance(y, (int, float)):
                return int(y)
    return None


def get_table_rows(driver):
    """
    Devuelve lista [(label, value), ...] de la ficha técnica.

    En Motofichas muchas filas son <tr><th>Etiqueta</th><td>Valor</td>,
    no solo <td><td>. Por eso miramos tanto th como td.
    """
    rows = []

    # Intentamos limitar la búsqueda a la zona de "Ficha técnica" / "Datos"
    try:
        container = driver.find_element(
            By.XPATH,
            "//h2[contains(translate(., 'ÁÉÍÓÚáéíóú', 'AEIOUaeiou'), 'ficha tecnica')]/ancestor::div[1]"
        )
        tr_elements = container.find_elements(By.CSS_SELECTOR, "tr")
    except Exception:
        # Si falla, buscamos en toda la página
        tr_elements = driver.find_elements(By.CSS_SELECTOR, "tr")

    for tr in tr_elements:
        # Celdas pueden ser <th> o <td>
        cells = tr.find_elements(By.CSS_SELECTOR, "th,td")
        if len(cells) < 2:
            continue

        label = cells[0].text.strip()
        value = cells[1].text.strip()

        if not label or not value:
            continue

        rows.append((label, value))

    return rows


def map_fields(rows):
    data = {
        "Brand": "Yamaha",
        "Model": "Unknown",
        "Year": "Unknown",
        "Category": "Unknown",
        "Displacement (ccm)": "Unknown",
        "Power (hp)": "Unknown",
        "Torque (Nm)": "Unknown",
        "Fuel capacity (lts)": "Unknown",
        "Dry weight (kg)": "Unknown",
        "Seat height (mm)": "Unknown",
        "Cooling system": "Unknown",
        "Transmission type": "Unknown",
        "Gearbox": "Unknown",
        "Engine stroke": "Unknown",
        "Engine cylinder": "Unknown",
        "URL": "Unknown",
    }

    for label, value in rows:
        l = label.lower()

        if "modelo" in l or "nombre" in l:
            data["Model"] = value

        if "año" in l:
            year = extract_number(value)
            if isinstance(year, (int, float)):
                data["Year"] = int(year)

        if "cilindrada" in l:
            cc = extract_number(value)
            data["Displacement (ccm)"] = cc

        if "potencia" in l:
            hp = extract_number(value)
            data["Power (hp)"] = hp

        if "par máximo" in l or "par maximo" in l:
            nm = extract_number(value)
            data["Torque (Nm)"] = nm

        if "capacidad del depósito" in l or "capacidad deposito" in l:
            dep = extract_number(value)
            data["Fuel capacity (lts)"] = dep

        if "peso declarado" in l or "peso en orden" in l or "peso en seco" in l:
            kg = extract_number(value)
            data["Dry weight (kg)"] = kg

        if "altura del asiento" in l:
            h = extract_number(value)
            data["Seat height (mm)"] = h

        if "refrigeración" in l:
            data["Cooling system"] = value

        if "tipo de motor" in l or "tipo:" in l and data["Engine stroke"] == "Unknown":
            # suele ser 4T, 2T, etc.
            data["Engine stroke"] = value

        if "cilindros" in l:
            cyl = extract_number(value)
            data["Engine cylinder"] = cyl

        if "cambio" in l:
            data["Transmission type"] = value
            speeds = extract_number(value)
            data["Gearbox"] = speeds

        if "número de velocidades" in l:
            speeds = extract_number(value)
            data["Gearbox"] = speeds

        if "tipo de carnet" in l:
            data["Category"] = value

    return data


def scrape_yamaha_models(driver):
    model_urls = get_yamaha_model_links(driver)
    rows = []

    for i, url in enumerate(model_urls, start=1):
        print(f"[INFO] ({i}/{len(model_urls)}) Procesando modelo: {url}")
        try:
            driver.get(url)
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(1.5)

            # Intentamos ir a la pestaña "Datos" si existe
            try:
                datos_tab = driver.find_element(
                    By.XPATH, "//a[contains(., 'Datos')]"
                )
                datos_tab.click()
                time.sleep(1.0)
            except Exception:
                pass  # si no está, seguimos igual

            # Bajamos hasta ficha técnica
            driver.execute_script("window.scrollBy(0, 600);")
            time.sleep(1.0)

            table_rows = get_table_rows(driver)
            if not table_rows:
                print("   [WARN] No se encontraron filas de ficha técnica")
                continue

            year = parse_year_from_table(table_rows)
            if year is None or year < 2023 or year > 2025:
                print(f"   [INFO] Año {year} fuera de rango, se omite")
                continue

            data = map_fields(table_rows)
            data["URL"] = url

            # Si el título de la página tiene el nombre del modelo, aprovechamos
            try:
                title = driver.title.strip()
                if "Yamaha" in title and data["Model"] == "Unknown":
                    data["Model"] = title
            except Exception:
                pass

            print(f"   [OK] Guardando modelo {data['Model']} ({data['Year']})")
            rows.append(data)

        except Exception as e:
            print(f"   [ERROR] Fallo procesando {url}: {e}")

    return rows


def main():
    driver = create_driver(headless=False)

    try:
        all_rows = scrape_yamaha_models(driver)
    finally:
        driver.quit()

    print(f"[INFO] Total filas válidas: {len(all_rows)}")

    if not all_rows:
        print("[ERROR] No hay filas, no se genera CSV")
        return

    fieldnames = [
        "Brand", "Model", "Year", "Category",
        "Displacement (ccm)", "Power (hp)", "Torque (Nm)",
        "Fuel capacity (lts)", "Dry weight (kg)", "Seat height (mm)",
        "Cooling system", "Transmission type", "Gearbox",
        "Engine stroke", "Engine cylinder", "URL"
    ]

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"[OK] CSV guardado en: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
