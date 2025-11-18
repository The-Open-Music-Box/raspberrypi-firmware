# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Tests for unified broadcasting service."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.src.services.broadcasting.unified_broadcasting_service import (
    UnifiedBroadcastingService,
)
from app.src.common.socket_events import StateEventType
from app.src.domain.audio.engine.state_manager import StateManager


class TestUnifiedBroadcastingServiceInit:
    """Test UnifiedBroadcastingService initialization."""

    def test_init(self):
        """Test initialization with state manager."""
        state_manager = Mock(spec=StateManager)
        service = UnifiedBroadcastingService(state_manager)

        assert service.state_manager == state_manager
        assert service._broadcast_count == 0
        assert service._acknowledgment_count == 0


class TestBroadcastWithAcknowledgment:
    """Test broadcast_with_acknowledgment method."""

    @pytest.mark.asyncio
    async def test_broadcast_without_acknowledgment(self):
        """Test broadcasting without client_op_id (no acknowledgment)."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()

        service = UnifiedBroadcastingService(state_manager)

        result = await service.broadcast_with_acknowledgment(
            event_type=StateEventType.PLAYER_STATE,
            data={"is_playing": True},
        )

        assert result is True
        state_manager.broadcast_state_change.assert_called_once_with(
            StateEventType.PLAYER_STATE, {"is_playing": True}, None
        )
        assert service._broadcast_count == 1
        assert service._acknowledgment_count == 0

    @pytest.mark.asyncio
    async def test_broadcast_with_acknowledgment(self):
        """Test broadcasting with client_op_id (includes acknowledgment)."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()
        state_manager.send_acknowledgment = AsyncMock()

        service = UnifiedBroadcastingService(state_manager)

        result = await service.broadcast_with_acknowledgment(
            event_type=StateEventType.PLAYER_STATE,
            data={"is_playing": True},
            client_op_id="op-123",
        )

        assert result is True
        state_manager.broadcast_state_change.assert_called_once()
        state_manager.send_acknowledgment.assert_called_once_with(
            "op-123", True, {"is_playing": True}
        )
        assert service._broadcast_count == 1
        assert service._acknowledgment_count == 1

    @pytest.mark.asyncio
    async def test_broadcast_with_custom_acknowledgment_data(self):
        """Test broadcasting with custom acknowledgment data."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()
        state_manager.send_acknowledgment = AsyncMock()

        service = UnifiedBroadcastingService(state_manager)

        custom_ack = {"status": "success", "message": "Operation completed"}
        result = await service.broadcast_with_acknowledgment(
            event_type=StateEventType.PLAYER_STATE,
            data={"is_playing": True},
            client_op_id="op-456",
            acknowledge_data=custom_ack,
        )

        assert result is True
        state_manager.send_acknowledgment.assert_called_once_with(
            "op-456", True, custom_ack
        )

    @pytest.mark.asyncio
    async def test_broadcast_to_specific_room(self):
        """Test broadcasting to a specific room."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()

        service = UnifiedBroadcastingService(state_manager)

        result = await service.broadcast_with_acknowledgment(
            event_type=StateEventType.PLAYER_STATE,
            data={"is_playing": True},
            room="player-room",
        )

        assert result is True
        state_manager.broadcast_state_change.assert_called_once_with(
            StateEventType.PLAYER_STATE, {"is_playing": True}, "player-room"
        )

    @pytest.mark.asyncio
    async def test_broadcast_failure_acknowledgment(self):
        """Test broadcasting with failure acknowledgment."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()
        state_manager.send_acknowledgment = AsyncMock()

        service = UnifiedBroadcastingService(state_manager)

        result = await service.broadcast_with_acknowledgment(
            event_type=StateEventType.ERROR,
            data={"error": "Operation failed"},
            client_op_id="op-789",
            acknowledge_success=False,
        )

        assert result is True
        state_manager.send_acknowledgment.assert_called_once_with(
            "op-789", False, {"error": "Operation failed"}
        )


class TestBroadcastPlaylistChange:
    """Test broadcast_playlist_change method."""

    @pytest.mark.asyncio
    async def test_broadcast_playlist_change_with_data(self):
        """Test broadcasting playlist change with data."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()
        state_manager.send_acknowledgment = AsyncMock()

        service = UnifiedBroadcastingService(state_manager)

        playlist_data = {"id": "pl-123", "title": "My Playlist"}
        result = await service.broadcast_playlist_change(
            playlist_id="pl-123",
            change_type="created",
            playlist_data=playlist_data,
            client_op_id="op-abc",
        )

        assert result is True
        # Should broadcast to playlists room
        assert state_manager.broadcast_state_change.call_count >= 1
        # Should send acknowledgment
        state_manager.send_acknowledgment.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_playlist_change_without_data(self):
        """Test broadcasting playlist change without playlist data."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()

        service = UnifiedBroadcastingService(state_manager)

        result = await service.broadcast_playlist_change(
            playlist_id="pl-456", change_type="deleted"
        )

        assert result is True
        state_manager.broadcast_state_change.assert_called()

    @pytest.mark.asyncio
    async def test_broadcast_playlist_change_to_specific_room(self):
        """Test playlist broadcast to both global and specific rooms."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()

        service = UnifiedBroadcastingService(state_manager)

        playlist_data = {"id": "pl-789", "title": "Another Playlist"}
        result = await service.broadcast_playlist_change(
            playlist_id="pl-789",
            change_type="updated",
            playlist_data=playlist_data,
        )

        assert result is True
        # Should broadcast to both playlists room and specific playlist room
        assert state_manager.broadcast_state_change.call_count >= 2


