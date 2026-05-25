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
    "Eres EduBot, un asistente virtual del TecNM ITCJ. "
    "Tu ÚNICA fuente de información son los documentos que te proporciono en cada consulta. "
    "NO uses conocimiento general de internet. NO inventes datos. NO supongas. "
    "Si la respuesta NO está en los documentos, di EXACTAMENTE: 'Lo siento, no tengo esa información en mis documentos. Te sugiero acudir a Servicios Escolares o al Coordinador de Carrera para confirmar.' "
    "Responde SIEMPRE en español. Sé conciso. Usa viñetas para listas. "
    "\n\n"
    "EJEMPLO DE RESPUESTA CORRECTA:\n"
    "Documentos: [1] ISC - Semestre 1: Materias: Cálculo Diferencial (ACF-0901, 5 créditos), Fundamentos de Programación (AED-1285, 5 créditos)...\n"
    "Pregunta: ¿Qué materias son de primer semestre?\n"
    "Respuesta: Las materias del primer semestre son:\n"
    "• Cálculo Diferencial (ACF-0901)\n"
    "• Fundamentos de Programación (AED-1285)\n"
    "• Taller de Ética (ACA-0907)\n"
    "• Matemáticas Discretas (AEF-1041)\n"
    "• Taller de Administración (SCH-1024)\n"
    "• Fundamentos de Investigación (ACC-0906)\n\n"
    "EJEMPLO DE RESPUESTA INCORRECTA (NUNCA hagas esto):\n"
    "Documentos: [1] ISC - Semestre 1...\n"
    "Pregunta: ¿Qué materias son de primer semestre?\n"
    "Respuesta incorrecta: Las materias del primer semestre son Cálculo Integral y Programación Orientada a Objetos... "
    "(ERROR: esas son del semestre 2, no del 1)\n\n"
    "EJEMPLO DE 'NO SÉ':\n"
    "Documentos: (vacío o sin información relevante)\n"
    "Pregunta: ¿Cuál es el horario de la biblioteca?\n"
    "Respuesta: Lo siento, no tengo esa información en mis documentos. Te sugiero acudir a Servicios Escolares o al Coordinador de Carrera para confirmar."
)

def build_messages(query: str, context: str) -> list:
    """Construye la lista de mensajes para apply_chat_template de Qwen2."""
    user_content = (
        "INSTRUCCIÓN: Lee los siguientes documentos y responde la pregunta del usuario. "
        "Usa ÚNICAMENTE la información de los documentos. "
        "Si la respuesta no está en los documentos, di: 'Lo siento, no tengo esa información en mis documentos. Te sugiero acudir a Servicios Escolares o al Coordinador de Carrera para confirmar.'\n\n"
        "DOCUMENTOS:\n"
        "===========\n"
        f"{context}\n"
        "===========\n\n"
        f"PREGUNTA DEL USUARIO: {query}\n\n"
        "Responde de forma directa y concisa usando solo los documentos anteriores."
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content}
    ]

def clean_response(text: str) -> str:
    """
    Post-processing para limpiar alucinaciones comunes del modelo pequeño.
    """
    import re
    
    original = text.strip()
    
    # Lista de frases que indican alucinación o respuesta genérica
    hallucination_patterns = [
        r"(?i)linux es una familia de",
        r"(?i)como asistente",
        r"(?i)estoy aquí para ayudarte",
        r"(?i)estoy aquí para asistirte",
        r"(?i)puedo decirte varias cosas sobre",
        r"(?i)por lo tanto",
        r"(?i)en conclusión",
        r"(?i)en resumen",
        r"(?i)es importante tener en cuenta",
        r"(?i)te recomendaría verificar",
        r"(?i)sin embargo",
        r"(?i)por otro lado",
        r"(?i)aunque no tenga información específica",
        r"(?i)aunque no tengo información",
        r"(?i)no tengo información específica sobre",
    ]
    
    # Detectar si la respuesta es probablemente una alucinación
    is_hallucination = any(re.search(p, original) for p in hallucination_patterns)
    
    # Si es muy corta y genérica, probablemente es alucinación
    if len(original) < 30 and ("no" in original.lower() or "sé" in original.lower() or "información" in original.lower()):
        is_hallucination = True
    
    # Si menciona cosas que NO están en los documentos conocidos
    if "microsoft" in original.lower() or "windows" in original.lower() or "macos" in original.lower():
        is_hallucination = True
    
    if is_hallucination:
        return "Lo siento, no tengo esa información en mis documentos. Te sugiero acudir a Servicios Escolares o al Coordinador de Carrera para confirmar."
    
    # Limpiar repeticiones al final
    sentences = original.split('. ')
    if len(sentences) > 2:
        # Eliminar última oración si es casi igual a la penúltima
        if sentences[-1].strip() and sentences[-2].strip():
            if sentences[-1][:20].lower() == sentences[-2][:20].lower():
                original = '. '.join(sentences[:-1])
    
    return original.strip()


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
            max_new_tokens=400,          # Más tokens para respuestas completas
            do_sample=True,
            temperature=0.3,              # Baja temperatura = menos inventos
            top_p=0.85,                   # Más conservador
            top_k=40,                     # Restringe vocabulario
            repetition_penalty=1.15,      # Penaliza repeticiones
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id
        )
        
        generated_ids = outputs[0][inputs["input_ids"].shape[-1]:]
        response_text = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        
        # Post-processing: limpiar alucinaciones comunes
        response_text = clean_response(response_text)
        
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
