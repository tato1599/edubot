"""
Rutas de la API FastAPI.
Endpoints: health, status, chat, chat/stream, stats
"""

import json
import re
import time
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from backend.app.core.config import settings
from backend.app.models.schemas import (
    ChatRequest, ChatResponse, ChatStats, SourceInfo,
    HealthStatus, StatusResponse, RAGStats
)
from backend.app.utils.query_expansion import expand_query

router = APIRouter()

# Referencias inyectadas desde main.py
rag_service = None
llm_service = None
startup_status = {}


# ───────────────────────────────────────────────
# System Prompt
# ───────────────────────────────────────────────

SYSTEM_PROMPT = (
    "Eres EduBot, el asistente virtual OFICIAL del Instituto Tecnologico de Ciudad Juarez (TecNM ITCJ). "
    "Tu unica mision es ayudar a estudiantes del TecNM ITCJ usando UNICAMENTE la informacion del CONTEXTO DOCUMENTAL proporcionado abajo.\n\n"

    "=== IDIOMA ABSOLUTO ===\n"
    "- Responde EXCLUSIVAMENTE en ESPANOL de Mexico.\n"
    "- NUNCA escribas en ingles, frances, chino, japones, aleman, italiano, portugues o cualquier otro idioma.\n"
    "- NUNCA uses palabras en ingles como: Hello, Hi, Sure, Welcome, Of course, I am, I'm, Yes, No, Sorry, Thanks, Please, etc.\n"
    "- NUNCA uses frases en ingles como: 'How can I help you?', 'I'm here to help', 'I don't have that information', etc.\n"
    "- SI el usuario escribe en otro idioma, responde en ESPANOL de todas formas.\n"
    "- Todas tus respuestas deben estar escritas UNICAMENTE con caracteres del alfabeto espanol, numeros y signos de puntuacion.\n"
    "- NO uses markdown, codigo, tablas, listas con guiones largos ni formato extrano. Usa solo texto plano simple.\n\n"

    "=== FUENTE UNICA DE VERDAD ===\n"
    "- Tu UNICA fuente de informacion es el CONTEXTO DOCUMENTAL que aparece en cada mensaje.\n"
    "- NO tienes internet. NO tienes conocimiento general. NO sabes nada fuera del contexto.\n"
    "- Si la pregunta NO esta en el contexto, responde EXACTAMENTE: 'Lo siento, no tengo esa informacion. Solo puedo ayudarte con tramites escolares, reticula ISC, nutricion SMAE, locales de comida y reglamento del TecNM ITCJ.'\n"
    "- NUNCA inventes datos, numeros, nombres, fechas, precios, lugares, personas o hechos.\n"
    "- NUNCA digas 'segun mis archivos', 'los documentos indican', 'en mis fuentes'. Ve directo al punto.\n\n"

    "=== TEMAS VALIDOS (solo estos) ===\n"
    "1. Tramites escolares (constancias, kardex, credencial, reinscripcion, baja, etc.)\n"
    "2. Reticula de Ingenieria en Sistemas Computacionales (ISC)\n"
    "3. Reglamento de estudiantes del TecNM ITCJ\n"
    "4. Locales de comida en/near campus (Doña Pelos, Cafe Tec, Manos Sucias, etc.)\n"
    "5. Nutricion SMAE (dieta estudiantil, listas de compra, snacks, porciones)\n"
    "- Si preguntan sobre director del ITCJ, personajes, memes, cultura pop, deportes, noticias, musica, politica, juegos, anime, Star Wars, ciencia general, matematicas, historia mundial, etc., responde: 'Lo siento, no tengo esa informacion. Solo puedo ayudarte con tramites escolares, reticula ISC, nutricion SMAE, locales de comida y reglamento del TecNM ITCJ.'\n\n"

    "=== ESTILO DE RESPUESTA ===\n"
    "- Se claro, conciso, directo y amigable.\n"
    "- No escribas ensayos largos. Usa viñetas cuando sea util.\n"
    "- Si mencionas un tramite, incluye los requisitos y pasos del contexto.\n"
    "- Si mencionas una materia, incluye clave, semestre, creditos y prerequisitos del contexto.\n"
    "- Si mencionas un local de comida, incluye ubicacion, menu y precios del contexto.\n"
    "- NUNCA mezcles informacion de diferentes fuentes en una sola respuesta.\n"
    "- NUNCA uses markdown complejo (tablas, bloques de codigo) a menos que sea necesario.\n\n"

    "=== EASTER EGG ===\n"
    "- Si el usuario menciona EXPLICITAMENTE 'lado oscuro', 'sith', 'force', 'sable', 'darth', 'vader', 'padawan', 'jedi', 'imperio' o 'rebelion', puedes responder con humor breve mezclando Star Wars con el TecNM ITCJ, PERO solo despues de haber respondido su pregunta real (si la hay).\n\n"

    "=== MEMORIA ===\n"
    "- Usa el historial de la conversacion SOLO para seguimiento y contexto de la charla actual.\n"
    "- NUNCA inventes informacion del historial.\n"
)


