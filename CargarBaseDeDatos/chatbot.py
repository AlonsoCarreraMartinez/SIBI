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
    url=os.getenv("NEO4J_URI"),
    username=os.getenv("NEO4J_USER"),
    password=os.getenv("NEO4J_PASSWORD"),
    database=os.getenv("NEO4J_DATABASE")
)

# Inicializamos el LLM.
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

llm = Groq(
    model="llama-3.1-8b-instant",   
    api_key=GROQ_API_KEY,          
    temperature=0.2,               
    request_timeout=300.0         
)
Settings.llm = llm

# Embeddings.
EMBEDDING_DIR = os.path.join(os.path.dirname(__file__), "storage_motos")
os.makedirs(EMBEDDING_DIR, exist_ok=True)  # Creamos la carpeta en caso de que no exista.
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
        print("El índice ya existe.")


# Buscamos en el índice de Neo4j motos semánticamente.
def buscar_motos_semanticamente(pregunta: str):

    try:
        pregunta = (pregunta or "").strip()
        
        import re
        match_num = re.search(r"(\d+)\s*(?:moto|motos)", pregunta.lower())
        limit = int(match_num.group(1)) if match_num else 5

        embedding = EMBED_MODEL.get_text_embedding(pregunta)

        cypher = f"""
        CALL db.index.vector.queryNodes('moto_embeddings', {limit}, $embedding)
        YIELD node, score
        RETURN 
            node.Brand                 AS marca,
            node.Model                 AS modelo,
            node.Category              AS tipo,
            node['Displacement (ccm)'] AS cilindrada,
            node['Power (hp)']         AS potencia,
            node['Dry weight (kg)']    AS peso,
            node.Year                  AS año,
            node['Seat height (mm)']   AS asiento,
            node['Fuel capacity (lts)'] AS deposito,
            node['Cooling system']     AS refrigeracion,
            node['Transmission type']  AS transmision,
            node['Gearbox']            AS caja,
            node['Engine stroke']      AS ciclo,
            node['Engine cylinder']    AS cilindros,
            node['Torque (Nm)']        AS torque,
            score
        ORDER BY score DESC
        LIMIT {limit}
        """

        resultados = graph_store.query(cypher, params={"embedding": embedding})

        motos = []
        for r in resultados:
            motos.append({
                "marca": r.get("marca"),
                "modelo": r.get("modelo"),
                "tipo": r.get("tipo"),
                "cilindrada": r.get("cilindrada"),
                "potencia": r.get("potencia"),
                "peso": r.get("peso"),
                "año": r.get("año"),
                "asiento": r.get("asiento"),
                "deposito": r.get("deposito"),
                "refrigeracion": r.get("refrigeracion"),
                "transmision": r.get("transmision"),
                "caja": r.get("caja"),
                "ciclo": r.get("ciclo"),
                "cilindros": r.get("cilindros"),
                "torque": r.get("torque"),
            })

        return motos

    except Exception:
        return []

# Respuesta.
def generar_respuesta(pregunta, motos):

    if not motos or "Error" in motos[0]:
        motos = buscar_motos_semanticamente(pregunta)
    
    print("\nResultados encontrados:")
    for i, moto in enumerate(motos, 1):
        print(f"  {i}. {moto}")
    print()

    lista_para_llm = []
    for m in motos:
        texto = f"{m['marca']} {m['modelo']} ({m['tipo']}) - {m['cilindrada']} cc, {m['potencia']} hp, {m['peso']} kg, año {m['año']}"
        lista_para_llm.append(texto)

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
11. No realices comparaciones directas con motos que no aparezcan en la lista.
12. No utilices términos como “probablemente”, “podría”, “seguramente” o cualquier forma especulativa.
13. NUNCA puedes usar la palabra base de datos.

FORMATO DE RESPUESTA:

Explicale brevemente (2–3 líneas) al usuario qué tipo de moto está buscando, 
qué necesidades o criterios se desprenden de la pregunta y qué enfoque seguirás 
para seleccionar las recomendaciones. Trata al usuario como si estuvieras hablando con el en persona 
y tienes PROHIBIDA utilizar la palabra base de datos.

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
   - Motivo de recomendación: explicación breve, técnica y coherente con la solicitud del usuario indicando en que se diferencia del resto de recomendaciones si las hay, además de que si las hay no repitas lo mismo en todas.

