"""Contract tests for Socket.IO Subscription events.

Validates that Socket.IO room subscription events conform to the expected contract.

Progress: 7/7 events tested ✅
"""

import pytest
from unittest.mock import AsyncMock, Mock
import socketio
from fastapi import HTTPException
from app.src.routes.factories.websocket_handlers_state import WebSocketStateHandlers
from app.src.domain.audio.engine.state_manager import StateManager


@pytest.fixture
async def mock_state_manager():
    """Create mock StateManager for subscription testing."""
    state_manager = Mock(spec=StateManager)
    state_manager.get_global_sequence = Mock(return_value=100)
    state_manager.get_playlist_sequence = Mock(return_value=50)
    state_manager.subscribe_client = AsyncMock(return_value=None)
    state_manager.unsubscribe_client = AsyncMock(return_value=None)
    state_manager.socketio = None
    return state_manager


@pytest.fixture
async def mock_app():
    """Create mock app with NFC service."""
    app = Mock()
    app.container = Mock()
    # Mock NFC service for join:nfc tests
    nfc_service = Mock()
    nfc_service.get_session_snapshot = AsyncMock(return_value=None)
    app.container.nfc = nfc_service
    return app


@pytest.fixture
async def socketio_handlers(mock_state_manager, mock_app):
    """Create WebSocket handlers with subscription support."""
    sio = Mock(spec=socketio.AsyncServer)
    sio.emit = AsyncMock()

    handlers = WebSocketStateHandlers(sio, mock_app, mock_state_manager)
    handlers._registered_handlers = {}

    def mock_event(func):
        handlers._registered_handlers[func.__name__] = func
        return func

    def mock_on(event_name):
        def decorator(func):
            handlers._registered_handlers[event_name] = func
            return func
        return decorator

    sio.event = mock_event
    sio.on = mock_on

    handlers.register()
    return handlers