class TestBroadcastPlayerState:
    """Test broadcast_player_state method."""

    @pytest.mark.asyncio
    async def test_broadcast_player_state_basic(self):
        """Test broadcasting basic player state."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()
        state_manager.send_acknowledgment = AsyncMock()

        service = UnifiedBroadcastingService(state_manager)

        state_data = {"is_playing": True, "volume": 75}
        result = await service.broadcast_player_state(state_data)

        assert result is True
        state_manager.broadcast_state_change.assert_called_once()
        # Should add timestamp
        call_args = state_manager.broadcast_state_change.call_args
        assert "timestamp" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_broadcast_player_state_with_acknowledgment(self):
        """Test broadcasting player state with acknowledgment."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()
        state_manager.send_acknowledgment = AsyncMock()

        service = UnifiedBroadcastingService(state_manager)

        state_data = {"is_playing": False}
        result = await service.broadcast_player_state(
            state_data, client_op_id="op-player"
        )

        assert result is True
        state_manager.send_acknowledgment.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_player_state_without_position(self):
        """Test broadcasting player state without position."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()

        service = UnifiedBroadcastingService(state_manager)

        state_data = {"is_playing": True, "position_ms": 5000}
        result = await service.broadcast_player_state(
            state_data, include_position=False
        )

        assert result is True
        # position_ms should be removed from broadcasted data
        call_args = state_manager.broadcast_state_change.call_args
        broadcasted_data = call_args[0][1]
        assert "position_ms" not in broadcasted_data

    @pytest.mark.asyncio
    async def test_broadcast_player_state_with_timestamp(self):
        """Test that timestamp is preserved if already present."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()

        service = UnifiedBroadcastingService(state_manager)

        existing_timestamp = 1234567890.0
        state_data = {"is_playing": True, "timestamp": existing_timestamp}
        result = await service.broadcast_player_state(state_data)

        assert result is True
        call_args = state_manager.broadcast_state_change.call_args
        assert call_args[0][1]["timestamp"] == existing_timestamp


