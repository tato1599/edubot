#!/bin/bash
# Script de inicio rapido para el Agente Escolar Inteligente v2.0

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "  EduBot v2.0 - Agente Escolar"
echo "========================================"

# Detectar si estamos en entorno virtual
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -d "venv" ]; then
        echo "[INFO] Activando entorno virtual..."
        source venv/bin/activate
    else
        echo "[WARN] No se encontro entorno virtual. Se recomienda crear uno."
    fi
fi

# Verificar dependencias
echo "[INFO] Verificando dependencias..."
python -c "import fastapi, chromadb, transformers" 2>/dev/null || {
    echo "[INFO] Instalando dependencias..."
    pip install -r requirements.txt
}

# Verificar datos
echo "[INFO] Verificando datos..."
if [ ! -d "backend/data" ]; then
    echo "[ERROR] Directorio backend/data no encontrado"
    exit 1
fi

echo "[INFO] Iniciando servidor FastAPI..."
echo "[INFO] API Docs: http://localhost:8000/docs (modo debug)"
echo "[INFO] Frontend: http://localhost:8000/"
echo "========================================"

# Iniciar con uvicorn
python -m uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload
