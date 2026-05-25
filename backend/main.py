"""
Backend FastAPI para el Agente Escolar Inteligente.
Integra RAG + modelo local Qwen2.5-7B-Instruct (4-bit) para responder sobre trámites y nutrición.
"""

import os
import sys
import torch
import asyncio
import threading
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from transformers import (
    AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer,
    BitsAndBytesConfig
)
from contextlib import asynccontextmanager

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from rag_engine import RAGEngine

# ──────────────────────────────────────────────────────────────
# Configuración
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"
TOP_K_RETRIEVAL = 5
TEMPERATURE = 0.2  # Baja: determinista, fiel al contexto
MAX_NEW_TOKENS = 350

print(f"[CONFIG] Dispositivo: {DEVICE}")
print(f"[CONFIG] Modelo: {MODEL_NAME}")
print(f"[CONFIG] Quantization: 4-bit (NF4)")
print(f"[CONFIG] top_k retrieval: {TOP_K_RETRIEVAL}")
print(f"[CONFIG] Temperature: {TEMPERATURE}")

# ──────────────────────────────────────────────────────────────
# Variables globales (se inicializan en lifespan)
# ──────────────────────────────────────────────────────────────
rag_engine = None
llm_model = None
tokenizer = None

# Estado de carga para /health (progreso real)
startup_status = {
    "stage": "initializing",   # initializing | rag | tokenizer | model | ready
    "stage_name": "Iniciando...",
    "progress": 0.0,           # 0.0 - 1.0
    "model_loaded": False,
    "rag_documents": 0,
}

# ──────────────────────────────────────────────────────────────
# Lifespan: carga pesada al iniciar el servidor
# ──────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global rag_engine, llm_model, tokenizer, startup_status
    
    print("\n" + "="*50)
    print("INICIANDO AGENTE ESCOLAR INTELIGENTE")
    print("="*50 + "\n")
    
    # 1. Cargar RAG Engine (~10% del tiempo total)
    startup_status["stage"] = "rag"
    startup_status["stage_name"] = "Indexando documentos..."
    startup_status["progress"] = 0.05
    print("[1/3] Cargando motor de RAG...")
    rag_engine = RAGEngine()
    stats = rag_engine.get_stats()
    startup_status["rag_documents"] = stats["total_documents"]
    startup_status["progress"] = 0.15
    print(f"      Documentos: {stats['total_documents']}")
    print(f"      Motor: {stats['embedding_model']}")
    
    # 2. Cargar modelo de lenguaje (~85% del tiempo total)
    startup_status["stage"] = "tokenizer"
    startup_status["stage_name"] = "Descargando tokenizador..."
    startup_status["progress"] = 0.20
    print("\n[2/3] Cargando modelo de lenguaje local...")
    print(f"      Esto puede tomar unos minutos la primera vez.")
    
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
        startup_status["stage"] = "model"
        startup_status["stage_name"] = "Cargando modelo de IA (descarga ~4GB, puede tardar)..."
        startup_status["progress"] = 0.35
        
        # Configuración 4-bit quantization para caber en 8GB VRAM
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        
        llm_model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
            low_cpu_mem_usage=True,
        )
        
        startup_status["model_loaded"] = True
        startup_status["progress"] = 1.0
        startup_status["stage"] = "ready"
        startup_status["stage_name"] = "Sistema listo"
        print(f"      Modelo {MODEL_NAME} cargado correctamente en GPU (4-bit).")
    except Exception as e:
        print(f"      ERROR al cargar modelo: {e}")
        llm_model = None
        startup_status["stage"] = "error"
        startup_status["stage_name"] = f"Error: {e}"
        startup_status["progress"] = 1.0
    
    print("\n[3/3] Servidor listo para recibir peticiones.")
    print("="*50 + "\n")
    
    yield
    
    # Cleanup
    print("\n[SHUTDOWN] Liberando recursos...")
    if llm_model is not None:
        del llm_model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

# ──────────────────────────────────────────────────────────────
# FastAPI App
# ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="Agente Escolar Inteligente",
    description="Asistente de trámites escolares, retícula ISC y nutrición basado en SMAE con RAG local.",
    version="1.1.0",
    lifespan=lifespan
)

