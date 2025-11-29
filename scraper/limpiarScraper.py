import pandas as pd
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
INPUT_CSV = BASE_DIR / "motos_motofichas_2023_2025.csv"
OUTPUT_CSV = BASE_DIR / "motos_motofichas_2023_2025_clean.csv"

# Limpia el nombre del modelo
def clean_model_name(row):
    name = str(row['Model'])
    name = name.replace("▷", "").strip()
    if name.lower().startswith("yamaha"):
        name = name[6:].strip()
    name = re.sub(r'\s202[0-9]$', '', name)
    
    return name.strip()

# Limpia la categoría
def infer_category(row):
    if row['Category'] != 'Unknown':
        return row['Category']
    
    model = str(row['Model']).upper()
    
    if any(x in model for x in ['YZ', 'WR', 'TT-R', 'PW']):
        return "Cross / Enduro"
    if any(x in model for x in ['MT', 'XSR']):
        return "Naked"
    if any(x in model for x in ['R1', 'R6', 'R7', 'R3', 'R125', 'R-']):
        return "Sport"
    if any(x in model for x in ['TRACER', 'TENERE', 'NIKEN']):
        return "Touring / Trail"
    if any(x in model for x in ['TMAX', 'XMAX', 'NMAX', 'TRICITY', 'D\'ELIGHT', 'NEO', 'RAY']):
        return "Scooter"
    
    return "Street" 

def clean_torque(val):

    try:
        if pd.isna(val) or val == "Unknown":
            return "Unknown"
        
        val_str = str(val).replace(',', '.')
        num = float(val_str)
        
        if num > 400: return "Unknown" 
        if num < 1: return "Unknown"
        
        return num
    except:
        return "Unknown"

def main():
    print(f"--- LIMPIANDO DATASET: {INPUT_CSV.name} ---")
    
    try:
        df = pd.read_csv(INPUT_CSV)
    except FileNotFoundError:
        print(f"No se encuentra el archivo '{INPUT_CSV.name}'.")
        print("Asegúrate de haber ejecutado el scraper primero.")
        return

    df['Model'] = df.apply(clean_model_name, axis=1)
    
    df['Category'] = df.apply(infer_category, axis=1)
    
    cols_to_numeric = ["Displacement (ccm)", "Power (hp)", "Torque (Nm)", "Dry weight (kg)", "Seat height (mm)"]
    
    for col in cols_to_numeric:
        if col == "Torque (Nm)":
            df[col] = df[col].apply(clean_torque)
        else:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    df = df.fillna("Unknown")

    if 'URL' in df.columns:
        df = df.drop(columns=['URL'])
        print("Columna URL eliminada.")
    
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8')
    print(f"Limpieza completada.")
    print(f"Archivo guardado en: {OUTPUT_CSV.name}")
    print("\nPrimeras filas del resultado:")
    print(df[['Brand', 'Model', 'Year', 'Category', 'Power (hp)']].head(5))

if __name__ == "__main__":
    main()