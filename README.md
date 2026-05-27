# EduBot v2.0 - Agente Escolar Inteligente

> **Asistente conversacional de tramites escolares y nutricion SMAE con RAG vectorial e IA local.**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20DB-purple)](https://www.trychroma.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://docker.com/)
[![License](https://img.shields.io/badge/Licencia-MIT-green.svg)]()

## ¿Que es EduBot?

EduBot es un asistente virtual que responde preguntas sobre **tramites escolares** (inscripciones, reinscripciones, becas, constancias, titulacion) y **nutricion escolar basada en el SMAE** (Sistema Mexicano de Alimentos Equivalentes).

Todo funciona **100% local**: el modelo de lenguaje y los embeddings corren en tu computadora, sin depender de APIs externas.

### Arquitectura v2.0 (Enterprise)

- **Base de datos vectorial ChromaDB** con persistencia en disco e indice HNSW
- **Backend modular** con servicios separados (RAG, LLM), middlewares, logging JSON
- **Rate limiting** y request tracing
- **Docker + Docker Compose** listo para produccion
- **Tests automatizados** con pytest
- **Configuracion por variables de entorno**

---

## Estructura del proyecto

```
edubot/
├── backend/
│   ├── app/
│   │   ├── core/           # Configuracion, logging
│   │   ├── models/         # Schemas Pydantic
│   │   ├── services/       # RAG Service, LLM Service
│   │   ├── api/            # Rutas, middlewares
│   │   └── utils/          # Query expansion
│   ├── data/               # Fuentes de conocimiento JSON
│   ├── chroma_db/          # Persistencia ChromaDB
│   ├── tests/              # Tests con pytest
│   └── main.py             # Entry point FastAPI
├── frontend/               # UI HTML/CSS/JS
├── docs/                   # Documentacion LaTeX
├── Dockerfile              # Multi-stage build
├── docker-compose.yml      # Orquestacion completa
├── nginx.conf              # Reverse proxy
├── Makefile                # Comandos estandar
├── requirements.txt
├── .env.example            # Configuracion de ejemplo
└── start.sh                # Inicio rapido
```

---

## Requisitos

- **Python 3.11+**
- **GPU NVIDIA con CUDA** (recomendado) o CPU
- **~2-3 GB de VRAM** para GPU (3B en 4-bit) / **~6 GB de RAM** para CPU
- **Docker** (opcional, para despliegue)

---

## Instalacion

### Opcion A: Local (desarrollo)

```bash
# 1. Clonar
python -m venv venv
source venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar (opcional)
cp .env.example .env
# Editar .env segun necesites

# 4. Iniciar
./start.sh
# o: make dev
```

### Opcion B: Docker (produccion)

```bash
# Todo en un comando
./docker-start.sh

# O manual:
docker-compose build
docker-compose up -d
```

Accede a:
- **App**: http://localhost
- **API**: http://localhost:8000
- **Health**: http://localhost:8000/health

---

## Uso

### Comandos Make

```bash
make install      # Instalar dependencias
make dev          # Modo desarrollo con reload
make test         # Ejecutar tests
make docker-build # Construir imagen Docker
make docker-up    # Iniciar con Docker
make clean        # Limpiar cache
```

### Tests

```bash
./test.sh
# o: make test
```

---

## API Endpoints

| Endpoint | Metodo | Descripcion |
|----------|--------|-------------|
| `/` | GET | Frontend |
| `/health` | GET | Estado de carga con progreso |
| `/status` | GET | Estado completo del sistema |
| `/stats` | GET | Estadisticas del RAG |
| `/chat` | POST | Chat sincrono |
| `/chat/stream` | POST | Chat con streaming SSE |
| `/api/*` | - | Rutas con prefijo `/api/` |

### Headers de respuesta

Todas las respuestas incluyen:
- `X-Request-ID`: ID unico de traza
- `X-Response-Time`: Tiempo de respuesta en ms
- `X-RateLimit-Limit`: Limite de peticiones
- `X-RateLimit-Remaining`: Peticiones restantes

---

## Configuracion

Variables de entorno (ver `.env.example`):

| Variable | Default | Descripcion |
|----------|---------|-------------|
| `MODEL_NAME` | Qwen/Qwen2.5-3B-Instruct | Modelo de lenguaje (3B para GPUs de 8GB) |
| `LOAD_IN_4BIT` | true | Quantization 4-bit (NF4) |
| `TEMPERATURE` | 0.2 | Creatividad (0-1) |
| `TOP_K_RETRIEVAL` | 5 | Documentos recuperados |
| `ENABLE_QUERY_CACHE` | true | Cache de queries |
| `RATE_LIMIT_REQUESTS` | 60 | Peticiones/minuto |
| `LOG_FORMAT` | json | Formato de logs |

---

## Docker

### Estructura

```
nginx (puerto 80)
  └── proxy a edubot:8000
      
edubot (puerto 8000)
  ├── FastAPI + LLM
  └── ChromaDB persistido en volumen
```

### Volumenes

- `./backend/chroma_db`: Persistencia de embeddings
- `huggingface_cache`: Cache de modelos (no se re-descargan)
- `./backend/data`: Datos JSON (actualizables sin rebuild)

---

## Caracteristicas tecnicas v2.0

### RAG (Retrieval-Augmented Generation)

- **ChromaDB** con indice HNSW optimizado (`construction_ef=128`, `M=16`)
- **Persistencia en disco**: embeddings no se recalculan al reiniciar
- **Cache de queries**: respuestas frecuentes son instantaneas
- **Batch indexing**: indexa 100 documentos por lote
- **Filtrado por fuente**: busca solo en `tramites`, `smae`, etc.
- **Boosting semantico**: corrige confusion entre semestres (primer vs segundo)

### LLM

- **Qwen2.5-3B-Instruct** con quantization 4-bit (NF4)
- **Streaming SSE**: respuestas token por token
- **Historial de conversacion**: mantiene contexto (ultimos 6 mensajes)
- **Query expansion**: sinonimos automaticos para mejor recuperacion
- **Bloqueo de idioma**: sanitizacion automatica que fuerza respuestas 100% en espanol

### Middlewares

- **Request logging**: cada peticion con ID, timing, status
- **Rate limiting**: 60 peticiones/minuto por IP
- **CORS**: configurado para multiples origenes
- **Exception handlers**: errores del servidor traducidos automaticamente a espanol

### Tunneling / Compartir

- **Cloudflare Tunnel** integrado (recomendado, mas estable)
- **LocalTunnel** como alternativa (con npx)
- **API REST** para gestionar tunnels desde el frontend
- **Panel de compartir** en la UI con copiar al portapapeles
- **Scripts automatizados** (`scripts/tunnel.sh`)

---

## Compartir con companeros (Tunneling)

### Opcion 1: Desde el Frontend (recomendado)

1. Abre EduBot en tu navegador
2. Haz click en el icono **Compartir** (🔗) en la esquina superior derecha
3. Click en **"Crear Tunnel"**
4. Espera 5-15 segundos
5. La URL publica aparece — **copiala y compartela**

### Opcion 2: Script de linea de comandos

```bash
# Modo interactivo (menu)
./scripts/tunnel.sh

# Crear tunnel directamente
./scripts/tunnel.sh create cloudflare
./scripts/tunnel.sh create localtunnel

# Listar tunnels activos
./scripts/tunnel.sh list

# Cerrar todos los tunnels
./scripts/tunnel.sh close all

# Verificar dependencias
./scripts/tunnel.sh status
```

### Opcion 3: Scripts legacy

```bash
# Cloudflare (mas estable)
./expose-cloudflare.sh

# LocalTunnel (alternativa)
./expose.sh
```

### Instalar dependencias de tunneling

**Cloudflare (recomendado):**
```bash
# Linux
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# macOS
brew install cloudflared

# Windows
# Descarga desde: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
```

**LocalTunnel (alternativa):**
```bash
# Requiere Node.js
npm install -g localtunnel
# o usa npx directamente
```

### API de Tunneling

| Endpoint | Metodo | Descripcion |
|----------|--------|-------------|
| `/api/tunnel/create?provider=cloudflare` | POST | Crear tunnel |
| `/api/tunnel/close/{id}` | POST | Cerrar tunnel |
| `/api/tunnel/list` | GET | Listar activos |
| `/api/tunnel/stats` | GET | Estadisticas |
| `/api/tunnel/close-all` | POST | Cerrar todos |

---

## Bloqueo de idioma (Espanol 100%)

EduBot esta configurado para responder **exclusivamente en espanol**, incluso si el usuario escribe en otro idioma. Este comportamiento se garantiza mediante tres mecanismos:

1. **System prompt estricto**: instrucciones explicitas al modelo para nunca usar ingles ni otros idiomas.
2. **Sanitizacion de respuestas**: heuristica en el backend que detecta texto en ingles/portugues/frances y lo reemplaza automaticamente por una respuesta predefinida en espanol.
3. **Exception handlers en espanol**: errores del servidor (404, 422, 500, etc.) se devuelven en espanol en lugar de ingles.

Si el modelo responde en otro idioma por error, el frontend recibe un evento de `correction` que reemplaza el mensaje instantaneamente.

---

## Solucion de problemas

### El backend no inicia
```bash
# Verificar GPU
python -c "import torch; print(torch.cuda.is_available())"

# Sin GPU, usar CPU
export DEVICE=cpu
export LOAD_IN_4BIT=false
```

### ChromaDB bloqueado
```bash
# Eliminar lock files
make clean
rm -rf backend/chroma_db/*.lock
```

### Modelo muy lento
```bash
# Reducir tokens
export MAX_NEW_TOKENS=200

# O usar modelo mas pequeño
export MODEL_NAME=Qwen/Qwen2-1.5B-Instruct
```

---

## Roadmap

- [x] Base de datos vectorial (ChromaDB)
- [x] Arquitectura modular (services, api, core)
- [x] Docker + Docker Compose
- [x] Tests automatizados
- [x] Rate limiting + logging
- [x] Configuracion por .env
- [ ] Soporte para subir PDFs al RAG
- [ ] Historial persistente de conversaciones (SQLite/ChromaDB)
- [ ] Multi-modelo (seleccionar modelo por endpoint)
- [ ] Panel de administracion web
- [ ] Metrics Prometheus

---

## Creditos

- Modelo: [Qwen2.5-3B-Instruct](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct)
- Embeddings: [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- Vector DB: [ChromaDB](https://www.trychroma.com/)
- Framework: [FastAPI](https://fastapi.tiangolo.com/) + [Transformers](https://huggingface.co/docs/transformers/)

---

## Licencia

Uso academico. Puedes usarlo, modificarlo y distribuirlo libremente mencionando la fuente.
