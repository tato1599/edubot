#!/bin/bash
# ──────────────────────────────────────────────────────────────
# Script para exponer EduBot a Internet mediante túnel
# Uso: ./expose.sh
# Requiere: Node.js con npx (npm install -g npx si no lo tienes)
# ──────────────────────────────────────────────────────────────

set -e

PORT=8000
TUNNEL_CMD="npx localtunnel --port $PORT"

echo "========================================"
echo "  EduBot - Exposición pública"
echo "========================================"
echo ""
echo "Este script va a:"
echo "  1. Iniciar el backend de EduBot en puerto $PORT"
echo "  2. Crear un túnel público con localtunnel"
echo "  3. Darte una URL para compartir con tus compañeros"
echo ""
echo "Presiona ENTER para continuar o Ctrl+C para cancelar..."
read

# Verificar que npx existe
if ! command -v npx &> /dev/null; then
    echo "❌ ERROR: npx no está instalado."
    echo "   Instálalo con: npm install -g npx"
    echo "   O instala Node.js desde: https://nodejs.org/"
    exit 1
fi

# Verificar que el entorno virtual de Python esté activo o pip esté disponible
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

# Función para limpiar al salir
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
echo "🌐 Creando túnel público..."
echo "   (La primera vez puede pedirte que abras un enlace y verifiques)"
echo ""

# Iniciar túnel
$TUNNEL_CMD &
TUNNEL_PID=$!

# Esperar a que localtunnel muestre la URL
sleep 5

# Mostrar información final
echo ""
echo "========================================"
echo "  ✅ EduBot está en línea!"
echo "========================================"
echo ""
echo "🌐 URL pública (comparte esta):"
# Intentar obtener la URL del túnel (localtunnel la imprime en stderr/stdout)
# La URL típica aparece como https://nombre-random.loca.lt
echo "   Esperando a que localtunnel genere la URL..."
echo "   (Si no aparece abajo, revisa las líneas anteriores)"
echo ""
echo "📋 Instrucciones para compartir:"
echo "   1. Copia la URL que aparece arriba (empieza con https://)"
echo "   2. Pásala a tus compañeros por WhatsApp/Discord/Slack"
echo "   3. Ellos abren la URL en su navegador y ven el chat"
echo ""
echo "⚠️  NOTAS:"
echo "   • Mantén esta terminal abierta mientras quieras que esté disponible"
echo "   • Presiona Ctrl+C para cerrar todo (backend + túnel)"
echo "   • La URL puede cambiar cada vez que reinicies este script"
echo ""

# Esperar indefinidamente
wait $TUNNEL_PID
