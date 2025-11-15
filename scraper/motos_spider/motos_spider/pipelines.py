import pandas as pd
from pathlib import Path


class Motos2023_2025Pipeline:

    def open_spider(self, spider):
        self.rows = []

    def process_item(self, item, spider):
        self.rows.append(dict(item))
        return item

    def close_spider(self, spider):

        if not self.rows:
            print("No se han recogido filas desde el spider.")
            return

        df = pd.DataFrame(self.rows)

        numeric_cols = [
            "Year",
            "Displacement (ccm)",
            "Power (hp)",
            "Fuel capacity (lts)",
            "Dry weight (kg)",
            "Seat height (mm)",
            "Torque (Nm)",
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.drop_duplicates(subset=["Brand", "Model", "Year"])
        df = df.dropna(subset=["Model"])
        df = df.fillna("Unknown")

        base_dir = Path(__file__).resolve().parents[2]  
        data_dir = base_dir / "data"
        data_dir.mkdir(exist_ok=True)

        output_file = data_dir / "motos_2023_2025_scraped.csv"
        df.to_csv(output_file, index=False, encoding="utf-8")

        print(f"\nCSV generado en: {output_file}\n")
