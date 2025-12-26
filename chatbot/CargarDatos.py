from neo4j import GraphDatabase
from dotenv import load_dotenv
import os
import pandas as pd
import numpy as np

load_dotenv()

# Conexión a Neo4j. 
uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")
driver = GraphDatabase.driver(uri, auth=(user, password))

# Cargamos el dataset.

# df = pd.read_csv(r"C:\Users\Admin\Desktop\SIBI\data\all_bikez_clean.csv")
current_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(current_dir, '..', 'data', 'all_bikez_clean.csv')
df = pd.read_csv(csv_path)

# Reemplazamos NaN o None por "Unknown".
df = df.replace({np.nan: "Unknown"})

# Eliminamos filas sin marca o modelo.
df = df[(df["Brand"] != "Unknown") & (df["Model"] != "Unknown")]

# Insertamos los datos.
def insertar_moto(tx, row):
    query = """
    MERGE (b:Brand {name: $brand})
    MERGE (m:Motorcycle {
        model: $model,
        year: $year,
        category: $category,
        displacement: $displacement,
        power: $power,
        fuel_capacity: $fuel_capacity,
        dry_weight: $dry_weight,
        seat_height: $seat_height,
        torque: $torque,
        cooling_system: $cooling,
        transmission: $transmission,
        gearbox: $gearbox,
        engine_stroke: $stroke,
        engine_cylinder: $cylinder
    })
    MERGE (b)-[:FABRICA]->(m)
    """
    tx.run(query, {
        "brand": str(row["Brand"]),
        "model": str(row["Model"]),
        "year": str(row["Year"]),
        "category": str(row["Category"]),
        "displacement": str(row["Displacement (ccm)"]),
        "power": str(row["Power (hp)"]),
        "fuel_capacity": str(row["Fuel capacity (lts)"]),
        "dry_weight": str(row["Dry weight (kg)"]),
        "seat_height": str(row["Seat height (mm)"]),
        "torque": str(row["Torque (Nm)"]),
        "cooling": str(row["Cooling system"]),
        "transmission": str(row["Transmission type"]),
        "gearbox": str(row["Gearbox"]),
        "stroke": str(row["Engine stroke"]),
        "cylinder": str(row["Engine cylinder"])
    })

# Ejecutamos la carga.
with driver.session() as session:
    for i, row in df.iterrows():
        try:
            session.execute_write(insertar_moto, row)
        except Exception as e:
            print(f"Error en fila {i}: {e}")
        if i % 500 == 0:
            print(f"{i} motos cargadas...")

print("Todas las motos han sido cargadas")

driver.close()
