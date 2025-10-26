"""Tests for StateEventCoordinator class."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from app.src.application.services.state_event_coordinator import StateEventCoordinator, StateEventType
from app.src.services.event_outbox import EventOutbox
from app.src.services.sequence_generator import SequenceGenerator


class TestStateEventCoordinator:
    """Test suite for StateEventCoordinator class."""

    @pytest.fixture
    def mock_socketio(self):
        """Mock Socket.IO server."""
        mock = AsyncMock()
        return mock

    @pytest.fixture
    def mock_outbox(self):
        """Mock event outbox."""
        mock = AsyncMock()
        mock.add_event = AsyncMock()
        mock.process_outbox = AsyncMock()
        mock.get_stats = Mock(return_value={"pending": 0, "processed": 10})
        return mock

    @pytest.fixture
    def mock_sequences(self):
        """Mock sequence generator."""
        mock = Mock()
        mock.get_next_global_seq = AsyncMock(return_value=42)
        mock.get_next_playlist_seq = AsyncMock(return_value=5)
        mock.get_current_global_seq = Mock(return_value=41)
        mock.get_current_playlist_seq = Mock(return_value=4)
        return mock

    @pytest.fixture
    def coordinator(self, mock_socketio, mock_outbox, mock_sequences):
        """Create StateEventCoordinator instance."""
        return StateEventCoordinator(mock_socketio, mock_outbox, mock_sequences)

    def test_init(self, mock_socketio, mock_outbox, mock_sequences):
        """Test StateEventCoordinator initialization."""
        coordinator = StateEventCoordinator(mock_socketio, mock_outbox, mock_sequences)

        assert coordinator.socketio == mock_socketio
        assert coordinator.outbox == mock_outbox
        assert coordinator.sequences == mock_sequences
        assert coordinator._last_position_emit_time == 0
        assert not coordinator._position_state_logged
        assert not coordinator._first_position_logged
        assert coordinator._position_log_counter == 0

    def test_init_with_defaults(self):
        """Test StateEventCoordinator initialization with default dependencies."""
        coordinator = StateEventCoordinator()

        assert coordinator.socketio is None
        assert isinstance(coordinator.outbox, EventOutbox)
        assert isinstance(coordinator.sequences, SequenceGenerator)

    @pytest.mark.asyncio
    async def test_broadcast_state_change_success(self, coordinator, mock_socketio, mock_outbox, mock_sequences):
        """Test successful state change broadcasting."""
        # Setup
        event_type = StateEventType.PLAYER_STATE
        data = {"state": "playing", "track_id": "123"}
        playlist_id = "playlist_456"

        with patch('time.time', return_value=1234567890.123):
            with patch('uuid.uuid4') as mock_uuid:
                mock_uuid.return_value = Mock()
                mock_uuid.return_value.__str__ = Mock(return_value="test-uuid-1234")

                # Execute
                result = await coordinator.broadcast_state_change(
                    event_type, data, playlist_id, immediate=True
                )

        # Verify
        assert result["event_type"] == "state:player"
        assert result["server_seq"] == 42
        assert result["data"]["playlist_seq"] == 5
        assert result["playlist_id"] == playlist_id
        assert result["timestamp"] == 1234567890123
        assert result["event_id"] == "test-uui"  # First 8 chars

        # Verify outbox interaction
        mock_outbox.add_event.assert_called_once()
        mock_outbox.process_outbox.assert_called_once()

        # Verify Socket.IO broadcast
        mock_socketio.emit.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_position_update_throttling(self, coordinator):
        """Test position update throttling mechanism."""
        with patch('app.src.application.services.state_event_coordinator.socket_config.POSITION_THROTTLE_MIN_MS', 1000):  # 1 second throttle
            with patch('time.time', side_effect=[1.0, 1.5, 2.5]):  # Simulate time progression
                with patch.object(coordinator, 'broadcast_state_change', new_callable=AsyncMock) as mock_broadcast:
                    # First call should succeed
                    result1 = await coordinator.broadcast_position_update(1000, "track_1", True)
                    assert result1 is not None
                    mock_broadcast.assert_called_once()

                    # Second call within throttle window should be blocked
                    mock_broadcast.reset_mock()
                    result2 = await coordinator.broadcast_position_update(1500, "track_1", True)
                    assert result2 is None
                    mock_broadcast.assert_not_called()

                    # Third call after throttle window should succeed
                    mock_broadcast.reset_mock()
                    result3 = await coordinator.broadcast_position_update(2000, "track_1", True)
                    assert result3 is not None
                    mock_broadcast.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_position_update_logging(self, coordinator):
        """Test position update logging behavior."""
        with patch('app.src.application.services.state_event_coordinator.socket_config.POSITION_THROTTLE_MIN_MS', 0):  # No throttling
            with patch('time.time', return_value=1.0):
                with patch.object(coordinator, 'broadcast_state_change', new_callable=AsyncMock):
                    # Call multiple times to test logging counter
                    for i in range(15):
                        await coordinator.broadcast_position_update(i * 100, "track_1", True)

                    # Verify counter incremented
                    assert coordinator._position_log_counter == 15

    @pytest.mark.asyncio
    async def test_emit_playlists_index_update(self, coordinator):
        """Test playlists index update emission."""
        updates = [
            {"type": "upsert", "item": {"id": "1", "title": "Test Playlist"}},
            {"type": "delete", "id": "2"}
        ]

        with patch.object(coordinator, 'broadcast_state_change', new_callable=AsyncMock) as mock_broadcast:
            mock_broadcast.return_value = {"event_id": "test"}

            result = await coordinator.emit_playlists_index_update(updates)

            mock_broadcast.assert_called_once_with(
                StateEventType.PLAYLISTS_INDEX_UPDATE,
                {"updates": updates},
                immediate=True
            )
            assert result == {"event_id": "test"}

    @pytest.mark.asyncio
    async def test_send_acknowledgment_with_client_id(self, coordinator, mock_socketio, mock_sequences):
        """Test sending acknowledgment to specific client."""
        mock_sequences.get_current_global_seq.return_value = 100

        await coordinator.send_acknowledgment("op_123", True, {"result": "success"}, "client_456")

        # Verify Socket.IO emit called with correct parameters
        mock_socketio.emit.assert_called_once()
        call_args = mock_socketio.emit.call_args
        assert call_args[0][0] == "ack:op"  # event name
        assert call_args[1]["room"] == "client_456"

    @pytest.mark.asyncio
    async def test_send_acknowledgment_failure(self, coordinator, mock_socketio, mock_sequences):
        """Test sending acknowledgment for failed operation."""
        mock_sequences.get_current_global_seq.return_value = 100

        await coordinator.send_acknowledgment("op_123", False, None, "client_456")

        # Verify error event sent
        mock_socketio.emit.assert_called_once()
        call_args = mock_socketio.emit.call_args
        assert call_args[0][0] == "err:op"  # event name

    @pytest.mark.asyncio
    async def test_send_acknowledgment_no_socketio(self, mock_outbox, mock_sequences):
        """Test acknowledgment handling when Socket.IO is unavailable."""
        coordinator = StateEventCoordinator(None, mock_outbox, mock_sequences)

        # Should not raise error when socketio is None
        await coordinator.send_acknowledgment("op_123", True, {"result": "success"}, "client_456")

    @pytest.mark.asyncio
    async def test_process_outbox(self, coordinator, mock_outbox):
        """Test outbox processing delegation."""
        await coordinator.process_outbox()
        mock_outbox.process_outbox.assert_called_once()

    def test_get_global_sequence(self, coordinator, mock_sequences):
        """Test global sequence retrieval."""
        result = coordinator.get_global_sequence()
        assert result == 41
        mock_sequences.get_current_global_seq.assert_called_once()

    def test_get_playlist_sequence(self, coordinator, mock_sequences):
        """Test playlist sequence retrieval."""
        result = coordinator.get_playlist_sequence("playlist_123")
        assert result == 4
        mock_sequences.get_current_playlist_seq.assert_called_once_with("playlist_123")

    def test_convert_state_event_type_to_socket_event_type(self, coordinator):
        """Test state event type conversion."""
        # Test known conversion
        result = coordinator._convert_state_event_type_to_socket_event_type(StateEventType.PLAYLISTS_SNAPSHOT)
        assert result.value == "state:playlists"

        # Test unknown event type (should create new SocketEventType)
        from enum import Enum
        class CustomEventType(Enum):
            CUSTOM = "custom:event"

        result = coordinator._convert_state_event_type_to_socket_event_type(CustomEventType.CUSTOM)
        assert result.value == "custom:event"

    @pytest.mark.asyncio
    async def test_broadcast_event_to_specific_room(self, coordinator, mock_socketio):
        """Test broadcasting event to specific room."""
        envelope = {
            "event_type": "test:event",
            "server_seq": 42,
            "data": {"test": "data"},
            "timestamp": 1234567890,
            "event_id": "test123"
        }

        # Mock SocketEventType for conversion
        from app.src.common.socket_events import SocketEventType
        socket_event_type = SocketEventType.STATE_PLAYER

        await coordinator._broadcast_event(envelope, "specific_room", socket_event_type, None)

        # Verify emit called with specific room
        mock_socketio.emit.assert_called_once_with("test:event", envelope, room="specific_room")

    @pytest.mark.asyncio
    async def test_broadcast_event_with_room_routing(self, coordinator, mock_socketio):
        """Test broadcasting event with automatic room routing."""
        envelope = {
            "event_type": "state:player",
            "server_seq": 42,
            "data": {"test": "data"},
            "timestamp": 1234567890,
            "event_id": "test123"
        }

        from app.src.common.socket_events import SocketEventType
        socket_event_type = SocketEventType.STATE_PLAYER

        with patch('app.src.application.services.state_event_coordinator.get_event_room') as mock_get_room:
            mock_get_room.return_value = "auto_room"

            await coordinator._broadcast_event(envelope, None, socket_event_type, "playlist_123")

            # Verify room routing called
            mock_get_room.assert_called_once_with(socket_event_type, "playlist_123")
            mock_socketio.emit.assert_called_once_with("state:player", envelope, room="auto_room")

    @pytest.mark.asyncio
    async def test_broadcast_event_no_socketio(self, mock_outbox, mock_sequences):
        """Test broadcast event handling when Socket.IO is unavailable."""
        coordinator = StateEventCoordinator(None, mock_outbox, mock_sequences)
        envelope = {"event_type": "test:event"}

        from app.src.common.socket_events import SocketEventType
        socket_event_type = SocketEventType.STATE_PLAYER

        # Should not raise error when socketio is None
        await coordinator._broadcast_event(envelope, "room", socket_event_type, None)