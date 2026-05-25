# EduBot - Agente Escolar Inteligente

> **Asistente conversacional de trámites escolares y nutrición SMAE con RAG e IA local.**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/Licencia-MIT-green.svg)]()

## ¿Qué es EduBot?

EduBot es un asistente virtual que responde preguntas sobre **trámites escolares** (inscripciones, reinscripciones, becas, constancias, titulación) y **nutrición escolar basada en el SMAE** (Sistema Mexicano de Alimentos Equivalentes).

Todo funciona **100% local**: el modelo de lenguaje y los embeddings corren en tu computadora, sin depender de APIs externas ni conexión a Internet después de la primera descarga.

### ¿Por qué existe este proyecto?

- **Problema:** Los estudiantes pierden tiempo buscando información de trámites dispersa en PDFs y sitios web. Además, no tienen acceso fácil a información nutricional confiable basada en el SMAE.
- **Solución:** Un chatbot inteligente que responde con información exacta extraída de documentos oficiales, usando técnicas de RAG (Retrieval Augmented Generation) para no alucinar respuestas.

---

## 🚀 Características principales

| Característica | Descripción |
|----------------|-------------|
| **RAG local** | Recuperación semántica sobre documentos JSON de trámites y tablas SMAE |
| **IA 100% local** | Modelo `Qwen2-1.5B-Instruct` ejecutándose en GPU/CPU sin APIs externas |
| **Frontend premium** | Interfaz con glassmorphism, gradientes animados y microinteracciones GSAP |
| **Documentación académica** | Contenido LaTeX listo para pegar en Overleaf |

---

## 📁 Estructura del proyecto

```
edubot/
├── backend/
│   ├── main.py                 # API FastAPI (punto de entrada del backend)
│   ├── src/
│   │   └── rag_engine.py       # Motor de embeddings + búsqueda semántica
│   └── data/
│       ├── tramites.json       # Base de datos de trámites escolares
│       └── smae.json           # Tablas de nutrición SMAE
├── frontend/
│   ├── index.html              # Interfaz principal
│   ├── css/style.css           # Estilos glassmorphism
│   └── js/app.js               # Animaciones GSAP + lógica del chat
├── docs/
│   ├── contenido.tex           # Cuerpo del documento LaTeX
│   └── bibliografia.bib        # Referencias bibliográficas
├── requirements.txt            # Dependencias Python
└── start.sh                    # Script de inicio rápido (opcional)
```

### Guía rápida para el equipo de desarrollo

| Archivo | ¿Qué hace? | ¿Cuándo modificarlo? |
|---------|-----------|---------------------|
| `backend/main.py` | API FastAPI, endpoints `/chat`, `/stats`, carga del modelo LLM | Agregar endpoints, cambiar modelo, ajustar prompt del sistema |
| `backend/src/rag_engine.py` | Carga JSON, genera embeddings, búsqueda por similitud coseno | Agregar nuevos documentos, cambiar modelo de embeddings, ajustar top_k |
| `backend/data/*.json` | Fuentes de conocimiento (trámites y nutrición) | Actualizar información de trámites o tablas SMAE |
| `frontend/index.html` | Estructura visual del chat | Cambiar textos, agregar secciones UI |
| `frontend/css/style.css` | Estilos visuales (glassmorphism, animaciones) | Ajustar colores, tamaños, animaciones |
| `frontend/js/app.js` | Lógica del cliente: envía mensajes, recibe respuestas, animaciones | Cambiar URL del backend, agregar funcionalidades del chat |
| `docs/contenido.tex` | Contenido académico del proyecto | Actualizar secciones del documento LaTeX |

---

## ⚙️ Requisitos

- **Python 3.10+**
- **GPU NVIDIA con CUDA** (recomendado) o CPU
- **~4 GB de VRAM** para GPU / **~6 GB de RAM** para CPU
- **Conexión a Internet** (solo la primera vez para descargar modelos)

### Dependencias principales

Las dependencias están listadas en `requirements.txt`. Las más importantes son:

- `fastapi` + `uvicorn` — Servidor web y API
- `transformers` + `torch` — Modelo de lenguaje e inferencia
- `sentence-transformers` — Modelo de embeddings para RAG
- `numpy` — Operaciones numéricas

