from llama_index.llms.ollama import Ollama
from llama_index.graph_stores.neo4j import Neo4jGraphStore
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core import Settings, Document, VectorStoreIndex, StorageContext, load_index_from_storage
import streamlit as st
import pandas as pd
import os
import re

# Conexión a Neo4j.
graph_store = Neo4jGraphStore(
    username="neo4j",
    password="neo4j123",
    url="bolt://127.0.0.1:7687",
    database="neo4j"
)

# Configuración del modelo Ollama(llama3:instruct).
llm = Ollama(model="llama3:instruct", request_timeout=300.0)
Settings.llm = llm

# Embeddings con LlamaIndex.
EMBEDDING_DIR = os.path.join(os.path.dirname(__file__), "storage_motos")
os.makedirs(EMBEDDING_DIR, exist_ok=True) #Creamos la carpeta en caso de que  no exista
EMBED_MODEL = OllamaEmbedding(model_name="llama3")

def crear_indice_si_no_existe():

    docstore_path = os.path.join(EMBEDDING_DIR, "docstore.json")

    if not os.path.exists(docstore_path):
        print("Creando índice vectorial")

        base_dir = os.path.dirname(__file__)
        csv_path = os.path.abspath(os.path.join(base_dir, "..", "LimpiadorDeColumnas", "all_bikez_clean.csv"))

        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"No se encontró el CSV en la ruta: {csv_path}")

        df = pd.read_csv(csv_path, encoding="utf-8").fillna("Unknown")

        def describir_moto(row):
            return (
                f"{row['Brand']} {row['Model']} es una moto {row['Category']} "
                f"con {row['Power (hp)']} caballos, {row['Displacement (ccm)']} cc, "
                f"peso {row['Dry weight (kg)']} kg, "
                f"altura de asiento {row['Seat height (mm)']} mm y valoración {row['Rating']}."
            )

        documentos = [Document(text=describir_moto(r)) for _, r in df.iterrows()]
        index = VectorStoreIndex.from_documents(documentos, embed_model=EMBED_MODEL)
        index.storage_context.persist(persist_dir=EMBEDDING_DIR)

        print(f"El índice fue creado correctamente en: {EMBEDDING_DIR}")

    else:
        print("El índice ya existe")

# Función generadora de consultas Cypher 
def generar_cypher(pregunta: str) -> str:

    pregunta_lower = pregunta.lower()
    condiciones = []

    marcas = ["honda", "yamaha", "kawasaki", "suzuki", "bmw", "ducati", "ktm", "triumph", "harley"] 
    for marca in marcas: # Detectamos la marca
        if marca in pregunta_lower:
            condiciones.append(f"b.name =~ '(?i){marca}'")

    match_cc = re.search(r"(\d{2,4})\s*(?:cc|cm3|cm cúbicos)?", pregunta_lower)
    if match_cc: # Detectamos la cilindrada
        cc = int(match_cc.group(1))
        condiciones.append(f"cc >= {cc - 100} AND cc <= {cc + 100}")

    match_year = re.search(r"\b(20\d{2}|19\d{2})\b", pregunta_lower)
    if match_year: # Detectamos el año
        year = match_year.group(1)
        condiciones.append(f"toInteger(m.year) >= {year}")

    categorias = {
        "naked": ["naked"],
        "sport": ["sport", "deportiva", "racing"],
        "touring": ["touring", "viaje"],
        "trail": ["trail", "enduro", "adventure"],
        "custom": ["custom", "chopper"],
        "scooter": ["scooter", "urbana"]
    }

    for key, alias in categorias.items(): # Detectamos la categoría
        if any(word in pregunta_lower for word in alias):
            condiciones.append(f"toLower(m.category) CONTAINS '{key}'")

    # Detectamos si la moto es ligera o potente 
    if "ligera" in pregunta_lower or "liviana" in pregunta_lower:
        condiciones.append("dw <= 180")
    if any(word in pregunta_lower for word in ["potente", "más de 100", "mas de 100", "fuerte"]):
        condiciones.append("hp >= 100")

    # Detectamos si el usuario especifica un número concreto de resultados
    match_num = re.search(r"(\d+)\s*(?:moto|motos)", pregunta_lower)
    limit_clause = f"LIMIT {match_num.group(1)}" if match_num else ""  # solo si lo pide el usuario

    # Contruir consultas Cypher 
    where_clause = " AND ".join(condiciones)
    if where_clause:
        where_clause = f"WHERE {where_clause}"

    query = f"""
    MATCH (b:Brand)-[:FABRICA]->(m:Motorcycle)
    WITH 
        b, 
        m,
        toFloat(m.displacement) AS cc,
        toFloat(m.power) AS hp,
        toFloat(m.dry_weight) AS dw
    {where_clause}
    RETURN 
        b.name AS marca,
        m.model AS modelo,
        m.category AS tipo,
        cc AS cilindrada,
        hp AS potencia,
        m.year AS año,
        dw AS peso
    ORDER BY rand()
    {limit_clause}
    """
    print(f"\n Query generada:\n{query}\n")
    return query.strip()

