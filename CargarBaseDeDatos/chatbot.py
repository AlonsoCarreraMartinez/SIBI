from llama_index.llms.ollama import Ollama
from llama_index.graph_stores.neo4j import Neo4jGraphStore
from llama_index.core import Settings
import streamlit as st
import re

# Conexión a Neo4j 
graph_store = Neo4jGraphStore(
    username="neo4j",
    password="neo4j123",
    url="bolt://127.0.0.1:7687",
    database="neo4j"
)

# Configuración del modelo Ollama(llama3:instruct)
llm = Ollama(model="llama3:instruct", request_timeout=300.0)
Settings.llm = llm


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

    match_year = re.search(r"(20\\d{2}|19\\d{2})", pregunta_lower)
    if match_year: # Detectamos el año
        year = match_year.group(1)
        condiciones.append(f"toString(m.year) CONTAINS '{year}'")

    categorias = ["naked", "sport", "touring", "trail", "custom", "scooter", "enduro"]
    for cat in categorias: # Detectamos la categoría
        if cat in pregunta_lower:
            condiciones.append(f"toLower(m.category) CONTAINS '{cat}'")

    # # Detectamos si la moto es “ligera” o “potente” 
    if "ligera" in pregunta_lower:
        condiciones.append("dw <= 180")
    if "potente" in pregunta_lower or "más de 100" in pregunta_lower or "mas de 100" in pregunta_lower:
        condiciones.append("hp >= 100")

    match_num = re.search(r"\b(\d+)\b", pregunta_lower) # Detectamos limit
    if match_num:
        limit = int(match_num.group(1))
        if limit < 1 or limit > 20:  
            limit = 5
    elif any(word in pregunta_lower for word in ["una", "un"]):
        limit = 1
    elif any(word in pregunta_lower for word in ["dos", "par"]):
        limit = 2
    elif any(word in pregunta_lower for word in ["varias", "algunas", "unas", "pocas"]):
        limit = 8
    else:
        limit = 1  

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
    LIMIT {limit}
    """
    print(f"\n Query generada:\n{query}\n")
    return query.strip()


# Ejecutar consulta Cypher 
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


# Generar respuesta 
def generar_respuesta(pregunta, motos):
    if not motos or "Error" in motos[0]:
        return "No encontré motos que cumplan esos criterios. Prueba con otros términos o verifica la marca."

    print("\n Resultados encontrados:")
    for i, moto in enumerate(motos, 1):
        print(f"  {i}. {moto}")
    print()

    prompt = f"""
    El usuario preguntó: "{pregunta}"
    Estas son las motos encontradas en la base de datos:
    {chr(10).join(f"{i+1}. {m}" for i, m in enumerate(motos))}

    Redacta una respuesta clara, amable y razonada explicando
    por qué estas motos podrían ser adecuadas según lo solicitado.
    """
    try:
        respuesta = llm.complete(prompt)
        return respuesta.text.strip()
    except Exception as e:
        return f"Error al generar la respuesta: {e}"

# StreamLit
pregunta = st.text_input("Pregunta")
if st.button("Hacer pregunta"):
    with st.spinner("Recomendando..."):
        query = generar_cypher(pregunta)
        motos = ejecutar_cypher(query)
        respuesta = generar_respuesta(pregunta, motos)
        st.write(respuesta)
     