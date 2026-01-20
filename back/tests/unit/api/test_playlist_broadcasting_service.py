# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Tests for PlaylistBroadcastingService (DDD Architecture)

Comprehensive tests for the WebSocket broadcasting service.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.src.api.services.playlist_broadcasting_service import PlaylistBroadcastingService
from app.src.common.socket_events import StateEventType


class TestPlaylistBroadcastingService:
    """Test suite for PlaylistBroadcastingService."""

    @pytest.fixture
    def mock_state_manager(self):
        """Mock StateManager."""
        state_manager = Mock()
        state_manager.broadcast_state_change = AsyncMock()
        state_manager.get_global_sequence = Mock(return_value=123)
        return state_manager

    @pytest.fixture
    def broadcasting_service(self, mock_state_manager):
        """Create PlaylistBroadcastingService instance."""
        return PlaylistBroadcastingService(mock_state_manager)

    @pytest.mark.asyncio
    async def test_broadcast_playlist_created(self, broadcasting_service, mock_state_manager):
        """Test broadcasting playlist creation event."""
        # Arrange
        playlist_id = "test-playlist-id"
        playlist_data = {"id": playlist_id, "title": "Test Playlist", "tracks": []}

        # Act
        await broadcasting_service.broadcast_playlist_created(playlist_id, playlist_data)

        # Assert
        mock_state_manager.broadcast_state_change.assert_called_once()
        call_args = mock_state_manager.broadcast_state_change.call_args
        assert call_args[0][0] == StateEventType.PLAYLIST_CREATED
        event_data = call_args[0][1]
        assert event_data["playlist_id"] == playlist_id
        assert event_data["playlist"] == playlist_data
        assert event_data["operation"] == "create"

    @pytest.mark.asyncio
    async def test_broadcast_playlist_updated(self, broadcasting_service, mock_state_manager):
        """Test broadcasting playlist update event."""
        # Arrange
        playlist_id = "test-playlist-id"
        updates = {"title": "Updated Title", "description": "Updated description"}

        # Act
        await broadcasting_service.broadcast_playlist_updated(playlist_id, updates)

        # Assert
        mock_state_manager.broadcast_state_change.assert_called_once()
        call_args = mock_state_manager.broadcast_state_change.call_args
        assert call_args[0][0] == StateEventType.PLAYLIST_UPDATED
        event_data = call_args[0][1]
        assert event_data["playlist_id"] == playlist_id
        assert event_data["updates"] == updates
        assert event_data["operation"] == "update"

    @pytest.mark.asyncio
    async def test_broadcast_playlist_deleted(self, broadcasting_service, mock_state_manager):
        """Test broadcasting playlist deletion event."""
        # Arrange
        playlist_id = "test-playlist-id"

        # Act
        await broadcasting_service.broadcast_playlist_deleted(playlist_id)

        # Assert
        mock_state_manager.broadcast_state_change.assert_called_once()
        call_args = mock_state_manager.broadcast_state_change.call_args
        assert call_args[0][0] == StateEventType.PLAYLIST_DELETED
        event_data = call_args[0][1]
        assert event_data["playlist_id"] == playlist_id
        assert event_data["operation"] == "delete"

    @pytest.mark.asyncio
    async def test_broadcast_track_added(self, broadcasting_service, mock_state_manager):
        """Test broadcasting track addition event."""
        # Arrange
        playlist_id = "test-playlist-id"
        track_data = {"id": "track-1", "title": "Test Track", "track_number": 1}

        # Act
        await broadcasting_service.broadcast_track_added(playlist_id, track_data)

        # Assert
        mock_state_manager.broadcast_state_change.assert_called_once()
        call_args = mock_state_manager.broadcast_state_change.call_args
        assert call_args[0][0] == StateEventType.TRACK_ADDED
        event_data = call_args[0][1]
        assert event_data["playlist_id"] == playlist_id
        assert event_data["track"] == track_data
        assert event_data["operation"] == "add_track"

    @pytest.mark.asyncio
    async def test_broadcast_tracks_deleted(self, broadcasting_service, mock_state_manager):
        """Test broadcasting track deletion event."""
        # Arrange
        playlist_id = "test-playlist-id"
        track_numbers = [1, 3, 5]

        # Act
        await broadcasting_service.broadcast_tracks_deleted(playlist_id, track_numbers)

        # Assert
        mock_state_manager.broadcast_state_change.assert_called_once()
        call_args = mock_state_manager.broadcast_state_change.call_args
        assert call_args[0][0] == StateEventType.TRACKS_DELETED
        event_data = call_args[0][1]
        assert event_data["playlist_id"] == playlist_id
        assert event_data["track_numbers"] == track_numbers
        assert event_data["operation"] == "delete_tracks"

    @pytest.mark.asyncio
    async def test_broadcast_tracks_reordered(self, broadcasting_service, mock_state_manager):
        """Test broadcasting track reordering event."""
        # Arrange
        playlist_id = "test-playlist-id"
        track_order = [3, 1, 2, 4]

        # Act
        await broadcasting_service.broadcast_tracks_reordered(playlist_id, track_order)

        # Assert
        mock_state_manager.broadcast_state_change.assert_called_once()
        call_args = mock_state_manager.broadcast_state_change.call_args
        assert call_args[0][0] == StateEventType.TRACKS_REORDERED
        event_data = call_args[0][1]
        assert event_data["playlist_id"] == playlist_id
        assert event_data["track_order"] == track_order
        assert event_data["operation"] == "reorder_tracks"

    @pytest.mark.asyncio
    async def test_broadcast_playlist_started(self, broadcasting_service, mock_state_manager):
        """Test broadcasting playlist started event."""
        # Arrange
        playlist_id = "test-playlist-id"
        track_data = {"id": "track-1", "title": "Current Track"}

        # Act
        await broadcasting_service.broadcast_playlist_started(playlist_id, track_data)

        # Assert
        mock_state_manager.broadcast_state_change.assert_called_once()
        call_args = mock_state_manager.broadcast_state_change.call_args
        assert call_args[0][0] == StateEventType.PLAYLIST_STARTED
        event_data = call_args[0][1]
        assert event_data["playlist_id"] == playlist_id
        assert event_data["current_track"] == track_data
        assert event_data["operation"] == "start_playlist"

    @pytest.mark.asyncio
    async def test_broadcast_playlist_started_without_track(self, broadcasting_service, mock_state_manager):
        """Test broadcasting playlist started event without track data."""
        # Arrange
        playlist_id = "test-playlist-id"

        # Act
        await broadcasting_service.broadcast_playlist_started(playlist_id)

        # Assert
        mock_state_manager.broadcast_state_change.assert_called_once()
        call_args = mock_state_manager.broadcast_state_change.call_args
        event_data = call_args[0][1]
        assert event_data["playlist_id"] == playlist_id
        assert "current_track" not in event_data
        assert event_data["operation"] == "start_playlist"

    @pytest.mark.asyncio
    async def test_broadcast_nfc_associated(self, broadcasting_service, mock_state_manager):
        """Test broadcasting NFC association event."""
        # Arrange
        playlist_id = "test-playlist-id"
        nfc_tag_id = "nfc-tag-123"

        # Act
        await broadcasting_service.broadcast_nfc_associated(playlist_id, nfc_tag_id)

        # Assert
        mock_state_manager.broadcast_state_change.assert_called_once()
        call_args = mock_state_manager.broadcast_state_change.call_args
        assert call_args[0][0] == StateEventType.NFC_ASSOCIATED
        event_data = call_args[0][1]
        assert event_data["playlist_id"] == playlist_id
        assert event_data["nfc_tag_id"] == nfc_tag_id
        assert event_data["operation"] == "nfc_associate"

    @pytest.mark.asyncio
    async def test_broadcast_nfc_disassociated(self, broadcasting_service, mock_state_manager):
        """Test broadcasting NFC disassociation event."""
        # Arrange
        playlist_id = "test-playlist-id"

        # Act
        await broadcasting_service.broadcast_nfc_disassociated(playlist_id)

        # Assert
        mock_state_manager.broadcast_state_change.assert_called_once()
        call_args = mock_state_manager.broadcast_state_change.call_args
        assert call_args[0][0] == StateEventType.NFC_DISASSOCIATED
        event_data = call_args[0][1]
        assert event_data["playlist_id"] == playlist_id
        assert event_data["operation"] == "nfc_disassociate"

    @pytest.mark.asyncio
    async def test_broadcast_playlists_synced(self, broadcasting_service, mock_state_manager):
        """Test broadcasting playlists synchronization event."""
        # Arrange
        playlists_data = [
            {"id": "1", "title": "Playlist 1"},
            {"id": "2", "title": "Playlist 2"}
        ]

        # Act
        await broadcasting_service.broadcast_playlists_synced(playlists_data)

        # Assert
        mock_state_manager.broadcast_state_change.assert_called_once()
        call_args = mock_state_manager.broadcast_state_change.call_args
        assert call_args[0][0] == StateEventType.PLAYLISTS_SNAPSHOT
        event_data = call_args[0][1]
        assert event_data["playlists"] == playlists_data
        assert event_data["operation"] == "sync"

    def test_get_global_sequence(self, broadcasting_service, mock_state_manager):
        """Test getting global sequence number."""
        # Act
        sequence = broadcasting_service.get_global_sequence()

        # Assert
        assert sequence == 123
        mock_state_manager.get_global_sequence.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_in_broadcast_methods(self, broadcasting_service, mock_state_manager):
        """Test error handling in broadcast methods."""
        # Arrange
        mock_state_manager.broadcast_state_change.side_effect = Exception("Broadcast error")

        # Act & Assert - should not raise exceptions
        await broadcasting_service.broadcast_playlist_created("test-id", {})
        await broadcasting_service.broadcast_playlist_updated("test-id", {})
        await broadcasting_service.broadcast_playlist_deleted("test-id")
        await broadcasting_service.broadcast_track_added("test-id", {})
        await broadcasting_service.broadcast_tracks_deleted("test-id", [])
        await broadcasting_service.broadcast_tracks_reordered("test-id", [])
        await broadcasting_service.broadcast_playlist_started("test-id")
        await broadcasting_service.broadcast_nfc_associated("test-id", "nfc")
        await broadcasting_service.broadcast_nfc_disassociated("test-id")
        await broadcasting_service.broadcast_playlists_synced([])

        # All methods should have been called despite errors
        assert mock_state_manager.broadcast_state_change.call_count == 10

    @pytest.mark.asyncio
    async def test_single_responsibility_principle(self, broadcasting_service):
        """Test that the service follows Single Responsibility Principle."""
        # The service should only handle broadcasting, not business logic or HTTP handling
        assert hasattr(broadcasting_service, '_state_manager')

        # Should not have business logic methods
        assert not hasattr(broadcasting_service, 'create_playlist')
        assert not hasattr(broadcasting_service, 'update_playlist')
        assert not hasattr(broadcasting_service, 'handle_request')

        # Should have only broadcasting methods
        broadcast_methods = [
            'broadcast_playlist_created',
            'broadcast_playlist_updated',
            'broadcast_playlist_deleted',
            'broadcast_track_added',
            'broadcast_tracks_deleted',
            'broadcast_tracks_reordered',
            'broadcast_playlist_started',
            'broadcast_nfc_associated',
            'broadcast_nfc_disassociated',
            'broadcast_playlists_synced'
        ]

        for method in broadcast_methods:
            assert hasattr(broadcasting_service, method)

    def test_service_initialization(self, mock_state_manager):
        """Test service initialization."""
        # Act
        service = PlaylistBroadcastingService(mock_state_manager)

        # Assert
        assert service._state_manager == mock_state_manager

    def test_service_initialization_requires_state_manager(self):
        """Test that service requires state manager."""
        # Act & Assert
        with pytest.raises(TypeError):
            PlaylistBroadcastingService()  # Missing required argument