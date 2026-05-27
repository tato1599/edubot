"""
Servicio de Tunneling para exposicion publica de EduBot.
Soporta Cloudflare Tunnel y LocalTunnel.
"""

import os
import re
import subprocess
import time
import logging
import signal
import threading
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class TunnelInfo:
    """Informacion de un tunnel activo."""
    provider: str  # 'cloudflare' | 'localtunnel'
    url: str
    pid: int
    local_port: int
    created_at: float
    status: str = "active"  # active | closing | error
    error_message: Optional[str] = None


class TunnelService:
    """
    Servicio para gestionar tunnels de exposicion publica.
    
    Soporta:
    - Cloudflare Tunnel (recomendado, mas estable)
    - LocalTunnel (alternativa con npx)
    """
    
    def __init__(self):
        self.tunnels: Dict[str, TunnelInfo] = {}
        self._lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
    
    def _extract_cloudflare_url(self, output: str) -> Optional[str]:
        """Extrae la URL de cloudflared del output."""
        patterns = [
            r'(https://[a-zA-Z0-9-]+\.trycloudflare\.com)',
            r'(https://[a-zA-Z0-9-]+\.loca\.lt)',
        ]
        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                return match.group(1)
        return None
    
    def create_tunnel(
        self,
        provider: str = "cloudflare",
        local_port: int = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Crea un nuevo tunnel.
        
        Args:
            provider: 'cloudflare' o 'localtunnel'
            local_port: Puerto local a exponer (default: config.port)
            timeout: Segundos para esperar URL
        
        Returns:
            Dict con info del tunnel o error
        """
        local_port = local_port or settings.port
        
        with self._lock:
            # Verificar si ya existe tunnel para este puerto
            for tid, info in self.tunnels.items():
                if info.local_port == local_port and info.status == "active":
                    return {
                        "success": True,
                        "tunnel_id": tid,
                        "url": info.url,
                        "provider": provider,
                        "message": "Tunnel ya existe",
                        "existing": True
                    }
        
        if provider == "cloudflare":
            return self._create_cloudflare_tunnel(local_port, timeout)
        elif provider == "localtunnel":
            return self._create_localtunnel(local_port, timeout)
        else:
            return {
                "success": False,
                "error": f"Provider no soportado: {provider}"
            }
    
    def _create_cloudflare_tunnel(self, local_port: int, timeout: int) -> Dict[str, Any]:
        """Crea tunnel con Cloudflare."""
        # Verificar que cloudflared existe
        if not self._command_exists("cloudflared"):
            return {
                "success": False,
                "error": "cloudflared no instalado. Instala: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/",
                "install_cmd": "curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb && sudo dpkg -i cloudflared.deb"
            }
        
        try:
            # Iniciar cloudflared
            logger.info(f"[Tunnel] Iniciando Cloudflare tunnel en puerto {local_port}")
            
            process = subprocess.Popen(
                ["cloudflared", "tunnel", "--url", f"http://localhost:{local_port}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Esperar a que aparezca la URL
            url = None
            output_buffer = []
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                import select
                if process.poll() is not None:
                    # Proceso termino prematuramente
                    break
                
                # Leer output sin bloquear
                if process.stdout:
                    line = process.stdout.readline()
                    if line:
                        output_buffer.append(line)
                        logger.debug(f"[Cloudflare] {line.strip()}")
                        url = self._extract_cloudflare_url(line)
                        if url:
                            break
                
                time.sleep(0.1)
            
            if url:
                tunnel_id = f"cf_{int(time.time())}"
                info = TunnelInfo(
                    provider="cloudflare",
                    url=url,
                    pid=process.pid,
                    local_port=local_port,
                    created_at=time.time()
                )
                
                with self._lock:
                    self.tunnels[tunnel_id] = info
                
                logger.info(f"[Tunnel] Cloudflare tunnel creado: {url}")
                
                # Iniciar monitoreo
                self._start_monitoring()
                
                return {
                    "success": True,
                    "tunnel_id": tunnel_id,
                    "url": url,
                    "provider": "cloudflare",
                    "local_port": local_port,
                    "message": "Tunnel creado exitosamente"
                }
            else:
                # No se encontro URL, matar proceso
                process.terminate()
                try:
                    process.wait(timeout=5)
                except:
                    process.kill()
                
                output = "".join(output_buffer)
                return {
                    "success": False,
                    "error": "No se pudo obtener URL del tunnel",
                    "output": output[-500:] if len(output) > 500 else output
                }
                
        except Exception as e:
            logger.error(f"[Tunnel] Error creando Cloudflare tunnel: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _create_localtunnel(self, local_port: int, timeout: int) -> Dict[str, Any]:
        """Crea tunnel con LocalTunnel (npx)."""
        if not self._command_exists("npx"):
            return {
                "success": False,
                "error": "npx no instalado. Instala Node.js: https://nodejs.org/",
                "install_cmd": "sudo apt update && sudo apt install -y nodejs npm"
            }
        
        try:
            logger.info(f"[Tunnel] Iniciando LocalTunnel en puerto {local_port}")
            
            process = subprocess.Popen(
                ["npx", "localtunnel", "--port", str(local_port)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            url = None
            output_buffer = []
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if process.poll() is not None:
                    break
                
                line = process.stdout.readline()
                if line:
                    output_buffer.append(line)
                    url = self._extract_cloudflare_url(line)
                    if url:
                        break
                
                time.sleep(0.1)
            
            if url:
                tunnel_id = f"lt_{int(time.time())}"
                info = TunnelInfo(
                    provider="localtunnel",
                    url=url,
                    pid=process.pid,
                    local_port=local_port,
                    created_at=time.time()
                )
                
                with self._lock:
                    self.tunnels[tunnel_id] = info
                
                logger.info(f"[Tunnel] LocalTunnel creado: {url}")
                self._start_monitoring()
                
                return {
                    "success": True,
                    "tunnel_id": tunnel_id,
                    "url": url,
                    "provider": "localtunnel",
                    "local_port": local_port,
                    "message": "Tunnel creado exitosamente"
                }
            else:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except:
                    process.kill()
                
                output = "".join(output_buffer)
                return {
                    "success": False,
                    "error": "No se pudo obtener URL del tunnel",
                    "output": output[-500:] if len(output) > 500 else output
                }
                
        except Exception as e:
            logger.error(f"[Tunnel] Error creando LocalTunnel: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def close_tunnel(self, tunnel_id: str) -> Dict[str, Any]:
        """Cierra un tunnel especifico."""
        with self._lock:
            info = self.tunnels.get(tunnel_id)
            if not info:
                return {
                    "success": False,
                    "error": "Tunnel no encontrado"
                }
            
            info.status = "closing"
        
        try:
            os.kill(info.pid, signal.SIGTERM)
            # Esperar un poco y forzar si es necesario
            time.sleep(1)
            try:
                os.kill(info.pid, 0)  # Verificar si existe
                os.kill(info.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass  # Ya murio
            
            with self._lock:
                if tunnel_id in self.tunnels:
                    del self.tunnels[tunnel_id]
            
            logger.info(f"[Tunnel] Tunnel {tunnel_id} cerrado")
            return {
                "success": True,
                "message": f"Tunnel {tunnel_id} cerrado",
                "url": info.url
            }
            
        except Exception as e:
            logger.error(f"[Tunnel] Error cerrando tunnel: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def close_all(self) -> None:
        """Cierra todos los tunnels."""
        with self._lock:
            tunnel_ids = list(self.tunnels.keys())
        
        for tid in tunnel_ids:
            self.close_tunnel(tid)
        
        self._running = False
    
    def list_tunnels(self) -> Dict[str, Any]:
        """Lista todos los tunnels activos."""
        active = {}
        with self._lock:
            for tid, info in self.tunnels.items():
                if info.status == "active":
                    active[tid] = {
                        "tunnel_id": tid,
                        "provider": info.provider,
                        "url": info.url,
                        "local_port": info.local_port,
                        "created_at": info.created_at,
                        "uptime_seconds": round(time.time() - info.created_at, 0)
                    }
        
        return {
            "count": len(active),
            "tunnels": list(active.values())
        }
    
    def _command_exists(self, cmd: str) -> bool:
        """Verifica si un comando existe en el sistema."""
        return subprocess.run(
            ["which", cmd],
            capture_output=True,
            text=True
        ).returncode == 0
    
    def _start_monitoring(self) -> None:
        """Inicia hilo de monitoreo de tunnels."""
        if self._monitor_thread is None or not self._monitor_thread.is_alive():
            self._running = True
            self._monitor_thread = threading.Thread(target=self._monitor_tunnels, daemon=True)
            self._monitor_thread.start()
    
    def _monitor_tunnels(self) -> None:
        """Monitorea tunnels y elimina los que mueren."""
        while self._running:
            with self._lock:
                to_remove = []
                for tid, info in self.tunnels.items():
                    try:
                        os.kill(info.pid, 0)
                    except ProcessLookupError:
                        # Proceso muerto
                        to_remove.append(tid)
                    except Exception:
                        pass
                
                for tid in to_remove:
                    logger.info(f"[Tunnel] Proceso {tid} terminado, eliminando")
                    del self.tunnels[tid]
            
            time.sleep(5)
    
    def get_stats(self) -> Dict[str, Any]:
        """Estadisticas del servicio."""
        return {
            "cloudflare_available": self._command_exists("cloudflared"),
            "localtunnel_available": self._command_exists("npx"),
            "active_tunnels": len(self.tunnels),
            "tunnels": self.list_tunnels()["tunnels"]
        }
