"""
Rutas API para gestion de tunnels.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException

from backend.app.services.tunnel_service import TunnelService

router = APIRouter(prefix="/tunnel", tags=["tunnel"])

# Servicio inyectado desde main.py
tunnel_service: Optional[TunnelService] = None


@router.post("/create")
async def create_tunnel(provider: str = "cloudflare", local_port: int = None):
    """
    Crea un nuevo tunnel publico.
    
    Args:
        provider: 'cloudflare' (recomendado) o 'localtunnel'
        local_port: Puerto local a exponer (default: 8000)
    
    Returns:
        Informacion del tunnel creado
    """
    if tunnel_service is None:
        raise HTTPException(status_code=503, detail="Servicio de tunneling no disponible")
    
    result = tunnel_service.create_tunnel(
        provider=provider,
        local_port=local_port
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=400 if "install" in result.get("error", "") else 500,
            detail=result
        )
    
    return result


@router.post("/close/{tunnel_id}")
async def close_tunnel(tunnel_id: str):
    """Cierra un tunnel especifico."""
    if tunnel_service is None:
        raise HTTPException(status_code=503, detail="Servicio de tunneling no disponible")
    
    result = tunnel_service.close_tunnel(tunnel_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result)
    
    return result


@router.get("/list")
async def list_tunnels():
    """Lista todos los tunnels activos."""
    if tunnel_service is None:
        raise HTTPException(status_code=503, detail="Servicio de tunneling no disponible")
    
    return tunnel_service.list_tunnels()


@router.get("/stats")
async def tunnel_stats():
    """Estadisticas del servicio de tunneling."""
    if tunnel_service is None:
        raise HTTPException(status_code=503, detail="Servicio de tunneling no disponible")
    
    return tunnel_service.get_stats()


@router.post("/close-all")
async def close_all_tunnels():
    """Cierra todos los tunnels activos."""
    if tunnel_service is None:
        raise HTTPException(status_code=503, detail="Servicio de tunneling no disponible")
    
    tunnel_service.close_all()
    return {"success": True, "message": "Todos los tunnels cerrados"}