---

## 🛠️ Instalación

```bash
# 1. Clonar el repositorio
git clone git@github.com:tato1599/edubot.git
cd edubot

# 2. Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o: venv\Scripts\activate  # Windows

# 3. Instalar dependencias
pip install -r requirements.txt
```

---

## ▶️ Ejecución

### Opción A: Manual (desarrollo)

**1. Iniciar el backend**

```bash
cd edubot
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

> **Nota:** La primera vez descargará automáticamente:
> - `all-MiniLM-L6-v2` (~80 MB) para embeddings
> - `Qwen2-1.5B-Instruct` (~3 GB) para el chat
>
> La descarga inicial puede tardar 5–15 minutos según tu conexión. Los modelos se cachean para usos posteriores.

**2. Abrir el frontend**

Abre directamente en tu navegador:

```
edubot/frontend/index.html
```

O usa un servidor estático para evitar restricciones CORS:

```bash
cd edubot/frontend
python -m http.server 3000
```

Luego visita: [http://localhost:3000](http://localhost:3000)

### Opción B: Script de inicio rápido

```bash
./start.sh
```

*(Si existe y está configurado en tu entorno)*

---

## 💬 Cómo usar el chat

1. Haz clic en **"Iniciar conversación"**
2. Escribe tu pregunta sobre trámites o nutrición SMAE
3. EduBot responderá usando **únicamente** la información de los documentos JSON

### Ejemplos de preguntas

| Tema | Ejemplo de pregunta |
|------|---------------------|
| Trámites | "¿Qué necesito para inscribirme si soy extranjero?" |
| Reinscripción | "¿Cómo es el proceso de reinscripción?" |
| SMAE | "¿Cuántas calorías tiene una porción de fruta?" |
| Menús | "Recomiéndame un menú escolar para primaria" |
| Becas | "¿Qué becas hay por excelencia académica?" |

---

## 🌐 Compartir con compañeros (túnel público)

Para que tus compañeros vean el proyecto desde su celular o computadora, necesitas exponerlo a Internet. EduBot ahora puede servirse todo desde un solo puerto (frontend + backend juntos).

### Opción rápida: LocalTunnel (con npx)

```bash
# Desde la carpeta del proyecto
./expose.sh
```

Esto hace lo siguiente:
1. Inicia el backend en `localhost:8000`
2. Crea un túnel público gratuito con `localtunnel`
3. Te da una URL tipo `https://nombre-aleatorio.loca.lt`
4. **Copia esa URL y pásala a tus compañeros**

**Requisito:** tener `npx` instalado (viene con Node.js). Si no lo tienes:
```bash
# Instalar Node.js (incluye npx)
sudo apt update && sudo apt install -y nodejs npm
```

### Opción estable: Cloudflare Tunnel

```bash
./expose-cloudflare.sh
```

**Requisito:** instalar `cloudflared` primero:
```bash
# Linux (Debian/Ubuntu)
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb
```

Ventajas de Cloudflare:
- ✅ Más estable que localtunnel
- ✅ No caduca tan rápido
- ✅ Funciona sin crear cuenta

### ¿Qué verán tus compañeros?

Al abrir la URL, verán directamente la pantalla de bienvenida de EduBot con el botón **"Iniciar conversación"**. El chat funcionará completamente porque el backend y el frontend van juntos por el mismo túnel.

> ⚠️ **Importante:** mantén la terminal abierta mientras quieras que esté disponible. Presiona `Ctrl+C` para cerrar.

---

## 🏗️ Arquitectura técnica

```
Usuario
  │
  ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Frontend   │────▶│  FastAPI     │────▶│  RAG Engine     │
│  (HTML/CSS/ │     │  (/chat)     │     │  (Embeddings +  │
│   JS/GSAP)  │     │              │     │   Búsqueda)     │
└─────────────┘     └──────────────┘     └─────────────────┘
                                                │
                                                ▼
                                         ┌──────────────┐
                                         │  Documentos  │
                                         │  JSON        │
                                         │ (tramites /  │
                                         │  smae)       │
                                         └──────────────┘
                                                │
                                                ▼
                                         ┌──────────────┐
                                         │  Qwen2-1.5B  │
                                         │  Instruct    │
                                         │  (Local)     │
                                         └──────────────┘
```

