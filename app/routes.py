import json
import urllib.parse
import uuid

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app.services.memory_service import append_to_history, clear_history, get_history
from app.services.rag_service import stream_answer

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

SESSION_COOKIE = "alura_session_id"


def _get_or_create_session_id(request: Request):
    session_id = request.cookies.get(SESSION_COOKIE)
    is_new = session_id is None
    if is_new:
        session_id = str(uuid.uuid4())
    return session_id, is_new


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@router.post("/chat")
async def chat(request: Request, question: str = Form(...)):
    vectorstore = request.app.state.vectorstore
    session_id, is_new_session = _get_or_create_session_id(request)

    if vectorstore is None:
        async def no_docs_stream():
            yield (
                "⚠️ Todavía no hay documentos indexados. Agrega archivos PDF "
                "en la carpeta documents/ y reinicia el servidor."
            )

        response = StreamingResponse(no_docs_stream(), media_type="text/plain")
        if is_new_session:
            response.set_cookie(SESSION_COOKIE, session_id, httponly=True, samesite="lax")
        return response

    history = get_history(session_id)
    token_stream, sources = await stream_answer(vectorstore, question, history)

    # Las fuentes se calculan antes de empezar el streaming (la recuperación
    # ya ocurrió), así que las mandamos en un header para que el frontend
    # las muestre sin tener que mezclarlas con el texto que se va escribiendo.
    encoded_sources = urllib.parse.quote(json.dumps(sources, ensure_ascii=False))

    async def tracked_stream():
        # Acumulamos la respuesta completa mientras se transmite, para
        # poder guardarla en el historial de la sesión una vez termine.
        full_answer_parts = []
        async for token in token_stream:
            full_answer_parts.append(token)
            yield token
        append_to_history(session_id, question, "".join(full_answer_parts))

    response = StreamingResponse(
        tracked_stream(),
        media_type="text/plain",
        headers={"X-Sources": encoded_sources},
    )
    if is_new_session:
        response.set_cookie(SESSION_COOKIE, session_id, httponly=True, samesite="lax")
    return response


@router.post("/reset")
async def reset(request: Request):
    """Borra el historial de conversación de la sesión actual ('Nueva conversación')."""
    session_id = request.cookies.get(SESSION_COOKIE)
    if session_id:
        clear_history(session_id)
    return JSONResponse({"status": "ok"})
