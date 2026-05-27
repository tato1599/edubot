"""
Servicio de LLM (Large Language Model) con carga optimizada y manejo de errores.
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional, Iterator

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TextIteratorStreamer,
    BitsAndBytesConfig,
)

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """
    Servicio enterprise para inferencia con modelos de lenguaje locales.
    
    Caracteristicas:
    - Carga lazy (solo cuando se necesita)
    - Quantization 4-bit/8-bit para VRAM limitada
    - Streaming de tokens
    - Manejo de errores robusto
    """
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = settings.device
        self._loaded = False
        self._load_time = 0.0
    
    @property
    def is_loaded(self) -> bool:
        return self._loaded and self.model is not None and self.tokenizer is not None
    
    def load(self) -> bool:
        """Carga el modelo y tokenizador. Retorna True si tuvo exito."""
        if self._loaded:
            return True
        
        logger.info(f"[LLM] Cargando modelo: {settings.model_name}")
        start = time.time()
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                settings.model_name,
                trust_remote_code=True,
                cache_dir=os.environ.get("HF_CACHE_DIR", None)
            )
            
            quantization = None
            if settings.load_in_4bit:
                quantization = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                )
                logger.info("[LLM] Usando quantization 4-bit (NF4)")
            elif settings.load_in_8bit:
                quantization = BitsAndBytesConfig(load_in_8bit=True)
                logger.info("[LLM] Usando quantization 8-bit")
            
            load_kwargs = {
                "trust_remote_code": True,
                "low_cpu_mem_usage": True,
            }
            
            if quantization:
                load_kwargs["quantization_config"] = quantization
            
            if self.device != "auto":
                load_kwargs["device_map"] = self.device
            else:
                load_kwargs["device_map"] = "auto"
            
            self.model = AutoModelForCausalLM.from_pretrained(
                settings.model_name,
                **load_kwargs
            )
            
            self._load_time = time.time() - start
            self._loaded = True
            
            logger.info(f"[LLM] Modelo cargado en {self._load_time:.1f}s")
            return True
            
        except Exception as e:
            logger.error(f"[LLM] Error cargando modelo: {e}")
            self.model = None
            self.tokenizer = None
            self._loaded = False
            return False
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        max_new_tokens: int = None,
        temperature: float = None,
    ) -> str:
        """
        Genera una respuesta completa (no streaming).
        
        Args:
            messages: Lista de mensajes [{role, content}]
            max_new_tokens: Max tokens a generar
            temperature: Temperatura de muestreo
        """
        if not self.is_loaded:
            raise RuntimeError("Modelo no cargado")
        
        max_new_tokens = max_new_tokens or settings.max_new_tokens
        temperature = temperature or settings.temperature
        
        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=temperature,
                top_p=settings.top_p,
                top_k=settings.top_k,
                repetition_penalty=settings.repetition_penalty,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )
        
        generated_ids = outputs[0][inputs["input_ids"].shape[-1]:]
        return self.tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
    
    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        max_new_tokens: int = None,
        temperature: float = None,
    ) -> Iterator[str]:
        """
        Genera respuesta en streaming (yield token por token).
        
        Yields:
            str: Tokens individuales
        """
        if not self.is_loaded:
            raise RuntimeError("Modelo no cargado")
        
        max_new_tokens = max_new_tokens or settings.max_new_tokens
        temperature = temperature or settings.temperature
        
        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        streamer = TextIteratorStreamer(
            self.tokenizer,
            skip_prompt=True,
            skip_special_tokens=True
        )
        
        import threading
        
        generation_kwargs = {
            **inputs,
            "streamer": streamer,
            "max_new_tokens": max_new_tokens,
            "do_sample": True,
            "temperature": temperature,
            "top_p": settings.top_p,
            "top_k": settings.top_k,
            "repetition_penalty": settings.repetition_penalty,
            "pad_token_id": self.tokenizer.eos_token_id,
            "eos_token_id": self.tokenizer.eos_token_id,
        }
        
        thread = threading.Thread(target=lambda: self.model.generate(**generation_kwargs))
        thread.start()
        
        for text in streamer:
            if text:
                yield text
        
        thread.join()
    
    def unload(self) -> None:
        """Libera memoria del modelo."""
        if self.model is not None:
            del self.model
            self.model = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        self._loaded = False
        logger.info("[LLM] Modelo descargado de memoria")
    
    def get_stats(self) -> Dict[str, Any]:
        """Estadisticas del servicio LLM."""
        return {
            "loaded": self.is_loaded,
            "model_name": settings.model_name,
            "device": str(self.device),
            "load_time_seconds": round(self._load_time, 2),
            "quantization": "4-bit" if settings.load_in_4bit else ("8-bit" if settings.load_in_8bit else "full"),
        }