def _build_messages(query: str, context: str, history: list = None) -> list:
    """Construye mensajes para el LLM."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    if history and len(history) > 0:
        recent = history[-6:] if len(history) > 6 else history
        for msg in recent:
            if msg.get("role") in ["user", "assistant"] and msg.get("content"):
                messages.append({"role": msg["role"], "content": msg["content"]})
    
    user_content = (
        "INFORMACION QUE TIENES:\n"
        "===================\n"
        f"{context}\n"
        "===================\n\n"
        f"PREGUNTA DEL USUARIO: {query}\n\n"
        "Responde como EduBot. Si es una pregunta de seguimiento, usa el contexto de la conversacion. "
        "Se natural, directo y conciso.\n\n"
        "REGLA INQUEBRANTABLE: Tu respuesta DEBE estar 100% en ESPANOL. "
        "NO escribas ni una sola palabra en ingles. "
        "Si no sabes que responder, di: 'Lo siento, no tengo esa informacion. Solo puedo ayudarte con tramites escolares, reticula ISC, nutricion SMAE, locales de comida y reglamento del TecNM ITCJ.'"
    )
    messages.append({"role": "user", "content": user_content})
    return messages


# ───────────────────────────────────────────────
# Sanitizacion de respuestas (bloqueo de ingles)
# ───────────────────────────────────────────────

# Palabras/frases comunes en ingles que el modelo 3B suele generar
_ENGLISH_PATTERNS = [
    r"^hello[\s!,]",
    r"^hi[\s!,]",
    r"^hey[\s!,]",
    r"^sure[\s!,]",
    r"^of course[\s!,]",
    r"^certainly[\s!,]",
    r"^welcome[\s!,]",
    r"^i'm\b",
    r"^i am\b",
    r"^i'd\b",
    r"^i would\b",
    r"^i don't\b",
    r"^i do not\b",
    r"^i can't\b",
    r"^i cannot\b",
    r"^how can i\b",
    r"^what can i\b",
    r"^may i\b",
    r"^can i\b",
    r"^sorry[\s!,]",
    r"^thanks[\s!,]",
    r"^thank you[\s!,]",
    r"^please[\s!,]",
    r"\bhow can i help\b",
    r"\bi'm here\b",
    r"\bi would be happy\b",
    r"\bi don't have\b",
    r"\bi do not have\b",
]

# Palabras de otros idiomas que el modelo 3B suele mezclar
_FOREIGN_WORDS = {
    # Ingles
    "the", "and", "you", "your", "help", "today", "information", "can", "how",
    "what", "is", "are", "for", "with", "have", "that", "this", "please", "sorry",
    "don't", "can't", "hello", "hi", "hey", "sure", "welcome", "about", "from",
    "would", "could", "should", "will", "shall", "may", "might", "here", "there",
    "where", "when", "who", "why", "which", "was", "were", "been", "has", "had",
    "did", "does", "doing", "done", "get", "got", "getting", "know", "think",
    "see", "look", "want", "need", "like", "feel", "find", "found", "give", "gave",
    "take", "took", "make", "made", "come", "came", "go", "went", "say", "said",
    "tell", "told", "ask", "asked", "work", "working", "worked", "try", "trying",
    "tried", "use", "using", "used", "call", "called", "yes", "no", "not", "or",
    "but", "if", "then", "than", "so", "very", "just", "now", "only", "also",
    "back", "after", "first", "well", "way", "even", "new", "because",
    "any", "these", "day", "most", "us", "goodbye", "bye",
    # Portugues / Frances / Italiano comunes que no son espanol
    "ou", "do", "da", "dos", "das", "nosso", "nossa", "voce", "você",
    "je", "tu", "il", "elle", "nous", "vous", "ils", "elles", "et", "ou",
    "le", "la", "les", "un", "une", "des", "du", "de", "au", "aux",
    "sono", "sei", "è", "siamo", "siete", "sono", "il", "lo", "la", "gli", "le",
}

_FALLBACK_MSG = (
    "Lo siento, no tengo esa informacion. "
    "Solo puedo ayudarte con tramites escolares, reticula ISC, nutricion SMAE, "
    "locales de comida y reglamento del TecNM ITCJ."
)


def _looks_like_foreign(text: str) -> bool:
    """Heuristica para detectar si el modelo respondio en otro idioma."""
    text_lower = text.lower().strip()
    if not text_lower:
        return True

    # 1. Detectar patrones iniciales muy comunes en ingles
    for pattern in _ENGLISH_PATTERNS:
        if re.search(pattern, text_lower):
            return True

    # 2. Contar palabras extranjeras de alta frecuencia
    words = re.findall(r"[a-zA-ZÀ-ÿ]+", text_lower)
    if not words:
        return False

    foreign_count = sum(1 for w in words if w in _FOREIGN_WORDS)
    # Si mas del 20% de las palabras son extranjeras muy comunes, probablemente no esta en espanol
    if len(words) >= 4 and foreign_count / len(words) > 0.20:
        return True

    return False


def _sanitize_response(query: str, response: str) -> str:
    """
    Fuerza la respuesta a estar en espanol puro.
    Si el modelo respondio en otro idioma, reemplaza con una respuesta predefinida.
    """
    if not response or not response.strip():
        return _FALLBACK_MSG

    query_lower = query.lower().strip()

    # Para saludos y frases sociales simples, SIEMPRE usar respuesta predefinida
    # para evitar que el modelo invente en otros idiomas
    if any(w in query_lower for w in ["hola", "buenos", "buenas", "saludos", "hey", "que tal", "que onda"]):
        return "Hola! Soy EduBot, el asistente virtual del TecNM ITCJ. En que puedo ayudarte hoy?"

    if any(w in query_lower for w in ["adios", "bye", "hasta luego", "nos vemos", "chao"]):
        return "Hasta luego! Que tengas un buen dia."

    if any(w in query_lower for w in ["gracias", "thank", "thanks"]):
        return "De nada! Estoy aqui para ayudarte."

    if any(w in query_lower for w in ["como estas", "que haces", "quien eres", "presentate", "presentate"]):
        return "Soy EduBot, el asistente virtual del TecNM ITCJ. Estoy para ayudarte con tramites escolares, reticula ISC, nutricion SMAE, locales de comida y reglamento."

    # Para preguntas de capacidades
    if any(w in query_lower for w in ["que sabes", "que puedes", "que haces", "ayuda", "capacidades"]):
        return (
            "Puedo ayudarte con estos temas del TecNM ITCJ:\n"
            "1. Tramites escolares (constancias, kardex, credencial, inscripcion, baja, servicio social, residencia, titulacion).\n"
            "2. Reticula de Ingenieria en Sistemas Computacionales (materias, semestres, creditos, prerequisitos).\n"
            "3. Reglamento de estudiantes (derechos, obligaciones, sanciones, conductas).\n"
            "4. Locales de comida cerca del campus (Doña Pelos, Cafe Tec, Manos Sucias).\n"
            "5. Nutricion SMAE (dieta estudiantil, listas de compra economicas, snacks saludables).\n\n"
            "Solo tengo informacion de estos temas. De que te gustaria saber?"
        )

    # Si la respuesta parece estar en otro idioma, usar fallback
    if _looks_like_foreign(response):
        return _FALLBACK_MSG

    return response.strip()


def _format_sources(sources: list) -> list:
    """Formatea fuentes para la respuesta."""
    return [
        SourceInfo(
            titulo=s["titulo"],
            categoria=s["categoria"],
            score=round(s.get("score", 0), 3),
            fuente=s.get("fuente")
        ) for s in sources
    ]


# ───────────────────────────────────────────────
# Endpoints
# ───────────────────────────────────────────────

@router.get("/health", response_model=HealthStatus)
async def health_check():
    """Estado de salud del sistema con progreso de carga."""
    is_ready = llm_service is not None and llm_service.is_loaded
    return HealthStatus(
        status="ready" if is_ready else "loading",
        stage=startup_status.get("stage", "unknown"),
        stage_name=startup_status.get("stage_name", "Unknown"),
        progress=startup_status.get("progress", 0.0),
        model_loaded=is_ready,
        rag_documents=startup_status.get("rag_documents", 0),
        version=settings.app_version,
    )


@router.get("/status", response_model=StatusResponse)
async def status():
    """Estado completo del sistema."""
    rag_stats = RAGStats(**rag_service.get_stats()) if rag_service else RAGStats(
        total_documents=0, embedding_model="unknown", vector_database="unknown", sources=[]
    )
    
    device = "cuda" if llm_service and llm_service.is_loaded and hasattr(llm_service.model, 'device') else "cpu"
    if llm_service and llm_service.is_loaded and hasattr(llm_service.model, 'hf_device_map'):
        device = str(llm_service.model.hf_device_map)
    
    return StatusResponse(
        status="online",
        model=settings.model_name,
        device=device,
        rag_stats=rag_stats,
        version=settings.app_version,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat sincrono. Retorna la respuesta completa.
    Para produccion, preferir /chat/stream.
    """
    if rag_service is None:
        raise HTTPException(status_code=503, detail="Motor RAG no inicializado")
    
    if llm_service is None or not llm_service.is_loaded:
        raise HTTPException(status_code=503, detail="Modelo de lenguaje no disponible")
    
    start_time = time.time()
    
    # 1. Expandir query y recuperar contexto
    expanded = expand_query(request.message)
    context = rag_service.build_context(expanded, top_k=settings.top_k_retrieval)
    sources = rag_service.search(expanded, top_k=settings.top_k_retrieval)
    
    # 2. Construir prompt
    history = [m.model_dump() for m in request.history] if request.history else []
    messages = _build_messages(request.message, context, history)
    
    # 3. Generar respuesta
    try:
        response_text = llm_service.generate(messages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando respuesta: {str(e)}")
    
    # 4. Sanitizar idioma (forzar espanol)
    response_text = _sanitize_response(request.message, response_text)
    
    # 5. Formatear respuesta
    formatted_sources = _format_sources(sources)
    stats = ChatStats(
        model_used=settings.model_name,
        device=str(llm_service.device),
        context_length=len(llm_service.tokenizer.apply_chat_template(messages, tokenize=False)),
        sources_found=len(sources),
        response_time_ms=round((time.time() - start_time) * 1000, 2),
        query_expanded=(expanded != request.message),
    )
    
    return ChatResponse(
        response=response_text,
        sources=formatted_sources,
        stats=stats
    )


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Chat con streaming SSE (Server-Sent Events).
    Devuelve la respuesta token por token.
    """
    if rag_service is None:
        raise HTTPException(status_code=503, detail="Motor RAG no inicializado")
    
    if llm_service is None or not llm_service.is_loaded:
        raise HTTPException(status_code=503, detail="Modelo de lenguaje no disponible")
    
    start_time = time.time()
    
    # 1. Expandir query y recuperar
    expanded = expand_query(request.message)
    context = rag_service.build_context(expanded, top_k=settings.top_k_retrieval)
    sources = rag_service.search(expanded, top_k=settings.top_k_retrieval)
    
    # 2. Construir prompt
    history = [m.model_dump() for m in request.history] if request.history else []
    messages = _build_messages(request.message, context, history)
    
    # 3. Formatear fuentes
    formatted_sources = _format_sources(sources)
    
    async def generate_sse() -> AsyncGenerator[str, None]:
        full_response = ""
        try:
            # Enviar fuentes primero
            yield f"data: {json.dumps({'type': 'sources', 'sources': [s.model_dump() for s in formatted_sources]})}\n\n"
            
            # Generar tokens
            for token in llm_service.generate_stream(messages):
                if token:
                    full_response += token
                    yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"
            
            # Sanitizar idioma al final del stream
            sanitized = _sanitize_response(request.message, full_response)
            if sanitized != full_response:
                # Enviar correccion para que el frontend reemplace el mensaje
                yield f"data: {json.dumps({'type': 'correction', 'text': sanitized})}\n\n"
            
            # Señal de fin
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/stats")
async def stats():
    """Estadisticas del motor RAG."""
    if rag_service is None:
        raise HTTPException(status_code=503, detail="RAG no inicializado")
    return rag_service.get_stats()
