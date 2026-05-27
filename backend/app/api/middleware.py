"""
Middleware personalizado para la API.
- Request ID tracing
- Logging de requests
- Rate limiting basico
- Tiempo de respuesta
"""

import time
import uuid
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Almacenamiento simple para rate limiting (en produccion usar Redis)
_rate_limit_store: dict = {}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware que loggea todas las requests con timing y request ID."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        
        start = time.time()
        
        # Log request
        logger.info(
            f"[{request_id}] {request.method} {request.url.path}",
            extra={"request_id": request_id, "method": request.method, "path": request.url.path}
        )
        
        try:
            response = await call_next(request)
            duration = (time.time() - start) * 1000
            
            logger.info(
                f"[{request_id}] {request.method} {request.url.path} -> {response.status_code} ({duration:.1f}ms)",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "duration_ms": round(duration, 2),
                }
            )
            
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration:.1f}ms"
            return response
            
        except Exception as e:
            duration = (time.time() - start) * 1000
            logger.error(
                f"[{request_id}] {request.method} {request.url.path} -> ERROR ({duration:.1f}ms): {e}",
                extra={"request_id": request_id, "duration_ms": round(duration, 2)},
                exc_info=True
            )
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware de rate limiting simple basado en IP."""
    
    def __init__(self, app, max_requests: int = 60, window: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Excluir health checks y archivos estaticos
        if request.url.path in ["/health", "/", "/static"] or request.url.path.startswith("/static/"):
            return await call_next(request)
        
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        
        # Limpiar entradas antiguas
        if client_ip in _rate_limit_store:
            _rate_limit_store[client_ip] = [
                t for t in _rate_limit_store[client_ip] if now - t < self.window
            ]
        else:
            _rate_limit_store[client_ip] = []
        
        if len(_rate_limit_store[client_ip]) >= self.max_requests:
            return Response(
                content='{"detail": "Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(self.window)}
            )
        
        _rate_limit_store[client_ip].append(now)
        
        response = await call_next(request)
        remaining = max(0, self.max_requests - len(_rate_limit_store[client_ip]))
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response
