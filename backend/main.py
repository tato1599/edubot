"""
Entry point principal de la aplicacion FastAPI.
Arquitectura limpia con lifespan para carga ordenada de servicios.
"""

import os
import sys
import time
import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Setup paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app.core.config import settings
from backend.app.core.logging_config import setup_logging
from backend.app.api.routes import router as api_router
from backend.app.api import routes as routes_module
from backend.app.api import tunnel_routes

rag_ref = routes_module.rag_service
llm_ref = routes_module.llm_service
startup_status = routes_module.startup_status
from backend.app.api.middleware import RequestLoggingMiddleware, RateLimitMiddleware
from backend.app.services.rag_service import RAGService
from backend.app.services.llm_service import LLMService
from backend.app.services.tunnel_service import TunnelService

# Configurar logging
setup_logging()
logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────
# Lifespan: carga ordenada de servicios
# ───────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carga servicios al iniciar y limpia al cerrar."""
    global rag_ref, llm_ref
    
    logger.info("=" * 50)
    logger.info("INICIANDO AGENTE ESCOLAR INTELIGENTE v%s", settings.app_version)
    logger.info("=" * 50)
    
    startup_status.update({
        "stage": "rag",
        "stage_name": "Indexando documentos...",
        "progress": 0.05,
        "model_loaded": False,
        "rag_documents": 0,
    })
    
    # 1. Cargar RAG
    try:
        logger.info("[1/3] Cargando motor RAG...")
        rag_ref = RAGService()
        routes_module.rag_service = rag_ref
        rag_stats = rag_ref.get_stats()
        startup_status["rag_documents"] = rag_stats["total_documents"]
        startup_status["progress"] = 0.20
        logger.info("      Documentos: %d", rag_stats["total_documents"])
        logger.info("      Motor: %s", rag_stats["embedding_model"])
        logger.info("      DB: %s", rag_stats["vector_database"])
    except Exception as e:
        logger.error("Error cargando RAG: %s", e)
        startup_status["stage"] = "error"
        startup_status["stage_name"] = f"Error RAG: {e}"
        raise
    
    # 2. Cargar LLM
    startup_status.update({
        "stage": "model",
        "stage_name": "Cargando modelo de IA...",
        "progress": 0.30,
    })
    
    try:
        logger.info("[2/3] Cargando modelo de lenguaje: %s", settings.model_name)
        llm_ref = LLMService()
        success = llm_ref.load()
        
        if success:
            routes_module.llm_service = llm_ref
            llm_stats = llm_ref.get_stats()
            startup_status.update({
                "model_loaded": True,
                "progress": 0.80,
                "stage": "ready",
                "stage_name": "Sistema listo",
            })
            logger.info("      Modelo cargado en %.1fs", llm_stats["load_time_seconds"])
        else:
            startup_status.update({
                "stage": "error",
                "stage_name": "Error cargando modelo",
                "progress": 1.0,
            })
            logger.error("      Fallo al cargar el modelo")
            
    except Exception as e:
        logger.error("Error cargando LLM: %s", e)
        startup_status.update({
            "stage": "error",
            "stage_name": f"Error: {e}",
            "progress": 1.0,
        })
    
    # 3. Inicializar Tunnel Service
    logger.info("[3/3] Inicializando servicio de tunneling...")
    tunnel_service = TunnelService()
    tunnel_routes.tunnel_service = tunnel_service
    logger.info("      Tunneling listo (cloudflared: %s, npx: %s)",
                tunnel_service.get_stats()["cloudflare_available"],
                tunnel_service.get_stats()["localtunnel_available"])
    
    logger.info("Servidor listo para recibir peticiones.")
    logger.info("=" * 50)
    
    yield
    
    # Cleanup
    logger.info("[SHUTDOWN] Liberando recursos...")
    if tunnel_service:
        tunnel_service.close_all()
    if llm_ref:
        llm_ref.unload()


# ───────────────────────────────────────────────
# FastAPI App
# ───────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Middlewares
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    max_requests=settings.rate_limit_requests,
    window=settings.rate_limit_window,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Exception handlers en espanol
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    detail = exc.detail
    # Traducir mensajes comunes de FastAPI/Starlette
    translations = {
        "Not Found": "Recurso no encontrado.",
        "Method Not Allowed": "Metodo no permitido.",
        "Unauthorized": "No autorizado. Inicia sesion primero.",
        "Forbidden": "Acceso denegado.",
        "Bad Request": "Solicitud incorrecta.",
        "Service Unavailable": "Servicio no disponible. Intenta de nuevo en un momento.",
        "Internal Server Error": "Error interno del servidor.",
    }
    if detail in translations:
        detail = translations[detail]
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": detail}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"detail": "Error en los datos enviados. Verifica el formato de tu peticion."}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logger.error(f"Error inesperado: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor. Por favor intenta de nuevo en un momento."}
    )

# API Routes
app.include_router(api_router, prefix="/api")
app.include_router(tunnel_routes.router, prefix="/api")

# Tambien montar rutas legacy sin /api para compatibilidad
app.include_router(api_router)
app.include_router(tunnel_routes.router)

# Static files (frontend)
if os.path.exists(settings.frontend_dir):
    app.mount("/static", StaticFiles(directory=settings.frontend_dir), name="static")
    
    @app.get("/", include_in_schema=False)
    async def serve_index():
        return FileResponse(os.path.join(settings.frontend_dir, "index.html"))


# ───────────────────────────────────────────────
# Entry point
# ───────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=settings.workers if not settings.debug else 1,
    )