# ──────────────────────────────────────────────────────────────
# Servir frontend estático
# ──────────────────────────────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
FRONTEND_DIR = os.path.abspath(FRONTEND_DIR)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/", include_in_schema=False)
async def serve_index():
    """Sirve el frontend cuando se accede a la raíz."""
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────
# Health Check (progreso real de carga)
# ──────────────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    """Devuelve el estado actual de carga con progreso real."""
    is_ready = llm_model is not None
    return {
        "status": "ready" if is_ready else "loading",
        "stage": startup_status["stage"],
        "stage_name": startup_status["stage_name"],
        "progress": startup_status["progress"],
        "model_loaded": is_ready,
        "rag_documents": startup_status["rag_documents"],
    }

# ──────────────────────────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    history: list = []

class ChatResponse(BaseModel):
    response: str
    sources: list
    stats: dict

class StatusResponse(BaseModel):
    status: str
    model: str
    device: str
    rag_stats: dict

# ──────────────────────────────────────────────────────────────
# Prompt Builder (formato chat Qwen2)
# ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = (
    "Eres EduBot, un asistente virtual del TecNM ITCJ. Tu ÚNICA FUENTE DE INFORMACIÓN es el CONTEXTO DOCUMENTAL que se te proporciona a continuación. "
    "NO tienes acceso a internet. NO conoces nada fuera de ese contexto. NO uses conocimiento previo.\n\n"
    "REGLAS ESTRICTAS:\n"
    "1. Usa ÚNICAMENTE la información del CONTEXTO DOCUMENTAL. Si algo NO está en el contexto, di EXACTAMENTE: 'Lo siento, no tengo esa información.' NUNCA inventes datos, números, nombres o hechos.\n"
    "2. NUNCA inventes números. Si el contexto dice 9 semestres, di 9. Si dice 260 créditos, di 260. Si no sabes un número, di 'Lo siento, no tengo esa información.'\n"
    "3. NUNCA mezcles información de diferentes fuentes. Si preguntan por Doña Pelos, SOLO habla de Doña Pelos. Si preguntan por SMAE, SOLO habla de SMAE. No menciones SMAE cuando hablan de comida rápida ni viceversa.\n"
    "4. Si te preguntan sobre director del ITCJ, personajes, memes, cultura pop, deportes, noticias, o CUALQUIER tema fuera de trámites/retícula/SMAE/comida/reglamento, di: 'Lo siento, no tengo esa información. Solo puedo ayudarte con trámites escolares, retícula ISC, nutrición SMAE, locales de comida y reglamento del TecNM.'\n"
    "5. NUNCA digas 'los documentos no contienen', 'en mis archivos', 'según mis fuentes', 'basado en mi conocimiento'. Ve directo a la respuesta.\n"
    "6. Responde SIEMPRE en español. Sé claro, conciso y amigable.\n"
    "7. EASTER EGG SITH: Si el usuario menciona palabras como 'lado oscuro', 'sith', 'force', 'sable', 'darth', 'vader', 'padawan', 'maestro', 'jedi', 'imperio', 'rebelion', responde con humor mezclando Star Wars con el TecNM ITCJ, pero brevemente.\n"
    "8. MEMORIA: Usa el historial de la conversación para seguimiento.\n\n"
    "EJEMPLOS DE RESPUESTAS CORRECTAS:\n"
    "P: ¿Cuántos semestres tiene ISC?\n"
    "R: 9 semestres.\n"
    "P: ¿Cuál es la capital de Francia?\n"
    "R: Lo siento, no tengo esa información.\n"
    "P: ¿Quién es el director?\n"
    "R: Lo siento, no tengo esa información.\n"
    "P: ¿Qué vende Doña Pelos?\n"
    "R: Sándwich de pechuga, ensalada de pollo, burritos, hamburguesas, boneless, salchipapas, nachos. [SOLO lo del contexto]\n"
    "P: Dame el menú completo de Doña Pelos\n"
    "R: [Lista EXACTA del menú del contexto, sin agregar ni quitar nada]\n"
    "P: ¿Qué hay en el menú de Café Tec?\n"
    "R: Lo siento, no tengo el menú completo de Café Tec.\n"
)

