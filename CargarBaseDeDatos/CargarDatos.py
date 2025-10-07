from neo4j import GraphDatabase
import pandas as pd
import numpy as np

# Nos onectamos a Neo4j 
uri = "bolt://localhost:7687"
user = "neo4j"
password = "neo4j123"
driver = GraphDatabase.driver(uri, auth=(user, password))

# Cargamos el dataset 
df = pd.read_csv(r"C:\Users\Admin\Desktop\SIBI\LimpiadorDeColumnas\all_bikez_clean.csv")

# Reemplazamos NaN o None por "Unknown" 
df = df.replace({np.nan: "Unknown"})

# Eliminamos filas sin marca o modelo 
df = df[(df["Brand"] != "Unknown") & (df["Model"] != "Unknown")]

# Insertamos los datos
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
        rating: $rating,
        color_options: $colors,
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
        "rating": str(row["Rating"]),
        "colors": str(row["Color options"]),
        "gearbox": str(row["Gearbox"]),
        "stroke": str(row["Engine stroke"]),
        "cylinder": str(row["Engine cylinder"])
    })

# Ejecutamos la carga 
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
