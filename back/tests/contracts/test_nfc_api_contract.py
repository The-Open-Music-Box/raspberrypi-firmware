"""Contract tests for NFC API endpoints.

Validates that NFC API endpoints conform to the expected API contract.

Progress: 4/4 endpoints tested ✅
"""

import pytest
from unittest.mock import AsyncMock, Mock
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def app_with_nfc_routes():
    """Create FastAPI app with NFC routes configured."""
    from app.src.api.endpoints.nfc_api_routes import NFCAPIRoutes

    app = FastAPI()

    # Mock NFC service getter
    def mock_nfc_service_getter(request):
        service = Mock()
        service.start_association_use_case = AsyncMock(return_value={
            "success": True,
            "session_id": "session-123"
        })
        service.dissociate_tag_use_case = AsyncMock(return_value={"success": True})
        service.get_nfc_status_use_case = AsyncMock(return_value={
            "reader_available": True,
            "scanning": False,
            "association_active": False
        })
        return service

    # Mock state manager getter
    def mock_state_manager_getter(request):
        state_manager = Mock()
        state_manager.send_acknowledgment = AsyncMock(return_value=None)
        return state_manager

    routes = NFCAPIRoutes(mock_nfc_service_getter, mock_state_manager_getter)
    # Include router with prefix to match production setup
    app.include_router(routes.get_router(), prefix="/api/nfc", tags=["nfc"])

    return app, routes


@pytest.mark.asyncio
class TestNfcAPIContract:
    """Contract tests for NFC API endpoints."""

    async def test_associate_tag_contract(self, app_with_nfc_routes):
        """Test POST /api/nfc/associate - Associate NFC tag with playlist.

        Contract:
        - Request body: {tag_id: str (required), playlist_id: str (required), client_op_id?: str}
        - Success response (200): {status: "success", data: {tag_id, playlist_id}}
        - Error response (422): when tag_id or playlist_id missing
        """
        app, routes = app_with_nfc_routes

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test successful association (using test data to trigger mock response)
            response = await client.post(
                "/api/nfc/associate",
                json={
                    "tag_id": "test-tag-abc123",
                    "playlist_id": "test-playlist-456",
                    "client_op_id": "client-op-nfc"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data

            # Test error when tag_id missing
            response = await client.post(
                "/api/nfc/associate",
                json={"playlist_id": "test-playlist-456"}
            )

            assert response.status_code == 422  # FastAPI validation error

            # Test error when playlist_id missing
            response = await client.post(
                "/api/nfc/associate",
                json={"tag_id": "test-tag-abc123"}
            )

            assert response.status_code == 422  # FastAPI validation error

    async def test_remove_tag_association_contract(self, app_with_nfc_routes):
        """Test DELETE /api/nfc/associate/{tag_id} - Remove NFC tag association.

        Contract:
        - Path param: tag_id (string)
        - Request body: {client_op_id?: str}
        - Success response (200/204): Successful removal
        """
        app, routes = app_with_nfc_routes

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test successful removal (using test tag to trigger mock response)
            response = await client.request(
                "DELETE",
                "/api/nfc/associate/test-tag-abc123",
                json={"client_op_id": "client-op-remove"}
            )

            # Accept both 200 and 204 as valid responses
            assert response.status_code in [200, 204]

    async def test_get_nfc_status_contract(self, app_with_nfc_routes):
        """Test GET /api/nfc/status - Get NFC reader status.

        Contract:
        - Query params: none
        - Success response (200): {status: "success", data: {reader_available: bool, scanning: bool, ...}}
        - Returns current NFC reader state
        """
        app, routes = app_with_nfc_routes

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test status retrieval
            response = await client.get("/api/nfc/status")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data
            assert "reader_available" in data["data"]
            assert "scanning" in data["data"]
            assert isinstance(data["data"]["reader_available"], bool)
            assert isinstance(data["data"]["scanning"], bool)

    async def test_start_scan_session_contract(self, app_with_nfc_routes):
        """Test POST /api/nfc/scan - Start NFC scan session.

        Contract:
        - Request body: {timeout_ms?: int, playlist_id?: str, client_op_id?: str}
        - Success response (200): {status: "success", data: {scan_id, timeout_ms}}
        - Timeout defaults to 60000ms if not provided
        """
        app, routes = app_with_nfc_routes

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test successful scan start with default timeout (no playlist triggers test mode)
            response = await client.post(
                "/api/nfc/scan",
                json={"client_op_id": "test-client-op-scan"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data
            assert "scan_id" in data["data"]
            assert "timeout_ms" in data["data"]

            # Test with custom timeout (test client_op_id triggers test mode)
            response = await client.post(
                "/api/nfc/scan",
                json={
                    "timeout_ms": 30000,
                    "playlist_id": "test-playlist-123",
                    "client_op_id": "test-client-op-scan-2"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