Conclusión:
Resume cuál o cuáles se ajustan mejor a los criterios solicitados, explica brevemente por qué y haz una pequeña conclusión.

El usuario preguntó: "{pregunta}"

Motos encontradas:
{chr(10).join(f"{i+1}. {t}" for i, t in enumerate(lista_para_llm))}
"""

    try:
        respuesta = llm.complete(prompt)
        return respuesta.text.strip()
    except Exception:
        return "[]"


# streamlit run chatbot.py
st.set_page_config(page_title="MOTORBOT", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

# Aplicar el tema oscuro.
def aplicar_tema():
    tema_oscuro = st.session_state.dark_mode

    if tema_oscuro:
        fondo = "#0e1117"
        texto = "#ffffff"
        burbuja_user = "#1e222a"
        burbuja_bot = "#161a23"
        input_bg = "#1e222a"
        arrow_color = "#000000"
        extra_css_asistente = """
        [data-testid="stChatMessageContent"] * {
            color: #ffffff !important;
        }
        """
    else:
        fondo = "#ffffff"
        texto = "#000000"
        burbuja_user = "#f0f2f6"
        burbuja_bot = "#e8ebf0"
        input_bg = "#f7f7f9"
        arrow_color = "#000000"
        extra_css_asistente = ""

    st.markdown(
        f"""
        <style>

        {extra_css_asistente}

        [data-testid="column"]:first-child > div:first-child {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            z-index: 9999;
            background: {fondo} !important;
            padding-bottom: 10px;
        }}

        .main > div {{
            padding-top: 140px !important;
        }}

        html, body, .stApp, .appview-container, .main, main, main > div {{
            background: {fondo} !important;
            color: {texto} !important;
        }}

        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stHeader"],
        [data-testid="stStatusWidget"] {{
            background: {fondo} !important;
        }}

        .stChatMessage.user {{
            background: {burbuja_user} !important;
            color: {texto} !important;
        }}

        .stChatMessage.assistant {{
            background: {burbuja_bot} !important;
        }}

        [data-testid="stBottomBlockContainer"],
        [data-testid="stBottomBlockContainer"] > div {{
            background: {fondo} !important;
        }}

        [data-testid="stChatInput"] {{
            background: {fondo} !important;
        }}

        [data-testid="stChatInput"] > div:first-child {{
            background: {input_bg} !important;
            border-radius: 12px !important;
            padding: 6px !important;
        }}

        [data-testid="stChatInput"] input {{
            background: {input_bg} !important;
            color: {texto} !important;
        }}

        [data-testid="stChatInput"] button svg {{
            fill: {arrow_color} !important;
            stroke: {arrow_color} !important;
        }}

        button[kind="secondary"] {{
            color: #000000 !important;
        }}

        </style>
        """,
        unsafe_allow_html=True
    )

aplicar_tema()

top_left, top_right = st.columns([0.7, 0.3])

with top_left:
    st.markdown(
        """
        <div style="
            width: 100%;
            display: flex;
            justify-content: center;
            align-items: center;
            margin-top: 10px;
        ">
            <span style="
                font-size: 46px;
                font-weight: 900;
                font-family: 'Segoe UI', sans-serif;
            ">
                隼 MOTORBOT
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

with top_right:
    st.toggle("🌙 Modo oscuro", key="dark_mode")

    if st.button("🔄 Reiniciar"):
        st.session_state.messages = []
        st.rerun()


if len(st.session_state.messages) == 0:
    st.session_state.messages.append({
        "role": "assistant",
        "content": (
            "Hola soy MOTORBOT, tu sistema recomendador de motos.\n"
            "¿En que puedo ayudarte?"
        )
    })


for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

pregunta = st.chat_input("Escribe tu pregunta...")

if pregunta:
    st.session_state.messages.append({"role": "user", "content": pregunta})

    with st.chat_message("user"):
        st.write(pregunta)

    with st.chat_message("assistant"):
        with st.spinner("Analizando motos..."):
            motos = buscar_motos_semanticamente(pregunta)
            respuesta = generar_respuesta(pregunta, motos)
            st.write(respuesta)

    st.session_state.messages.append({"role": "assistant", "content": respuesta})
