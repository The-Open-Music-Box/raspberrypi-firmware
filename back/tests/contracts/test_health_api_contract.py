"""Contract tests for Health API endpoint.

Validates that health check endpoint conforms to the expected API contract.

Progress: 1/1 endpoints tested ✅
"""

import pytest
from unittest.mock import AsyncMock, Mock
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def app_with_health_routes():
    """Create FastAPI app with health routes configured."""
    from app.src.api.endpoints.system_api_routes import SystemAPIRoutes

    app = FastAPI()

    # Mock playback coordinator getter
    def mock_coordinator_getter(request):
        return Mock()

    routes = SystemAPIRoutes(mock_coordinator_getter)
    app.include_router(routes.get_router())

    return app, routes


@pytest.mark.asyncio
class TestHealthAPIContract:
    """Contract tests for health check endpoint."""

    async def test_health_check_contract(self, app_with_health_routes):
        """Test GET /api/health - Health check endpoint.

        Contract:
        - Query params: none
        - Success response (200): {status: "success", data: {status: str, services: {}, timestamp}}
        - Should include health status and service checks
        """
        app, routes = app_with_health_routes

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test successful health check
            response = await client.get("/api/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data
            assert "status" in data["data"]  # health status (healthy/degraded/unhealthy)
            assert "services" in data["data"]
            assert "timestamp" in data["data"]
            assert isinstance(data["data"]["services"], dict)
            assert isinstance(data["data"]["timestamp"], (int, float))
