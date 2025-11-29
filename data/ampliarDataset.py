import pandas as pd
from pathlib import Path
import sys


BASE_DIR = Path(__file__).resolve().parent

MAIN_CSV_PATH = BASE_DIR / "all_bikez_clean.csv"
NEW_CSV_PATH = BASE_DIR.parent / "scraper" / "motos_motofichas_2023_2025_clean.csv" 

def main():
    
    if not MAIN_CSV_PATH.exists():
        print(f"No se encuentra el dataset principal en: {MAIN_CSV_PATH}")
        return
    if not NEW_CSV_PATH.exists():
        print(f"No se encuentra el archivo a añadir en: {NEW_CSV_PATH}")
        return

    print(f"Cargando dataset principal...")
    try:
        df_main = pd.read_csv(MAIN_CSV_PATH)
        rows_before = len(df_main)
    except Exception as e:
        print(f"Error leyendo dataset principal: {e}")
        return

    print(f"Cargando nuevos datos desde scraper...")
    try:
        df_new = pd.read_csv(NEW_CSV_PATH)
        rows_new = len(df_new)
        print(f"Encontradas {rows_new} motos nuevas para añadir.")
    except Exception as e:
        print(f"Error leyendo nuevos datos: {e}")
        return

    print("Ampliando el dataset...")
    df_combined = pd.concat([df_main, df_new], ignore_index=True)

    print("Eliminando duplicados exactos...")
    df_combined = df_combined.drop_duplicates(
        subset=['Brand', 'Model', 'Year'], 
        keep='last'
    )

    print("Organizando alfabéticamente...")
    df_combined = df_combined.sort_values(
        by=['Brand', 'Model', 'Year'], 
        ascending=[True, True, False]
    )

    try:
        df_combined.to_csv(MAIN_CSV_PATH, index=False, encoding='utf-8')
        rows_after = len(df_combined)
        added = rows_after - rows_before
        
        print(f"\n Dataset ampliado.")
        print(f"   Archivo: {MAIN_CSV_PATH}")
        print(f"   Filas iniciales: {rows_before}")
        print(f"   Filas actuales:  {rows_after} (añadido: {added})")
        
        print("\nVista previa de las últimas motos añadidas:")
        print(df_combined[['Brand', 'Model', 'Year']].head(3))
        print(df_combined[['Brand', 'Model', 'Year']].tail(3))
        
    except Exception as e:
        print(f"Error guardando el archivo: {e}")

if __name__ == "__main__":
    main()