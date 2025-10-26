# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Tests for PlaylistAPIRoutes (DDD Architecture)

Comprehensive tests for the clean API routes implementation.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Updated import: now using modular playlist API
from app.src.api.endpoints.playlist import PlaylistAPIRoutes
from app.src.services.response.unified_response_service import UnifiedResponseService


class TestPlaylistAPIRoutes:
    """Test suite for PlaylistAPIRoutes."""

    @pytest.fixture
    def mock_playlist_service(self):
        """Mock playlist application service."""
        service = Mock()
        service.get_playlists_use_case = AsyncMock()
        service.create_playlist_use_case = AsyncMock()
        service.get_playlist_use_case = AsyncMock()
        service.delete_playlist_use_case = AsyncMock()
        service.reorder_tracks_use_case = AsyncMock()
        service.delete_tracks_use_case = AsyncMock()
        return service

    @pytest.fixture
    def mock_broadcasting_service(self):
        """Mock broadcasting service."""
        service = Mock()
        service.broadcast_playlist_created = AsyncMock()
        service.broadcast_playlist_updated = AsyncMock()
        service.broadcast_playlist_deleted = AsyncMock()
        service.broadcast_tracks_reordered = AsyncMock()
        service.broadcast_tracks_deleted = AsyncMock()
        return service

    @pytest.fixture
    def mock_operations_service(self):
        """Mock operations service."""
        service = Mock()
        service.update_playlist_use_case = AsyncMock()
        service.reorder_tracks_use_case = AsyncMock()
        return service

    @pytest.fixture
    def playlist_routes(self, mock_playlist_service, mock_broadcasting_service, mock_operations_service):
        """Create PlaylistAPIRoutes instance."""
        return PlaylistAPIRoutes(
            playlist_service=mock_playlist_service,
            broadcasting_service=mock_broadcasting_service,
            operations_service=mock_operations_service
        )

    @pytest.fixture
    def app(self, playlist_routes):
        """Create FastAPI app with routes."""
        app = FastAPI()
        app.include_router(playlist_routes.router)
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_list_playlists_success(self, client, mock_playlist_service):
        """Test successful playlist listing."""
        # Arrange
        mock_playlists = [
            {"id": "1", "title": "Test Playlist 1", "tracks": []},
            {"id": "2", "title": "Test Playlist 2", "tracks": []}
        ]
        # DDD service returns raw domain data directly
        mock_playlist_service.get_playlists_use_case.return_value = {
            "playlists": mock_playlists,
            "total": len(mock_playlists),
            "page": 1,
            "page_size": 50,
            "total_pages": 1
        }

        with patch("app.src.services.serialization.unified_serialization_service.UnifiedSerializationService.serialize_bulk_playlists") as mock_serialize:
            mock_serialize.return_value = mock_playlists

            # Act
            response = client.get("/api/playlists")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data
            assert "playlists" in data["data"]
            mock_playlist_service.get_playlists_use_case.assert_called_once_with(page=1, page_size=50)

    @pytest.mark.asyncio
    async def test_list_playlists_with_pagination(self, client, mock_playlist_service):
        """Test playlist listing with pagination."""
        # Arrange
        # DDD service returns raw domain data directly
        mock_playlist_service.get_playlists_use_case.return_value = {
            "playlists": [],
            "total": 0,
            "page": 2,
            "page_size": 10,
            "total_pages": 0
        }

        with patch("app.src.services.serialization.unified_serialization_service.UnifiedSerializationService.serialize_bulk_playlists") as mock_serialize:
            mock_serialize.return_value = []

            # Act
            response = client.get("/api/playlists?page=2&limit=10")

            # Assert
            assert response.status_code == 200
            mock_playlist_service.get_playlists_use_case.assert_called_once_with(page=2, page_size=10)

    @pytest.mark.asyncio
    async def test_create_playlist_success(self, client, mock_playlist_service, mock_broadcasting_service):
        """Test successful playlist creation."""
        # Arrange
        playlist_data = {"title": "New Playlist", "description": "Test description"}
        mock_playlist_service.create_playlist_use_case.return_value = {
            "id": "new-id",
            "title": "New Playlist",
            "description": "Test description"
        }
        mock_playlist_service.get_playlist_use_case.return_value = {
            "status": "success",
            "playlist": {"id": "new-id", "title": "New Playlist", "description": "Test description"}
        }

        with patch("app.src.services.validation.unified_validation_service.UnifiedValidationService.validate_playlist_data") as mock_validate:
            mock_validate.return_value = (True, [])

            with patch("app.src.services.serialization.unified_serialization_service.UnifiedSerializationService.serialize_playlist") as mock_serialize:
                mock_serialize.return_value = {"id": "new-id", "title": "New Playlist"}

                # Act
                response = client.post("/api/playlists", json=playlist_data)

                # Assert
                assert response.status_code == 201
                data = response.json()
                assert data["status"] == "success"
                mock_playlist_service.create_playlist_use_case.assert_called_once_with("New Playlist", "Test description")
                mock_broadcasting_service.broadcast_playlist_created.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_playlist_validation_error(self, client):
        """Test playlist creation with validation error."""
        # Arrange
        playlist_data = {"title": ""}  # Invalid empty title

        with patch("app.src.services.validation.unified_validation_service.UnifiedValidationService.validate_playlist_data") as mock_validate:
            mock_validate.return_value = (False, ["Title is required"])

            # Act
            response = client.post("/api/playlists", json=playlist_data)

            # Assert
            assert response.status_code == 400
            data = response.json()
            assert data["status"] == "error"
            assert "validation" in data["error_type"]

    @pytest.mark.asyncio
    async def test_get_playlist_success(self, client, mock_playlist_service):
        """Test successful playlist retrieval."""
        # Arrange
        playlist_id = "playlist-123"
        mock_playlist_data = {"id": playlist_id, "title": "Test Playlist", "tracks": []}
        mock_playlist_service.get_playlist_use_case.return_value = {
            "status": "success",
            "playlist": mock_playlist_data
        }

        with patch("app.src.services.serialization.unified_serialization_service.UnifiedSerializationService.serialize_playlist") as mock_serialize:
            mock_serialize.return_value = mock_playlist_data

            # Act
            response = client.get(f"/api/playlists/{playlist_id}")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            # Contract expects PlaylistDetailed directly in data, not wrapped in "playlist"
            assert "id" in data["data"], "Response must have id field per contract"
            assert data["data"]["id"] == playlist_id
            mock_playlist_service.get_playlist_use_case.assert_called_once_with(playlist_id)

    @pytest.mark.asyncio
    async def test_get_playlist_not_found(self, client, mock_playlist_service):
        """Test playlist retrieval when playlist doesn't exist."""
        # Arrange
        playlist_id = "non-existent"
        # DDD service returns None directly when playlist not found
        mock_playlist_service.get_playlist_use_case.return_value = None

        # Act
        response = client.get(f"/api/playlists/{playlist_id}")

        # Assert
        assert response.status_code == 404
        data = response.json()
        assert data["status"] == "error"
        assert "not found" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_update_playlist_success(self, client, mock_playlist_service, mock_broadcasting_service, mock_operations_service):
        """Test successful playlist update."""
        # Arrange
        playlist_id = "playlist-123"
        update_data = {"title": "Updated Title", "description": "Updated description"}

        # Configure mock to return success
        mock_playlist_service.update_playlist_use_case = AsyncMock(return_value=True)

        # Act
        response = client.put(f"/api/playlists/{playlist_id}", json=update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        mock_playlist_service.update_playlist_use_case.assert_called_once_with(
            playlist_id, {"title": "Updated Title", "description": "Updated description"}
        )

    @pytest.mark.asyncio
    async def test_update_playlist_no_updates(self, client):
        """Test playlist update with no valid updates."""
        # Arrange
        playlist_id = "playlist-123"
        update_data = {}  # No updates

        # Act
        response = client.put(f"/api/playlists/{playlist_id}", json=update_data)

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert data["status"] == "error"
        assert "no valid updates" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_delete_playlist_success(self, client, mock_playlist_service, mock_broadcasting_service):
        """Test successful playlist deletion."""
        # Arrange
        playlist_id = "playlist-123"

        # Configure mock to return success
        mock_playlist_service.delete_playlist_use_case.return_value = True

        # Act
        response = client.request("DELETE", f"/api/playlists/{playlist_id}", json={})

        # Assert
        assert response.status_code == 204  # API returns 204 No Content for successful deletion
        mock_playlist_service.delete_playlist_use_case.assert_called_once_with(playlist_id)

    @pytest.mark.asyncio
    async def test_reorder_tracks_success(self, client, mock_playlist_service, mock_broadcasting_service):
        """Test successful track reordering."""
        # Arrange
        playlist_id = "playlist-123"
        reorder_data = {"track_order": [3, 1, 2]}

        with patch("app.src.api.services.playlist_operations_service.PlaylistOperationsService") as mock_ops:
            mock_ops_instance = Mock()
            mock_ops_instance.reorder_tracks_use_case = AsyncMock(return_value={"status": "success"})
            mock_ops.return_value = mock_ops_instance

            # Mock the operations service in the routes
            with patch.object(mock_playlist_service, "reorder_tracks_use_case", AsyncMock(return_value={"status": "success"})):
                # Act
                response = client.post(f"/api/playlists/{playlist_id}/reorder", json=reorder_data)

                # Assert
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_reorder_tracks_invalid_data(self, client):
        """Test track reordering with invalid data."""
        # Arrange
        playlist_id = "playlist-123"
        reorder_data = {"track_order": "not-a-list"}  # Invalid data

        # Act
        response = client.post(f"/api/playlists/{playlist_id}/reorder", json=reorder_data)

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert data["status"] == "error"
        assert "list" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_delete_tracks_success(self, client, mock_playlist_service, mock_broadcasting_service):
        """Test successful track deletion."""
        # Arrange
        playlist_id = "playlist-123"
        delete_data = {"track_numbers": [1, 3]}

        # Configure mock to return success
        mock_playlist_service.delete_tracks_use_case.return_value = {"status": "success"}

        # Act
        response = client.request("DELETE", f"/api/playlists/{playlist_id}/tracks", json=delete_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        mock_playlist_service.delete_tracks_use_case.assert_called_once_with(playlist_id, [1, 3])

    @pytest.mark.asyncio
    async def test_delete_tracks_invalid_data(self, client):
        """Test track deletion with invalid data."""
        # Arrange
        playlist_id = "playlist-123"
        delete_data = {"track_numbers": "not-a-list"}  # Invalid data

        # Act
        response = client.request("DELETE", f"/api/playlists/{playlist_id}/tracks", json=delete_data)

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert data["status"] == "error"
        assert "list" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_error_handling(self, client, mock_playlist_service):
        """Test error handling in routes."""
        # Arrange
        mock_playlist_service.get_playlists_use_case.side_effect = Exception("Database error")

        # Act
        response = client.get("/api/playlists")

        # Assert
        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "error"
        assert "internal" in data["error_type"].lower()

    def test_router_configuration(self, playlist_routes):
        """Test router configuration."""
        router = playlist_routes.get_router()
        assert router.prefix == "/api/playlists"
        assert "playlists" in router.tags

        # Check that routes are registered
        route_paths = [route.path for route in router.routes]
        expected_paths = [
            "/api/playlists",
            "/api/playlists/",
            "/api/playlists/{playlist_id}",
            "/api/playlists/{playlist_id}/reorder",
            "/api/playlists/{playlist_id}/tracks"
        ]

        for expected_path in expected_paths:
            assert any(expected_path in path for path in route_paths), f"Missing route: {expected_path}"

    def test_single_responsibility_principle(self, playlist_routes):
        """Test that the class follows Single Responsibility Principle."""
        # The class should only handle router aggregation, not business logic
        # With direct registration architecture, sub-modules receive services directly
        assert hasattr(playlist_routes, 'router')

        # Should not have business logic methods
        assert not hasattr(playlist_routes, 'create_playlist')
        assert not hasattr(playlist_routes, 'update_playlist')
        assert not hasattr(playlist_routes, 'broadcast_state')