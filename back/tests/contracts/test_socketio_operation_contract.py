"""Contract tests for Socket.IO Operation acknowledgment events.

Validates that Socket.IO operation ack/error events conform to the expected contract.

Progress: 2/2 events tested ✅
"""

import pytest
from app.src.common.socket_events import SocketEventBuilder


@pytest.mark.asyncio
class TestSocketIOOperationContract:
    """Contract tests for Socket.IO operation acknowledgment events."""

    async def test_ack_op_event_contract(self):
        """Test 'ack:op' event - Operation success acknowledgment.

        Contract:
        - Direction: server_to_client
        - Payload: {client_op_id: str, success: bool, server_seq: number, data?: any, message?: str}
        - Required fields: client_op_id, success, server_seq
        - success must be true
        """
        # Create operation acknowledgment event
        ack_event = SocketEventBuilder.create_operation_ack_event(
            client_op_id="client-op-123",
            success=True,
            server_seq=200,
            data={"playlist_id": "new-playlist-456", "tracks_count": 0},
            message="Playlist created successfully"
        )

        # Verify contract compliance
        assert "client_op_id" in ack_event, "Must include client_op_id"
        assert "success" in ack_event, "Must include success"
        assert "server_seq" in ack_event, "Must include server_seq"

        assert isinstance(ack_event["client_op_id"], str), "client_op_id must be string"
        assert isinstance(ack_event["success"], bool), "success must be boolean"
        assert isinstance(ack_event["server_seq"], int), "server_seq must be number"

        assert ack_event["client_op_id"] == "client-op-123", "client_op_id must match request"
        assert ack_event["success"] is True, "success must be true for ack"
        assert ack_event["server_seq"] == 200, "server_seq must be present"

        # Verify optional fields
        assert "data" in ack_event, "Should include operation result data"
        assert "message" in ack_event, "Should include success message"

    async def test_err_op_event_contract(self):
        """Test 'err:op' event - Operation error acknowledgment.

        Contract:
        - Direction: server_to_client
        - Payload: {client_op_id: str, success: bool, server_seq: number, message: str}
        - Required fields: client_op_id, success, server_seq, message
        - success must be false
        - message contains error description
        """
        # Create operation error event
        err_event = SocketEventBuilder.create_operation_ack_event(
            client_op_id="client-op-456",
            success=False,
            server_seq=201,
            message="Playlist creation failed: Invalid playlist name"
        )

        # Verify contract compliance
        assert "client_op_id" in err_event, "Must include client_op_id"
        assert "success" in err_event, "Must include success"
        assert "server_seq" in err_event, "Must include server_seq"
        assert "message" in err_event, "Must include error message"

        assert isinstance(err_event["client_op_id"], str), "client_op_id must be string"
        assert isinstance(err_event["success"], bool), "success must be boolean"
        assert isinstance(err_event["server_seq"], int), "server_seq must be number"
        assert isinstance(err_event["message"], str), "message must be string"

        assert err_event["client_op_id"] == "client-op-456", "client_op_id must match request"
        assert err_event["success"] is False, "success must be false for error"
        assert err_event["server_seq"] == 201, "server_seq must be present"
        assert "failed" in err_event["message"].lower(), "message should describe the error"
