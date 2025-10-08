from llama_index.llms.ollama import Ollama
from llama_index.graph_stores.neo4j import Neo4jGraphStore
from llama_index.core import Settings

# Nos conectamos a Neo4j
graph_store = Neo4jGraphStore(
    username="neo4j",
    password="neo4j123",
    url="bolt://localhost:7687",
    database="neo4j"
)

# Nos conectamos a Ollama
llm = Ollama(model="llama3.1")
Settings.llm = llm

def consultar_grafo(pregunta):
    query = f"""
    MATCH (b:Brand)-[:FABRICA]->(m:Motorcycle)
    WHERE toLower(m.category) CONTAINS toLower("{pregunta}")
       OR toLower(m.model) CONTAINS toLower("{pregunta}")
       OR toLower(b.name) CONTAINS toLower("{pregunta}")
    RETURN b.name AS marca, m.model AS modelo, m.category AS tipo, m.power AS potencia
    LIMIT 10
    """
    try:
        result = graph_store.query(query)

        if not result:
            return "No encontré resultados."
        if hasattr(result, "raw_result"):
            data = result.raw_result
        elif isinstance(result, list):
            data = result
        else:
            data = [result]

        if not data:
            return "No encontré resultados."

        response = "\n".join(
            [f"{r.get('marca', '?')} - {r.get('modelo', '?')} ({r.get('tipo', '?')}, {r.get('potencia', '?')} hp)" for r in data]
        )
        return response
    except Exception as e:
        return f" Error al consultar el grafo: {e}"

# Chat interactivo 
print("Motos GPT — escribe 'salir' para terminar")
while True:
    pregunta = input("Tú: ")
    if pregunta.lower() in ["salir", "exit", "quit"]:
        break
    respuesta = consultar_grafo(pregunta)
    print("Bot:", respuesta)