@pytest.mark.asyncio
class TestSocketIOSubscriptionContract:
    """Contract tests for Socket.IO subscription/room management events."""

    async def test_join_playlists_event_contract(self, socketio_handlers, mock_state_manager):
        """Test 'join:playlists' event - Subscribe to global playlists updates.

        Contract:
        - Direction: client_to_server
        - Payload: {} (empty object)
        - Server should add client to 'playlists' room
        - Server should emit ack:join confirmation
        """
        handler = socketio_handlers._registered_handlers['join:playlists']
        test_sid = "test-client-playlists"

        await handler(test_sid, {})

        # Verify subscribe_client called
        mock_state_manager.subscribe_client.assert_called_once_with(test_sid, "playlists")

        # Verify ack:join emitted
        socketio_handlers.sio.emit.assert_called_once()
        call_args = socketio_handlers.sio.emit.call_args

        assert call_args[0][0] == "ack:join", "Should emit ack:join"

        payload = call_args[0][1]
        assert payload["room"] == "playlists", "Room should be 'playlists'"
        assert payload["success"] is True, "Success should be true"
        assert "server_seq" in payload, "Must include server_seq"

    async def test_join_playlist_event_contract(self, socketio_handlers, mock_state_manager):
        """Test 'join:playlist' event - Subscribe to specific playlist updates.

        Contract:
        - Direction: client_to_server
        - Payload: {playlist_id: str (required)}
        - Server should add client to 'playlist:{playlist_id}' room
        - Server should emit ack:join confirmation
        - Error if playlist_id missing
        """
        handler = socketio_handlers._registered_handlers['join:playlist']
        test_sid = "test-client-playlist"
        test_playlist_id = "test-playlist-123"

        # Test successful join
        await handler(test_sid, {"playlist_id": test_playlist_id})

        # Verify subscribe_client called with correct room
        expected_room = f"playlist:{test_playlist_id}"
        mock_state_manager.subscribe_client.assert_called_once_with(test_sid, expected_room)

        # Verify ack:join emitted
        call_args = socketio_handlers.sio.emit.call_args
        assert call_args[0][0] == "ack:join", "Should emit ack:join"

        payload = call_args[0][1]
        assert payload["room"] == expected_room, "Room should be playlist:{id}"
        assert payload["playlist_id"] == test_playlist_id, "Must include playlist_id"
        assert payload["success"] is True, "Success should be true"
        assert "playlist_seq" in payload, "Must include playlist_seq"

        # Test error when playlist_id missing
        with pytest.raises(HTTPException) as exc_info:
            await handler(test_sid, {})
        assert "playlist_id is required" in str(exc_info.value.detail)

    async def test_join_nfc_event_contract(self, socketio_handlers, mock_state_manager):
        """Test 'join:nfc' event - Subscribe to NFC events.

        Contract:
        - Direction: client_to_server
        - Payload: {assoc_id: str (required)}
        - Server should add client to 'nfc:{assoc_id}' room
        - Server should emit ack:join confirmation
        """
        handler = socketio_handlers._registered_handlers['join:nfc']
        test_sid = "test-client-nfc"
        test_assoc_id = "test-assoc-456"

        await handler(test_sid, {"assoc_id": test_assoc_id})

        # Verify subscribe_client called with NFC room
        expected_room = f"nfc:{test_assoc_id}"
        mock_state_manager.subscribe_client.assert_called_once_with(test_sid, expected_room)

        # Verify ack:join emitted (should be the last emit call)
        emit_calls = socketio_handlers.sio.emit.call_args_list
        last_call = emit_calls[-1]

        assert last_call[0][0] == "ack:join", "Should emit ack:join"
        payload = last_call[0][1]
        assert payload["room"] == expected_room, "Room should be nfc:{assoc_id}"
        assert payload["success"] is True, "Success should be true"

    async def test_leave_playlists_event_contract(self, socketio_handlers, mock_state_manager):
        """Test 'leave:playlists' event - Unsubscribe from global playlists.

        Contract:
        - Direction: client_to_server
        - Payload: {} (empty object)
        - Server should remove client from 'playlists' room
        - Server should emit ack:leave confirmation
        """
        handler = socketio_handlers._registered_handlers['leave:playlists']
        test_sid = "test-client-leave-playlists"

        await handler(test_sid, {})

        # Verify unsubscribe_client called
        mock_state_manager.unsubscribe_client.assert_called_once_with(test_sid, "playlists")

        # Verify ack:leave emitted
        socketio_handlers.sio.emit.assert_called_once()
        call_args = socketio_handlers.sio.emit.call_args

        assert call_args[0][0] == "ack:leave", "Should emit ack:leave"

        payload = call_args[0][1]
        assert payload["room"] == "playlists", "Room should be 'playlists'"
        assert payload["success"] is True, "Success should be true"

    async def test_leave_playlist_event_contract(self, socketio_handlers, mock_state_manager):
        """Test 'leave:playlist' event - Unsubscribe from specific playlist.

        Contract:
        - Direction: client_to_server
        - Payload: {playlist_id: str (required)}
        - Server should remove client from 'playlist:{playlist_id}' room
        - Server should emit ack:leave confirmation
        """
        handler = socketio_handlers._registered_handlers['leave:playlist']
        test_sid = "test-client-leave-playlist"
        test_playlist_id = "test-playlist-789"

        # Test successful leave
        await handler(test_sid, {"playlist_id": test_playlist_id})

        # Verify unsubscribe_client called with correct room
        expected_room = f"playlist:{test_playlist_id}"
        mock_state_manager.unsubscribe_client.assert_called_once_with(test_sid, expected_room)

        # Verify ack:leave emitted
        call_args = socketio_handlers.sio.emit.call_args
        assert call_args[0][0] == "ack:leave", "Should emit ack:leave"

        payload = call_args[0][1]
        assert payload["room"] == expected_room, "Room should be playlist:{id}"
        assert payload["playlist_id"] == test_playlist_id, "Must include playlist_id"
        assert payload["success"] is True, "Success should be true"

        # Test error when playlist_id missing
        with pytest.raises(HTTPException) as exc_info:
            await handler(test_sid, {})
        assert "playlist_id is required" in str(exc_info.value.detail)

    async def test_ack_join_event_contract(self, socketio_handlers, mock_state_manager):
        """Test 'ack:join' event - Server confirms room subscription.

        Contract:
        - Direction: server_to_client
        - Payload: {room: str, success: bool, server_seq: number}
        - Required fields: room, success, server_seq
        - Emitted after successful join
        """
        # Test via join:playlists which emits ack:join
        handler = socketio_handlers._registered_handlers['join:playlists']
        test_sid = "test-ack-join"

        await handler(test_sid, {})

        # Get ack:join payload
        payload = socketio_handlers.sio.emit.call_args[0][1]

        # Verify contract compliance
        assert "room" in payload, "Must include room field"
        assert "success" in payload, "Must include success field"
        assert "server_seq" in payload, "Must include server_seq field"

        assert isinstance(payload["room"], str), "room must be string"
        assert isinstance(payload["success"], bool), "success must be boolean"
        assert isinstance(payload["server_seq"], int), "server_seq must be number"

        assert payload["success"] is True, "success should be true for successful join"

    async def test_ack_leave_event_contract(self, socketio_handlers, mock_state_manager):
        """Test 'ack:leave' event - Server confirms room unsubscription.

        Contract:
        - Direction: server_to_client
        - Payload: {room: str, success: bool}
        - Required fields: room, success
        - Emitted after successful leave
        """
        # Test via leave:playlists which emits ack:leave
        handler = socketio_handlers._registered_handlers['leave:playlists']
        test_sid = "test-ack-leave"

        await handler(test_sid, {})

        # Get ack:leave payload
        payload = socketio_handlers.sio.emit.call_args[0][1]

        # Verify contract compliance
        assert "room" in payload, "Must include room field"
        assert "success" in payload, "Must include success field"

        assert isinstance(payload["room"], str), "room must be string"
        assert isinstance(payload["success"], bool), "success must be boolean"

        assert payload["success"] is True, "success should be true for successful leave"
