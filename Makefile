.PHONY: help install dev test docker-build docker-up docker-down clean

help:
	@echo "EduBot v2.0 - Comandos disponibles:"
	@echo ""
	@echo "  make install      - Instalar dependencias"
	@echo "  make dev          - Iniciar en modo desarrollo"
	@echo "  make test         - Ejecutar tests"
	@echo "  make docker-build - Construir imagen Docker"
	@echo "  make docker-up    - Iniciar con Docker Compose"
	@echo "  make docker-down  - Detener Docker Compose"
	@echo "  make clean        - Limpiar cache y archivos temporales"

install:
	pip install -r requirements.txt

dev:
	python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

test:
	python -m pytest backend/tests/ -v

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf backend/chroma_db/*.lock