class TestBroadcastTrackProgress:
    """Test broadcast_track_progress method."""

    @pytest.mark.asyncio
    async def test_broadcast_track_progress_basic(self):
        """Test broadcasting basic track progress."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()

        service = UnifiedBroadcastingService(state_manager)

        result = await service.broadcast_track_progress(
            position_ms=30000, duration_ms=180000
        )

        assert result is True
        state_manager.broadcast_state_change.assert_called_once()
        call_args = state_manager.broadcast_state_change.call_args
        data = call_args[0][1]
        assert data["position_ms"] == 30000
        assert data["duration_ms"] == 180000
        assert abs(data["progress_percentage"] - 16.67) < 0.1

    @pytest.mark.asyncio
    async def test_broadcast_track_progress_with_ids(self):
        """Test broadcasting track progress with track and playlist IDs."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()

        service = UnifiedBroadcastingService(state_manager)

        result = await service.broadcast_track_progress(
            position_ms=60000,
            duration_ms=240000,
            track_id="track-123",
            playlist_id="pl-456",
        )

        assert result is True
        call_args = state_manager.broadcast_state_change.call_args
        data = call_args[0][1]
        assert data["track_id"] == "track-123"
        assert data["playlist_id"] == "pl-456"

    @pytest.mark.asyncio
    async def test_broadcast_track_progress_zero_duration(self):
        """Test broadcasting progress with zero duration."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()

        service = UnifiedBroadcastingService(state_manager)

        result = await service.broadcast_track_progress(
            position_ms=1000, duration_ms=0
        )

        assert result is True
        call_args = state_manager.broadcast_state_change.call_args
        data = call_args[0][1]
        assert data["progress_percentage"] == 0


class TestBroadcastError:
    """Test broadcast_error method."""

    @pytest.mark.asyncio
    async def test_broadcast_error_basic(self):
        """Test broadcasting basic error."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()

        service = UnifiedBroadcastingService(state_manager)

        result = await service.broadcast_error(
            error_message="Something went wrong", error_type="validation"
        )

        assert result is True
        state_manager.broadcast_state_change.assert_called_once()
        call_args = state_manager.broadcast_state_change.call_args
        data = call_args[0][1]
        assert data["error"] == "Something went wrong"
        assert data["error_type"] == "validation"

    @pytest.mark.asyncio
    async def test_broadcast_error_with_acknowledgment(self):
        """Test broadcasting error with client_op_id."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()
        state_manager.send_acknowledgment = AsyncMock()

        service = UnifiedBroadcastingService(state_manager)

        result = await service.broadcast_error(
            error_message="Operation failed",
            error_type="server_error",
            client_op_id="op-error",
        )

        assert result is True
        # Should send failure acknowledgment
        state_manager.send_acknowledgment.assert_called_once()
        call_args = state_manager.send_acknowledgment.call_args
        assert call_args[0][1] is False  # acknowledge_success=False

    @pytest.mark.asyncio
    async def test_broadcast_error_with_details(self):
        """Test broadcasting error with operation and details."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()

        service = UnifiedBroadcastingService(state_manager)

        details = {"field": "email", "reason": "invalid format"}
        result = await service.broadcast_error(
            error_message="Validation failed",
            operation="user_registration",
            details=details,
        )

        assert result is True
        call_args = state_manager.broadcast_state_change.call_args
        data = call_args[0][1]
        assert data["operation"] == "user_registration"
        assert data["details"] == details


