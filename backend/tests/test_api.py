"""
Tests de integracion para la API.
"""

import os
import sys
import pytest
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestHealth:
    """Tests para el endpoint de health."""
    
    @pytest.mark.asyncio
    async def test_health_returns_status(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "progress" in data
    
    @pytest.mark.asyncio
    async def test_health_has_version(self, client):
        response = await client.get("/health")
        data = response.json()
        assert "version" in data


class TestStatus:
    """Tests para el endpoint de status."""
    
    @pytest.mark.asyncio
    async def test_status_online(self, client):
        response = await client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
    
    @pytest.mark.asyncio
    async def test_status_has_rag_stats(self, client):
        response = await client.get("/status")
        data = response.json()
        assert "rag_stats" in data
        assert "total_documents" in data["rag_stats"]


class TestStats:
    """Tests para el endpoint de stats."""
    
    @pytest.mark.asyncio
    async def test_stats_returns_data(self, client):
        response = await client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_documents" in data
        assert "sources" in data


class TestChat:
    """Tests para el endpoint de chat (requiere modelo cargado)."""
    
    @pytest.mark.asyncio
    async def test_chat_without_model(self, client):
        # Si el modelo no esta cargado, deberia retornar 503
        response = await client.post("/chat", json={
            "message": "hola",
            "history": []
        })
        # Puede ser 200 (si modelo cargo) o 503 (si no)
        assert response.status_code in [200, 503]
    
    @pytest.mark.asyncio
    async def test_chat_invalid_request(self, client):
        response = await client.post("/chat", json={})
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_chat_stream(self, client):
        response = await client.post("/chat/stream", json={
            "message": "hola",
            "history": []
        })
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            assert "text/event-stream" in response.headers.get("content-type", "")


class TestMiddleware:
    """Tests para middlewares."""
    
    @pytest.mark.asyncio
    async def test_request_id_header(self, client):
        response = await client.get("/health")
        assert "X-Request-ID" in response.headers
    
    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, client):
        response = await client.get("/status")
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
