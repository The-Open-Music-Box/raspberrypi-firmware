# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Tests for PlayerAPIRoutes."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.src.api.endpoints.player_api_routes import PlayerAPIRoutes
from app.src.services.response.unified_response_service import UnifiedResponseService


class TestPlayerAPIRoutes:
    """Test suite for PlayerAPIRoutes."""

    @pytest.fixture
    def mock_player_service(self):
        """Mock PlayerApplicationService."""
        service = Mock()
        service.play_use_case = AsyncMock(return_value={
            "success": True,
            "message": "Playback started",
            "status": {"is_playing": True}
        })
        service.pause_use_case = AsyncMock(return_value={
            "success": True,
            "message": "Playback paused",
            "status": {"is_playing": False}
        })
        service.stop_use_case = AsyncMock(return_value={
            "success": True,
            "message": "Playback stopped",
            "status": {"is_playing": False}
        })
        service.next_track_use_case = AsyncMock(return_value={
            "success": True,
            "message": "Next track",
            "track": {"id": "2", "title": "Next Track"},
            "status": {"current_track": {"id": "2"}}
        })
        service.previous_track_use_case = AsyncMock(return_value={
            "success": True,
            "message": "Previous track",
            "track": {"id": "1", "title": "Previous Track"},
            "status": {"current_track": {"id": "1"}}
        })
        service.seek_use_case = AsyncMock(return_value={
            "success": True,
            "message": "Seek completed",
            "status": {"position_ms": 30000}
        })
        service.set_volume_use_case = AsyncMock(return_value={
            "success": True,
            "message": "Volume set",
            "volume": 80
        })
        service.get_status_use_case = AsyncMock(return_value={
            "success": True,
            "message": "Status retrieved",
            "status": {"is_playing": False, "volume": 75}
        })
        return service

    @pytest.fixture
    def mock_broadcasting_service(self):
        """Mock PlayerBroadcastingService."""
        service = Mock()
        service.broadcast_playback_state_changed = AsyncMock()
        service.broadcast_track_changed = AsyncMock()
        service.broadcast_volume_changed = AsyncMock()
        service.broadcast_position_changed = AsyncMock()
        return service

    @pytest.fixture
    def mock_operations_service(self):
        """Mock PlayerOperationsService."""
        service = Mock()
        service.check_rate_limit_use_case = AsyncMock(return_value={"allowed": True})
        service.next_track_use_case = AsyncMock(return_value={
            "success": True,
            "track": {"id": "2"},
            "status": {"current_track": {"id": "2"}}
        })
        service.previous_track_use_case = AsyncMock(return_value={
            "success": True,
            "track": {"id": "1"},
            "status": {"current_track": {"id": "1"}}
        })
        service.toggle_playback_use_case = AsyncMock(return_value={
            "success": True,
            "state": "playing",
            "status": {"is_playing": True}
        })
        service.stop_progress_service_use_case = AsyncMock(return_value={"success": True})
        service.trigger_immediate_progress_use_case = AsyncMock(return_value={"success": True})
        return service

    @pytest.fixture
    def player_api_routes(self, mock_player_service, mock_broadcasting_service, mock_operations_service):
        """Create PlayerAPIRoutes instance."""
        return PlayerAPIRoutes(
            player_service=mock_player_service,
            broadcasting_service=mock_broadcasting_service,
            operations_service=mock_operations_service
        )

    @pytest.fixture
    def test_app(self, player_api_routes):
        """Create test FastAPI app."""
        app = FastAPI()
        app.include_router(player_api_routes.get_router())
        return app

    @pytest.fixture
    def test_client(self, test_app):
        """Create test client."""
        return TestClient(test_app)

    def test_play_endpoint_success(self, test_client, mock_player_service, mock_broadcasting_service):
        """Test successful play endpoint."""
        response = test_client.post("/api/player/play", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Playback started successfully"
        mock_player_service.play_use_case.assert_called_once()
        mock_broadcasting_service.broadcast_playback_state_changed.assert_called_once()

    def test_pause_endpoint_success(self, test_client, mock_player_service, mock_broadcasting_service):
        """Test successful pause endpoint."""
        response = test_client.post("/api/player/pause", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Playback paused successfully"
        mock_player_service.pause_use_case.assert_called_once()
        mock_broadcasting_service.broadcast_playback_state_changed.assert_called_once()

    def test_stop_endpoint_success(self, test_client, mock_player_service, mock_broadcasting_service, mock_operations_service):
        """Test successful stop endpoint."""
        response = test_client.post("/api/player/stop", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Playback stopped successfully"
        mock_player_service.stop_use_case.assert_called_once()
        mock_operations_service.stop_progress_service_use_case.assert_called_once()
        mock_broadcasting_service.broadcast_playback_state_changed.assert_called_once()

    def test_next_track_endpoint_success(self, test_client, mock_operations_service, mock_broadcasting_service):
        """Test successful next track endpoint."""
        response = test_client.post("/api/player/next", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Skipped to next track"
        mock_operations_service.next_track_use_case.assert_called_once()
        mock_broadcasting_service.broadcast_track_changed.assert_called_once()

    def test_previous_track_endpoint_success(self, test_client, mock_operations_service, mock_broadcasting_service):
        """Test successful previous track endpoint."""
        response = test_client.post("/api/player/previous", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Skipped to previous track"
        mock_operations_service.previous_track_use_case.assert_called_once()
        mock_broadcasting_service.broadcast_track_changed.assert_called_once()

    def test_toggle_endpoint_success(self, test_client, mock_operations_service, mock_broadcasting_service):
        """Test successful toggle endpoint."""
        response = test_client.post("/api/player/toggle", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Playback toggled to" in data["message"]
        mock_operations_service.toggle_playback_use_case.assert_called_once()
        mock_broadcasting_service.broadcast_playback_state_changed.assert_called_once()

    def test_status_endpoint_success(self, test_client, mock_player_service):
        """Test successful status endpoint."""
        response = test_client.get("/api/player/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Player status retrieved successfully"
        mock_player_service.get_status_use_case.assert_called_once()

    def test_seek_endpoint_success(self, test_client, mock_player_service, mock_broadcasting_service, mock_operations_service):
        """Test successful seek endpoint."""
        seek_data = {"position_ms": 30000}
        response = test_client.post("/api/player/seek", json=seek_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Seek operation completed successfully"
        mock_player_service.seek_use_case.assert_called_once_with(30000)
        mock_operations_service.trigger_immediate_progress_use_case.assert_called_once()
        mock_broadcasting_service.broadcast_position_changed.assert_called_once_with(30000)

    def test_volume_endpoint_success(self, test_client, mock_player_service, mock_broadcasting_service):
        """Test successful volume endpoint."""
        volume_data = {"volume": 80}
        response = test_client.post("/api/player/volume", json=volume_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Volume set to 80%"
        mock_player_service.set_volume_use_case.assert_called_once_with(80)
        mock_broadcasting_service.broadcast_volume_changed.assert_called_once_with(80)

    def test_rate_limiting(self, test_client, mock_operations_service):
        """Test rate limiting functionality."""
        mock_operations_service.check_rate_limit_use_case.return_value = {
            "allowed": False,
            "message": "Too many requests"
        }

        response = test_client.post("/api/player/play", json={})

        assert response.status_code == 429  # Rate limit error
        data = response.json()
        assert data["status"] == "error"
        assert "Too many requests" in data["message"]

    def test_service_failure_handling(self, test_client, mock_player_service):
        """Test handling of service failures."""
        mock_player_service.play_use_case.return_value = {
            "success": False,
            "message": "Failed to start playback"
        }

        response = test_client.post("/api/player/play", json={})

        # API returns 200 OK even for service failures (contract requirement)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Failed to start playback"

    def test_seek_validation(self, test_client):
        """Test seek input validation."""
        # Test negative position
        response = test_client.post("/api/player/seek", json={"position_ms": -1000})
        assert response.status_code == 422  # Validation error

        # Test too large position
        response = test_client.post("/api/player/seek", json={"position_ms": 90000000})
        assert response.status_code == 422  # Validation error

    def test_volume_validation(self, test_client):
        """Test volume input validation."""
        # Test negative volume
        response = test_client.post("/api/player/volume", json={"volume": -10})
        assert response.status_code == 422  # Validation error

        # Test too high volume
        response = test_client.post("/api/player/volume", json={"volume": 150})
        assert response.status_code == 422  # Validation error

    def test_missing_operations_service(self):
        """Test behavior when operations service is not provided."""
        from app.src.api.endpoints.player_api_routes import PlayerAPIRoutes

        mock_player_service = Mock()
        mock_broadcasting_service = Mock()

        # Should not raise exception
        routes = PlayerAPIRoutes(
            player_service=mock_player_service,
            broadcasting_service=mock_broadcasting_service,
            operations_service=None
        )

        assert routes._operations_service is None