### Flujo de una consulta

1. **Recuperación (RAG):** La pregunta del usuario se convierte en un embedding y se buscan los 3 documentos JSON más similares por similitud coseno.
2. **Generación:** Los documentos recuperados se inyectan en un *prompt* con formato de chat (`chat_template` de Qwen2).
3. **Inferencia local:** El modelo `Qwen2-1.5B-Instruct` genera la respuesta condicionada al contexto, sin conexión a Internet.

---

## 📝 Documentación LaTeX

Los archivos de documentación están en `docs/`:

- **`contenido.tex`**: Pégalo en el cuerpo de tu plantilla Overleaf (dentro de `\begin{document}` ... `\end{document}`).
- **`bibliografia.bib`**: Importa este archivo como bibliografía en Overleaf.

La documentación incluye: Resumen, Introducción, Marco Teórico (LLM, RAG, SMAE, FastAPI, GSAP), Diseño e Implementación, Resultados, Conclusiones y Trabajo Futuro.

---

## 🔧 Solución de problemas

### El backend no inicia
- Verifica que PyTorch con CUDA esté instalado:
  ```bash
  python -c "import torch; print(torch.cuda.is_available())"
  ```
- Si no hay GPU, el modelo correrá en CPU (más lento pero funcional).

### El frontend no conecta al backend
- Asegúrate de que el backend esté corriendo en `http://localhost:8000`.
- Si abres `index.html` directamente, puede haber problemas de CORS. Usa `python -m http.server`.
- Verifica que el frontend apunte a la URL correcta del backend en `frontend/js/app.js`.

### Respuestas lentas
- La primera consulta puede tardar porque el modelo "calienta" la GPU. Las siguientes son más rápidas.
- **Respuesta típica:** 2–5 segundos en GPU / 10–20 segundos en CPU.

### Errores de memoria (OOM)
- Si tu GPU tiene menos de 4 GB de VRAM, prueba corriendo en CPU.
- Reduce `max_new_tokens` en `backend/main.py` si es necesario.

---

## 👥 Guía para contribuir (equipo)

1. **Trabaja en una rama:**
   ```bash
   git checkout -b feature/nombre-de-tu-cambio
   ```

2. **Haz commits pequeños y descriptivos:**
   ```bash
   git add .
   git commit -m "feat: agrega endpoint de estadísticas de trámites"
   ```

3. **Actualiza los JSON de datos cuando sea necesario:**
   - Si cambias información de trámites, actualiza `backend/data/tramites.json`
   - Si cambias información del SMAE, actualiza `backend/data/smae.json`

4. **Prueba local antes de subir:**
   - Asegúrate de que el backend inicie sin errores.
   - Verifica que el frontend se conecte correctamente.
   - Prueba al menos 3 preguntas diferentes.

---

## 📋 Roadmap / Tareas pendientes

- [ ] Agregar más trámites escolares al JSON
- [ ] Implementar historial de conversaciones persistente
- [ ] Mejorar el prompt del sistema para respuestas más estructuradas
- [ ] Agregar soporte para subir documentos PDF al RAG
- [ ] Optimizar inferencia con `bitsandbytes` o `llama.cpp`
- [ ] Dockerizar el proyecto para despliegue fácil
- [ ] Tests automatizados para el RAG y los endpoints

---

## 📄 Créditos

- Modelo de lenguaje: [Qwen2-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2-1.5B-Instruct) (Alibaba Cloud)
- Embeddings: [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) (SentenceTransformers)
- Framework backend: [FastAPI](https://fastapi.tiangolo.com/) + [Transformers](https://huggingface.co/docs/transformers/)
- Animaciones: [GSAP](https://greensock.com/gsap/)

---

## 📜 Licencia

Este proyecto es de uso académico. Puedes usarlo, modificarlo y distribuirlo libremente mencionando la fuente.

---

> **¿Preguntas o problemas?** Abre un issue en GitHub o contacta al equipo de desarrollo.
