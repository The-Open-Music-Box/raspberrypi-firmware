"""Tests for UnifiedStateManager class."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.src.application.services.unified_state_manager import UnifiedStateManager
from app.src.common.socket_events import StateEventType
from app.src.domain.protocols.state_manager_protocol import PlaybackState


class TestUnifiedStateManager:
    """Test suite for UnifiedStateManager class."""

    @pytest.fixture
    def mock_socketio(self):
        """Mock Socket.IO server."""
        return AsyncMock()

    @pytest.fixture
    def unified_manager(self, mock_socketio):
        """Create UnifiedStateManager instance."""
        return UnifiedStateManager(mock_socketio)

    def test_init(self, mock_socketio):
        """Test UnifiedStateManager initialization."""
        manager = UnifiedStateManager(mock_socketio)

        assert manager.socketio == mock_socketio
        assert manager.sequences is not None
        assert manager.outbox is not None
        assert manager.subscriptions is not None
        assert manager.operations is not None
        assert manager.state_manager is not None
        assert manager.serialization_service is not None
        assert manager.event_coordinator is not None
        assert manager.snapshot_service is not None
        assert manager.lifecycle_service is not None

    def test_init_without_socketio(self):
        """Test initialization without Socket.IO server."""
        manager = UnifiedStateManager()
        assert manager.socketio is None

    @pytest.mark.asyncio
    async def test_subscribe_client(self, unified_manager):
        """Test client subscription with snapshot delivery."""
        with patch.object(unified_manager.subscriptions, 'subscribe_client', new_callable=AsyncMock) as mock_subscribe:
            with patch.object(unified_manager.snapshot_service, 'send_state_snapshot', new_callable=AsyncMock) as mock_snapshot:
                await unified_manager.subscribe_client("client_123", "playlists")

                mock_subscribe.assert_called_once_with("client_123", "playlists")
                mock_snapshot.assert_called_once_with("client_123", "playlists")

    @pytest.mark.asyncio
    async def test_unsubscribe_client(self, unified_manager):
        """Test client unsubscription."""
        with patch.object(unified_manager.subscriptions, 'unsubscribe_client', new_callable=AsyncMock) as mock_unsubscribe:
            await unified_manager.unsubscribe_client("client_123", "playlists")
            mock_unsubscribe.assert_called_once_with("client_123", "playlists")

    def test_get_client_subscriptions(self, unified_manager):
        """Test getting client subscriptions."""
        mock_subscriptions = {"room1", "room2"}
        unified_manager.subscriptions.get_client_subscriptions = Mock(return_value=mock_subscriptions)

        result = unified_manager.get_client_subscriptions("client_123")
        assert result == mock_subscriptions

    @pytest.mark.asyncio
    async def test_operation_tracking(self, unified_manager):
        """Test operation tracking methods."""
        # Test is_operation_processed
        unified_manager.operations.is_operation_processed = AsyncMock(return_value=True)
        result = await unified_manager.is_operation_processed("op_123")
        assert result is True

        # Test mark_operation_processed
        unified_manager.operations.mark_operation_processed = AsyncMock()
        await unified_manager.mark_operation_processed("op_123", {"result": "success"})
        unified_manager.operations.mark_operation_processed.assert_called_once_with("op_123", {"result": "success"})

        # Test get_operation_result
        unified_manager.operations.get_operation_result = AsyncMock(return_value={"cached": "result"})
        result = await unified_manager.get_operation_result("op_123")
        assert result == {"cached": "result"}

    @pytest.mark.asyncio
    async def test_broadcast_state_change(self, unified_manager):
        """Test state change broadcasting delegation."""
        expected_result = {"event_id": "test123", "server_seq": 42}
        unified_manager.event_coordinator.broadcast_state_change = AsyncMock(return_value=expected_result)

        result = await unified_manager.broadcast_state_change(
            StateEventType.PLAYER_STATE,
            {"state": "playing"},
            playlist_id="playlist_123",
            room="test_room",
            immediate=True
        )

        assert result == expected_result
        unified_manager.event_coordinator.broadcast_state_change.assert_called_once_with(
            StateEventType.PLAYER_STATE,
            {"state": "playing"},
            "playlist_123",
            "test_room",
            True
        )

    @pytest.mark.asyncio
    async def test_broadcast_position_update(self, unified_manager):
        """Test position update broadcasting delegation."""
        expected_result = {"event_id": "position123"}
        unified_manager.event_coordinator.broadcast_position_update = AsyncMock(return_value=expected_result)

        result = await unified_manager.broadcast_position_update(5000, "track_123", True, 180000)

        assert result == expected_result
        unified_manager.event_coordinator.broadcast_position_update.assert_called_once_with(
            5000, "track_123", True, 180000
        )

    @pytest.mark.asyncio
    async def test_emit_playlists_index_update(self, unified_manager):
        """Test playlists index update emission."""
        updates = [{"type": "upsert", "item": {"id": "1"}}]
        expected_result = {"event_id": "update123"}
        unified_manager.event_coordinator.emit_playlists_index_update = AsyncMock(return_value=expected_result)

        result = await unified_manager.emit_playlists_index_update(updates)

        assert result == expected_result
        unified_manager.event_coordinator.emit_playlists_index_update.assert_called_once_with(updates)

    @pytest.mark.asyncio
    async def test_send_acknowledgment(self, unified_manager):
        """Test acknowledgment sending delegation."""
        unified_manager.event_coordinator.send_acknowledgment = AsyncMock()

        await unified_manager.send_acknowledgment("op_123", True, {"result": "ok"}, "client_456")

        unified_manager.event_coordinator.send_acknowledgment.assert_called_once_with(
            "op_123", True, {"result": "ok"}, "client_456"
        )

    def test_sequence_management(self, unified_manager):
        """Test sequence number management."""
        # Test global sequence
        unified_manager.sequences.get_current_global_seq = Mock(return_value=100)
        result = unified_manager.get_global_sequence()
        assert result == 100

        # Test playlist sequence
        unified_manager.sequences.get_current_playlist_seq = Mock(return_value=50)
        result = unified_manager.get_playlist_sequence("playlist_123")
        assert result == 50

    @pytest.mark.asyncio
    async def test_process_outbox(self, unified_manager):
        """Test outbox processing delegation."""
        unified_manager.outbox.process_outbox = AsyncMock()
        await unified_manager.process_outbox()
        unified_manager.outbox.process_outbox.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifecycle_management(self, unified_manager):
        """Test lifecycle management methods."""
        # Test start cleanup task
        unified_manager.lifecycle_service.start_lifecycle_management = AsyncMock()
        await unified_manager.start_cleanup_task()
        unified_manager.lifecycle_service.start_lifecycle_management.assert_called_once()

        # Test stop cleanup task
        unified_manager.lifecycle_service.stop_lifecycle_management = AsyncMock()
        await unified_manager.stop_cleanup_task()
        unified_manager.lifecycle_service.stop_lifecycle_management.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_health_metrics(self, unified_manager):
        """Test health metrics collection."""
        # Mock component stats
        lifecycle_metrics = {"lifecycle_service": {"is_running": True}}
        unified_manager.lifecycle_service.get_health_metrics = AsyncMock(return_value=lifecycle_metrics)
        unified_manager.sequences.get_stats = Mock(return_value={"global_seq": 100})
        unified_manager.subscriptions.get_stats = Mock(return_value={"clients": 5})

        # Mock state manager methods
        unified_manager.state_manager.get_current_state = Mock(return_value=PlaybackState.PLAYING)
        unified_manager.state_manager.get_last_updated = Mock(return_value=1234567890.0)
        unified_manager.state_manager.is_error = Mock(return_value=False)

        result = await unified_manager.get_health_metrics()

        assert "lifecycle_service" in result
        assert "sequences" in result
        assert "subscriptions" in result
        assert "state_manager" in result
        assert result["state_manager"]["current_state"] == "playing"
        assert result["state_manager"]["last_updated"] == 1234567890.0
        assert result["state_manager"]["has_error"] is False

    def test_state_manager_protocol_delegation(self, unified_manager):
        """Test StateManagerProtocol method delegation."""
        # Test get_current_state
        unified_manager.state_manager.get_current_state = Mock(return_value=PlaybackState.PLAYING)
        result = unified_manager.get_current_state()
        assert result == PlaybackState.PLAYING

        # Test set_state
        unified_manager.state_manager.set_state = Mock()
        unified_manager.set_state(PlaybackState.PAUSED)
        unified_manager.state_manager.set_state.assert_called_once_with(PlaybackState.PAUSED)

        # Test get_state_dict
        state_dict = {"state": "playing", "volume": 75}
        unified_manager.state_manager.get_state_dict = Mock(return_value=state_dict)
        result = unified_manager.get_state_dict()
        assert result == state_dict

        # Test update methods
        unified_manager.state_manager.update_track_info = Mock()
        unified_manager.state_manager.update_playlist_info = Mock()
        unified_manager.state_manager.update_position = Mock()
        unified_manager.state_manager.update_volume = Mock()

        track_info = {"id": "track_123", "title": "Test Track"}
        playlist_info = {"id": "playlist_456", "title": "Test Playlist"}

        unified_manager.update_track_info(track_info)
        unified_manager.update_playlist_info(playlist_info)
        unified_manager.update_position(30.5)
        unified_manager.update_volume(80)

        unified_manager.state_manager.update_track_info.assert_called_once_with(track_info)
        unified_manager.state_manager.update_playlist_info.assert_called_once_with(playlist_info)
        unified_manager.state_manager.update_position.assert_called_once_with(30.5)
        unified_manager.state_manager.update_volume.assert_called_once_with(80)

    def test_error_handling_delegation(self, unified_manager):
        """Test error handling method delegation."""
        # Test set_error
        unified_manager.state_manager.set_error = Mock()
        unified_manager.set_error("Test error")
        unified_manager.state_manager.set_error.assert_called_once_with("Test error")

        # Test clear_error
        unified_manager.state_manager.clear_error = Mock()
        unified_manager.clear_error()
        unified_manager.state_manager.clear_error.assert_called_once()

        # Test get_last_error
        unified_manager.state_manager.get_last_error = Mock(return_value="Test error")
        result = unified_manager.get_last_error()
        assert result == "Test error"

    def test_extended_state_management_delegation(self, unified_manager):
        """Test extended state management method delegation."""
        # Test current playlist methods
        playlist = {"id": "playlist_123", "title": "Test Playlist"}
        unified_manager.state_manager.get_current_playlist = Mock(return_value=playlist)
        unified_manager.state_manager.set_current_playlist = Mock()

        result = unified_manager.get_current_playlist()
        assert result == playlist

        unified_manager.set_current_playlist(playlist)
        unified_manager.state_manager.set_current_playlist.assert_called_once_with(playlist)

        # Test current track number methods
        unified_manager.state_manager.get_current_track_number = Mock(return_value=3)
        unified_manager.state_manager.set_current_track_number = Mock()

        result = unified_manager.get_current_track_number()
        assert result == 3

        unified_manager.set_current_track_number(5)
        unified_manager.state_manager.set_current_track_number.assert_called_once_with(5)

    def test_serialization_legacy_methods(self, unified_manager):
        """Test legacy serialization method delegation."""
        # Test _serialize_playlist
        playlist = {"id": "playlist_123", "title": "Test Playlist"}
        expected_result = {"id": "playlist_123", "title": "Test Playlist", "server_seq": 100}
        unified_manager.serialization_service.serialize_playlist = Mock(return_value=expected_result)

        result = unified_manager._serialize_playlist(playlist)
        assert result == expected_result
        unified_manager.serialization_service.serialize_playlist.assert_called_once_with(playlist)

        # Test _serialize_track
        track = {"id": "track_123", "title": "Test Track"}
        expected_result = {"id": "track_123", "title": "Test Track", "server_seq": 100}
        unified_manager.serialization_service.serialize_track = Mock(return_value=expected_result)

        result = unified_manager._serialize_track(track)
        assert result == expected_result
        unified_manager.serialization_service.serialize_track.assert_called_once_with(track)

    @pytest.mark.asyncio
    async def test_snapshot_legacy_methods(self, unified_manager):
        """Test legacy snapshot method delegation."""
        # Test _send_state_snapshot
        unified_manager.snapshot_service.send_state_snapshot = AsyncMock()
        await unified_manager._send_state_snapshot("client_123", "playlists")
        unified_manager.snapshot_service.send_state_snapshot.assert_called_once_with("client_123", "playlists")

        # Test _send_playlists_snapshot
        unified_manager.snapshot_service._send_playlists_snapshot = AsyncMock()
        await unified_manager._send_playlists_snapshot("client_123")
        unified_manager.snapshot_service._send_playlists_snapshot.assert_called_once_with("client_123")

        # Test _send_playlist_snapshot
        unified_manager.snapshot_service._send_playlist_snapshot = AsyncMock()
        await unified_manager._send_playlist_snapshot("client_123", "playlist_456")
        unified_manager.snapshot_service._send_playlist_snapshot.assert_called_once_with("client_123", "playlist_456")