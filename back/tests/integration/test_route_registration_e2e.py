"""Integration tests for route registration.

Validates that all routes are properly registered with correct prefixes
and accessible at their expected paths. This prevents double-prefix bugs
and other route registration issues.
"""

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from unittest.mock import Mock, AsyncMock
import socketio


@pytest.fixture
async def app_with_all_routes():
    """Create FastAPI app with full route registration using factories."""
    from app.src.routes.factories.nfc_unified_routes import UnifiedNFCRoutes

    app = FastAPI()
    sio = socketio.AsyncServer(async_mode="asgi")

    # Mock the application and services
    mock_application = Mock()
    mock_nfc_service = Mock()
    mock_nfc_service.get_nfc_status_use_case = AsyncMock(return_value={
        "hardware_available": True,
        "listening": False,
        "association_active": False,
        "current_session_id": None,
    })
    mock_nfc_service.start_scan_session = AsyncMock(return_value={
        "status": "success",
        "scan_id": "test-scan-123"
    })
    mock_application._nfc_app_service = mock_nfc_service
    app.application = mock_application

    # Initialize NFC routes using the factory (this is how it's done in production)
    nfc_routes = UnifiedNFCRoutes(app, sio)
    nfc_routes.register_with_app()  # Uses default prefix "/api/nfc"

    return app


@pytest.mark.asyncio
class TestRouteRegistrationE2E:
    """End-to-end tests for route registration."""

    async def test_nfc_routes_registered_at_correct_path(self, app_with_all_routes):
        """Test that NFC routes are accessible at /api/nfc/* (not /api/nfc/api/nfc/*).

        This test prevents the double-prefix bug where routes were registered
        at /api/nfc/api/nfc/* instead of /api/nfc/*.
        """
        app = app_with_all_routes

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test GET /api/nfc/status (should work)
            response = await client.get("/api/nfc/status")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"

            # Test POST /api/nfc/scan with test data (should work)
            response = await client.post(
                "/api/nfc/scan",
                json={"client_op_id": "test-op-123"}
            )
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"

            # Verify the double-prefix path does NOT work (should be 404)
            response = await client.get("/api/nfc/api/nfc/status")
            assert response.status_code == 404, (
                "Double-prefix path should return 404, "
                f"but got {response.status_code}. This indicates a double-prefix bug!"
            )

    async def test_nfc_scan_endpoint_accepts_post(self, app_with_all_routes):
        """Test that POST /api/nfc/scan returns 200, not 405 Method Not Allowed.

        This test specifically addresses the reported bug where the scan endpoint
        was returning 405 instead of accepting POST requests.
        """
        app = app_with_all_routes

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/nfc/scan",
                json={"client_op_id": "test-client-op"}
            )

            # Should NOT return 405 Method Not Allowed
            assert response.status_code != 405, (
                f"POST /api/nfc/scan returned 405 Method Not Allowed. "
                f"This indicates the route is not properly registered."
            )

            # Should return 200 (success)
            assert response.status_code == 200, (
                f"Expected 200, got {response.status_code}. "
                f"Response: {response.text}"
            )

            data = response.json()
            assert data["status"] == "success"
            assert "data" in data
            assert "scan_id" in data["data"]

    async def test_all_nfc_endpoints_accessible(self, app_with_all_routes):
        """Test that all NFC endpoints are accessible at their expected paths."""
        app = app_with_all_routes

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # GET /api/nfc/status
            response = await client.get("/api/nfc/status")
            assert response.status_code == 200

            # POST /api/nfc/scan
            response = await client.post(
                "/api/nfc/scan",
                json={"client_op_id": "test-scan-op"}
            )
            assert response.status_code == 200

            # POST /api/nfc/associate (using test data to trigger mock response)
            response = await client.post(
                "/api/nfc/associate",
                json={
                    "tag_id": "test-tag-123",
                    "playlist_id": "test-playlist-456",
                    "client_op_id": "test-assoc-op"
                }
            )
            assert response.status_code == 200

            # DELETE /api/nfc/associate/{tag_id}
            response = await client.request(
                "DELETE",
                "/api/nfc/associate/test-tag-123",
                json={"client_op_id": "test-delete-op"}
            )
            assert response.status_code in [200, 204]