def expand_query(query: str) -> str:
    """
    Expande sinónimos comunes para mejorar la recuperación del RAG.
    Ejemplo: 'sistemas' -> 'sistemas computacionales ISC'
    """
    q_lower = query.lower()
    expansions = []
    
    # Mapeo de sinónimos/ambiguaciones
    synonyms = {
        'sistemas': 'sistemas computacionales ISC ingenieria',
        'la carrera': 'ingenieria sistemas computacionales ISC reticula',
        'primer semestre': 'semestre 1',
        'segundo semestre': 'semestre 2',
        'tercer semestre': 'semestre 3',
        'cuarto semestre': 'semestre 4',
        'quinto semestre': 'semestre 5',
        'sexto semestre': 'semestre 6',
        'séptimo semestre': 'semestre 7',
        'septimo semestre': 'semestre 7',
        'octavo semestre': 'semestre 8',
        'noveno semestre': 'semestre 9',
        'servicio social': 'servicio social liberacion constancia 480 horas',
        'ss': 'servicio social liberacion constancia',
        'residencia': 'residencia profesional',
        'titulacion': 'titulacion opciones tesis ceneval',
        'beca': 'becas excelencia economico descuento',
        'dieta': 'dieta estudiante economico saludable nutricion sma',
        'comer sano': 'dieta estudiante saludable economico nutricion sma',
        'comer saludable': 'dieta estudiante saludable economico nutricion sma',
        'presupuesto': 'economico barato estudiante dieta lista compras',
        'bajo presupuesto': 'economico barato estudiante dieta lista compras',
        'poco dinero': 'economico barato estudiante dieta lista compras',
        'alimentacion': 'nutricion sma dieta alimentos saludable',
        'nutricion': 'nutricion sma dieta alimentos estudiante saludable',
        'smae': 'sistema mexicano alimentos equivalentes nutricion porciones calorias',
        'doña pelos': 'doña pelos comida rapida menu hamburguesas burritos snacks local restaurante',
        'don pelos': 'doña pelos comida rapida menu hamburguesas burritos snacks local restaurante',
        'menu doña pelos': 'doña pelos comida rapida menu hamburguesas burritos snacks',
        'café tec': 'café tec cafetería comida campus restaurante local menu',
        'cafe tec': 'café tec cafetería comida campus restaurante local menu',
        'manos sucias': 'manos sucias comida rapida campus restaurante local menu',
        'coffee shop': 'coffee shop café campus restaurante local menu',
        'comida rapida': 'comedores locales campus doña pelos cafe tec manos sucias menu',
        'lugar para comer': 'comedores locales campus doña pelos cafe tec manos sucias restaurante',
        'reglamento': 'reglamento estudiantes tecnormas derechos obligaciones',
        'derechos': 'reglamento estudiantes derechos obligaciones normas',
        'obligaciones': 'reglamento estudiantes derechos obligaciones normas',
        'sancion': 'reglamento estudiantes conductas sanciones disciplina',
        'conducta': 'reglamento estudiantes conductas prohibidas sanciones',
        'baja': 'reglamento estudiantes baja temporal definitiva reinscripcion',
        'equidad': 'reglamento estudiantes equidad genero derechos humanos',
    }
    
    for key, expansion in synonyms.items():
        if key in q_lower:
            expansions.append(expansion)
    
    if expansions:
        return f"{query} {' '.join(expansions)}"
    return query

def build_messages(query: str, context: str, history: list = None) -> list:
    """Construye la lista de mensajes para apply_chat_template de Qwen2.
    Incluye historial de conversación si existe."""
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    
    # Agregar historial de conversación (máximo últimos 6 mensajes = 3 turnos)
    if history and len(history) > 0:
        # Tomar solo los últimos mensajes para no exceder tokens
        recent_history = history[-6:] if len(history) > 6 else history
        for msg in recent_history:
            if msg.get("role") in ["user", "assistant"] and msg.get("content"):
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
    
    # Agregar contexto RAG + pregunta actual
    user_content = (
        "INFORMACIÓN QUE TIENES:\n"
        "===================\n"
        f"{context}\n"
        "===================\n\n"
        f"PREGUNTA DEL USUARIO: {query}\n\n"
        "Responde como EduBot. Si es una pregunta de seguimiento o referencia a algo anterior, usa el contexto de la conversación. "
        "Sé natural, directo y conciso."
    )
    
    messages.append({"role": "user", "content": user_content})
    return messages


