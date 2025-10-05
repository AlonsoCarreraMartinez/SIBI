import pandas as pd

# Cargamos el CSV
df = pd.read_csv(
    r"C:\Users\Admin\Desktop\Proyecto\all_bikez_curated.csv",
    encoding="utf-8"
)

# Seleccionamos las columnas que vamos a utilizar
cols = [
    "Brand", "Model", "Year", "Category", "Displacement (ccm)", "Power (hp)",
    "Fuel capacity (lts)", "Dry weight (kg)", "Seat height (mm)", "Torque (Nm)",
    "Cooling system", "Transmission type", "Rating", "Color options",
    "Gearbox", "Engine stroke", "Engine cylinder"
]

df = df[cols]

print("Primeras 5 filas del dataset:\n", df.head(), "\n")

# Rellenamos valores vacíos
df = df.fillna("Unknown")

# Convertimos a formato numérico
numeric_cols = [
    "Year", "Displacement (ccm)", "Power (hp)", "Fuel capacity (lts)",
    "Dry weight (kg)", "Seat height (mm)", "Torque (Nm)"
]
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

print("Tipos de datos por columna:\n", df.dtypes, "\n")

# Eliminamos duplicados
df = df.drop_duplicates(subset=["Brand", "Model", "Year"])
df = df.dropna(subset=["Model"])

# Guardamos el dataset
df.to_csv(r"C:\Users\Admin\Desktop\Proyecto\all_bikez_clean.csv", index=False, encoding="utf-8")


