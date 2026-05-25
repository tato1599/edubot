"""
Backend FastAPI para el Agente Escolar Inteligente.
Integra RAG + modelo local Qwen2-1.5B-Instruct para responder sobre trámites y nutrición.
"""

import os
import sys
import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from contextlib import asynccontextmanager

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from rag_engine import RAGEngine

# ──────────────────────────────────────────────────────────────
# Configuración
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MODEL_NAME = "Qwen/Qwen2-1.5B-Instruct"
TOP_K_RETRIEVAL = 5  # Más contexto = menos alucinaciones

print(f"[CONFIG] Dispositivo: {DEVICE}")
print(f"[CONFIG] Modelo: {MODEL_NAME}")
print(f"[CONFIG] top_k retrieval: {TOP_K_RETRIEVAL}")

# ──────────────────────────────────────────────────────────────
# Variables globales (se inicializan en lifespan)
# ──────────────────────────────────────────────────────────────
rag_engine = None
llm_model = None
tokenizer = None

# ──────────────────────────────────────────────────────────────
# Lifespan: carga pesada al iniciar el servidor
# ──────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global rag_engine, llm_model, tokenizer
    
    print("\n" + "="*50)
    print("INICIANDO AGENTE ESCOLAR INTELIGENTE")
    print("="*50 + "\n")
    
    # 1. Cargar RAG Engine
    print("[1/3] Cargando motor de RAG...")
    rag_engine = RAGEngine()
    stats = rag_engine.get_stats()
    print(f"      Documentos: {stats['total_documents']}")
    print(f"      Motor: {stats['embedding_model']}")
    
    # 2. Cargar modelo de lenguaje
    print("\n[2/3] Cargando modelo de lenguaje local...")
    print(f"      Esto puede tomar unos minutos la primera vez.")
    
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
        
        if DEVICE == "cuda":
            llm_model = AutoModelForCausalLM.from_pretrained(
                MODEL_NAME,
                dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True
            )
        else:
            llm_model = AutoModelForCausalLM.from_pretrained(
                MODEL_NAME,
                dtype=torch.float32,
                trust_remote_code=True
            )
            llm_model = llm_model.to(DEVICE)
        
        print("      Modelo cargado correctamente.")
    except Exception as e:
        print(f"      ERROR al cargar modelo: {e}")
        llm_model = None
    
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
    "Eres EduBot, un asistente virtual del TecNM ITCJ que ayuda a estudiantes con trámites escolares, información de la carrera de Ingeniería en Sistemas Computacionales, nutrición escolar, y locales de comida dentro del campus. "
    "Responde SIEMPRE en español, de forma clara, concisa y amigable. "
    "Usa viñetas (•) para listas. Ve directo a la respuesta sin frases introductorias como 'como asistente' o 'estoy aquí para'. "
    "\n\n"
    "REGLAS:\n"
    "1. Usa ÚNICAMENTE la información que tienes. NO inventes datos. NO uses conocimiento de internet.\n"
    "2. Si la pregunta es específica y tienes la respuesta, responde con los datos exactos.\n"
    "3. Si la pregunta es general ('qué sabes de...', 'cuéntame sobre...') y tienes información relacionada, RESUME lo que sabes de forma natural.\n"
    "4. Si NO tienes información sobre lo que preguntan, di simplemente: 'Lo siento, no tengo esa información. Te sugiero acudir a Servicios Escolares o al Coordinador de Carrera para confirmar.' NUNCA digas 'los documentos no contienen' o menciones que buscaste en archivos.\n"
    "5. Si alguien pregunta algo ambiguo ('sistemas', 'la carrera') y tienes información de 'sistemas computacionales', asume que se refiere a eso y responde naturalmente.\n"
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
    }
    
    for key, expansion in synonyms.items():
        if key in q_lower:
            expansions.append(expansion)
    
    if expansions:
        return f"{query} {' '.join(expansions)}"
    return query

def build_messages(query: str, context: str) -> list:
    """Construye la lista de mensajes para apply_chat_template de Qwen2."""
    user_content = (
        "INFORMACIÓN QUE TIENES:\n"
        "===================\n"
        f"{context}\n"
        "===================\n\n"
        f"PREGUNTA: {query}\n\n"
        "Responde como EduBot, el asistente escolar. Sé natural y directo. "
        "Si la pregunta es general y tienes información relacionada, resume lo que sabes. "
        "Si no sabes la respuesta, di que no tienes la información y sugiere acudir a Servicios Escolares. "
        "NO digas 'los documentos no contienen' ni menciones que buscaste archivos."
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content}
    ]


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
    
    # 2. Construir mensajes y aplicar chat template
    messages = build_messages(request.message, context)
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
            max_new_tokens=400,
            do_sample=True,
            temperature=0.5,              # Balanceado: creatividad controlada
            top_p=0.9,
            top_k=50,
            repetition_penalty=1.1,
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
