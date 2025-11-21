# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Unit tests for StateSnapshotApplicationService

Tests the state snapshot functionality for newly connected WebSocket clients.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from app.src.application.services.state_snapshot_application_service import StateSnapshotApplicationService
from app.src.application.services.state_serialization_application_service import StateSerializationApplicationService
from app.src.services.sequence_generator import SequenceGenerator


@pytest.mark.asyncio
class TestStateSnapshotApplicationService:
    """Test suite for StateSnapshotApplicationService."""

    @pytest.fixture
    def mock_socketio(self):
        """Create mock Socket.IO server."""
        socketio = Mock()
        socketio.emit = AsyncMock()
        return socketio

    @pytest.fixture
    def mock_data_service(self):
        """Create mock data application service."""
        service = Mock()
        service.get_playlists_use_case = AsyncMock(return_value={
            "playlists": [
                {"id": "playlist-1", "name": "Test Playlist 1", "tracks": []},
                {"id": "playlist-2", "name": "Test Playlist 2", "tracks": []},
            ]
        })
        service.get_playlist_use_case = AsyncMock(return_value={
            "id": "playlist-1",
            "name": "Test Playlist 1",
            "tracks": [
                {"id": "track-1", "title": "Track 1"}
            ]
        })
        return service

    @pytest.fixture
    def snapshot_service(self, mock_socketio, mock_data_service):
        """Create StateSnapshotApplicationService with dependencies."""
        sequences = SequenceGenerator()
        serialization_service = StateSerializationApplicationService(sequences)
        return StateSnapshotApplicationService(
            mock_socketio,
            serialization_service,
            sequences,
            mock_data_service
        )

    async def test_initialization_with_data_service(self, snapshot_service, mock_data_service):
        """Test that StateSnapshotApplicationService is initialized with data_application_service."""
        assert snapshot_service._data_application_service is mock_data_service
        assert snapshot_service._data_application_service is not None

    async def test_initialization_without_data_service(self, mock_socketio):
        """Test that StateSnapshotApplicationService can be initialized without data_application_service."""
        sequences = SequenceGenerator()
        serialization_service = StateSerializationApplicationService(sequences)
        service = StateSnapshotApplicationService(
            mock_socketio,
            serialization_service,
            sequences,
            data_application_service=None
        )
        assert service._data_application_service is None

    async def test_send_playlists_snapshot_with_data_service(self, snapshot_service, mock_socketio, mock_data_service):
        """Test that playlists snapshot is sent with actual data when data_application_service is available."""
        client_id = "test-client-123"

        await snapshot_service._send_playlists_snapshot(client_id)

        # Verify data service was called
        mock_data_service.get_playlists_use_case.assert_called_once()

        # Verify emit was called
        assert mock_socketio.emit.called
        call_args = mock_socketio.emit.call_args
        event_name = call_args[0][0]
        event_data = call_args[0][1]

        # Verify event format
        assert event_name == "state:playlists"
        assert "data" in event_data
        assert "playlists" in event_data["data"]
        assert len(event_data["data"]["playlists"]) == 2
        # Verify playlists have required fields (serialization may transform the structure)
        assert "id" in event_data["data"]["playlists"][0]

    async def test_send_playlists_snapshot_without_data_service(self, mock_socketio):
        """Test that playlists snapshot sends empty array when data_application_service is None."""
        sequences = SequenceGenerator()
        serialization_service = StateSerializationApplicationService(sequences)
        service = StateSnapshotApplicationService(
            mock_socketio,
            serialization_service,
            sequences,
            data_application_service=None
        )

        client_id = "test-client-123"
        await service._send_playlists_snapshot(client_id)

        # Verify emit was called with empty playlists
        assert mock_socketio.emit.called
        call_args = mock_socketio.emit.call_args
        event_data = call_args[0][1]

        assert event_data["data"]["playlists"] == []

    async def test_send_playlist_snapshot_with_data_service(self, snapshot_service, mock_socketio, mock_data_service):
        """Test that specific playlist snapshot is sent with actual data."""
        client_id = "test-client-123"
        playlist_id = "playlist-1"

        await snapshot_service._send_playlist_snapshot(client_id, playlist_id)

        # Verify data service was called
        mock_data_service.get_playlist_use_case.assert_called_once_with(playlist_id)

        # Verify emit was called
        assert mock_socketio.emit.called
        call_args = mock_socketio.emit.call_args
        event_name = call_args[0][0]
        event_data = call_args[0][1]

        # Verify event format
        assert event_name == "state:playlist"
        assert "data" in event_data
        assert "id" in event_data["data"]  # Verify playlist data is present
        assert event_data["playlist_id"] == playlist_id

    async def test_send_state_snapshot_routes_to_playlists(self, snapshot_service, mock_socketio):
        """Test that send_state_snapshot routes to _send_playlists_snapshot for 'playlists' room."""
        client_id = "test-client-123"

        with patch.object(snapshot_service, '_send_playlists_snapshot', new=AsyncMock()) as mock_send:
            await snapshot_service.send_state_snapshot(client_id, "playlists")
            mock_send.assert_called_once_with(client_id)

    async def test_send_state_snapshot_routes_to_playlist(self, snapshot_service, mock_socketio):
        """Test that send_state_snapshot routes to _send_playlist_snapshot for 'playlist:id' room."""
        client_id = "test-client-123"
        playlist_id = "playlist-1"

        with patch.object(snapshot_service, '_send_playlist_snapshot', new=AsyncMock()) as mock_send:
            await snapshot_service.send_state_snapshot(client_id, f"playlist:{playlist_id}")
            mock_send.assert_called_once_with(client_id, playlist_id)

    async def test_send_state_snapshot_handles_unknown_room(self, snapshot_service, mock_socketio):
        """Test that send_state_snapshot handles unknown room types gracefully."""
        client_id = "test-client-123"

        # Should not raise exception for unknown room
        await snapshot_service.send_state_snapshot(client_id, "unknown-room")

        # Verify emit was not called
        assert not mock_socketio.emit.called

    async def test_playlists_snapshot_handles_service_error(self, mock_socketio, mock_data_service):
        """Test that playlists snapshot handles errors from data service gracefully."""
        # Make data service raise an exception
        mock_data_service.get_playlists_use_case = AsyncMock(side_effect=Exception("Database error"))

        sequences = SequenceGenerator()
        serialization_service = StateSerializationApplicationService(sequences)
        service = StateSnapshotApplicationService(
            mock_socketio,
            serialization_service,
            sequences,
            mock_data_service
        )

        client_id = "test-client-123"

        # Should not raise exception
        await service._send_playlists_snapshot(client_id)

        # Verify emit was still called with empty playlists
        assert mock_socketio.emit.called
        call_args = mock_socketio.emit.call_args
        event_data = call_args[0][1]
        assert event_data["data"]["playlists"] == []

    async def test_playlist_snapshot_handles_not_found(self, snapshot_service, mock_socketio, mock_data_service):
        """Test that playlist snapshot handles playlist not found gracefully."""
        # Make data service return None (playlist not found)
        mock_data_service.get_playlist_use_case = AsyncMock(return_value=None)

        client_id = "test-client-123"
        playlist_id = "nonexistent-playlist"

        await snapshot_service._send_playlist_snapshot(client_id, playlist_id)

        # Verify emit was NOT called (no snapshot for nonexistent playlist)
        assert not mock_socketio.emit.called

    async def test_player_state_snapshot_without_player_service(self, mock_socketio):
        """Test that player state snapshot handles missing player service gracefully."""
        sequences = SequenceGenerator()
        serialization_service = StateSerializationApplicationService(sequences)
        service = StateSnapshotApplicationService(
            mock_socketio,
            serialization_service,
            sequences,
            data_application_service=None,
            player_application_service=None  # No player service
        )

        client_id = "test-client-123"

        # Should not raise exception
        await service._send_player_state_snapshot(client_id)

        # Verify emit was NOT called (no player service available)
        assert not mock_socketio.emit.called

    async def test_player_state_snapshot_with_none_result(self, mock_socketio):
        """Test that player state snapshot handles None result from player service."""
        # Create mock player service that returns None
        mock_player_service = Mock()
        mock_player_service.get_status_use_case = AsyncMock(return_value=None)

        sequences = SequenceGenerator()
        serialization_service = StateSerializationApplicationService(sequences)
        service = StateSnapshotApplicationService(
            mock_socketio,
            serialization_service,
            sequences,
            data_application_service=None,
            player_application_service=mock_player_service
        )

        client_id = "test-client-123"

        # Should not raise exception
        await service._send_player_state_snapshot(client_id)

        # Verify emit was NOT called (None result handled)
        assert not mock_socketio.emit.called

    async def test_player_state_snapshot_with_error_result(self, mock_socketio):
        """Test that player state snapshot handles error result from player service."""
        # Create mock player service that returns error dict
        mock_player_service = Mock()
        mock_player_service.get_status_use_case = AsyncMock(return_value={
            "status": "error",
            "message": "Player error"
        })

        sequences = SequenceGenerator()
        serialization_service = StateSerializationApplicationService(sequences)
        service = StateSnapshotApplicationService(
            mock_socketio,
            serialization_service,
            sequences,
            data_application_service=None,
            player_application_service=mock_player_service
        )

        client_id = "test-client-123"

        # Should not raise exception
        await service._send_player_state_snapshot(client_id)

        # Verify emit was NOT called (error handled)
        assert not mock_socketio.emit.called

    async def test_player_state_snapshot_with_valid_state(self, mock_socketio):
        """Test that player state snapshot sends valid player state."""
        # Create mock player service with valid response
        mock_player_service = Mock()
        mock_player_service.get_status_use_case = AsyncMock(return_value={
            "success": True,
            "status": {
                "is_playing": True,
                "active_playlist_id": "playlist-123",
                "active_track": {"id": "track-1", "title": "Test Track"}
            }
        })

        sequences = SequenceGenerator()
        serialization_service = StateSerializationApplicationService(sequences)
        service = StateSnapshotApplicationService(
            mock_socketio,
            serialization_service,
            sequences,
            data_application_service=None,
            player_application_service=mock_player_service
        )

        client_id = "test-client-123"

        await service._send_player_state_snapshot(client_id)

        # Verify emit was called with player state
        assert mock_socketio.emit.called
        call_args = mock_socketio.emit.call_args
        event_name = call_args[0][0]
        event_data = call_args[0][1]

        # Verify event format
        assert event_name == "state:player"
        assert "data" in event_data
        assert event_data["data"]["is_playing"] is True
        assert event_data["data"]["active_playlist_id"] == "playlist-123"
