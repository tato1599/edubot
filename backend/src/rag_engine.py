"""
Motor de RAG (Retrieval-Augmented Generation) para el Agente Escolar.
Implementa búsqueda por similitud de embeddings sobre los datos JSON locales.
"""

import json
import os
import numpy as np
from typing import List, Dict, Any

# Intentar cargar sentence-transformers; si no está, usar fallback por keyword matching
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False
    print("[ADVERTENCIA] sentence-transformers no instalado. Usando fallback por palabras clave.")


class RAGEngine:
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        self.data_dir = os.path.abspath(data_dir)
        
        self.documents = []
        self.embeddings = None
        self.model = None
        
        self._load_data()
        self._build_index()
    
    def _load_data(self):
        """Carga los JSON de trámites y SMAE."""
        # Trámites
        tramites_path = os.path.join(self.data_dir, "tramites.json")
        if os.path.exists(tramites_path):
            with open(tramites_path, "r", encoding="utf-8") as f:
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
        
        # SMAE
        smae_path = os.path.join(self.data_dir, "smae.json")
        if os.path.exists(smae_path):
            with open(smae_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Indexar grupos de alimentos
                for grupo in data.get("grupos", []):
                    contenido = (
                        f"Grupo de alimentos: {grupo['nombre']}. "
                        f"Porción base: {grupo['porcion_base']}. "
                        f"Calorías por porción: {grupo['calorias_porcion']} kcal. "
                        f"Nutrientes: {json.dumps(grupo.get('nutrientes_porcion', {}))}. "
                        f"Recomendaciones escolares: {grupo.get('recomendaciones_escuela', '')}"
                    )
                    self.documents.append({
                        "id": f"smae_grupo_{grupo['nombre'].replace(' ', '_').lower()}",
                        "categoria": "smae",
                        "titulo": f"SMAE - {grupo['nombre']}",
                        "contenido": contenido,
                        "keywords": [grupo['nombre'].lower()] + [a['nombre'].lower() for a in grupo.get('alimentos_equivalentes', [])[:5]],
                        "fuente": "smae"
                    })
                
                # Indexar recomendaciones generales
                for i, rec in enumerate(data.get("recomendaciones_generales", [])):
                    self.documents.append({
                        "id": f"smae_rec_{i}",
                        "categoria": "smae",
                        "titulo": "Recomendación nutricional escolar",
                        "contenido": rec,
                        "keywords": ["nutricion", "escuela", "recomendacion"],
                        "fuente": "smae"
                    })
                
                # Indexar menús de ejemplo
                for menu in data.get("menus_ejemplo", []):
                    contenido = (
                        f"Menú: {menu['nombre']}. "
                        f"Desayuno: {', '.join(menu.get('desayuno', []))}. "
                        f"Almuerzo: {', '.join(menu.get('almuerzo', []))}. "
                        f"Refrigerio: {', '.join(menu.get('refrigerio', []))}."
                    )
                    self.documents.append({
                        "id": f"smae_menu_{menu['nombre'].replace(' ', '_').lower()}",
                        "categoria": "smae",
                        "titulo": menu["nombre"],
                        "contenido": contenido,
                        "keywords": ["menu", "desayuno", "almuerzo", "refrigerio"],
                        "fuente": "smae"
                    })
        
        print(f"[RAG] {len(self.documents)} documentos indexados.")
    
    def _build_index(self):
        """Construye embeddings para todos los documentos."""
        if not ST_AVAILABLE:
            return
        
        print("[RAG] Cargando modelo de embeddings...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        texts = []
        for doc in self.documents:
            # Combinar título + contenido + keywords para mejor representación
            text = f"{doc['titulo']}. {doc['contenido']} {' '.join(doc.get('keywords', []))}"
            texts.append(text)
        
        print("[RAG] Generando embeddings...")
        self.embeddings = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        print("[RAG] Índice construido correctamente.")
    
    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Busca los documentos más relevantes para la query."""
        if ST_AVAILABLE and self.embeddings is not None and self.model is not None:
            return self._search_embedding(query, top_k)
        else:
            return self._search_keyword(query, top_k)
    
    def _search_embedding(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        query_embedding = self.model.encode([query], convert_to_numpy=True)
        similarities = cosine_similarity(query_embedding, self.embeddings)[0]
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            doc = self.documents[idx].copy()
            doc["score"] = float(similarities[idx])
            results.append(doc)
        return results
    
    def _search_keyword(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Fallback: búsqueda por palabras clave."""
        query_words = set(query.lower().split())
        scored = []
        
        for doc in self.documents:
            score = 0
            # Coincidencia en keywords
            for kw in doc.get("keywords", []):
                if any(qw in kw.lower() or kw.lower() in qw for qw in query_words):
                    score += 2
            # Coincidencia en título
            for qw in query_words:
                if qw in doc["titulo"].lower():
                    score += 1.5
                if qw in doc["contenido"].lower():
                    score += 0.5
            scored.append((score, doc))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, doc in scored[:top_k]:
            doc_copy = doc.copy()
            doc_copy["score"] = score
            results.append(doc_copy)
        return results
    
    def build_context(self, query: str, top_k: int = 3) -> str:
        """Construye un contexto concatenado para el LLM."""
        results = self.search(query, top_k)
        
        if not results:
            return "No se encontró información relevante en la base de datos."
        
        context_parts = []
        for i, res in enumerate(results, 1):
            context_parts.append(f"[{i}] {res['titulo']}: {res['contenido']}")
        
        return "\n\n".join(context_parts)
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_documents": len(self.documents),
            "embedding_model": "all-MiniLM-L6-v2" if ST_AVAILABLE else "keyword-matching",
            "sources": list(set(d["fuente"] for d in self.documents))
        }
