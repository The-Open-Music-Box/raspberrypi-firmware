"""Contract tests for Socket.IO Connection events.

Validates that Socket.IO connection events conform to the expected contract.

Progress: 5/5 events tested ✅
"""

import pytest
import time
from unittest.mock import AsyncMock, Mock
import socketio
from app.src.routes.factories.websocket_handlers_state import WebSocketStateHandlers
from app.src.domain.audio.engine.state_manager import StateManager


@pytest.fixture
async def mock_state_manager():
    """Create mock StateManager for testing."""
    state_manager = Mock(spec=StateManager)
    state_manager.get_global_sequence = Mock(return_value=42)
    state_manager.unsubscribe_client = AsyncMock(return_value=None)
    state_manager.socketio = None
    return state_manager


@pytest.fixture
async def mock_app():
    """Create mock app for testing."""
    app = Mock()
    app.container = Mock()
    return app


@pytest.fixture
async def socketio_handlers(mock_state_manager, mock_app):
    """Create WebSocket handlers with mocked dependencies."""
    # Create mock Socket.IO server
    sio = Mock(spec=socketio.AsyncServer)
    sio.emit = AsyncMock()

    # Create handlers
    handlers = WebSocketStateHandlers(sio, mock_app, mock_state_manager)

    # Store registered handlers for testing
    handlers._registered_handlers = {}

    # Override decorator to capture handlers
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

    # Register handlers
    handlers.register()

    return handlers


@pytest.mark.asyncio
class TestSocketIOConnectionContract:
    """Contract tests for Socket.IO connection lifecycle events."""

    async def test_connect_event_contract(self, socketio_handlers, mock_state_manager):
        """Test 'connect' event - Client connects to server.

        Contract:
        - Direction: client_to_server
        - Payload: null (environ dict)
        - Server should acknowledge connection
        - Server should emit connection_status with sid
        """
        # Get the connect handler
        connect_handler = socketio_handlers._registered_handlers['connect']

        # Simulate client connection
        test_sid = "test-client-123"
        test_environ = {}

        # Call the connect handler
        await connect_handler(test_sid, test_environ)

        # Verify server emitted connection_status
        socketio_handlers.sio.emit.assert_called_once()
        call_args = socketio_handlers.sio.emit.call_args

        assert call_args[0][0] == "connection_status", "Should emit connection_status event"

        # Verify payload
        payload = call_args[0][1]
        assert payload["status"] == "connected", "Status must be 'connected'"
        assert payload["sid"] == test_sid, "Must include client sid"
        assert "server_seq" in payload, "Must include server_seq"
        assert payload["server_seq"] == 42, "server_seq should match state manager value"

        # Verify room targeting
        assert call_args[1]["room"] == test_sid, "Should emit to client's room"

    async def test_disconnect_event_contract(self, socketio_handlers, mock_state_manager):
        """Test 'disconnect' event - Client disconnects from server.

        Contract:
        - Direction: client_to_server
        - Payload: null
        - Server should clean up resources
        - Server should remove client from all rooms
        """
        # Get the disconnect handler
        disconnect_handler = socketio_handlers._registered_handlers['disconnect']

        # Simulate client disconnection
        test_sid = "test-client-456"

        # Call the disconnect handler
        await disconnect_handler(test_sid)

        # Verify server called unsubscribe_client to clean up
        mock_state_manager.unsubscribe_client.assert_called_once_with(test_sid)

    async def test_connection_status_event_contract(self, socketio_handlers, mock_state_manager):
        """Test 'connection_status' event - Server sends connection confirmation.

        Contract:
        - Direction: server_to_client
        - Payload: {status: "connected", sid: str, server_seq: number}
        - Required fields: status, sid, server_seq
        - Status must be "connected"
        """
        # This is tested as part of connect event, but verify payload structure explicitly
        connect_handler = socketio_handlers._registered_handlers['connect']

        test_sid = "test-client-status"
        await connect_handler(test_sid, {})

        # Get the emitted payload
        payload = socketio_handlers.sio.emit.call_args[0][1]

        # Verify contract compliance
        assert "status" in payload, "Must include status field"
        assert "sid" in payload, "Must include sid field"
        assert "server_seq" in payload, "Must include server_seq field"

        assert isinstance(payload["status"], str), "status must be string"
        assert isinstance(payload["sid"], str), "sid must be string"
        assert isinstance(payload["server_seq"], int), "server_seq must be number"

        assert payload["status"] == "connected", "status must be 'connected'"

    async def test_client_ping_event_contract(self, socketio_handlers, mock_state_manager):
        """Test 'client_ping' event - Client health check ping.

        Contract:
        - Direction: client_to_server
        - Payload: {timestamp: number}
        - Server should respond with client_pong
        """
        # Get the client_ping handler
        ping_handler = socketio_handlers._registered_handlers['client_ping']

        # Simulate client ping
        test_sid = "test-client-ping"
        ping_timestamp = time.time()
        ping_data = {"timestamp": ping_timestamp}

        # Call the ping handler
        await ping_handler(test_sid, ping_data)

        # Verify server emitted client_pong
        socketio_handlers.sio.emit.assert_called_once()
        call_args = socketio_handlers.sio.emit.call_args

        assert call_args[0][0] == "client_pong", "Should emit client_pong event"

        # Verify pong payload
        pong_payload = call_args[0][1]
        assert "timestamp" in pong_payload, "Pong must include timestamp"
        assert "server_time" in pong_payload, "Pong must include server_time"
        assert "server_seq" in pong_payload, "Pong must include server_seq"

        # Verify room targeting
        assert call_args[1]["room"] == test_sid, "Should emit to client's room"

    async def test_client_pong_event_contract(self, socketio_handlers, mock_state_manager):
        """Test 'client_pong' event - Server health check pong.

        Contract:
        - Direction: server_to_client
        - Payload: {timestamp: number, server_time: number, server_seq: number}
        - Required fields: timestamp, server_time, server_seq
        - timestamp should match ping timestamp
        """
        # This is tested as part of client_ping, but verify payload structure explicitly
        ping_handler = socketio_handlers._registered_handlers['client_ping']

        test_sid = "test-client-pong"
        ping_timestamp = 1234567890.123
        ping_data = {"timestamp": ping_timestamp}

        await ping_handler(test_sid, ping_data)

        # Get the emitted pong payload
        pong_payload = socketio_handlers.sio.emit.call_args[0][1]

        # Verify contract compliance
        assert "timestamp" in pong_payload, "Must include timestamp field"
        assert "server_time" in pong_payload, "Must include server_time field"
        assert "server_seq" in pong_payload, "Must include server_seq field"

        assert isinstance(pong_payload["timestamp"], (int, float)), "timestamp must be number"
        assert isinstance(pong_payload["server_time"], (int, float)), "server_time must be number"
        assert isinstance(pong_payload["server_seq"], int), "server_seq must be number"

        # Verify timestamp echo
        assert pong_payload["timestamp"] == ping_timestamp, "timestamp should match ping"
        assert pong_payload["server_seq"] == 42, "server_seq should match state manager value"
