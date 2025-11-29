import pandas as pd
from pathlib import Path

csv_path = Path(__file__).resolve().parent / "all_bikez_clean.csv"
df = pd.read_csv(csv_path)
df['Brand'] = df['Brand'].astype(str).str.capitalize()
df['Category'] = df['Category'].astype(str).str.capitalize()

df.to_csv(csv_path, index=False, encoding='utf-8')
print(f"Dataset normalizado")