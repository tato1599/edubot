#!/bin/bash
# Script para construir y ejecutar con Docker

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "  Docker Build & Run - EduBot v2.0"
echo "========================================"

# Crear .env si no existe
if [ ! -f ".env" ]; then
    echo "[INFO] Creando .env desde ejemplo..."
    cp .env.example .env
fi

echo "[INFO] Construyendo imagen..."
docker-compose build

echo "[INFO] Iniciando servicios..."
docker-compose up -d

echo "========================================"
echo "  Servicios iniciados:"
echo "  - App:     http://localhost:8000"
echo "  - Nginx:   http://localhost:80"
echo "  - Health:  http://localhost:8000/health"
echo "========================================"
echo ""
echo "Logs: docker-compose logs -f"
echo "Stop: docker-compose down"
