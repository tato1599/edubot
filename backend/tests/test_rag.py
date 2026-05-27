"""
Tests para el motor RAG.
"""

import os
import sys
import pytest

# Asegurar que el backend esta en el path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.app.utils.query_expansion import expand_query


class TestQueryExpansion:
    """Tests para la expansion de queries."""
    
    def test_expand_semestre(self):
        result = expand_query("primer semestre")
        assert "semestre 1" in result
    
    def test_expand_sistemas(self):
        result = expand_query("sistemas")
        assert "sistemas computacionales" in result
    
    def test_expand_dona_pelos(self):
        result = expand_query("doña pelos")
        assert "hamburguesas" in result
    
    def test_no_expansion_needed(self):
        result = expand_query("hola mundo")
        assert result == "hola mundo"
    
    def test_cache_works(self):
        # Segunda llamada deberia usar cache
        r1 = expand_query("smae")
        r2 = expand_query("smae")
        assert r1 == r2


class TestRAGService:
    """Tests para el servicio RAG (requiere modelo descargado)."""
    
    @pytest.fixture(scope="class")
    def rag(self):
        from backend.app.services.rag_service import RAGService
        return RAGService()
    
    def test_load_documents(self, rag):
        assert len(rag.documents) > 0
        stats = rag.get_stats()
        assert stats["total_documents"] > 0
    
    def test_search_returns_results(self, rag):
        results = rag.search("inscripcion", top_k=3)
        assert len(results) > 0
        assert all("score" in r for r in results)
    
    def test_search_filter_by_source(self, rag):
        results = rag.search("smae", top_k=3, fuente="smae")
        assert len(results) > 0
        assert all(r["fuente"] == "smae" for r in results)
    
    def test_build_context(self, rag):
        context = rag.build_context("inscripcion", top_k=2)
        assert len(context) > 0
        assert "No se encontro" not in context
    
    def test_semantic_boost_semestre(self, rag):
        results = rag.search("primer semestre", top_k=3)
        # El primer resultado deberia ser del semestre 1
        assert any("semestre 1" in r["titulo"].lower() for r in results)


class TestLLMService:
    """Tests para el servicio LLM."""
    
    @pytest.fixture(scope="class")
    def llm(self):
        from backend.app.services.llm_service import LLMService
        service = LLMService()
        return service
    
    def test_initially_not_loaded(self, llm):
        assert not llm.is_loaded
    
    def test_stats_before_load(self, llm):
        stats = llm.get_stats()
        assert stats["loaded"] == False
