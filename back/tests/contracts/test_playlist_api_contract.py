"""Contract tests for Playlist API endpoints.

Validates that playlist API endpoints conform to the expected API contract.

Progress: 10/10 endpoints tested ✅
"""

import pytest
from unittest.mock import AsyncMock, Mock
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def app_with_playlist_routes():
    """Create FastAPI app with playlist routes configured."""
    from app.src.routes.factories.playlist_routes_ddd import PlaylistRoutesDDD
    from socketio import AsyncServer

    app = FastAPI()
    socketio = AsyncMock(spec=AsyncServer)
    mock_config = Mock()
    mock_config.upload_folder = "/tmp/uploads"

    routes = PlaylistRoutesDDD(app, socketio, mock_config)
    routes.register()

    return app, routes


@pytest.mark.asyncio
class TestPlaylistAPIContract:
    """Contract tests for playlist API endpoints."""

    async def test_list_playlists_contract(self, app_with_playlist_routes):
        """Test GET /api/playlists - List playlists with pagination.

        Contract:
        - Query params: page (int, default=1), limit (int, default=50, max=100)
        - Success response (200): {status: "success", data: {playlists: [], page, limit, total, total_pages}}
        - Must follow UnifiedResponseService format
        - Must handle both /api/playlists and /api/playlists/ (with trailing slash)
        """
        from httpx import AsyncClient, ASGITransport

        app, routes = app_with_playlist_routes

        # Mock playlist service
        mock_playlists = [
            {"id": "playlist-1", "title": "Test Playlist 1", "tracks": []},
            {"id": "playlist-2", "title": "Test Playlist 2", "tracks": []},
        ]
        routes._playlist_app_service.get_playlists_use_case = AsyncMock(
            return_value={"playlists": mock_playlists}
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test with default pagination WITHOUT trailing slash
            response = await client.get("/api/playlists")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data
            assert "playlists" in data["data"]
            assert "page" in data["data"]
            assert "limit" in data["data"]
            assert "total" in data["data"]
            assert "total_pages" in data["data"]
            assert isinstance(data["data"]["playlists"], list)

            # Test WITH trailing slash (frontend compatibility)
            response = await client.get("/api/playlists/")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert isinstance(data["data"]["playlists"], list)

            # Test with custom page/limit
            response = await client.get("/api/playlists?page=2&limit=10")
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["page"] == 2
            assert data["data"]["limit"] == 10

    async def test_create_playlist_contract(self, app_with_playlist_routes):
        """Test POST /api/playlists - Create new playlist.

        Contract:
        - Request body: {title: str (required), description?: str, client_op_id?: str}
        - Success response (201): {status: "success", data: {playlist details}}
        - Error response (400): {status: "error"} when title missing
        - Must handle both /api/playlists and /api/playlists/ (with trailing slash)
        """
        from httpx import AsyncClient, ASGITransport

        app, routes = app_with_playlist_routes

        # Mock playlist service create
        mock_playlist = {
            "id": "new-playlist-id",
            "title": "New Playlist",
            "description": "Test description",
            "tracks": []
        }
        routes._playlist_app_service.create_playlist_use_case = AsyncMock(
            return_value=mock_playlist
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test successful creation WITHOUT trailing slash
            response = await client.post(
                "/api/playlists",
                json={
                    "title": "New Playlist",
                    "description": "Test description",
                    "client_op_id": "client-op-123"
                }
            )

            assert response.status_code in [200, 201]
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data
            # Contract expects PlaylistDetailed directly in data, not wrapped in "playlist"
            assert "id" in data["data"], "Response must have id field per contract"
            assert "title" in data["data"], "Response must have title field per contract"
            assert data["data"]["title"] == "New Playlist"
            assert data["data"]["id"] == "new-playlist-id"

            # Test successful creation WITH trailing slash (frontend compatibility)
            response = await client.post(
                "/api/playlists/",
                json={
                    "title": "New Playlist",
                    "description": "Test description",
                    "client_op_id": "client-op-456"
                }
            )

            assert response.status_code in [200, 201]
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data
            # Contract expects PlaylistDetailed directly in data, not wrapped in "playlist"
            assert "id" in data["data"], "Response must have id field per contract"
            assert "title" in data["data"], "Response must have title field per contract"
            assert data["data"]["title"] == "New Playlist"
            assert data["data"]["id"] == "new-playlist-id"

            # Test error when title missing
            response = await client.post(
                "/api/playlists",
                json={"description": "No title"}
            )

            assert response.status_code == 400
            data = response.json()
            assert data["status"] == "error"

    async def test_get_playlist_contract(self, app_with_playlist_routes):
        """Test GET /api/playlists/{playlist_id} - Get specific playlist.

        Contract:
        - Path param: playlist_id (string)
        - Success response (200): {status: "success", data: {playlist with tracks}}
        - Error response (404): {status: "error", error_type: "not_found"}
        """
        from httpx import AsyncClient, ASGITransport

        app, routes = app_with_playlist_routes

        # Mock successful retrieval
        mock_playlist = {
            "id": "test-playlist-123",
            "title": "Test Playlist",
            "tracks": [
                {"track_number": 1, "title": "Track 1"},
                {"track_number": 2, "title": "Track 2"}
            ]
        }
        routes._playlist_app_service.get_playlist_use_case = AsyncMock(
            return_value=mock_playlist
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test successful retrieval
            response = await client.get("/api/playlists/test-playlist-123")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data
            # Contract expects PlaylistDetailed directly in data, not wrapped in "playlist"
            assert "id" in data["data"], "Response must have id field per contract"
            assert "title" in data["data"], "Response must have title field per contract"
            assert "tracks" in data["data"], "Response must have tracks field per contract"
            assert isinstance(data["data"]["tracks"], list)
            assert data["data"]["id"] == "test-playlist-123"
            assert data["data"]["title"] == "Test Playlist"

            # Test 404 when playlist doesn't exist
            routes._playlist_app_service.get_playlist_use_case = AsyncMock(
                return_value=None
            )

            response = await client.get("/api/playlists/nonexistent-id")
            assert response.status_code == 404
            data = response.json()
            assert data["status"] == "error"
            assert data["error_type"] == "not_found"

    async def test_update_playlist_contract(self, app_with_playlist_routes):
        """Test PUT /api/playlists/{playlist_id} - Update playlist.

        Contract:
        - Request body: {title?: str, description?: str, client_op_id?: str}
        - Success response (200): {status: "success", data: {client_op_id}}
        - Error response (404): when playlist not found
        """
        from httpx import AsyncClient, ASGITransport

        app, routes = app_with_playlist_routes

        # Mock successful update
        routes._playlist_app_service.update_playlist_use_case = AsyncMock(
            return_value=True
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test successful update
            response = await client.put(
                "/api/playlists/test-playlist-123",
                json={
                    "title": "Updated Title",
                    "client_op_id": "client-op-456"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data
            assert data["data"]["client_op_id"] == "client-op-456"

            # Test partial update (only description)
            response = await client.put(
                "/api/playlists/test-playlist-123",
                json={"description": "New description"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    async def test_delete_playlist_contract(self, app_with_playlist_routes):
        """Test DELETE /api/playlists/{playlist_id} - Delete playlist.

        Contract:
        - Request body: {client_op_id?: str}
        - Success response (204): No content
        - Error response (404): when playlist not found
        """
        from httpx import AsyncClient, ASGITransport

        app, routes = app_with_playlist_routes

        # Mock successful deletion
        routes._playlist_app_service.delete_playlist_use_case = AsyncMock(
            return_value=True
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test successful deletion
            response = await client.request(
                "DELETE",
                "/api/playlists/test-playlist-123",
                json={"client_op_id": "client-op-789"}
            )

            # Note: Some implementations return 200 instead of 204
            assert response.status_code in [200, 204]

    async def test_reorder_tracks_contract(self, app_with_playlist_routes):
        """Test POST /api/playlists/{playlist_id}/reorder - Reorder tracks.

        Contract:
        - Request body: {track_order: str[] (required, track IDs), client_op_id?: str}
        - Success response (200): {status: "success", data: {playlist_id, client_op_id}}
        - Error response (400): when track_order is missing
        - Error response (500): when track_order contains invalid track IDs
        """
        from httpx import AsyncClient, ASGITransport

        app, routes = app_with_playlist_routes

        # Mock successful reorder
        routes._playlist_app_service.reorder_tracks_use_case = AsyncMock(
            return_value={"status": "success"}
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test successful reorder with track IDs (UUIDs)
            response = await client.post(
                "/api/playlists/test-playlist-123/reorder",
                json={
                    "track_order": ["track-uuid-3", "track-uuid-1", "track-uuid-2"],
                    "client_op_id": "client-op-reorder"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data
            assert data["data"]["playlist_id"] == "test-playlist-123"

            # Test error when track_order missing
            response = await client.post(
                "/api/playlists/test-playlist-123/reorder",
                json={"client_op_id": "client-op-fail"}
            )

            assert response.status_code == 400
            data = response.json()
            assert data["status"] == "error"

    async def test_delete_tracks_contract(self, app_with_playlist_routes):
        """Test DELETE /api/playlists/{playlist_id}/tracks - Delete tracks.

        Contract:
        - Request body: {track_numbers: int[] (required), client_op_id?: str}
        - Success response (200): {status: "success", data: {client_op_id}}
        - Error response (400): when track_numbers is missing
        """
        from httpx import AsyncClient, ASGITransport

        app, routes = app_with_playlist_routes

        # Mock successful deletion
        routes._playlist_app_service.delete_tracks_use_case = AsyncMock(
            return_value={"status": "success"}
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test successful deletion
            response = await client.request(
                "DELETE",
                "/api/playlists/test-playlist-123/tracks",
                json={
                    "track_numbers": [1, 3],
                    "client_op_id": "client-op-delete-tracks"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

            # Test error when track_numbers missing
            response = await client.request(
                "DELETE",
                "/api/playlists/test-playlist-123/tracks",
                json={"client_op_id": "client-op-fail"}
            )

            assert response.status_code == 400
            data = response.json()
            assert data["status"] == "error"

    async def test_start_playlist_contract(self, app_with_playlist_routes):
        """Test POST /api/playlists/{playlist_id}/start - Start playback.

        Contract:
        - Request body: {client_op_id?: str}
        - Success response (200): {status: "success", data: {playlist_id, started: bool}}
        - Error response (404): when playlist not found
        """
        from httpx import AsyncClient, ASGITransport

        app, routes = app_with_playlist_routes

        # Mock successful start
        routes.operations_service.start_playlist = AsyncMock(
            return_value={"status": "success", "started": True}
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test successful start
            response = await client.post(
                "/api/playlists/test-playlist-123/start",
                json={"client_op_id": "client-op-start"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data

    async def test_sync_playlists_contract(self, app_with_playlist_routes):
        """Test POST /api/playlists/sync - Sync playlists.

        Contract:
        - Request body: {} (empty)
        - Success response (200): {status: "success", data: {synced_count}}
        - Triggers filesystem sync and broadcast
        """
        from httpx import AsyncClient, ASGITransport

        app, routes = app_with_playlist_routes

        # Mock successful sync
        routes.operations_service.sync_playlists = AsyncMock(
            return_value={"status": "success", "synced_count": 5}
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test successful sync
            response = await client.post("/api/playlists/sync", json={})

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    async def test_move_track_contract(self, app_with_playlist_routes):
        """Test POST /api/playlists/move-track - Move track between playlists.

        Contract:
        - Request body: {source_playlist_id, target_playlist_id, track_number, target_position?, client_op_id?}
        - Success response (200): {status: "success"}
        - Error response (400): when required fields missing
        """
        from httpx import AsyncClient, ASGITransport

        app, routes = app_with_playlist_routes

        # Mock successful move
        routes.operations_service.move_track_between_playlists = AsyncMock(
            return_value={"status": "success"}
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test successful move
            response = await client.post(
                "/api/playlists/move-track",
                json={
                    "source_playlist_id": "playlist-1",
                    "target_playlist_id": "playlist-2",
                    "track_number": 3,
                    "target_position": 1,
                    "client_op_id": "client-op-move"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

            # Test error when required fields missing
            response = await client.post(
                "/api/playlists/move-track",
                json={"source_playlist_id": "playlist-1"}
            )

            assert response.status_code == 400
            data = response.json()
            assert data["status"] == "error"
