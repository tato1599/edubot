"""
Motor de RAG (Retrieval-Augmented Generation) para el Agente Escolar.
Implementa busqueda por similitud de embeddings usando ChromaDB como base de datos vectorial.

Ventajas sobre la version anterior (en memoria):
- Persistencia: los embeddings se guardan en disco, no se recalculan al iniciar
- Velocidad: usa indice HNSW para busqueda aproximada mas rapida
- Escalabilidad: soporta miles de documentos sin degradacion
- Filtrado: permite buscar solo en ciertas fuentes (ej: solo tramites)
"""

import json
import os
import numpy as np
from typing import List, Dict, Any, Optional

# Intentar cargar sentence-transformers; si no esta, usar fallback por keyword matching
try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False
    print("[ADVERTENCIA] sentence-transformers no instalado. Usando fallback por palabras clave.")

# ChromaDB como base de datos vectorial
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    print("[ADVERTENCIA] chromadb no instalado. Usando almacenamiento en memoria.")


class RAGEngine:
    def __init__(self, data_dir: str = None, persist_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        self.data_dir = os.path.abspath(data_dir)
        
        # Directorio donde ChromaDB guardara los embeddings en disco
        if persist_dir is None:
            persist_dir = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
        self.persist_dir = os.path.abspath(persist_dir)
        os.makedirs(self.persist_dir, exist_ok=True)
        
        self.documents = []
        self.model = None
        self.collection = None
        self.client = None
        
        self._load_data()
        self._build_index()
    
    def _load_data(self):
        """Carga los JSON de tramites y SMAE."""
        # Tramites
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
        
        # Reticula ISC (Ingenieria en Sistemas Computacionales)
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
                        f"Creditos totales: {carrera.get('total_creditos_plan', '')}. "
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
                            f"Horas teoria: {mat.get('horas_teoria', 0)}. "
                            f"Horas practica: {mat.get('horas_practica', 0)}. "
                            f"Creditos: {mat.get('creditos', 0)}. "
                            f"Area: {mat.get('area', '')}. "
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
                            f"Semestre {sem_num} de Ingenieria en Sistemas Computacionales. "
                            f"Materias: {sem.get('total_materias', 0)}. "
                            f"Creditos del semestre: {sem.get('creditos_semestre', 0)}. "
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
                            f"Creditos: {act['creditos']}. "
                            f"Requisito: {act['requisito']}. "
                            f"Semestre recomendado: {act['semestre_recomendado']}. "
                            f"Descripcion: {act['descripcion']}"
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
                            f"Descripcion: {recs.get('descripcion', '')}. "
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
                        f"Ubicacion: {lugar.get('ubicacion', 'No especificada')}. "
                        f"Tipo: {lugar.get('tipo', 'No especificado')}. "
                    )
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
                            lugar['nombre'].lower(),
                            "comida", "comer", "restaurante", "snack", "menu",
                            "hamburguesa", "burrito", "boneless", "nachos", "ensalada",
                            "tecnm", "itcj", "campus"
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
        
        # SMAE (Sistema Mexicano de Alimentos Equivalentes)
        smae_path = os.path.join(self.data_dir, "smae.json")
        if os.path.exists(smae_path):
            with open(smae_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                for grupo in data.get("grupos", []):
                    nombre_grupo = grupo.get("nombre", "")
                    alimentos = grupo.get("alimentos", [])
                    alimentos_destacados = alimentos[:15]
                    
                    alimentos_texto = []
                    for a in alimentos_destacados:
                        linea = (
                            f"{a['nombre']}: {a['cantidad']} {a['unidad']} = "
                            f"{a['energia_kcal']} kcal, "
                            f"{a['proteina_g']}g proteina, "
                            f"{a['lipidos_g']}g grasa, "
                            f"{a['hidratos_carbono_g']}g carbohidratos"
                        )
                        alimentos_texto.append(linea)
                    
                    contenido = (
                        f"Grupo SMAE: {nombre_grupo}. "
                        f"Total de alimentos en este grupo: {len(alimentos)}. "
                        f"Alimentos mas comunes: {' | '.join(alimentos_texto)}."
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
                
                dieta = data.get("recomendaciones_dieta_estudiantil", {})
                
                if dieta:
                    principios = dieta.get("principios", [])
                    if principios:
                        self.documents.append({
                            "id": "smae_dieta_principios",
                            "categoria": "smae",
                            "titulo": "SMAE - Principios de dieta saludable para estudiantes",
                            "contenido": (
                                f"Consejos practicos para estudiantes universitarios con presupuesto limitado. "
                                f"{' | '.join(principios)}"
                            ),
                            "keywords": ["dieta", "estudiante", "economico", "saludable", "consejos", "nutricion", "smae"],
                            "fuente": "smae"
                        })
                    
                    compras = dieta.get("lista_compras_economica", [])
                    if compras:
                        self.documents.append({
                            "id": "smae_dieta_compras",
                            "categoria": "smae",
                            "titulo": "SMAE - Lista de compras economica para estudiantes",
                            "contenido": (
                                f"Alimentos economicos y nutritivos recomendados para estudiantes universitarios: "
                                f"{' | '.join(compras)}"
                            ),
                            "keywords": ["lista compras", "economico", "estudiante", "abarrotes", "mercado", "barato", "nutricion"],
                            "fuente": "smae"
                        })
                    
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
                    
                    snacks = dieta.get("snacks_saludables_baratos", [])
                    if snacks:
                        self.documents.append({
                            "id": "smae_dieta_snacks",
                            "categoria": "smae",
                            "titulo": "SMAE - Snacks saludables y baratos para estudiantes",
                            "contenido": (
                                f"Opciones de snacks nutritivos y economicos para estudiantes universitarios: "
                                f"{' | '.join(snacks)}"
                            ),
                            "keywords": ["snack", "botana", "saludable", "barato", "estudiante", "colacion", "nutricion"],
                            "fuente": "smae"
                        })
                    
                    evitar = dieta.get("alimentos_a_evitar_o_limitar", [])
                    if evitar:
                        self.documents.append({
                            "id": "smae_dieta_evitar",
                            "categoria": "smae",
                            "titulo": "SMAE - Alimentos a evitar o limitar para estudiantes",
                            "contenido": (
                                f"Alimentos que los estudiantes deben evitar o consumir con moderacion para mantener una dieta saludable: "
                                f"{' | '.join(evitar)}"
                            ),
                            "keywords": ["evitar", "limitar", "saludable", "estudiante", "consejos", "nutricion", "advertencias"],
                            "fuente": "smae"
                        })
        
        print(f"[RAG] {len(self.documents)} documentos cargados desde JSON.")
    
    def _build_index(self):
        """Construye o carga el indice vectorial con ChromaDB."""
        if not ST_AVAILABLE:
            print("[RAG] sentence-transformers no disponible. Usando keyword matching.")
            return
        
        print("[RAG] Cargando modelo de embeddings...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        if not CHROMA_AVAILABLE:
            print("[RAG] ChromaDB no disponible. Usando almacenamiento en memoria con numpy.")
            self._build_index_in_memory()
            return
        
        # Inicializar cliente ChromaDB con persistencia en disco
        print(f"[RAG] Inicializando ChromaDB en: {self.persist_dir}")
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        
        # Obtener o crear la coleccion
        self.collection = self.client.get_or_create_collection(
            name="edubot_knowledge",
            metadata={"hnsw:space": "cosine"}  # Usar distancia coseno
        )
        
        # Verificar si ya tenemos documentos persistidos
        existing_count = self.collection.count()
        
        if existing_count == 0:
            # Primera vez: indexar todos los documentos
            print(f"[RAG] Indexando {len(self.documents)} documentos en ChromaDB...")
            self._index_documents_chroma()
        else:
            # Ya existen embeddings persistidos
            print(f"[RAG] {existing_count} documentos cargados desde ChromaDB (persistencia en disco).")
            
            # Verificar si los documentos JSON han cambiado
            if existing_count != len(self.documents):
                print(f"[RAG] Detectada discrepancia: JSON tiene {len(self.documents)} docs, ChromaDB tiene {existing_count}.")
                print("[RAG] Reconstruyendo indice...")
                self.client.delete_collection("edubot_knowledge")
                self.collection = self.client.get_or_create_collection(
                    name="edubot_knowledge",
                    metadata={"hnsw:space": "cosine"}
                )
                self._index_documents_chroma()
    
    def _index_documents_chroma(self):
        """Indexa todos los documentos en ChromaDB por lotes."""
        batch_size = 100  # ChromaDB funciona mejor con lotes
        total = len(self.documents)
        
        for i in range(0, total, batch_size):
            batch = self.documents[i:i+batch_size]
            
            ids = [doc["id"] for doc in batch]
            texts = []
            metadatas = []
            
            for doc in batch:
                # Combinar titulo + contenido + keywords para mejor representacion
                text = f"{doc['titulo']}. {doc['contenido']} {' '.join(doc.get('keywords', []))}"
                texts.append(text)
                
                # Metadata para filtrado
                metadatas.append({
                    "categoria": doc["categoria"],
                    "fuente": doc["fuente"],
                    "titulo": doc["titulo"]
                })
            
            # Generar embeddings para el lote
            embeddings = self.model.encode(texts, show_progress_bar=False).tolist()
            
            # Agregar a ChromaDB
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=texts
            )
            
            print(f"[RAG] Indexados {min(i+batch_size, total)}/{total} documentos...")
        
        print(f"[RAG] Indice ChromaDB construido con {total} documentos.")
    
    def _build_index_in_memory(self):
        """Fallback: construye embeddings en memoria (version anterior)."""
        texts = []
        for doc in self.documents:
            text = f"{doc['titulo']}. {doc['contenido']} {' '.join(doc.get('keywords', []))}"
            texts.append(text)
        
        print("[RAG] Generando embeddings en memoria...")
        self.embeddings = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        print("[RAG] Indice en memoria construido correctamente.")
    
    def search(self, query: str, top_k: int = 3, fuente: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Busca los documentos mas relevantes para la query.
        
        Args:
            query: Texto de busqueda
            top_k: Numero de resultados
            fuente: Filtrar por fuente (ej: 'tramites', 'smae', 'reticula_isc')
        """
        if CHROMA_AVAILABLE and self.collection is not None:
            return self._search_chroma(query, top_k, fuente)
        elif ST_AVAILABLE and hasattr(self, 'embeddings'):
            return self._search_embedding(query, top_k)
        else:
            return self._search_keyword(query, top_k)
    
    def _search_chroma(self, query: str, top_k: int, fuente: Optional[str] = None) -> List[Dict[str, Any]]:
        """Busqueda usando ChromaDB con filtrado opcional."""
        query_embedding = self.model.encode([query]).tolist()
        
        # Construir filtro de metadata si se especifica fuente
        where_filter = {"fuente": fuente} if fuente else None
        
        # Realizar busqueda
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k * 2,  # Pedir mas para aplicar boosting semantico
            where=where_filter,
            include=["metadatas", "documents", "distances"]
        )
        
        # Convertir distancia coseno a similitud (1 - distancia)
        similarities = [1.0 - d for d in results["distances"][0]]
        
        # Aplicar boosting semantico para ordinales
        similarities = self._apply_semantic_boost_chroma(
            query, results["ids"][0], similarities
        )
        
        # Ordenar por similitud boosteada y tomar top_k
        indexed = list(zip(results["ids"][0], similarities, results["metadatas"][0], results["documents"][0]))
        indexed.sort(key=lambda x: x[1], reverse=True)
        
        output = []
        for doc_id, score, metadata, document in indexed[:top_k]:
            # Recuperar el documento completo de la lista
            doc = next((d for d in self.documents if d["id"] == doc_id), None)
            if doc:
                doc_copy = doc.copy()
                doc_copy["score"] = float(score)
                output.append(doc_copy)
        
        return output
    
    def _apply_semantic_boost_chroma(self, query: str, doc_ids: List[str], similarities: List[float]) -> List[float]:
        """Aplica boosting para ordinales en resultados de ChromaDB."""
        import re
        query_lower = query.lower()
        
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
        
        target_semester = None
        for pattern, num in ordinal_map.items():
            if re.search(pattern, query_lower):
                target_semester = num
                break
        
        if target_semester is None:
            m = re.search(r'semestre\s+(\d+)', query_lower)
            if m:
                target_semester = int(m.group(1))
        
        if target_semester is None:
            return similarities
        
        boosted = list(similarities)
        for i, doc_id in enumerate(doc_ids):
            doc = next((d for d in self.documents if d["id"] == doc_id), None)
            if not doc:
                continue
            
            titulo = doc['titulo'].lower()
            contenido = doc['contenido'].lower()
            
            sem_text = f'semestre {target_semester}'
            if sem_text in titulo or sem_text in contenido:
                boosted[i] += 0.25
            
            for other in range(1, 10):
                if other != target_semester:
                    other_text = f'semestre {other}'
                    if other_text in titulo and 'semestre' in query_lower:
                        boosted[i] -= 0.05
        
        return boosted
    
    def _search_embedding(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Fallback: busqueda en memoria con numpy."""
        from sklearn.metrics.pairwise import cosine_similarity
        
        query_embedding = self.model.encode([query], convert_to_numpy=True)
        similarities = cosine_similarity(query_embedding, self.embeddings)[0]
        similarities = self._apply_semantic_boost(query, similarities)
        
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            doc = self.documents[idx].copy()
            doc["score"] = float(similarities[idx])
            results.append(doc)
        return results
    
    def _apply_semantic_boost(self, query: str, similarities: np.ndarray) -> np.ndarray:
        """Detecta numeros ordinales y boostea documentos relevantes."""
        import re
        query_lower = query.lower()
        
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
        
        target_semester = None
        for pattern, num in ordinal_map.items():
            if re.search(pattern, query_lower):
                target_semester = num
                break
        
        if target_semester is None:
            m = re.search(r'semestre\s+(\d+)', query_lower)
            if m:
                target_semester = int(m.group(1))
        
        if target_semester is None:
            return similarities
        
        boosted = similarities.copy()
        for i, doc in enumerate(self.documents):
            titulo = doc['titulo'].lower()
            contenido = doc['contenido'].lower()
            
            sem_text = f'semestre {target_semester}'
            if sem_text in titulo or sem_text in contenido:
                boosted[i] += 0.25
            
            for other in range(1, 10):
                if other != target_semester:
                    other_text = f'semestre {other}'
                    if other_text in titulo and 'semestre' in query_lower:
                        boosted[i] -= 0.05
        
        return boosted
    
    def _search_keyword(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Fallback: busqueda por palabras clave."""
        query_words = set(query.lower().split())
        scored = []
        
        for doc in self.documents:
            score = 0
            for kw in doc.get("keywords", []):
                if any(qw in kw.lower() or kw.lower() in qw for qw in query_words):
                    score += 2
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
    
    def build_context(self, query: str, top_k: int = 3, fuente: Optional[str] = None) -> str:
        """Construye un contexto concatenado para el LLM."""
        results = self.search(query, top_k, fuente)
        
        if not results:
            return "No se encontro informacion relevante en la base de datos."
        
        context_parts = []
        for i, res in enumerate(results, 1):
            context_parts.append(f"[{i}] {res['titulo']}: {res['contenido']}")
        
        return "\n\n".join(context_parts)
    
    def add_document(self, doc_id: str, titulo: str, contenido: str, 
                     categoria: str, fuente: str, keywords: List[str] = None) -> bool:
        """
        Agrega un nuevo documento al indice vectorial en tiempo real.
        Util para agregar documentos dinamicamente sin reiniciar.
        """
        if not CHROMA_AVAILABLE or self.collection is None:
            print("[RAG] ChromaDB no disponible. No se puede agregar documento.")
            return False
        
        keywords = keywords or []
        
        # Verificar si ya existe
        existing = self.collection.get(ids=[doc_id])
        if existing and existing["ids"]:
            print(f"[RAG] Documento {doc_id} ya existe. Usa update_document para modificarlo.")
            return False
        
        text = f"{titulo}. {contenido} {' '.join(keywords)}"
        embedding = self.model.encode([text]).tolist()
        
        self.collection.add(
            ids=[doc_id],
            embeddings=embedding,
            metadatas=[{"categoria": categoria, "fuente": fuente, "titulo": titulo}],
            documents=[text]
        )
        
        # Tambien agregar a la lista en memoria
        self.documents.append({
            "id": doc_id,
            "categoria": categoria,
            "titulo": titulo,
            "contenido": contenido,
            "keywords": keywords,
            "fuente": fuente
        })
        
        print(f"[RAG] Documento {doc_id} agregado al indice.")
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Estadisticas del motor RAG."""
        stats = {
            "total_documents_json": len(self.documents),
            "embedding_model": "all-MiniLM-L6-v2" if ST_AVAILABLE else "keyword-matching",
            "vector_database": "ChromaDB (persistencia en disco)" if CHROMA_AVAILABLE else "numpy (memoria RAM)",
            "sources": list(set(d["fuente"] for d in self.documents))
        }
        
        if CHROMA_AVAILABLE and self.collection:
            stats["total_documents_indexed"] = self.collection.count()
            stats["persist_directory"] = self.persist_dir
        
        return stats
