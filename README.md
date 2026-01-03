# 隼 MOTORBOT

Este proyecto presenta **MOTORBOT**, un asistente inteligente diseñado para eliminar la barrera de entrada técnica en el mercado de motocicletas.

Frente a la ineficacia de los buscadores tradicionales basados en filtros rígidos, se ha desarrollado una solución que integra Inteligencia Artificial mediante una arquitectura **RAG (Retrieval-Augmented Generation)** sobre una base de datos de grafos (**Neo4j**).

El sistema combina la extracción de datos en tiempo real vía scraping (**Selenium**) con un motor de inferencia híbrido que utiliza **Groq** y **Ollama** para garantizar respuestas rápidas y contextualizadas. El resultado es una herramienta capaz de traducir la intención subjetiva del usuario en recomendaciones técnicas precisas, facilitando la toma de decisiones de compra al usuario.

## Herramientas

- **Lenguaje Principal:** Python 3.10
- **Base de Datos:** Neo4j 
- **Orquestación RAG:** LlamaIndex
- **LLM (Inferencia):** Groq (llama-3.1-8b-instant)
- **Embeddings:** Ollama (Llama 3)
- **Interfaz de Usuario:** Streamlit
- **Adquisición de Datos:** Selenium (Scraping)
- **Contenedores:** Docker 

## Capas de Seguridad

**Capa 1: Aislamiento de Red (LocalHost)**

Mediante **Localhost Binding** se garantiza que los servicios críticos sean invisibles para dispositivos externos.

   - **Base de Datos:** Configuración estricta en `neo4j.conf` para aceptar únicamente conexiones locales.

   - **Interfaz Web:** Ejecución forzada sobre el bucle local mediante el flag `--server.address=127.0.0.1`, bloqueando el acceso desde la red pública o LAN.

**Capa 2: Autenticación de usuario**

- **Autenticación:** Interfaz protegida por credenciales de usuario antes de permitir cualquier consulta.

- **Gestión de Secretos:** Las claves API y contraseñas no existen en el código fuente, se inyectan dinámicamente mediante variables de entorno (`.env`) para evitar fugas de información.

**Capa 3: Protección frente a prompt injection en el LLM**

Implementación de un **System Prompt** robusto que protege el sistema contra ataques de *Prompt Injection*, asegurando que el modelo rechace instrucciones maliciosas o consultas fuera del dominio del motociclismo.

## Guía de Usuario

1. Primero instalaremos todas las dependencias necesarias, para ello debemos situarnos en el directorio raíz del proyecto y escribir el siguiente comando:

         pip install -r requirements.txt 

   Tras instalar todas las dependecias continuaremos creando el archivo `.env` con las siguientes credenciales:

            GROQ_API_KEY=tu_api_key
            NEO4J_URI=bolt://127.0.0.1:7687
            NEO4J_USER=neo4j
            NEO4J_PASSWORD=tu_contraseña
            NEO4J_DATABASE=neo4j
            APP_USERNAME=tu_nombre
            APP_PASSWORD=tu_contraseña

2. Creamos un nuevo proyecto y una base de datos local en Neo4j Desktop. Antes de iniciar la base de datos en la pestaña de plugins instalamos **APOC**, a continuación editamos el archivo neo4j.conf descomentando y asignando la dirección *127.0.0.1* a las líneas de *server.default_listen_address*, *server.bolt.listen_address* y *server.http.listen_address*. Tras esto ejecutamos el siguiente script:

            python cargarDatos.py

   Y tras la ejecución de este ya tendremos creadas en la base de datos los nodos y relaciones en la base de datos.

3. Con la base de datos encendida procederemos a lanzar la interfaz de usuario desde la terminal mediante el siguiente comando: 

         streamlit run MOTORBOT.py --server.address=127.0.0.1 
         
   ya con esto únicamente deberemos realizar el login correctamente y ya podremos comenzar a realizarle consultas a MOTORBOT.


## Autor

**Alonso Carrera Martínez** Grado en Ingeniería Informática - Sistemas de Información de Gestión y Business Intelligence  
Universidad de León (2025-2026).