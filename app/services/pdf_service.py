import os

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import CHUNK_OVERLAP, CHUNK_SIZE, DOCUMENTS_DIR


def load_and_split_documents():
    """
    Lee todos los PDFs de la carpeta documents/, extrae su texto y los
    divide en fragmentos (chunks) listos para indexar en la base vectorial.

    Cada fragmento conserva metadatos útiles para la citación de fuentes:
    - source: nombre del archivo PDF
    - page: número de página (1-indexed, legible para humanos)
    """
    if not os.path.isdir(DOCUMENTS_DIR):
        return []

    pdf_files = sorted(
        f for f in os.listdir(DOCUMENTS_DIR) if f.lower().endswith(".pdf")
    )

    if not pdf_files:
        return []

    all_pages = []
    for filename in pdf_files:
        filepath = os.path.join(DOCUMENTS_DIR, filename)
        loader = PyPDFLoader(filepath)
        pages = loader.load()

        for page in pages:
            # PyPDFLoader guarda la página como 0-indexed; la pasamos a 1-indexed
            # y normalizamos el nombre de la fuente (sin ruta, solo el archivo).
            page.metadata["source"] = filename
            page.metadata["page"] = page.metadata.get("page", 0) + 1

        all_pages.extend(pages)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    return splitter.split_documents(all_pages)
