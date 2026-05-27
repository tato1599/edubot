"""
Configuracion centralizada de la aplicacion.
Usa Pydantic Settings para cargar desde variables de entorno o archivo .env
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuracion enterprise del Agente Escolar."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # App
    app_name: str = "Agente Escolar Inteligente"
    app_version: str = "2.0.0"
    app_description: str = "Asistente de tramites escolares, reticula ISC y nutricion basado en SMAE con RAG local."
    debug: bool = False
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    
    # CORS
    cors_origins: List[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]
    
    # Modelo LLM
    model_name: str = "Qwen/Qwen2.5-3B-Instruct"
    device: str = "auto"  # auto, cuda, cpu
    load_in_4bit: bool = True
    load_in_8bit: bool = False
    temperature: float = 0.2
    max_new_tokens: int = 350
    top_p: float = 0.9
    top_k: int = 50
    repetition_penalty: float = 1.15
    
    # RAG / Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"
    top_k_retrieval: int = 5
    rag_data_dir: str = "backend/data"
    chroma_persist_dir: str = "backend/chroma_db"
    chroma_collection_name: str = "edubot_knowledge"
    chroma_batch_size: int = 100
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # json, text
    
    # Performance
    enable_query_cache: bool = True
    query_cache_size: int = 1000
    enable_streaming: bool = True
    
    # Rate Limiting
    rate_limit_requests: int = 60
    rate_limit_window: int = 60  # segundos
    
    @property
    def frontend_dir(self) -> str:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend"))
    
    @property
    def data_dir(self) -> str:
        return os.path.abspath(self.rag_data_dir)
    
    @property
    def chroma_dir(self) -> str:
        return os.path.abspath(self.chroma_persist_dir)


# Instancia global de configuracion
settings = Settings()
