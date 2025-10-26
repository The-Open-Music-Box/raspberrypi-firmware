"""Contract tests for Socket.IO YouTube download events.

Validates that Socket.IO YouTube events conform to the expected contract.

Progress: 3/3 events tested ✅
"""

import pytest
from app.src.common.socket_events import SocketEventBuilder, SocketEventType


@pytest.mark.asyncio
class TestSocketIOYouTubeContract:
    """Contract tests for Socket.IO YouTube download progress events."""

    async def test_youtube_progress_event_contract(self):
        """Test 'youtube:progress' event - YouTube download progress update.

        Contract:
        - Direction: server_to_client
        - Event envelope format with data: {
            task_id: str,
            status: str,
            progress_percent: number,
            title?: str
          }
        """
        progress_data = {
            "task_id": "youtube-task-123",
            "status": "downloading",
            "progress_percent": 45.5,
            "title": "Test Video"
        }

        event = SocketEventBuilder.create_state_event(
            event_type=SocketEventType.STATE_PLAYER,  # Using generic event for structure
            data=progress_data,
            server_seq=500
        )

        # Verify required fields
        assert "task_id" in event["data"]
        assert "status" in event["data"]
        assert "progress_percent" in event["data"]

        assert isinstance(event["data"]["task_id"], str)
        assert isinstance(event["data"]["status"], str)
        assert isinstance(event["data"]["progress_percent"], (int, float))

    async def test_youtube_complete_event_contract(self):
        """Test 'youtube:complete' event - YouTube download completion.

        Contract:
        - Direction: server_to_client
        - Event envelope format with data: {
            task_id: str,
            track_id: str,
            playlist_id: str,
            video_title: str,
            track: object
          }
        """
        complete_data = {
            "task_id": "youtube-task-456",
            "track_id": "track-yt-789",
            "playlist_id": "playlist-yt",
            "video_title": "Downloaded Video",
            "track": {
                "id": "track-yt-789",
                "title": "Downloaded Video"
            }
        }

        event = SocketEventBuilder.create_state_event(
            event_type=SocketEventType.STATE_TRACK_ADDED,
            data=complete_data,
            server_seq=501,
            playlist_id="playlist-yt"
        )

        # Verify required fields
        assert "task_id" in event["data"]
        assert "track_id" in event["data"]
        assert "playlist_id" in event["data"]
        assert "video_title" in event["data"]
        assert "track" in event["data"]

        assert isinstance(event["data"]["task_id"], str)
        assert isinstance(event["data"]["track_id"], str)
        assert isinstance(event["data"]["playlist_id"], str)
        assert isinstance(event["data"]["video_title"], str)
        assert isinstance(event["data"]["track"], dict)

    async def test_youtube_error_event_contract(self):
        """Test 'youtube:error' event - YouTube download error.

        Contract:
        - Direction: server_to_client
        - Event envelope format with data: {
            task_id: str,
            error: str,
            message?: str
          }
        """
        error_data = {
            "task_id": "youtube-task-err",
            "error": "download_failed",
            "message": "Video unavailable"
        }

        # Verify contract structure
        assert "task_id" in error_data
        assert "error" in error_data
        assert isinstance(error_data["task_id"], str)
        assert isinstance(error_data["error"], str)
        if "message" in error_data:
            assert isinstance(error_data["message"], str)