# Ejecutamos la consulta Cypher
def ejecutar_cypher(query):
    try:
        resultados = graph_store.query(query)
        lista = []
        for r in resultados:
            marca = r.get("marca", "Desconocida")
            modelo = r.get("modelo", "N/A")
            tipo = r.get("tipo", "N/A")
            cc = r.get("cilindrada", "N/A")
            potencia = r.get("potencia", "N/A")
            año = r.get("año", "N/A")
            peso = r.get("peso", "N/A")
            lista.append(f"{marca} {modelo} ({tipo}) - {cc} cc, {potencia} hp, {peso} kg, año {año}")
        return lista
    except Exception as e:
        return [f"Error al ejecutar Cypher: {e}"]

# Realizamos la búsqueda semántica
def buscar_motos_semanticamente(pregunta):
    try:
        query_engine = index.as_query_engine(similarity_top_k=8)
        resultado = query_engine.query(pregunta)
        return [resultado.response]
    except Exception as e:
        return [f"Error en la búsqueda: {e}"]

# Respuesta
def generar_respuesta(pregunta, motos):
    if not motos or "Error" in motos[0]:

        print("No se encontraron coincidencias exactas. Buscando recomendaciones semánticas...")
        motos = buscar_motos_semanticamente(pregunta)
        if not motos:
            return "No encontré motos que encajen con esa descripción."
    
    print("\nResultados encontrados:")
    for i, moto in enumerate(motos, 1):
        print(f"  {i}. {moto}")
    print()

    prompt = f"""
Eres MOTORBOT, un experto en motociclismo con años de experiencia asesorando a motoristas de todo tipo. 
Tu función es actuar como un RECOMENDADOR DE MOTOS experto, ayudando al usuario a encontrar la moto perfecta según sus necesidades, nivel de experiencia, presupuesto y estilo de conducción.

Tienes acceso a una BASE DE DATOS de motocicletas con las siguientes columnas:
- Marca (Brand)
- Modelo (Model)
- Año (Year)
- Categoría (Category) [posibles valores: sport, naked, touring, adventure/trail, custom/cruiser, scooter, enduro, classic]
- Cilindrada (Displacement ccm)
- Potencia (Power hp)
- Par motor (Torque Nm)
- Peso en seco (Dry weight kg)
- Altura del asiento (Seat height mm)
- Capacidad del depósito (Fuel capacity lts)
- Sistema de refrigeración (Cooling system)
- Tipo de transmisión (Transmission type)
- Caja de cambios (Gearbox)
- Ciclo del motor (Engine stroke)
- Cilindros (Engine cylinder)
- Valoración general (Rating)
- Colores disponibles (Color options)
- Descripción o notas (description)

REGLAS DE CONDUCTA Y COMPORTAMIENTO:
1. Responde SIEMPRE en español, sin excepción.
2. Usa ÚNICAMENTE los datos disponibles en la base de datos. 
   Si un valor no está disponible, escribe “no especificado” o “dato no disponible”.
3. No inventes ni adivines cifras, peso, potencia o años.
4. Evita confundir categorías de motos. No llames “sport” a una naked ni “custom” a una touring.
5. Respeta las restricciones que pida el usuario (potencia, cilindrada, peso, color, año, tipo de moto...).
6. Si el usuario solicita comparar modelos, haz una comparación técnica y objetiva usando los datos.
7. No muestres IDs, consultas ni información técnica interna.
8. No limites tus recomendaciones a dos modelos: ofrece tantas como consideres útiles según la pregunta.
9. Mantén un tono profesional, claro y natural, demostrando conocimiento técnico.
10. No recomiendes motos inapropiadas para el nivel del usuario (por ejemplo, superbikes a principiantes).
11. Si no hay coincidencias exactas, ofrece las más cercanas y explícalo brevemente.

FORMATO DE RESPUESTA:
Usa siempre esta estructura:

Recomendaciones:
1. Marca Modelo (Año) — Tipo: {{Category}}
   - Cilindrada: {{Displacement (ccm)}} cc
   - Potencia: {{Power (hp)}} CV
   - Par motor: {{Torque (Nm)}} Nm
   - Peso: {{Dry weight (kg)}} kg
   - Altura de asiento: {{Seat height (mm)}} mm
   - Depósito: {{Fuel capacity (lts)}} L
   - Transmisión: {{Transmission type}}
   - Caja de cambios: {{Gearbox}}
   - Cilindros: {{Engine cylinder}}
   - Refrigeración: {{Cooling system}}
   - Colores disponibles: {{Color options}}
   - Motivo de recomendación: explicación breve, técnica y coherente con la solicitud del usuario.

2. (Siguiente modelo...)
   ...

Conclusión:
Cierra con una o dos líneas resumiendo qué modelo o modelos encajan mejor con la solicitud y por qué.

OBJETIVO FINAL:
Ofrecer recomendaciones técnicas y realistas, sin inventar información. 
Adapta siempre el nivel técnico a la experiencia del usuario (principiante, intermedio, experto). 
Tu prioridad es ayudarle a tomar una decisión informada, precisa y útil.

El usuario preguntó: "{pregunta}"

Estas son las motos encontradas en la base de datos o por similitud semántica:
{chr(10).join(f"{i+1}. {m}" for i, m in enumerate(motos))}
"""

    try:
        respuesta = llm.complete(prompt)
        return respuesta.text.strip()
    except Exception as e:
        return f"Error al generar la respuesta: {e}"

# Streamlit
pregunta = st.text_input("Pregunta")
if st.button("Hacer pregunta"):
    with st.spinner("Recomendando..."):
        query = generar_cypher(pregunta)
        motos = ejecutar_cypher(query)
        respuesta = generar_respuesta(pregunta, motos)
        st.write(respuesta)
