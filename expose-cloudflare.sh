#!/bin/bash
# ──────────────────────────────────────────────────────────────
# Script para exponer EduBot con Cloudflare Tunnel (más estable)
# Uso: ./expose-cloudflare.sh
# Requiere: instalar cloudflared primero
#   Linux: curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb && sudo dpkg -i cloudflared.deb
#   Otras opciones: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
# ──────────────────────────────────────────────────────────────

set -e

PORT=8000

echo "========================================"
echo "  EduBot - Exposición con Cloudflare"
echo "========================================"
echo ""

# Verificar cloudflared
if ! command -v cloudflared &> /dev/null; then
    echo "❌ ERROR: cloudflared no está instalado."
    echo ""
    echo "📥 Para instalar en Linux:"
    echo "   curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb"
    echo "   sudo dpkg -i cloudflared.deb"
    echo ""
    echo "📥 Otras plataformas: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/"
    exit 1
fi

# Verificar Python
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo "❌ ERROR: Python no está instalado."
    exit 1
fi

PYTHON_CMD=$(command -v python3 || command -v python)

echo "🚀 Iniciando backend de EduBot en puerto $PORT..."
cd "$(dirname "$0")"

# Iniciar backend en segundo plano
$PYTHON_CMD -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT &
BACKEND_PID=$!

cleanup() {
    echo ""
    echo "🛑 Cerrando backend (PID: $BACKEND_PID)..."
    kill $BACKEND_PID 2>/dev/null || true
    wait $BACKEND_PID 2>/dev/null || true
    echo "✅ Backend cerrado."
    exit
}
trap cleanup INT TERM EXIT

# Esperar a que el backend esté listo
echo "⏳ Esperando a que el backend esté listo..."
for i in {1..30}; do
    if curl -s http://localhost:$PORT/ > /dev/null 2>&1; then
        echo "✅ Backend listo!"
        break
    fi
    sleep 1
done

echo ""
echo "🌐 Creando túnel con Cloudflare..."
echo ""

# Iniciar túnel de Cloudflare (gratuito, sin necesidad de cuenta)
cloudflared tunnel --url http://localhost:$PORT &
TUNNEL_PID=$!

echo ""
echo "========================================"
echo "  ✅ EduBot está en línea!"
echo "========================================"
echo ""
echo "🌐 Tu URL pública aparece arriba (busca la línea que dice https://...)"
echo ""
echo "⚠️  Presiona Ctrl+C para cerrar todo"
echo ""

wait $TUNNEL_PID
