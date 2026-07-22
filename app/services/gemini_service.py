from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from app.config import CHAT_MODEL, EMBEDDING_MODEL, GEMINI_API_KEY


def get_embeddings_model():
    """Modelo de embeddings de Gemini (text-embedding-004)."""
    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=GEMINI_API_KEY,
    )


def get_chat_model():
    """Modelo de chat de Gemini (gemini-2.0-flash) usado para generar respuestas."""
    return ChatGoogleGenerativeAI(
        model=CHAT_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0.2,
    )
