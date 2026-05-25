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
        
        # Retícula ISC (Ingeniería en Sistemas Computacionales)
        reticula_path = os.path.join(self.data_dir, "reticula_isc.json")
        if os.path.exists(reticula_path):
            with open(reticula_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                carrera = data.get("carrera", {})
                
                # Documento general de la carrera
                self.documents.append({
                    "id": "isc_general",
                    "categoria": "reticula_isc",
                    "titulo": f"{carrera.get('nombre', 'ISC')} - {carrera.get('institucion', 'TecNM')}",
                    "contenido": (
                        f"Carrera: {carrera.get('nombre', '')}. "
                        f"Plan: {carrera.get('clave_plan', '')}. "
                        f"Total materias: {carrera.get('total_materias', '')}. "
                        f"Créditos totales: {carrera.get('total_creditos_plan', '')}. "
                        f"Estructura: {json.dumps(carrera.get('estructura_creditos', {}))}"
                    ),
                    "keywords": ["reticula", "isc", "sistemas computacionales", "plan estudios", "ITCJ", "TecNM"],
                    "fuente": "reticula_isc"
                })
                
                # Indexar materias por semestre
                for sem in data.get("semestres", []):
                    sem_num = sem.get("numero", 0)
                    for mat in sem.get("materias", []):
                        prereqs = ", ".join(mat.get("prerequisitos", [])) if mat.get("prerequisitos") else "Ninguno"
                        contenido = (
                            f"Materia: {mat['nombre']}. "
                            f"Clave: {mat['clave']}. "
                            f"Semestre: {sem_num}. "
                            f"Horas teoría: {mat.get('horas_teoria', 0)}. "
                            f"Horas práctica: {mat.get('horas_practica', 0)}. "
                            f"Créditos: {mat.get('creditos', 0)}. "
                            f"Área: {mat.get('area', '')}. "
                            f"Prerequisitos: {prereqs}."
                        )
                        self.documents.append({
                            "id": f"isc_mat_{mat['clave']}",
                            "categoria": "reticula_isc",
                            "titulo": f"ISC - {mat['nombre']} ({mat['clave']})",
                            "contenido": contenido,
                            "keywords": [mat['nombre'].lower(), mat['clave'].lower(), "semestre", f"semestre {sem_num}", mat.get('area', '').lower()],
                            "fuente": "reticula_isc"
                        })
                    
                    # Documento resumen por semestre
                    nombres_mats = ", ".join([m['nombre'] for m in sem.get("materias", [])])
                    self.documents.append({
                        "id": f"isc_sem_{sem_num}",
                        "categoria": "reticula_isc",
                        "titulo": f"ISC - Semestre {sem_num}",
                        "contenido": (
                            f"Semestre {sem_num} de Ingeniería en Sistemas Computacionales. "
                            f"Materias: {sem.get('total_materias', 0)}. "
                            f"Créditos del semestre: {sem.get('creditos_semestre', 0)}. "
                            f"Materias incluidas: {nombres_mats}."
                        ),
                        "keywords": [f"semestre {sem_num}", "materias", "plan", "isc", "sistemas computacionales"],
                        "fuente": "reticula_isc"
                    })
                
                # Indexar actividades integrales
                for act in data.get("actividades_integrales", []):
                    self.documents.append({
                        "id": f"isc_act_{act['nombre'].replace(' ', '_').lower()}",
                        "categoria": "reticula_isc",
                        "titulo": f"ISC - {act['nombre']}",
                        "contenido": (
                            f"Actividad: {act['nombre']}. "
                            f"Créditos: {act['creditos']}. "
                            f"Requisito: {act['requisito']}. "
                            f"Semestre recomendado: {act['semestre_recomendado']}. "
                            f"Descripción: {act['descripcion']}"
                        ),
                        "keywords": [act['nombre'].lower(), "creditos", "requisitos", "semestre", "isc"],
                        "fuente": "reticula_isc"
                    })
                
                # Indexar recomendaciones de plan
                recs = data.get("recomendaciones_plan", {})
                if recs.get("reglas_generales"):
                    self.documents.append({
                        "id": "isc_recomendaciones",
                        "categoria": "reticula_isc",
                        "titulo": "ISC - Recomendaciones y mejor plan de estudios",
                        "contenido": (
                            f"Descripción: {recs.get('descripcion', '')}. "
                            f"Reglas generales: {' | '.join(recs.get('reglas_generales', []))}. "
                            f"Plan completo recomendado: {recs.get('mejor_plan_completo', '')}"
                        ),
                        "keywords": ["plan", "recomendaciones", "estrategia", "carga", "semestre", "isc"],
                        "fuente": "reticula_isc"
                    })
                
                # Indexar objetivos y perfil de egreso
                obj = data.get("objetivos_carrera", {})
                if obj.get("objetivo_general"):
                    self.documents.append({
                        "id": "isc_objetivos",
                        "categoria": "reticula_isc",
                        "titulo": "ISC - Objetivos y perfil de egreso",
                        "contenido": (
                            f"Objetivo general: {obj.get('objetivo_general', '')}. "
                            f"Objetivos educacionales: {' | '.join(obj.get('objetivos_educacionales', []))}. "
                            f"Perfil de egreso: {' | '.join(obj.get('perfil_egreso', []))}"
                        ),
                        "keywords": ["objetivos", "perfil egreso", "competencias", "isc", "egresado"],
                        "fuente": "reticula_isc"
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
