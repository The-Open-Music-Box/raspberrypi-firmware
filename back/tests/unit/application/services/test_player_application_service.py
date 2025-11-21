# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Tests for PlayerApplicationService."""

import pytest
from unittest.mock import Mock, AsyncMock

from app.src.application.services.player_application_service import PlayerApplicationService


class TestPlayerApplicationService:
    """Test suite for PlayerApplicationService."""

    @pytest.fixture
    def mock_playback_coordinator(self):
        """Mock PlaybackCoordinator."""
        coordinator = Mock()
        coordinator.play.return_value = True
        coordinator.pause.return_value = True
        coordinator.stop.return_value = True
        coordinator.next_track.return_value = True
        coordinator.previous_track.return_value = True
        coordinator.seek_to_position.return_value = True
        coordinator.set_volume = AsyncMock(return_value=True)
        coordinator.get_playback_status.return_value = {
            "is_playing": False,
            "current_track": {"id": "1", "title": "Test Track"},
            "position_ms": 5000,
            "duration_ms": 180000,
            "volume": 75
        }
        return coordinator

    @pytest.fixture
    def player_service(self, mock_playback_coordinator):
        """Create PlayerApplicationService instance."""
        return PlayerApplicationService(mock_playback_coordinator)

    def test_init_requires_coordinator(self):
        """Test that initialization requires a PlaybackCoordinator."""
        with pytest.raises(ValueError, match="PlaybackCoordinator is required"):
            PlayerApplicationService(None)

    async def test_play_use_case_success(self, player_service, mock_playback_coordinator):
        """Test successful play operation."""
        result = await player_service.play_use_case()

        assert result["success"] is True
        assert result["message"] == "Playback started successfully"
        assert "status" in result
        mock_playback_coordinator.play.assert_called_once()
        mock_playback_coordinator.get_playback_status.assert_called_once()

    async def test_play_use_case_failure(self, player_service, mock_playback_coordinator):
        """Test failed play operation."""
        mock_playback_coordinator.play.return_value = False

        result = await player_service.play_use_case()

        # Service always returns success for contract compliance, but with different message
        assert result["success"] is True
        assert result["message"] == "Playback unavailable - no active playlist"
        mock_playback_coordinator.play.assert_called_once()

    async def test_pause_use_case_success(self, player_service, mock_playback_coordinator):
        """Test successful pause operation."""
        result = await player_service.pause_use_case()

        assert result["success"] is True
        assert result["message"] == "Playback paused successfully"
        assert "status" in result
        mock_playback_coordinator.pause.assert_called_once()

    async def test_pause_use_case_failure(self, player_service, mock_playback_coordinator):
        """Test failed pause operation."""
        mock_playback_coordinator.pause.return_value = False

        result = await player_service.pause_use_case()

        # Service always returns success for contract compliance, but with different message
        assert result["success"] is True
        assert result["message"] == "Pause unavailable - not playing"

    async def test_stop_use_case_success(self, player_service, mock_playback_coordinator):
        """Test successful stop operation."""
        result = await player_service.stop_use_case()

        assert result["success"] is True
        assert result["message"] == "Playback stopped successfully"
        assert "status" in result
        mock_playback_coordinator.stop.assert_called_once()

    async def test_next_track_use_case_success(self, player_service, mock_playback_coordinator):
        """Test successful next track operation."""
        result = await player_service.next_track_use_case()

        assert result["success"] is True
        assert result["message"] == "Skipped to next track"
        assert "track" in result
        assert "status" in result
        mock_playback_coordinator.next_track.assert_called_once()

    async def test_previous_track_use_case_success(self, player_service, mock_playback_coordinator):
        """Test successful previous track operation."""
        result = await player_service.previous_track_use_case()

        assert result["success"] is True
        assert result["message"] == "Skipped to previous track"
        assert "track" in result
        assert "status" in result
        mock_playback_coordinator.previous_track.assert_called_once()

    async def test_seek_use_case_success(self, player_service, mock_playback_coordinator):
        """Test successful seek operation."""
        position_ms = 30000

        result = await player_service.seek_use_case(position_ms)

        assert result["success"] is True
        assert result["message"] == f"Seeked to {position_ms}ms"
        assert result["position_ms"] == position_ms
        assert "status" in result
        mock_playback_coordinator.seek_to_position.assert_called_once_with(position_ms)

    async def test_seek_use_case_negative_position(self, player_service):
        """Test seek with negative position."""
        result = await player_service.seek_use_case(-1000)

        # Service always returns success for contract compliance, but with validation message
        assert result["success"] is True
        assert result["message"] == "Position cannot be negative"

    async def test_set_volume_use_case_success(self, player_service, mock_playback_coordinator):
        """Test successful volume setting."""
        volume = 80

        result = await player_service.set_volume_use_case(volume)

        assert result["success"] is True
        assert result["message"] == f"Volume set to {volume}%"
        assert result["volume"] == volume
        mock_playback_coordinator.set_volume.assert_called_once_with(volume)

    async def test_set_volume_use_case_invalid_range(self, player_service):
        """Test volume setting with invalid range."""
        # Test too low - service returns success for contract compliance
        result = await player_service.set_volume_use_case(-10)
        assert result["success"] is True
        assert result["message"] == "Volume must be between 0 and 100"

        # Test too high - service returns success for contract compliance
        result = await player_service.set_volume_use_case(150)
        assert result["success"] is True
        assert result["message"] == "Volume must be between 0 and 100"

    async def test_get_status_use_case_success(self, player_service, mock_playback_coordinator):
        """Test successful status retrieval."""
        result = await player_service.get_status_use_case()

        assert result["success"] is True
        assert result["message"] == "Player status retrieved successfully"
        assert "status" in result
        mock_playback_coordinator.get_playback_status.assert_called_once()

    async def test_exception_handling(self, player_service, mock_playback_coordinator):
        """Test exception handling in use cases."""
        mock_playback_coordinator.play.side_effect = Exception("Test error")

        result = await player_service.play_use_case()

        # Service returns success for contract compliance even on exceptions
        assert result["success"] is True
        assert result["message"] == "Playback unavailable"
        assert "status" in result

    async def test_active_track_structure_in_status(self, player_service, mock_playback_coordinator):
        """Test that get_status_use_case returns properly structured active_track object.

        This test verifies the fix for the issue where track title and playlist title
        weren't displaying in the frontend. The backend must send a complete active_track
        object, not just flat fields.
        """
        # Mock coordinator to return track with all fields
        mock_playback_coordinator.get_playback_status.return_value = {
            "is_playing": True,
            "position_ms": 11000,
            "duration_ms": 63000,
            "volume": 75,
            "playlist_id": "playlist-123",
            "playlist_name": "My Awesome Playlist",
            "current_track": {
                "id": "track-456",
                "title": "Amazing Song",
                "filename": "song.mp3",
                "file_path": "/music/song.mp3",
                "duration_ms": 63000
            },
            "current_track_number": 2,
            "total_tracks": 10,
            "can_prev": True,
            "can_next": True
        }

        result = await player_service.get_status_use_case()

        # Verify basic response structure
        assert result["success"] is True
        assert "status" in result

        status = result["status"]

        # CRITICAL: Verify active_track is a complete object, not null
        assert status["active_track"] is not None, "active_track must not be null when track is playing"
        assert isinstance(status["active_track"], dict), "active_track must be an object"

        # Verify all required track fields are present
        assert status["active_track"]["id"] == "track-456"
        assert status["active_track"]["title"] == "Amazing Song"
        assert status["active_track"]["filename"] == "song.mp3"
        assert status["active_track"]["file_path"] == "/music/song.mp3"
        assert status["active_track"]["duration_ms"] == 63000

        # Verify playlist information is included
        assert status["active_playlist_id"] == "playlist-123"
        assert status["active_playlist_title"] == "My Awesome Playlist"

        # Verify track index information
        assert status["track_index"] == 1  # 0-based index (track_number 2 = index 1)
        assert status["track_count"] == 10

        # Verify backward compatibility - flat fields should still exist
        assert status["active_track_id"] == "track-456"

    async def test_active_track_null_when_no_track(self, player_service, mock_playback_coordinator):
        """Test that active_track is null when no track is playing."""
        # Mock coordinator to return no current track
        mock_playback_coordinator.get_playback_status.return_value = {
            "is_playing": False,
            "position_ms": 0,
            "duration_ms": 0,
            "volume": 50,
            "current_track": None,
            "can_prev": False,
            "can_next": False
        }

        result = await player_service.get_status_use_case()

        assert result["success"] is True
        status = result["status"]

        # When no track, active_track should be None
        assert status["active_track"] is None
        assert status["active_track_id"] is None
        assert status["active_playlist_id"] is None
        assert status["active_playlist_title"] is None