#!/bin/bash
# Script para ejecutar tests

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "  Ejecutando Tests - EduBot"
echo "========================================"

# Activar venv si existe
if [ -z "$VIRTUAL_ENV" ] && [ -d "venv" ]; then
    source venv/bin/activate
fi

# Verificar pytest
python -c "import pytest" 2>/dev/null || {
    echo "[INFO] Instalando pytest..."
    pip install pytest pytest-asyncio httpx
}

echo "[INFO] Ejecutando tests..."
python -m pytest backend/tests/ -v "$@"

echo "========================================"
echo "  Tests completados"
echo "========================================"
