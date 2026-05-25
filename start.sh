#!/bin/bash
# Script de inicio rápido para EduBot

echo "====================================="
echo "  EduBot - Agente Escolar"
echo "====================================="
echo ""
echo "Iniciando backend en http://localhost:8000"
echo "(La primera vez descarga modelos, puede tardar 5-15 min)"
echo ""

cd "$(dirname "$0")"
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
