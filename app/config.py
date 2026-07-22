import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-3.5-flash")
EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-001")

DOCUMENTS_DIR = os.getenv("DOCUMENTS_DIR", "documents")

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1000))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 150))
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", 5))

if not GEMINI_API_KEY:
    print(
        "⚠️  GEMINI_API_KEY no está configurada. "
        "Crea un archivo .env (usa .env.example como base) con tu API key de Gemini."
    )
