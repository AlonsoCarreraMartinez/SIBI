from llama_index.llms.groq import Groq
from llama_index.graph_stores.neo4j import Neo4jGraphStore
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core import Settings, Document
import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
load_dotenv()


# Conexión a Neo4j.
graph_store = Neo4jGraphStore(
    username="neo4j",
    password="neo4j123",
    url="bolt://127.0.0.1:7687",
    database="neo4j"
)

# Inicializamos el LLM
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

llm = Groq(
    model="llama-3.1-8b-instant",   
    api_key=GROQ_API_KEY,          # OJO: clave cargada desde .env
    temperature=0.2,               # Control de creatividad (0.2 = más preciso)
    request_timeout=300.0          # Tiempo máximo de respuesta
)
Settings.llm = llm

# Embeddings.
EMBEDDING_DIR = os.path.join(os.path.dirname(__file__), "storage_motos")
os.makedirs(EMBEDDING_DIR, exist_ok=True)  # Creamos la carpeta en caso de que no exista
EMBED_MODEL = OllamaEmbedding(model_name="llama3")


# En caso de no existir 'docstore.json' en storage_motos/ creamos un índice en el disco a partir del CSV.
def crear_indice_si_no_existe():
    
    docstore_path = os.path.join(EMBEDDING_DIR, "docstore.json")

    if not os.path.exists(docstore_path):
        print("Creando índice vectorial local...")

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

        print(f"Índice vectorial creado correctamente en: {EMBEDDING_DIR}")
    else:
        print("El índice ya existe. No se vuelve a crear.")


# Buscamos en el índice de Neo4j motos semánticamente.
def buscar_motos_semanticamente(pregunta: str):

    try:
        pregunta = (pregunta or "").strip()
        
        import re
        match_num = re.search(r"(\d+)\s*(?:moto|motos)", pregunta.lower())
        limit = int(match_num.group(1)) if match_num else 5 # Si no se específica, el número de motos por defecto será 5 si las hay.

        embedding = EMBED_MODEL.get_text_embedding(pregunta) # A partir de la consulta generamos el embedding.

        # Consulta Cypher.
        cypher = f"""
        CALL db.index.vector.queryNodes('moto_embeddings', {limit}, $embedding)
        YIELD node, score
        RETURN 
            node.Brand                AS marca,
            node.Model                AS modelo,
            node.Category             AS tipo,
            node['Displacement (ccm)'] AS cilindrada,
            node['Power (hp)']        AS potencia,
            node['Dry weight (kg)']   AS peso,
            node.Year                 AS año,
            node['Color options']     AS colores,
            score
        ORDER BY score DESC
        LIMIT {limit}
        """

        resultados = graph_store.query(cypher, params={"embedding": embedding})

        motos = []
        for r in resultados:
            motos.append(
                f"{r.get('marca', 'Desconocida')} {r.get('modelo', '')} ({r.get('tipo', '')}) - "
                f"{r.get('cilindrada', 'N/A')} cc, {r.get('potencia', 'N/A')} hp, {r.get('peso', 'N/A')} kg, año {r.get('año', 'N/A')}, color: {r.get('colores', 'N/A')}"
            )

        return motos

    except Exception as e:
        return []


# Respuesta.
def generar_respuesta(pregunta, motos):

    if not motos or "Error" in motos[0]:
        motos = buscar_motos_semanticamente(pregunta)
    
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
- Categoría (Category)
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
1. Responde SIEMPRE en español, con redacción natural y fluida.
2. Usa únicamente los datos del dataset. No inventes, completes ni estimes ningún valor.
3. Si un dato falta en la base, simplemente omítelo del formato. Solo menciona su ausencia si afecta directamente a la recomendación (por ejemplo: “no hay información suficiente sobre este modelo para evaluar su potencia”).
4. Mantén un tono profesional, técnico y conciso, sin explicaciones innecesarias sobre el proceso de búsqueda.
5. Si no hay coincidencias exactas, aclara que son las más cercanas sin justificar el método de búsqueda.
6. Si el usuario pide un número específico de resultados, devuelve exactamente esa cantidad o menos si no existen más.
7. No repitas modelos idénticos ni versiones de distinto color del mismo modelo.
8. Si la pregunta no tiene relación con motocicletas, responde directamente que solo puedes ofrecer información sobre motos y evita frases como “no tengo acceso a la base de datos”.
9. Si la consulta combina parámetros imposibles o contradictorios (por ejemplo, “10 CV y 300 km/h”), explica brevemente por qué no existen modelos así y sugiere los más cercanos sin usar un tono de disculpa.
10. Evita cualquier referencia a procesos internos, “errores semánticos” o “base de datos”. Empieza siempre con una breve introducción contextual y luego las recomendaciones.

FORMATO DE RESPUESTA:
Recomendaciones:
1. Marca Modelo (Año) — Tipo: {{Category}}
   - Cilindrada: {{Displacement (ccm)}} cc
   - Potencia: {{Power (hp)}} CV
   - Par motor: {{Torque (Nm)}} Nm
   - Peso: {{Dry weight (kg)}} kg
   - Altura del asiento: {{Seat height (mm)}} mm
   - Depósito: {{Fuel capacity (lts)}} L
   - Sistema de refrigeración: {{Cooling system}}
   - Transmisión: {{Transmission type}}
   - Caja de cambios: {{Gearbox}}
   - Colores disponibles: {{Color options}}
   - Motivo de recomendación: explicación breve, técnica y coherente con la solicitud del usuario.

Conclusión:
Resume cuál o cuáles se ajustan mejor a los criterios solicitados y explica brevemente por qué.

El usuario preguntó: "{pregunta}"

Motos encontradas:
{chr(10).join(f"{i+1}. {m}" for i, m in enumerate(motos))}
"""

    try:
        respuesta = llm.complete(prompt)
        return respuesta.text.strip()
    except Exception as e:
        return f"[]"


# streamlit run chatbot.py
pregunta = st.text_input("Pregunta")
if st.button("Hacer pregunta"):
    with st.spinner("Buscando recomendaciones..."):
        motos = buscar_motos_semanticamente(pregunta)
        respuesta = generar_respuesta(pregunta, motos)
        st.write(respuesta)
