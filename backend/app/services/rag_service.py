"""
Servicio de RAG (Retrieval-Augmented Generation) con ChromaDB.
Version enterprise con persistencia, caching y batch processing optimizado.
"""

import json
import os
import time
import hashlib
from typing import List, Dict, Any, Optional
from functools import lru_cache

import numpy as np

# Embeddings
try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False

# ChromaDB
try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

import logging

from backend.app.core.config import settings
from backend.app.core.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


class RAGService:
    """
    Servicio enterprise de Recuperacion Augmentada por Generacion.
    
    Caracteristicas:
    - Persistencia en ChromaDB (no recalcula embeddings al iniciar)
    - Indice HNSW para busqueda aproximada rapida
    - Cache de queries frecuentes
    - Filtrado por fuente
    - Agregacion de documentos en tiempo real
    """
    
    def __init__(
        self,
        data_dir: Optional[str] = None,
        persist_dir: Optional[str] = None,
        collection_name: Optional[str] = None,
    ):
        self.data_dir = data_dir or settings.data_dir
        self.persist_dir = persist_dir or settings.chroma_dir
        self.collection_name = collection_name or settings.chroma_collection_name
        
        os.makedirs(self.persist_dir, exist_ok=True)
        
        self.documents: List[Dict[str, Any]] = []
        self.model = None
        self.collection = None
        self.client = None
        self._query_cache: Dict[str, tuple] = {}
        
        self._load_documents()
        self._build_index()
    
    # ───────────────────────────────────────────────
    # Carga de Documentos
    # ───────────────────────────────────────────────
    
    def _load_documents(self) -> None:
        """Carga todos los JSON desde data_dir."""
        loaders = [
            ("tramites.json", self._load_tramites),
            ("reticula_isc.json", self._load_reticula),
            ("comedores.json", self._load_comedores),
            ("reglamento_estudiantes.json", self._load_reglamento),
            ("smae.json", self._load_smae),
        ]
        
        for filename, loader in loaders:
            filepath = os.path.join(self.data_dir, filename)
            if os.path.exists(filepath):
                try:
                    loader(filepath)
                except Exception as e:
                    logger.error(f"Error cargando {filename}: {e}")
        
        # Deduplicar IDs para evitar conflictos en ChromaDB
        seen_ids = set()
        for doc in self.documents:
            original_id = doc["id"]
            counter = 1
            while doc["id"] in seen_ids:
                doc["id"] = f"{original_id}_{counter}"
                counter += 1
            seen_ids.add(doc["id"])
        
        logger.info(f"[RAG] {len(self.documents)} documentos cargados desde JSON")
    
    def _load_tramites(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for doc in data.get("documentos", []):
            self.documents.append({
                "id": doc["id"],
                "categoria": doc["categoria"],
                "titulo": doc["titulo"],
                "contenido": doc["contenido"],
                "keywords": doc.get("keywords", []),
                "fuente": "tramites"
            })
    
    def _load_reticula(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        carrera = data.get("carrera", {})
        
        # Info general
        self.documents.append({
            "id": "isc_general",
            "categoria": "reticula_isc",
            "titulo": f"{carrera.get('nombre', 'ISC')} - {carrera.get('institucion', 'TecNM')}",
            "contenido": (
                f"Carrera: {carrera.get('nombre', '')}. "
                f"Plan: {carrera.get('clave_plan', '')}. "
                f"Total materias: {carrera.get('total_materias', '')}. "
                f"Creditos totales: {carrera.get('total_creditos_plan', '')}. "
                f"Estructura: {json.dumps(carrera.get('estructura_creditos', {}))}"
            ),
            "keywords": ["reticula", "isc", "sistemas computacionales", "plan estudios", "ITCJ", "TecNM"],
            "fuente": "reticula_isc"
        })
        
        # Materias por semestre
        for sem in data.get("semestres", []):
            sem_num = sem.get("numero", 0)
            for mat in sem.get("materias", []):
                prereqs = ", ".join(mat.get("prerequisitos", [])) if mat.get("prerequisitos") else "Ninguno"
                contenido = (
                    f"Materia: {mat['nombre']}. Clave: {mat['clave']}. "
                    f"Semestre: {sem_num}. Horas teoria: {mat.get('horas_teoria', 0)}. "
                    f"Horas practica: {mat.get('horas_practica', 0)}. "
                    f"Creditos: {mat.get('creditos', 0)}. Area: {mat.get('area', '')}. "
                    f"Prerequisitos: {prereqs}."
                )
                self.documents.append({
                    "id": f"isc_mat_{mat['clave']}",
                    "categoria": "reticula_isc",
                    "titulo": f"ISC - {mat['nombre']} ({mat['clave']})",
                    "contenido": contenido,
                    "keywords": [mat['nombre'].lower(), mat['clave'].lower(), f"semestre {sem_num}", mat.get('area', '').lower()],
                    "fuente": "reticula_isc"
                })
            
            nombres_mats = ", ".join([m['nombre'] for m in sem.get("materias", [])])
            self.documents.append({
                "id": f"isc_sem_{sem_num}",
                "categoria": "reticula_isc",
                "titulo": f"ISC - Semestre {sem_num}",
                "contenido": (
                    f"Semestre {sem_num} de Ingenieria en Sistemas Computacionales. "
                    f"Materias: {sem.get('total_materias', 0)}. "
                    f"Creditos: {sem.get('creditos_semestre', 0)}. "
                    f"Incluye: {nombres_mats}."
                ),
                "keywords": [f"semestre {sem_num}", "materias", "plan", "isc"],
                "fuente": "reticula_isc"
            })
        
        # Actividades integrales
        for act in data.get("actividades_integrales", []):
            self.documents.append({
                "id": f"isc_act_{act['nombre'].replace(' ', '_').lower()}",
                "categoria": "reticula_isc",
                "titulo": f"ISC - {act['nombre']}",
                "contenido": (
                    f"Actividad: {act['nombre']}. Creditos: {act['creditos']}. "
                    f"Requisito: {act['requisito']}. "
                    f"Semestre recomendado: {act['semestre_recomendado']}. "
                    f"Descripcion: {act['descripcion']}"
                ),
                "keywords": [act['nombre'].lower(), "creditos", "requisitos", "semestre", "isc"],
                "fuente": "reticula_isc"
            })
        
        # Recomendaciones
        recs = data.get("recomendaciones_plan", {})
        if recs.get("reglas_generales"):
            self.documents.append({
                "id": "isc_recomendaciones",
                "categoria": "reticula_isc",
                "titulo": "ISC - Recomendaciones y mejor plan de estudios",
                "contenido": (
                    f"Descripcion: {recs.get('descripcion', '')}. "
                    f"Reglas: {' | '.join(recs.get('reglas_generales', []))}. "
                    f"Plan: {recs.get('mejor_plan_completo', '')}"
                ),
                "keywords": ["plan", "recomendaciones", "estrategia", "carga", "semestre", "isc"],
                "fuente": "reticula_isc"
            })
        
        # Objetivos
        obj = data.get("objetivos_carrera", {})
        if obj.get("objetivo_general"):
            self.documents.append({
                "id": "isc_objetivos",
                "categoria": "reticula_isc",
                "titulo": "ISC - Objetivos y perfil de egreso",
                "contenido": (
                    f"Objetivo: {obj.get('objetivo_general', '')}. "
                    f"Educativos: {' | '.join(obj.get('objetivos_educacionales', []))}. "
                    f"Perfil: {' | '.join(obj.get('perfil_egreso', []))}"
                ),
                "keywords": ["objetivos", "perfil egreso", "competencias", "isc", "egresado"],
                "fuente": "reticula_isc"
            })
    
    def _load_comedores(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        for lugar in data.get("lugares_comida", []):
            menu_items = []
            for item in lugar.get("menu", []):
                desc = item.get("descripcion", "")
                if item.get("opciones"):
                    desc += f" Opciones: {', '.join(item['opciones'])}."
                if item.get("incluye"):
                    desc += f" Incluye: {', '.join(item['incluye'])}."
                menu_items.append(f"{item['nombre']}: {desc}")
            
            contenido = f"Lugar: {lugar['nombre']}. Ubicacion: {lugar.get('ubicacion', 'No especificada')}. Tipo: {lugar.get('tipo', 'No especificado')}. "
            if menu_items:
                contenido += f"Menu: {' | '.join(menu_items)}. "
            if lugar.get("nota"):
                contenido += f"Nota: {lugar['nota']}. "
            if lugar.get("estado"):
                contenido += f"Estado: {lugar['estado']}. "
            
            self.documents.append({
                "id": f"comedor_{lugar['id']}",
                "categoria": "comedores",
                "titulo": f"Comida - {lugar['nombre']}",
                "contenido": contenido,
                "keywords": [
                    lugar['nombre'].lower(), "comida", "comer", "restaurante",
                    "snack", "menu", "tecnm", "itcj", "campus"
                ],
                "fuente": "comedores"
            })
        
        for i, rec in enumerate(data.get("recomendaciones_generales", [])):
            self.documents.append({
                "id": f"comedor_rec_{i}",
                "categoria": "comedores",
                "titulo": "Recomendaciones de comida en el TecNM ITCJ",
                "contenido": rec,
                "keywords": ["comida", "comer", "restaurante", "recomendacion", "tecnm", "itcj"],
                "fuente": "comedores"
            })
    
    def _load_reglamento(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for doc in data.get("documentos", []):
            self.documents.append({
                "id": doc["id"],
                "categoria": doc["categoria"],
                "titulo": doc["titulo"],
                "contenido": doc["contenido"],
                "keywords": doc.get("keywords", ["reglamento", "estudiantes", "tecnm"]),
                "fuente": "reglamento_estudiantes"
            })
    
    def _load_smae(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        for grupo in data.get("grupos", []):
            nombre = grupo.get("nombre", "")
            alimentos = grupo.get("alimentos", [])[:15]
            
            alimentos_texto = []
            for a in alimentos:
                alimentos_texto.append(
                    f"{a['nombre']}: {a['cantidad']} {a['unidad']} = "
                    f"{a['energia_kcal']} kcal, {a['proteina_g']}g proteina, "
                    f"{a['lipidos_g']}g grasa, {a['hidratos_carbono_g']}g carbohidratos"
                )
            
            self.documents.append({
                "id": f"smae_grupo_{nombre.replace(' ', '_').lower()}",
                "categoria": "smae",
                "titulo": f"SMAE - {nombre}",
                "contenido": (
                    f"Grupo SMAE: {nombre}. Total: {len(grupo.get('alimentos', []))}. "
                    f"Comunes: {' | '.join(alimentos_texto)}."
                ),
                "keywords": [nombre.lower(), "smae", "alimentos", "nutricion", "porcion", "calorias"],
                "fuente": "smae"
            })
        
        dieta = data.get("recomendaciones_dieta_estudiantil", {})
        
        if dieta.get("principios"):
            self.documents.append({
                "id": "smae_dieta_principios",
                "categoria": "smae",
                "titulo": "SMAE - Principios de dieta saludable",
                "contenido": f"Consejos para estudiantes: {' | '.join(dieta['principios'])}",
                "keywords": ["dieta", "estudiante", "economico", "saludable", "nutricion", "smae"],
                "fuente": "smae"
            })
        
        if dieta.get("lista_compras_economica"):
            self.documents.append({
                "id": "smae_dieta_compras",
                "categoria": "smae",
                "titulo": "SMAE - Lista de compras economica",
                "contenido": f"Alimentos economicos: {' | '.join(dieta['lista_compras_economica'])}",
                "keywords": ["lista compras", "economico", "estudiante", "nutricion"],
                "fuente": "smae"
            })
        
        for menu in dieta.get("menus_ejemplo_economicos", []):
            self.documents.append({
                "id": f"smae_menu_{menu['nombre'].replace(' ', '_').lower()}",
                "categoria": "smae",
                "titulo": f"SMAE - {menu['nombre']}",
                "contenido": (
                    f"{menu['nombre']}. Costo: {menu['costo_estimado']}. "
                    f"Desayuno: {menu['desayuno']} Comida: {menu['comida']} "
                    f"Cena: {menu['cena']} {menu.get('colacion', '')}"
                ),
                "keywords": ["menu", "economico", "estudiante", "desayuno", "comida", "cena"],
                "fuente": "smae"
            })
        
        if dieta.get("snacks_saludables_baratos"):
            self.documents.append({
                "id": "smae_dieta_snacks",
                "categoria": "smae",
                "titulo": "SMAE - Snacks saludables y baratos",
                "contenido": f"Snacks: {' | '.join(dieta['snacks_saludables_baratos'])}",
                "keywords": ["snack", "botana", "saludable", "barato", "estudiante"],
                "fuente": "smae"
            })
        
        if dieta.get("alimentos_a_evitar_o_limitar"):
            self.documents.append({
                "id": "smae_dieta_evitar",
                "categoria": "smae",
                "titulo": "SMAE - Alimentos a evitar",
                "contenido": f"Evitar: {' | '.join(dieta['alimentos_a_evitar_o_limitar'])}",
                "keywords": ["evitar", "limitar", "saludable", "estudiante", "nutricion"],
                "fuente": "smae"
            })
    
    # ───────────────────────────────────────────────
    # Indexacion
    # ───────────────────────────────────────────────
    
    def _build_index(self) -> None:
        """Construye o carga el indice vectorial."""
        if not ST_AVAILABLE:
            logger.warning("[RAG] sentence-transformers no disponible. Keyword matching only.")
            return
        
        logger.info("[RAG] Cargando modelo de embeddings...")
        start = time.time()
        self.model = SentenceTransformer(settings.embedding_model)
        logger.info(f"[RAG] Modelo cargado en {time.time()-start:.2f}s")
        
        if not CHROMA_AVAILABLE:
            logger.warning("[RAG] ChromaDB no disponible. Fallback a memoria.")
            self._build_index_memory()
            return
        
        logger.info(f"[RAG] Inicializando ChromaDB en: {self.persist_dir}")
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={
                "hnsw:space": "cosine",
                "hnsw:construction_ef": 128,
                "hnsw:search_ef": 128,
                "hnsw:M": 16,
            }
        )
        
        existing = self.collection.count()
        
        if existing == 0:
            logger.info(f"[RAG] Indexando {len(self.documents)} documentos en ChromaDB...")
            self._index_batch()
        elif existing != len(self.documents):
            logger.info(f"[RAG] Reconstruyendo indice: {existing} -> {len(self.documents)}")
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={
                    "hnsw:space": "cosine",
                    "hnsw:construction_ef": 128,
                    "hnsw:search_ef": 128,
                    "hnsw:M": 16,
                }
            )
            self._index_batch()
        else:
            logger.info(f"[RAG] {existing} documentos cargados desde ChromaDB (persistencia)")
    
    def _index_batch(self) -> None:
        """Indexa documentos por lotes para eficiencia."""
        batch_size = settings.chroma_batch_size
        total = len(self.documents)
        
        for i in range(0, total, batch_size):
            batch = self.documents[i:i+batch_size]
            ids = [d["id"] for d in batch]
            texts = [f"{d['titulo']}. {d['contenido']} {' '.join(d.get('keywords', []))}" for d in batch]
            metadatas = [{"categoria": d["categoria"], "fuente": d["fuente"], "titulo": d["titulo"]} for d in batch]
            
            embeddings = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True).tolist()
            
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=texts
            )
            
            logger.info(f"[RAG] Indexados {min(i+batch_size, total)}/{total}")
        
        logger.info(f"[RAG] Indice ChromaDB construido: {total} documentos")
    
    def _build_index_memory(self) -> None:
        """Fallback: embeddings en memoria con numpy."""
        texts = [f"{d['titulo']}. {d['contenido']} {' '.join(d.get('keywords', []))}" for d in self.documents]
        self.embeddings = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        logger.info("[RAG] Indice en memoria construido")
    
    # ───────────────────────────────────────────────
    # Busqueda
    # ───────────────────────────────────────────────
    
    def search(
        self,
        query: str,
        top_k: int = None,
        fuente: Optional[str] = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Busca documentos relevantes.
        
        Args:
            query: Texto de busqueda
            top_k: Numero de resultados (default: config)
            fuente: Filtrar por fuente (tramites, smae, etc.)
            use_cache: Usar cache de queries
        """
        top_k = top_k or settings.top_k_retrieval
        
        # Cache
        if use_cache and settings.enable_query_cache:
            cache_key = hashlib.md5(f"{query}:{top_k}:{fuente}".encode()).hexdigest()
            if cache_key in self._query_cache:
                return self._query_cache[cache_key]
        
        if CHROMA_AVAILABLE and self.collection is not None:
            results = self._search_chroma(query, top_k, fuente)
        elif ST_AVAILABLE and hasattr(self, 'embeddings'):
            results = self._search_embedding(query, top_k)
        else:
            results = self._search_keyword(query, top_k)
        
        if use_cache and settings.enable_query_cache:
            self._query_cache[cache_key] = results
            # Limitar cache
            if len(self._query_cache) > settings.query_cache_size:
                self._query_cache.pop(next(iter(self._query_cache)))
        
        return results
    
    def _search_chroma(self, query: str, top_k: int, fuente: Optional[str]) -> List[Dict[str, Any]]:
        query_embedding = self.model.encode([query]).tolist()
        where_filter = {"fuente": fuente} if fuente else None
        
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k * 2,
            where=where_filter,
            include=["metadatas", "documents", "distances"]
        )
        
        similarities = [1.0 - d for d in results["distances"][0]]
        similarities = self._apply_semantic_boost(query, results["ids"][0], similarities)
        
        indexed = list(zip(results["ids"][0], similarities, results["metadatas"][0]))
        indexed.sort(key=lambda x: x[1], reverse=True)
        
        output = []
        for doc_id, score, _ in indexed[:top_k]:
            doc = next((d for d in self.documents if d["id"] == doc_id), None)
            if doc:
                d = doc.copy()
                d["score"] = float(score)
                output.append(d)
        return output
    
    def _search_embedding(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        from sklearn.metrics.pairwise import cosine_similarity
        query_emb = self.model.encode([query], convert_to_numpy=True)
        sims = cosine_similarity(query_emb, self.embeddings)[0]
        sims = self._apply_semantic_boost(query, [d["id"] for d in self.documents], sims.tolist())
        sims = np.array(sims)
        
        top_idx = np.argsort(sims)[::-1][:top_k]
        return [{**self.documents[i].copy(), "score": float(sims[i])} for i in top_idx]
    
    def _search_keyword(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        words = set(query.lower().split())
        scored = []
        for doc in self.documents:
            score = 0
            for kw in doc.get("keywords", []):
                if any(w in kw.lower() or kw.lower() in w for w in words):
                    score += 2
            for w in words:
                if w in doc["titulo"].lower():
                    score += 1.5
                if w in doc["contenido"].lower():
                    score += 0.5
            scored.append((score, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{**doc.copy(), "score": score} for score, doc in scored[:top_k]]
    
    def _apply_semantic_boost(self, query: str, doc_ids: List[str], similarities: List[float]) -> List[float]:
        import re
        q = query.lower()
        
        ordinal_map = {
            r'\bprimer\b|\bprimero\b|1er|1°|1º': 1,
            r'\bsegundo\b|2do|2°|2º': 2,
            r'\btercer\b|\btercero\b|3er|3°|3º': 3,
            r'\bcuarto\b|4to|4°|4º': 4,
            r'\bquinto\b|5to|5°|5º': 5,
            r'\bsexto\b|6to|6°|6º': 6,
            r'\bseptimo\b|7mo|7°|7º': 7,
            r'\boctavo\b|8vo|8°|8º': 8,
            r'\bnoveno\b|9no|9°|9º': 9,
        }
        
        target = None
        for pattern, num in ordinal_map.items():
            if re.search(pattern, q):
                target = num
                break
        
        if target is None:
            m = re.search(r'semestre\s+(\d+)', q)
            if m:
                target = int(m.group(1))
        
        if target is None:
            return similarities
        
        boosted = list(similarities)
        for i, doc_id in enumerate(doc_ids):
            doc = next((d for d in self.documents if d["id"] == doc_id), None)
            if not doc:
                continue
            
            t = doc['titulo'].lower()
            c = doc['contenido'].lower()
            
            if f'semestre {target}' in t or f'semestre {target}' in c:
                boosted[i] += 0.25
            
            for other in range(1, 10):
                if other != target:
                    if f'semestre {other}' in t and 'semestre' in q:
                        boosted[i] -= 0.05
        
        return boosted
    
    def build_context(self, query: str, top_k: int = None, fuente: Optional[str] = None) -> str:
        """Construye contexto concatenado para el LLM."""
        results = self.search(query, top_k, fuente)
        if not results:
            return "No se encontro informacion relevante."
        return "\n\n".join([f"[{i+1}] {r['titulo']}: {r['contenido']}" for i, r in enumerate(results)])
    
    def add_document(self, doc_id: str, titulo: str, contenido: str,
                     categoria: str, fuente: str, keywords: List[str] = None) -> bool:
        """Agrega documento nuevo al indice en tiempo real."""
        if not CHROMA_AVAILABLE or not self.collection:
            return False
        
        keywords = keywords or []
        existing = self.collection.get(ids=[doc_id])
        if existing and existing["ids"]:
            return False
        
        text = f"{titulo}. {contenido} {' '.join(keywords)}"
        emb = self.model.encode([text]).tolist()
        
        self.collection.add(
            ids=[doc_id],
            embeddings=emb,
            metadatas=[{"categoria": categoria, "fuente": fuente, "titulo": titulo}],
            documents=[text]
        )
        
        self.documents.append({
            "id": doc_id, "categoria": categoria, "titulo": titulo,
            "contenido": contenido, "keywords": keywords, "fuente": fuente
        })
        
        logger.info(f"[RAG] Documento {doc_id} agregado")
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        stats = {
            "total_documents": len(self.documents),
            "embedding_model": settings.embedding_model if ST_AVAILABLE else "keyword-matching",
            "vector_database": "ChromaDB" if CHROMA_AVAILABLE else "numpy",
            "sources": sorted(list(set(d["fuente"] for d in self.documents))),
            "persist_directory": self.persist_dir,
        }
        if CHROMA_AVAILABLE and self.collection:
            stats["indexed_documents"] = self.collection.count()
        return stats
