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
        
        # Comedores y locales de comida del TecNM ITCJ
        comedores_path = os.path.join(self.data_dir, "comedores.json")
        if os.path.exists(comedores_path):
            with open(comedores_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                for lugar in data.get("lugares_comida", []):
                    # Indexar cada local
                    menu_items = []
                    for item in lugar.get("menu", []):
                        desc = item.get("descripcion", "")
                        if item.get("opciones"):
                            desc += f" Opciones: {', '.join(item['opciones'])}."
                        if item.get("incluye"):
                            desc += f" Incluye: {', '.join(item['incluye'])}."
                        menu_items.append(f"{item['nombre']}: {desc}")
                    
                    contenido = (
                        f"Lugar: {lugar['nombre']}. "
                        f"Ubicación: {lugar.get('ubicacion', 'No especificada')}. "
                        f"Tipo: {lugar.get('tipo', 'No especificado')}. "
                    )
                    if menu_items:
                        contenido += f"Menú: {' | '.join(menu_items)}. "
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
                            lugar['nombre'].lower(),
                            "comida", "comer", "restaurante", "snack", "menú",
                            "hamburguesa", "burrito", "boneless", "nachos", "ensalada",
                            "tecnm", "itcj", "campus"
                        ],
                        "fuente": "comedores"
                    })
                
                # Indexar recomendaciones generales
                for i, rec in enumerate(data.get("recomendaciones_generales", [])):
                    self.documents.append({
                        "id": f"comedor_rec_{i}",
                        "categoria": "comedores",
                        "titulo": "Recomendaciones de comida en el TecNM ITCJ",
                        "contenido": rec,
                        "keywords": ["comida", "comer", "restaurante", "recomendación", "tecnm", "itcj"],
                        "fuente": "comedores"
                    })
        
        # Reglamento de Estudiantes del TecNM
        reglamento_path = os.path.join(self.data_dir, "reglamento_estudiantes.json")
        if os.path.exists(reglamento_path):
            with open(reglamento_path, "r", encoding="utf-8") as f:
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
                
                print(f"[RAG] {len(data.get('documentos', []))} documentos del Reglamento de Estudiantes indexados.")
        
        # SMAE (Sistema Mexicano de Alimentos Equivalentes - completo)
        smae_path = os.path.join(self.data_dir, "smae.json")
        if os.path.exists(smae_path):
            with open(smae_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # 1. Indexar grupos de alimentos (solo los más comunes por grupo)
                for grupo in data.get("grupos", []):
                    nombre_grupo = grupo.get("nombre", "")
                    alimentos = grupo.get("alimentos", [])
                    
                    # Tomar los primeros 15 alimentos del grupo (más comunes)
                    alimentos_destacados = alimentos[:15]
                    
                    alimentos_texto = []
                    for a in alimentos_destacados:
                        linea = (
                            f"{a['nombre']}: {a['cantidad']} {a['unidad']} = "
                            f"{a['energia_kcal']} kcal, "
                            f"{a['proteina_g']}g proteína, "
                            f"{a['lipidos_g']}g grasa, "
                            f"{a['hidratos_carbono_g']}g carbohidratos"
                        )
                        alimentos_texto.append(linea)
                    
                    contenido = (
                        f"Grupo SMAE: {nombre_grupo}. "
                        f"Total de alimentos en este grupo: {len(alimentos)}. "
                        f"Alimentos más comunes: {' | '.join(alimentos_texto)}."
                    )
                    
                    self.documents.append({
                        "id": f"smae_grupo_{nombre_grupo.replace(' ', '_').lower()}",
                        "categoria": "smae",
                        "titulo": f"SMAE - {nombre_grupo}",
                        "contenido": contenido,
                        "keywords": [
                            nombre_grupo.lower(), "smae", "alimentos", "nutricion",
                            "porcion", "calorias", "proteina", "grupo alimenticio"
                        ],
                        "fuente": "smae"
                    })
                
                # 2. Indexar recomendaciones de dieta estudiantil
                dieta = data.get("recomendaciones_dieta_estudiantil", {})
                
                if dieta:
                    # Principios generales
                    principios = dieta.get("principios", [])
                    if principios:
                        self.documents.append({
                            "id": "smae_dieta_principios",
                            "categoria": "smae",
                            "titulo": "SMAE - Principios de dieta saludable para estudiantes",
                            "contenido": (
                                f"Consejos prácticos para estudiantes universitarios con presupuesto limitado. "
                                f"{' | '.join(principios)}"
                            ),
                            "keywords": ["dieta", "estudiante", "economico", "saludable", "consejos", "nutricion", "smae"],
                            "fuente": "smae"
                        })
                    
                    # Lista de compras económica
                    compras = dieta.get("lista_compras_economica", [])
                    if compras:
                        self.documents.append({
                            "id": "smae_dieta_compras",
                            "categoria": "smae",
                            "titulo": "SMAE - Lista de compras económica para estudiantes",
                            "contenido": (
                                f"Alimentos económicos y nutritivos recomendados para estudiantes universitarios: "
                                f"{' | '.join(compras)}"
                            ),
                            "keywords": ["lista compras", "economico", "estudiante", "abarrotes", "mercado", "barato", "nutricion"],
                            "fuente": "smae"
                        })
                    
                    # Menús de ejemplo económicos
                    for menu in dieta.get("menus_ejemplo_economicos", []):
                        self.documents.append({
                            "id": f"smae_menu_{menu['nombre'].replace(' ', '_').lower()}",
                            "categoria": "smae",
                            "titulo": f"SMAE - {menu['nombre']}",
                            "contenido": (
                                f"{menu['nombre']}. Costo estimado: {menu['costo_estimado']}. "
                                f"Desayuno: {menu['desayuno']} "
                                f"Comida: {menu['comida']} "
                                f"Cena: {menu['cena']} "
                                f"{menu.get('colacion', '')}"
                            ),
                            "keywords": ["menu", "economico", "estudiante", "desayuno", "comida", "cena", "dieta", "presupuesto"],
                            "fuente": "smae"
                        })
                    
                    # Snacks saludables y baratos
                    snacks = dieta.get("snacks_saludables_baratos", [])
                    if snacks:
                        self.documents.append({
                            "id": "smae_dieta_snacks",
                            "categoria": "smae",
                            "titulo": "SMAE - Snacks saludables y baratos para estudiantes",
                            "contenido": (
                                f"Opciones de snacks nutritivos y económicos para estudiantes universitarios: "
                                f"{' | '.join(snacks)}"
                            ),
                            "keywords": ["snack", "botana", "saludable", "barato", "estudiante", "colacion", "nutricion"],
                            "fuente": "smae"
                        })
                    
                    # Alimentos a evitar
                    evitar = dieta.get("alimentos_a_evitar_o_limitar", [])
                    if evitar:
                        self.documents.append({
                            "id": "smae_dieta_evitar",
                            "categoria": "smae",
                            "titulo": "SMAE - Alimentos a evitar o limitar para estudiantes",
                            "contenido": (
                                f"Alimentos que los estudiantes deben evitar o consumir con moderación para mantener una dieta saludable: "
                                f"{' | '.join(evitar)}"
                            ),
                            "keywords": ["evitar", "limitar", "saludable", "estudiante", "consejos", "nutricion", "advertencias"],
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
    
    def _apply_semantic_boost(self, query: str, similarities: np.ndarray) -> np.ndarray:
        """
        Detecta números ordinales en la query y boostea documentos relevantes.
        Esto corrige el problema donde embeddings confunden 'primer' con 'segundo'.
        """
        import re
        query_lower = query.lower()
        
        # Mapeo de ordinales a números de semestre
        ordinal_map = {
            r'\bprimer\b|\bprimero\b|1er|1°|1º': 1,
            r'\bsegundo\b|2do|2°|2º': 2,
            r'\btercer\b|\btercero\b|3er|3°|3º': 3,
            r'\bcuarto\b|4to|4°|4º': 4,
            r'\bquinto\b|5to|5°|5º': 5,
            r'\bsexto\b|6to|6°|6º': 6,
            r'\bséptimo\b|\bseptimo\b|7mo|7°|7º': 7,
            r'\boctavo\b|8vo|8°|8º': 8,
            r'\bnoveno\b|9no|9°|9º': 9,
        }
        
        # Detectar semestre buscado
        target_semester = None
        for pattern, num in ordinal_map.items():
            if re.search(pattern, query_lower):
                target_semester = num
                break
        
        # Si no hay número ordinal, también buscar "semestre [número]"
        if target_semester is None:
            m = re.search(r'semestre\s+(\d+)', query_lower)
            if m:
                target_semester = int(m.group(1))
        
        if target_semester is None:
            return similarities
        
        # Boostear documentos del semestre correcto
        boosted = similarities.copy()
        for i, doc in enumerate(self.documents):
            titulo = doc['titulo'].lower()
            contenido = doc['contenido'].lower()
            
            # Si el documento es del semestre correcto, boost significativo
            sem_text = f'semestre {target_semester}'
            if sem_text in titulo or sem_text in contenido:
                boosted[i] += 0.25  # Boost grande para superar similitud semántica confusa
            
            # Penalizar otros semestres si es claro que no son el correcto
            for other in range(1, 10):
                if other != target_semester:
                    other_text = f'semestre {other}'
                    if other_text in titulo and 'semestre' in query_lower:
                        boosted[i] -= 0.05
        
        return boosted
    
    def _search_embedding(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        query_embedding = self.model.encode([query], convert_to_numpy=True)
        similarities = cosine_similarity(query_embedding, self.embeddings)[0]
        
        # Aplicar boosting semántico para ordinales
        similarities = self._apply_semantic_boost(query, similarities)
        
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
