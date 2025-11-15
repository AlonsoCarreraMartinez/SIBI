import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent     
DATA_DIR = BASE_DIR                   
INPUT_FILE = DATA_DIR / "all_bikez_curated.csv"
OUTPUT_FILE = DATA_DIR / "all_bikez_clean.csv"

# Cargamos el CSV.
df = pd.read_csv(INPUT_FILE, encoding="utf-8")

# Seleccionamos las columnas que vamos a utilizar.
cols = [
    "Brand", "Model", "Year", "Category", "Displacement (ccm)", "Power (hp)",
    "Fuel capacity (lts)", "Dry weight (kg)", "Seat height (mm)", "Torque (Nm)",
    "Cooling system", "Transmission type", "Gearbox", "Engine stroke", "Engine cylinder"
]

df = df[cols]

print("Primeras 5 filas del dataset:\n", df.head(), "\n")

# Rellenamos valores vacíos.
df = df.fillna("Unknown")

# Convertimos a formato numérico.
numeric_cols = [
    "Year", "Displacement (ccm)", "Power (hp)", "Fuel capacity (lts)",
    "Dry weight (kg)", "Seat height (mm)", "Torque (Nm)"
]
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

print("Tipos de datos por columna:\n", df.dtypes, "\n")

# Eliminamos duplicados.
df = df.drop_duplicates(subset=["Brand", "Model", "Year"])
df = df.dropna(subset=["Model"])

# Guardamos el dataset.
df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")