class TestBroadcastBatch:
    """Test broadcast_batch method."""

    @pytest.mark.asyncio
    async def test_broadcast_batch_success(self):
        """Test broadcasting multiple events in batch."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()

        service = UnifiedBroadcastingService(state_manager)

        broadcasts = [
            {
                "event_type": StateEventType.PLAYER_STATE,
                "data": {"is_playing": True},
                "room": "player",
            },
            {
                "event_type": StateEventType.PLAYLISTS_SNAPSHOT,
                "data": {"playlists": []},
                "room": "playlists",
            },
        ]

        result = await service.broadcast_batch(broadcasts)

        assert result == 2
        assert state_manager.broadcast_state_change.call_count == 2

    @pytest.mark.asyncio
    async def test_broadcast_batch_with_acknowledgment(self):
        """Test batch broadcasting with final acknowledgment."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()
        state_manager.send_acknowledgment = AsyncMock()

        service = UnifiedBroadcastingService(state_manager)

        broadcasts = [
            {"event_type": StateEventType.PLAYER_STATE, "data": {"volume": 50}},
            {"event_type": StateEventType.POSITION_UPDATE, "data": {"position": 100}},
        ]

        result = await service.broadcast_batch(broadcasts, client_op_id="op-batch")

        assert result == 2
        # Should send final acknowledgment
        state_manager.send_acknowledgment.assert_called_once()
        call_args = state_manager.send_acknowledgment.call_args
        ack_data = call_args[0][2]
        assert ack_data["total"] == 2
        assert ack_data["successful"] == 2
        assert ack_data["failed"] == 0

    @pytest.mark.asyncio
    async def test_broadcast_batch_empty(self):
        """Test broadcasting empty batch."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()

        service = UnifiedBroadcastingService(state_manager)

        result = await service.broadcast_batch([])

        assert result == 0
        state_manager.broadcast_state_change.assert_not_called()


class TestStatisticsAndUtilities:
    """Test statistics and utility methods."""

    def test_get_statistics_initial(self):
        """Test getting statistics with no broadcasts."""
        state_manager = Mock(spec=StateManager)
        service = UnifiedBroadcastingService(state_manager)

        stats = service.get_statistics()

        assert stats["total_broadcasts"] == 0
        assert stats["total_acknowledgments"] == 0
        assert "average_per_minute" in stats

    @pytest.mark.asyncio
    async def test_get_statistics_after_broadcasts(self):
        """Test getting statistics after some broadcasts."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()
        state_manager.send_acknowledgment = AsyncMock()

        service = UnifiedBroadcastingService(state_manager)

        # Perform some broadcasts
        await service.broadcast_with_acknowledgment(
            StateEventType.PLAYER_STATE, {"is_playing": True}, client_op_id="op-1"
        )
        await service.broadcast_with_acknowledgment(
            StateEventType.PLAYER_STATE, {"is_playing": False}
        )

        stats = service.get_statistics()

        assert stats["total_broadcasts"] == 2
        assert stats["total_acknowledgments"] == 1

    def test_get_timestamp(self):
        """Test timestamp generation."""
        state_manager = Mock(spec=StateManager)
        service = UnifiedBroadcastingService(state_manager)

        timestamp = service._get_timestamp()

        assert isinstance(timestamp, float)
        assert timestamp > 0

    def test_calculate_average_rate(self):
        """Test average rate calculation."""
        state_manager = Mock(spec=StateManager)
        service = UnifiedBroadcastingService(state_manager)

        rate = service._calculate_average_rate()

        # Current implementation returns placeholder 0.0
        assert isinstance(rate, float)
        assert rate >= 0.0


class TestBroadcastNFCAssociation:
    """Test broadcast_nfc_association method."""

    @pytest.mark.asyncio
    async def test_broadcast_nfc_association_basic(self):
        """Test broadcasting basic NFC association."""
        # Mock socketio instance
        mock_socketio = Mock()
        mock_socketio.emit = AsyncMock()

        state_manager = Mock(spec=StateManager)
        state_manager.socketio = mock_socketio

        service = UnifiedBroadcastingService(state_manager)

        result = await service.broadcast_nfc_association(association_state="waiting")

        assert result is True
        mock_socketio.emit.assert_called_once()
        assert service._broadcast_count == 1

    @pytest.mark.asyncio
    async def test_broadcast_nfc_association_with_details(self):
        """Test broadcasting NFC association with all details."""
        mock_socketio = Mock()
        mock_socketio.emit = AsyncMock()

        state_manager = Mock(spec=StateManager)
        state_manager.socketio = mock_socketio
        state_manager.send_acknowledgment = AsyncMock()

        service = UnifiedBroadcastingService(state_manager)

        result = await service.broadcast_nfc_association(
            association_state="completed",
            playlist_id="pl-123",
            tag_id="tag-456",
            session_id="session-789",
            client_op_id="op-nfc",
            expires_at="2025-01-01T00:00:00Z",
        )

        assert result is True
        mock_socketio.emit.assert_called_once()
        # Should send acknowledgment
        state_manager.send_acknowledgment.assert_called_once()
        assert service._acknowledgment_count == 1

    @pytest.mark.asyncio
    async def test_broadcast_nfc_association_direct_socketio(self):
        """Test NFC broadcast with direct socketio instance (no wrapper)."""
        # Create a mock that mimics direct socketio (no .socketio attribute, but has .emit)
        mock_socketio = Mock(spec=['emit'])
        mock_socketio.emit = AsyncMock()

        # Pass socketio directly as state_manager
        service = UnifiedBroadcastingService(mock_socketio)

        result = await service.broadcast_nfc_association(association_state="detected")

        assert result is True
        mock_socketio.emit.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_nfc_association_no_socketio(self):
        """Test NFC broadcast with no socketio instance."""
        state_manager = Mock(spec=StateManager)
        # No socketio attribute

        service = UnifiedBroadcastingService(state_manager)

        result = await service.broadcast_nfc_association(association_state="error")

        # Should return False when no socketio available
        assert result is False