# ──────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────

@app.get("/", response_model=StatusResponse)
async def root():
    stats = rag_engine.get_stats() if rag_engine else {}
    return StatusResponse(
        status="online",
        model=MODEL_NAME,
        device=DEVICE,
        rag_stats=stats
    )

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if rag_engine is None:
        raise HTTPException(status_code=503, detail="Motor RAG no inicializado")
    
    if llm_model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="Modelo de lenguaje no disponible")
    
    # 1. Expandir sinónimos y recuperar contexto relevante
    expanded_query = expand_query(request.message)
    context = rag_engine.build_context(expanded_query, top_k=TOP_K_RETRIEVAL)
    sources = rag_engine.search(expanded_query, top_k=TOP_K_RETRIEVAL)
    
    # 2. Construir mensajes y aplicar chat template (con historial)
    messages = build_messages(request.message, context, request.history)
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    
    # 3. Generar respuesta
    try:
        inputs = tokenizer(prompt, return_tensors="pt").to(llm_model.device)
        outputs = llm_model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=True,
            temperature=TEMPERATURE,
            top_p=0.9,
            top_k=50,
            repetition_penalty=1.15,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id
        )
        
        generated_ids = outputs[0][inputs["input_ids"].shape[-1]:]
        response_text = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        
    except Exception as e:
        response_text = f"Error al generar respuesta: {str(e)}"
    
    # 4. Formatear fuentes
    formatted_sources = []
    for s in sources:
        formatted_sources.append({
            "titulo": s["titulo"],
            "categoria": s["categoria"],
            "score": round(s.get("score", 0), 3)
        })
    
    return ChatResponse(
        response=response_text,
        sources=formatted_sources,
        stats={
            "model_used": MODEL_NAME,
            "device": DEVICE,
            "context_length": len(prompt),
            "sources_found": len(sources)
        }
    )

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Endpoint de streaming que devuelve la respuesta token por token
    usando Server-Sent Events (SSE).
    """
    if rag_engine is None:
        raise HTTPException(status_code=503, detail="Motor RAG no inicializado")
    
    if llm_model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="Modelo de lenguaje no disponible")
    
    # 1. Expandir sinónimos y recuperar contexto
    expanded_query = expand_query(request.message)
    context = rag_engine.build_context(expanded_query, top_k=TOP_K_RETRIEVAL)
    sources = rag_engine.search(expanded_query, top_k=TOP_K_RETRIEVAL)
    
    # 2. Construir prompt con historial de conversación
    messages = build_messages(request.message, context, request.history)
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    
    # 3. Preparar streamer
    inputs = tokenizer(prompt, return_tensors="pt").to(llm_model.device)
    streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
    
    # 4. Generar en thread separado
    generation_kwargs = {
        **inputs,
        "streamer": streamer,
        "max_new_tokens": MAX_NEW_TOKENS,
        "do_sample": True,
        "temperature": TEMPERATURE,
        "top_p": 0.9,
        "top_k": 50,
        "repetition_penalty": 1.15,
        "pad_token_id": tokenizer.eos_token_id,
        "eos_token_id": tokenizer.eos_token_id,
    }
    
    thread = threading.Thread(target=lambda: llm_model.generate(**generation_kwargs))
    thread.start()
    
    # 5. Formatear fuentes
    formatted_sources = []
    for s in sources:
        formatted_sources.append({
            "titulo": s["titulo"],
            "categoria": s["categoria"],
            "score": round(s.get("score", 0), 3)
        })
    
    # 6. Generador SSE
    async def generate_stream():
        try:
            # Enviar fuentes primero
            import json
            yield f"data: {json.dumps({'type': 'sources', 'sources': formatted_sources})}\n\n"
            
            # Enviar tokens a medida que se generan
            for text in streamer:
                if text:
                    yield f"data: {json.dumps({'type': 'token', 'text': text})}\n\n"
            
            # Señal de fin
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            import json
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

@app.get("/stats")
async def stats():
    if rag_engine is None:
        return {"error": "RAG no inicializado"}
    return rag_engine.get_stats()

# ──────────────────────────────────────────────────────────────
# Para ejecución directa
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
