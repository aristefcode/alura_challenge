from collections import defaultdict, deque

# Cuántos intercambios (pregunta + respuesta) se recuerdan por sesión.
# Se limita para no dejar crecer el prompt indefinidamente.
MAX_TURNS = 6

# session_id -> deque[(pregunta, respuesta)]
# Vive en memoria del proceso: se pierde si el servidor se reinicia,
# igual que el índice vectorial. Es suficiente para el alcance de este proyecto.
_histories = defaultdict(lambda: deque(maxlen=MAX_TURNS))


def get_history(session_id: str):
    """Devuelve el historial de una sesión como lista de tuplas (pregunta, respuesta)."""
    return list(_histories[session_id])


def append_to_history(session_id: str, question: str, answer: str):
    """Agrega un intercambio (pregunta/respuesta) al historial de la sesión."""
    _histories[session_id].append((question, answer))


def clear_history(session_id: str):
    """Borra el historial de una sesión (usado por el botón 'Nueva conversación')."""
    _histories.pop(session_id, None)
