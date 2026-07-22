from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import routes
from app.services.rag_service import build_vectorstore


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Etapas 2 y 3 del pipeline RAG (extracción/chunking + indexación):
    # se ejecutan una sola vez al arrancar el servidor, leyendo los PDFs
    # de documents/ y construyendo el índice vectorial en ChromaDB.
    print("🔧 Construyendo índice vectorial desde documents/ ...")
    vectorstore = build_vectorstore()
    app.state.vectorstore = vectorstore

    if vectorstore is None:
        print(
            "⚠️  No se encontraron PDFs en documents/. "
            "El agente no podrá responder hasta que agregues documentos y reinicies el servidor."
        )
    else:
        print("✅ Índice vectorial listo.")

    yield


app = FastAPI(title="Alura Agente", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(routes.router)
