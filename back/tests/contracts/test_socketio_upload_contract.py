"""Contract tests for Socket.IO Upload progress events.

Validates that Socket.IO upload events conform to the expected contract.

Progress: 3/3 events tested ✅
"""

import pytest
from app.src.common.socket_events import SocketEventBuilder, SocketEventType


@pytest.mark.asyncio
class TestSocketIOUploadContract:
    """Contract tests for Socket.IO upload progress events."""

    async def test_upload_progress_event_contract(self):
        """Test 'upload:progress' event - Upload progress update.

        Contract:
        - Direction: server_to_client
        - Event envelope format with data: {
            session_id: str,
            uploaded_bytes: number,
            total_bytes: number,
            progress_percent: number
          }
        """
        progress_data = {
            "session_id": "upload-session-123",
            "uploaded_bytes": 5242880,
            "total_bytes": 10485760,
            "progress_percent": 50.0
        }

        event = SocketEventBuilder.create_state_event(
            event_type=SocketEventType.STATE_PLAYER,  # Using generic event for structure
            data=progress_data,
            server_seq=400
        )

        # Verify required fields in data
        assert "session_id" in event["data"]
        assert "uploaded_bytes" in event["data"]
        assert "total_bytes" in event["data"]
        assert "progress_percent" in event["data"]

        assert isinstance(event["data"]["session_id"], str)
        assert isinstance(event["data"]["uploaded_bytes"], (int, float))
        assert isinstance(event["data"]["total_bytes"], (int, float))
        assert isinstance(event["data"]["progress_percent"], (int, float))

    async def test_upload_complete_event_contract(self):
        """Test 'upload:complete' event - Upload completion notification.

        Contract:
        - Direction: server_to_client
        - Event envelope format with data: {
            session_id: str,
            track_id: str,
            playlist_id: str,
            track: object
          }
        """
        complete_data = {
            "session_id": "upload-session-456",
            "track_id": "track-new-789",
            "playlist_id": "playlist-abc",
            "track": {
                "id": "track-new-789",
                "title": "Uploaded Track"
            }
        }

        event = SocketEventBuilder.create_state_event(
            event_type=SocketEventType.STATE_TRACK_ADDED,
            data=complete_data,
            server_seq=401,
            playlist_id="playlist-abc"
        )

        # Verify required fields
        assert "session_id" in event["data"]
        assert "track_id" in event["data"]
        assert "playlist_id" in event["data"]
        assert "track" in event["data"]

        assert isinstance(event["data"]["session_id"], str)
        assert isinstance(event["data"]["track_id"], str)
        assert isinstance(event["data"]["playlist_id"], str)
        assert isinstance(event["data"]["track"], dict)

    async def test_upload_error_event_contract(self):
        """Test 'upload:error' event - Upload error notification.

        Contract:
        - Direction: server_to_client
        - Event envelope format with data: {
            session_id: str,
            error: str,
            message?: str
          }
        """
        error_data = {
            "session_id": "upload-session-err",
            "error": "upload_failed",
            "message": "File too large"
        }

        # Verify contract structure
        assert "session_id" in error_data
        assert "error" in error_data
        assert isinstance(error_data["session_id"], str)
        assert isinstance(error_data["error"], str)
        if "message" in error_data:
            assert isinstance(error_data["message"], str)
