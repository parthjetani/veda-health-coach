from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    # Patch the lifespan to avoid real connections
    with patch("app.main.create_client") as mock_create_client, \
         patch("app.main.genai"), \
         patch("builtins.open", create=True) as mock_open:

        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        mock_open.return_value.read = MagicMock(return_value="test prompt")

        from app.main import app
        app.state.supabase = MagicMock()
        app.state.http_client = AsyncMock()
        app.state.gemini_client = MagicMock()
        app.state.system_prompt = "test prompt"

        with TestClient(app, raise_server_exceptions=False) as c:
            yield c, app.state.supabase


class TestAdminAuth:
    def test_no_api_key_returns_422(self, client):
        c, _ = client
        response = c.get("/admin/users")
        assert response.status_code == 422

    def test_wrong_api_key_returns_403(self, client):
        c, _ = client
        response = c.get("/admin/users", headers={"X-API-Key": "wrong-key"})
        assert response.status_code == 403

    def test_correct_api_key_passes(self, client):
        c, mock_supabase = client

        # Mock the Supabase response
        mock_result = MagicMock()
        mock_result.data = []
        mock_result.count = 0
        mock_supabase.table.return_value.select.return_value.execute.return_value = mock_result
        mock_supabase.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value = mock_result

        response = c.get(
            "/admin/users",
            headers={"X-API-Key": "test-admin-key"},
        )
        assert response.status_code == 200


class TestHealthCheck:
    def test_health_endpoint(self, client):
        c, _ = client
        response = c.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
