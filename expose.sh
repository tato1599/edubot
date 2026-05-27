#!/bin/bash
# ──────────────────────────────────────────────────────────────
# Exponer EduBot con LocalTunnel (alternativa)
# Uso: ./expose.sh
# ──────────────────────────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/scripts/tunnel.sh" ]; then
    exec "$SCRIPT_DIR/scripts/tunnel.sh" create localtunnel
else
    echo "❌ Error: scripts/tunnel.sh no encontrado"
    echo "   Ejecuta desde el directorio raiz del proyecto"
    exit 1
fi
