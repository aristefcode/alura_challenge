from langchain_chroma import Chroma
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.config import RETRIEVAL_K
from app.services.gemini_service import get_chat_model, get_embeddings_model
from app.services.pdf_service import load_and_split_documents

SYSTEM_PROMPT = """Eres el Alura Agente, un asistente de inteligencia artificial corporativo.
Tu única función es responder preguntas de los colaboradores basándote EXCLUSIVAMENTE en el
contexto de documentos internos que se te entrega a continuación.

Reglas obligatorias:
1. Responde solo con información presente en el contexto. No uses conocimiento externo ni inventes datos.
2. Si el contexto no contiene la respuesta, dilo claramente: "No encontré esta información en los \
documentos disponibles." No intentes adivinar ni completar con suposiciones.
3. Puedes usar el historial de la conversación para entender preguntas de seguimiento (por ejemplo,
"¿y cuántos días son?" después de haber hablado de una política). Aun así, el contenido de tu
respuesta debe basarse siempre en el contexto documental recuperado, nunca en suposiciones.
4. Sé claro, directo y profesional. Responde siempre en español.
5. No repitas los nombres de archivo ni las páginas dentro del texto de tu respuesta: eso ya se \
muestra aparte en la interfaz como fuentes.

Contexto recuperado de los documentos internos:
----------------
{context}
----------------
"""

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder("history"),
        ("human", "{question}"),
    ]
)


def build_vectorstore():
    """
    Construye el índice vectorial (ChromaDB) a partir de los PDFs disponibles
    en documents/. Se ejecuta una única vez, al arrancar el servidor.

    Nota: no usamos persist_directory a propósito. Render (plan free) tiene
    disco efímero, así que el índice se reconstruye en cada arranque en vez
    de intentar persistirlo entre reinicios.
    """
    chunks = load_and_split_documents()
    if not chunks:
        return None

    embeddings = get_embeddings_model()

    return Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name="alura_agente",
    )


def _get_relevant_chunks(vectorstore, question: str):
    retriever = vectorstore.as_retriever(search_kwargs={"k": RETRIEVAL_K})
    return retriever.invoke(question)


def _format_context(chunks) -> str:
    parts = []
    for chunk in chunks:
        source = chunk.metadata.get("source", "documento desconocido")
        page = chunk.metadata.get("page", "?")
        parts.append(f"[Fuente: {source} - página {page}]\n{chunk.page_content}")
    return "\n\n".join(parts)


def _build_retrieval_query(question: str, history) -> str:
    """
    Para preguntas de seguimiento cortas ("¿y cuántos días son?"), sumar la
    última pregunta del historial ayuda a que la búsqueda semántica encuentre
    los fragmentos correctos, aunque la pregunta actual por sí sola sea ambigua.
    Es una heurística simple, no una reescritura de consulta con LLM.
    """
    if not history:
        return question
    last_question, _ = history[-1]
    return f"{last_question} {question}"


def _history_to_messages(history):
    messages = []
    for question, answer in history:
        messages.append(HumanMessage(content=question))
        messages.append(AIMessage(content=answer))
    return messages


def _build_sources_list(chunks):
    seen = set()
    sources = []
    for chunk in chunks:
        source = chunk.metadata.get("source", "documento desconocido")
        page = chunk.metadata.get("page", "?")
        key = (source, page)
        if key not in seen:
            seen.add(key)
            sources.append({"file": source, "page": page})
    return sources

def _extract_text(content) -> str:
    """
    Normaliza el contenido de un chunk de respuesta del LLM a texto plano.

    Con modelos más nuevos, chunk.content puede venir como una lista de
    bloques (p. ej. [{"type": "text", "text": "..."}]) en vez de un string
    plano. Esta función siempre devuelve un string.
    """
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") in (None, "text"):
                text = block.get("text")
                if text:
                    parts.append(text)
        return "".join(parts)

    return ""

async def stream_answer(vectorstore, question: str, history=None):
    """
    Ejecuta las etapas 4 y 5 del pipeline RAG:
    - Búsqueda semántica de los fragmentos más relevantes (considerando el
      historial reciente para preguntas de seguimiento).
    - Generación de la respuesta en streaming (token a token), usando el
      contexto recuperado y el historial de la conversación.

    `history` es una lista de tuplas (pregunta, respuesta) de la sesión actual.

    Devuelve una tupla (generador_de_texto, lista_de_fuentes).
    """
    history = history or []

    retrieval_query = _build_retrieval_query(question, history)
    chunks = _get_relevant_chunks(vectorstore, retrieval_query)

    if not chunks:
        async def empty_stream():
            yield "No encontré esta información en los documentos disponibles."

        return empty_stream(), []

    context = _format_context(chunks)
    sources = _build_sources_list(chunks)

    llm = get_chat_model()
    chain = PROMPT | llm

    async def token_stream():
        async for event in chain.astream(
            {
                "context": context,
                "question": question,
                "history": _history_to_messages(history),
            }
        ):
            text = _extract_text(event.content)
            if text:
                yield text

    return token_stream(), sources
