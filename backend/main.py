"""
Backend FastAPI para el Agente Escolar Inteligente.
Integra RAG + modelo local Qwen2-1.5B-Instruct para responder sobre trámites y nutrición.
"""

import os
import sys
import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from contextlib import asynccontextmanager

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from rag_engine import RAGEngine

# ──────────────────────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────────────────────
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MODEL_NAME = "Qwen/Qwen2-1.5B-Instruct"
TOP_K_RETRIEVAL = 3

print(f"[CONFIG] Dispositivo: {DEVICE}")
print(f"[CONFIG] Modelo: {MODEL_NAME}")

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
    description="Asistente de trámites escolares y nutrición basado en SMAE con RAG local.",
    version="1.0.0",
    lifespan=lifespan
)

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
    "Eres EduBot, un asistente virtual especializado en tres áreas principales: "
    "(1) Trámites escolares como inscripciones, reinscripciones, constancias, becas, titulación, cambio de carrera y servicio social; "
    "(2) Nutrición escolar basada en el Sistema de Alimentos Equivalentes (SMAE); "
    "y (3) Información académica de la carrera de Ingeniería en Sistemas Computacionales del TecNM ITCJ (plan ISIC-2010-224), "
    "incluyendo retícula, materias por semestre, prerequisitos, créditos, y recomendaciones de plan de estudios. "
    "Responde SIEMPRE en español. Usa ÚNICAMENTE la información del contexto proporcionado. "
    "Si no encuentras la información, di amablemente que no la tienes y sugiere acudir a Servicios Escolares, al Coordinador de Carrera o al nutriólogo según corresponda. "
    "Sé claro, conciso y amigable. Usa viñetas o pasos numerados cuando sea apropiado. "
    "NO inventes datos, costos, fechas, claves de materias ni procedimientos."
)

def build_messages(query: str, context: str) -> list:
    """Construye la lista de mensajes para apply_chat_template de Qwen2."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Utiliza el siguiente contexto para responder:\n\n{context}\n\nPregunta: {query}"}
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
    
    # 1. Recuperar contexto relevante
    context = rag_engine.build_context(request.message, top_k=TOP_K_RETRIEVAL)
    sources = rag_engine.search(request.message, top_k=TOP_K_RETRIEVAL)
    
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
            max_new_tokens=200,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            repetition_penalty=1.1,
            pad_token_id=tokenizer.eos_token_id
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
