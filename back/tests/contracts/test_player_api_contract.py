"""Contract tests for Player API endpoints.

Validates that player API endpoints conform to the expected API contract.

Progress: 9/9 endpoints tested ✅
"""

import pytest
from unittest.mock import AsyncMock, Mock
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def app_with_player_routes():
    """Create FastAPI app with player routes configured."""
    from app.src.routes.factories.player_routes_ddd import PlayerRoutesDDD
    from socketio import AsyncServer

    app = FastAPI()
    socketio = AsyncMock(spec=AsyncServer)

    # Mock playback coordinator
    mock_playback_coordinator = Mock()

    routes = PlayerRoutesDDD(app, socketio, mock_playback_coordinator)

    return app, routes


@pytest.mark.asyncio
class TestPlayerAPIContract:
    """Contract tests for player API endpoints."""

    async def test_play_contract(self, app_with_player_routes):
        """Test POST /api/player/play - Start/resume playback.

        Contract:
        - Request body: {client_op_id?: str}
        - Success response (200): {status: "success", data: {playing: bool, ...}}
        - Triggers Socket.IO state:player broadcast
        """
        app, routes = app_with_player_routes

        # Mock player service
        routes.player_application_service.play_use_case = AsyncMock(
            return_value={
                "success": True,
                "status": {"playing": True, "paused": False}
            }
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test successful play
            response = await client.post(
                "/api/player/play",
                json={"client_op_id": "client-op-play"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data
            assert "playing" in data["data"]

    async def test_pause_contract(self, app_with_player_routes):
        """Test POST /api/player/pause - Pause playback.

        Contract:
        - Request body: {client_op_id?: str}
        - Success response (200): {status: "success", data: {playing: bool, paused: bool}}
        """
        app, routes = app_with_player_routes

        # Mock player service
        routes.player_application_service.pause_use_case = AsyncMock(
            return_value={
                "success": True,
                "status": {"playing": False, "paused": True}
            }
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test successful pause
            response = await client.post(
                "/api/player/pause",
                json={"client_op_id": "client-op-pause"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data
            assert data["data"]["playing"] == False
            assert data["data"]["paused"] == True

    async def test_stop_contract(self, app_with_player_routes):
        """Test POST /api/player/stop - Stop playback.

        Contract:
        - Request body: {client_op_id?: str}
        - Success response (200): {status: "success", data: {playing: bool}}
        """
        app, routes = app_with_player_routes

        # Mock player service
        routes.player_application_service.stop_use_case = AsyncMock(
            return_value={
                "success": True,
                "status": {"playing": False, "paused": False}
            }
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test successful stop
            response = await client.post(
                "/api/player/stop",
                json={"client_op_id": "client-op-stop"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data
            assert data["data"]["playing"] == False

    async def test_next_contract(self, app_with_player_routes):
        """Test POST /api/player/next - Next track.

        Contract:
        - Request body: {client_op_id?: str}
        - Success response (200): {status: "success", data: {track_changed: bool}}
        """
        app, routes = app_with_player_routes

        # Mock player service
        routes.player_application_service.next_track_use_case = AsyncMock(
            return_value={
                "success": True,
                "track_changed": True,
                "status": {"current_track": {"title": "Next Track"}}
            }
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test successful next
            response = await client.post(
                "/api/player/next",
                json={"client_op_id": "client-op-next"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data

    async def test_previous_contract(self, app_with_player_routes):
        """Test POST /api/player/previous - Previous track.

        Contract:
        - Request body: {client_op_id?: str}
        - Success response (200): {status: "success", data: {track_changed: bool}}
        """
        app, routes = app_with_player_routes

        # Mock player service
        routes.player_application_service.previous_track_use_case = AsyncMock(
            return_value={
                "success": True,
                "track_changed": True,
                "status": {"current_track": {"title": "Previous Track"}}
            }
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test successful previous
            response = await client.post(
                "/api/player/previous",
                json={"client_op_id": "client-op-prev"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data

    async def test_toggle_contract(self, app_with_player_routes):
        """Test POST /api/player/toggle - Toggle play/pause.

        Contract:
        - Request body: {client_op_id?: str}
        - Success response (200): {status: "success", data: {playing: bool}}
        """
        app, routes = app_with_player_routes

        # Mock operations service (toggle uses operations_service, not player_service)
        routes.operations_service.toggle_playback_use_case = AsyncMock(
            return_value={
                "success": True,
                "state": "playing",
                "status": {"playing": True, "paused": False}
            }
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test successful toggle
            response = await client.post(
                "/api/player/toggle",
                json={"client_op_id": "client-op-toggle"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data
            assert "playing" in data["data"]

    async def test_get_status_contract(self, app_with_player_routes):
        """Test GET /api/player/status - Get player status.

        Contract:
        - Success response (200): {status: "success", data: PlayerState}
        - PlayerState must include active_track object when track is playing
        - Must include caching headers
        """
        app, routes = app_with_player_routes

        # Mock player service with complete PlayerState structure including active_track
        routes.player_application_service.get_status_use_case = AsyncMock(
            return_value={
                "success": True,
                "status": {
                    "is_playing": True,
                    "position_ms": 15000,
                    "duration_ms": 180000,
                    "can_prev": True,
                    "can_next": True,
                    "volume": 75,
                    "server_seq": 42,
                    "active_playlist_id": "playlist-abc",
                    "active_playlist_title": "Test Playlist",
                    "active_track_id": "track-123",
                    "active_track": {
                        "id": "track-123",
                        "title": "Test Song",
                        "filename": "test.mp3",
                        "file_path": "/music/test.mp3",
                        "duration_ms": 180000
                    },
                    "track_index": 0,
                    "track_count": 5
                }
            }
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test successful status retrieval
            response = await client.get("/api/player/status")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data

            # Validate PlayerState structure
            player_state = data["data"]

            # Required fields per contract
            assert "is_playing" in player_state
            assert "position_ms" in player_state
            assert "can_prev" in player_state
            assert "can_next" in player_state
            assert "server_seq" in player_state

            # CRITICAL: Validate active_track structure
            assert "active_track" in player_state
            assert player_state["active_track"] is not None
            assert isinstance(player_state["active_track"], dict)

            # Validate track object fields
            track = player_state["active_track"]
            assert "id" in track
            assert "title" in track
            assert "filename" in track
            assert track["title"] == "Test Song"

            # Validate playlist information
            assert player_state["active_playlist_id"] == "playlist-abc"
            assert player_state["active_playlist_title"] == "Test Playlist"

    async def test_seek_contract(self, app_with_player_routes):
        """Test POST /api/player/seek - Seek to position.

        Contract:
        - Request body: {position_ms: int (required), client_op_id?: str}
        - Success response (200): {status: "success", data: {position_ms}}
        - Error response (400): when position_ms missing or invalid
        """
        app, routes = app_with_player_routes

        # Mock player service
        routes.player_application_service.seek_use_case = AsyncMock(
            return_value={
                "success": True,
                "position_ms": 30000,
                "status": {"position_ms": 30000}
            }
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test successful seek
            response = await client.post(
                "/api/player/seek",
                json={"position_ms": 30000, "client_op_id": "client-op-seek"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data

            # Test error when position_ms missing
            response = await client.post(
                "/api/player/seek",
                json={"client_op_id": "client-op-fail"}
            )

            assert response.status_code == 422  # FastAPI validation error

    async def test_volume_contract(self, app_with_player_routes):
        """Test POST /api/player/volume - Set volume.

        Contract:
        - Request body: {volume: int (0-100, required), client_op_id?: str}
        - Success response (200): {status: "success", data: {volume}}
        - Error response (400/422): when volume missing or out of range
        """
        app, routes = app_with_player_routes

        # Mock player service (volume endpoint calls both set_volume and get_status)
        routes.player_application_service.set_volume_use_case = AsyncMock(
            return_value={"success": True}
        )
        routes.player_application_service.get_status_use_case = AsyncMock(
            return_value={
                "success": True,
                "status": {"volume": 75, "playing": False}
            }
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test successful volume change
            response = await client.post(
                "/api/player/volume",
                json={"volume": 75, "client_op_id": "client-op-volume"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data

            # Test error when volume out of range
            response = await client.post(
                "/api/player/volume",
                json={"volume": 150, "client_op_id": "client-op-fail"}
            )

            assert response.status_code == 422  # FastAPI validation error

            # Test error when volume missing
            response = await client.post(
                "/api/player/volume",
                json={"client_op_id": "client-op-fail"}
            )

            assert response.status_code == 422  # FastAPI validation error
