# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Tests for AudioApplicationService

Comprehensive tests for audio application service including playlist playback,
playback controls, status retrieval, and volume management.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.src.application.services.audio_application_service import AudioApplicationService


class TestAudioApplicationService:
    """Test suite for AudioApplicationService."""

    @pytest.fixture
    def mock_audio_container(self):
        """Mock audio domain container."""
        container = Mock()
        container.is_initialized = True
        # Audio engine has both async and sync methods
        engine = AsyncMock()
        engine.get_state_dict = Mock(return_value={})  # Sync method
        container.audio_engine = engine
        return container

    @pytest.fixture
    def mock_playlist_service(self):
        """Mock playlist application service."""
        return AsyncMock()

    @pytest.fixture
    def mock_state_manager(self):
        """Mock state manager."""
        return AsyncMock()

    @pytest.fixture
    def audio_service(self, mock_audio_container, mock_playlist_service):
        """Create AudioApplicationService instance."""
        return AudioApplicationService(
            mock_audio_container,
            mock_playlist_service
        )

    @pytest.fixture
    def audio_service_with_state_manager(self, mock_audio_container, mock_playlist_service, mock_state_manager):
        """Create AudioApplicationService instance with state manager."""
        return AudioApplicationService(
            mock_audio_container,
            mock_playlist_service,
            mock_state_manager
        )

    # ================================================================================
    # Test __init__()
    # ================================================================================

    def test_init_with_required_params(self, mock_audio_container, mock_playlist_service):
        """Test initialization with required parameters."""
        # Act
        service = AudioApplicationService(mock_audio_container, mock_playlist_service)

        # Assert
        assert service._audio_container == mock_audio_container
        assert service._playlist_service == mock_playlist_service
        assert service._state_manager is None

    def test_init_with_state_manager(self, mock_audio_container, mock_playlist_service, mock_state_manager):
        """Test initialization with optional state manager."""
        # Act
        service = AudioApplicationService(
            mock_audio_container,
            mock_playlist_service,
            mock_state_manager
        )

        # Assert
        assert service._state_manager == mock_state_manager

    def test_init_requires_audio_container(self, mock_playlist_service):
        """Test initialization fails without audio container."""
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            AudioApplicationService(None, mock_playlist_service)
        assert "Audio domain container is required" in str(exc_info.value)

    def test_init_requires_playlist_service(self, mock_audio_container):
        """Test initialization fails without playlist service."""
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            AudioApplicationService(mock_audio_container, None)
        assert "Playlist application service is required" in str(exc_info.value)

    # ================================================================================
    # Test play_playlist_use_case()
    # ================================================================================

    @pytest.mark.asyncio
    async def test_play_playlist_success(self, audio_service, mock_playlist_service, mock_audio_container):
        """Test successful playlist playback."""
        # Arrange
        playlist_id = "playlist-123"
        mock_playlist_service.get_playlist_use_case.return_value = {
            "status": "success",
            "playlist": {
                "id": playlist_id,
                "title": "Test Playlist",
                "tracks": [
                    {
                        "track_number": 1,
                        "title": "Song 1",
                        "filename": "song1.mp3",
                        "file_path": "/path/to/song1.mp3",
                        "duration_ms": 180000
                    }
                ]
            }
        }
        mock_audio_container.audio_engine.set_playlist.return_value = True

        # Act
        result = await audio_service.play_playlist_use_case(playlist_id)

        # Assert
        assert result["status"] == "success"
        assert result["playlist_id"] == playlist_id
        assert result["track_count"] == 1
        mock_audio_container.audio_engine.set_playlist.assert_called_once()

    @pytest.mark.asyncio
    async def test_play_playlist_broadcasts_state(self, audio_service_with_state_manager, mock_playlist_service, mock_audio_container, mock_state_manager):
        """Test playlist playback broadcasts state change."""
        # Arrange
        playlist_id = "playlist-123"
        mock_playlist_service.get_playlist_use_case.return_value = {
            "status": "success",
            "playlist": {
                "id": playlist_id,
                "title": "Test Playlist",
                "tracks": [{"track_number": 1, "title": "Song 1", "filename": "song1.mp3"}]
            }
        }
        mock_audio_container.audio_engine.set_playlist.return_value = True

        # Act
        result = await audio_service_with_state_manager.play_playlist_use_case(playlist_id)

        # Assert
        assert result["status"] == "success"
        mock_state_manager.broadcast_playlist_started.assert_called_once_with(playlist_id)

    @pytest.mark.asyncio
    async def test_play_playlist_not_found(self, audio_service, mock_playlist_service):
        """Test playback when playlist not found."""
        # Arrange
        playlist_id = "missing-playlist"
        mock_playlist_service.get_playlist_use_case.return_value = {
            "status": "error",
            "message": "Playlist not found"
        }

        # Act
        result = await audio_service.play_playlist_use_case(playlist_id)

        # Assert
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_play_playlist_empty_tracks(self, audio_service, mock_playlist_service):
        """Test playback of empty playlist."""
        # Arrange
        playlist_id = "empty-playlist"
        mock_playlist_service.get_playlist_use_case.return_value = {
            "status": "success",
            "playlist": {
                "id": playlist_id,
                "tracks": []
            }
        }

        # Act
        result = await audio_service.play_playlist_use_case(playlist_id)

        # Assert
        assert result["status"] == "error"
        assert "empty playlist" in result["message"].lower()
        assert result["error_type"] == "validation_error"

    @pytest.mark.asyncio
    async def test_play_playlist_no_tracks_key(self, audio_service, mock_playlist_service):
        """Test playback when playlist has no tracks key."""
        # Arrange
        playlist_id = "no-tracks-playlist"
        mock_playlist_service.get_playlist_use_case.return_value = {
            "status": "success",
            "playlist": {"id": playlist_id}
        }

        # Act
        result = await audio_service.play_playlist_use_case(playlist_id)

        # Assert
        assert result["status"] == "error"
        assert "empty playlist" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_play_playlist_engine_failure(self, audio_service, mock_playlist_service, mock_audio_container):
        """Test playback when audio engine fails."""
        # Arrange
        playlist_id = "playlist-123"
        mock_playlist_service.get_playlist_use_case.return_value = {
            "status": "success",
            "playlist": {
                "id": playlist_id,
                "tracks": [{"track_number": 1, "title": "Song 1", "filename": "song1.mp3"}]
            }
        }
        mock_audio_container.audio_engine.set_playlist.return_value = False

        # Act
        result = await audio_service.play_playlist_use_case(playlist_id)

        # Assert
        assert result["status"] == "error"
        assert "Failed to start playlist" in result["message"]
        assert result["error_type"] == "audio_error"

    @pytest.mark.asyncio
    async def test_play_playlist_container_not_initialized(self, mock_playlist_service):
        """Test playback when audio container not initialized."""
        # Arrange
        container = Mock()
        container.is_initialized = False
        service = AudioApplicationService(container, mock_playlist_service)
        playlist_id = "playlist-123"
        mock_playlist_service.get_playlist_use_case.return_value = {
            "status": "success",
            "playlist": {
                "id": playlist_id,
                "tracks": [{"track_number": 1, "title": "Song 1"}]
            }
        }

        # Act
        result = await service.play_playlist_use_case(playlist_id)

        # Assert
        assert result["status"] == "error"
        assert "not initialized" in result["message"].lower()
        assert result["error_type"] == "service_unavailable"

    # ================================================================================
    # Test control_playback_use_case()
    # ================================================================================

    @pytest.mark.asyncio
    async def test_control_playback_play(self, audio_service, mock_audio_container):
        """Test playback control - play."""
        # Arrange
        mock_audio_container.audio_engine.resume.return_value = True

        # Act
        result = await audio_service.control_playback_use_case("play")

        # Assert
        assert result["status"] == "success"
        assert result["action"] == "play"
        mock_audio_container.audio_engine.resume.assert_called_once()

    @pytest.mark.asyncio
    async def test_control_playback_pause(self, audio_service, mock_audio_container):
        """Test playback control - pause."""
        # Arrange
        mock_audio_container.audio_engine.pause.return_value = True

        # Act
        result = await audio_service.control_playback_use_case("pause")

        # Assert
        assert result["status"] == "success"
        assert result["action"] == "pause"
        mock_audio_container.audio_engine.pause.assert_called_once()

    @pytest.mark.asyncio
    async def test_control_playback_stop(self, audio_service, mock_audio_container):
        """Test playback control - stop."""
        # Arrange
        mock_audio_container.audio_engine.stop.return_value = True

        # Act
        result = await audio_service.control_playback_use_case("stop")

        # Assert
        assert result["status"] == "success"
        mock_audio_container.audio_engine.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_control_playback_next(self, audio_service, mock_audio_container):
        """Test playback control - next."""
        # Arrange
        mock_audio_container.audio_engine.next_track.return_value = True

        # Act
        result = await audio_service.control_playback_use_case("next")

        # Assert
        assert result["status"] == "success"
        mock_audio_container.audio_engine.next_track.assert_called_once()

    @pytest.mark.asyncio
    async def test_control_playback_previous(self, audio_service, mock_audio_container):
        """Test playback control - previous."""
        # Arrange
        mock_audio_container.audio_engine.previous_track.return_value = True

        # Act
        result = await audio_service.control_playback_use_case("previous")

        # Assert
        assert result["status"] == "success"
        mock_audio_container.audio_engine.previous_track.assert_called_once()

    @pytest.mark.asyncio
    async def test_control_playback_unknown_action(self, audio_service):
        """Test playback control with unknown action."""
        # Act
        result = await audio_service.control_playback_use_case("invalid_action")

        # Assert
        assert result["status"] == "error"
        assert "Unknown playback action" in result["message"]
        assert result["error_type"] == "validation_error"

    @pytest.mark.asyncio
    async def test_control_playback_broadcasts_state(self, audio_service_with_state_manager, mock_audio_container, mock_state_manager):
        """Test playback control broadcasts state change."""
        # Arrange
        mock_audio_container.audio_engine.pause.return_value = True

        # Act
        result = await audio_service_with_state_manager.control_playback_use_case("pause")

        # Assert
        assert result["status"] == "success"
        mock_state_manager.broadcast_playback_changed.assert_called_once_with("pause")

    @pytest.mark.asyncio
    async def test_control_playback_engine_failure(self, audio_service, mock_audio_container):
        """Test playback control when engine fails."""
        # Arrange
        mock_audio_container.audio_engine.resume.return_value = False  # play action calls resume()

        # Act
        result = await audio_service.control_playback_use_case("play")

        # Assert
        assert result["status"] == "error"
        assert "Failed to execute" in result["message"]
        assert result["error_type"] == "audio_error"

    @pytest.mark.asyncio
    async def test_control_playback_container_not_initialized(self, mock_playlist_service):
        """Test playback control when container not initialized."""
        # Arrange
        container = Mock()
        container.is_initialized = False
        service = AudioApplicationService(container, mock_playlist_service)

        # Act
        result = await service.control_playback_use_case("play")

        # Assert
        assert result["status"] == "error"
        assert "not initialized" in result["message"].lower()
        assert result["error_type"] == "service_unavailable"

    # ================================================================================
    # Test get_playback_status_use_case()
    # ================================================================================

    def test_get_playback_status_success(self, audio_service, mock_audio_container):
        """Test successful playback status retrieval."""
        # Arrange
        expected_state = {
            "is_playing": True,
            "current_track": 1,
            "volume": 75
        }
        mock_audio_container.audio_engine.get_state_dict.return_value = expected_state

        # Act
        result = audio_service.get_playback_status_use_case()

        # Assert
        assert result["status"] == "success"
        assert result["playback_status"] == expected_state
        mock_audio_container.audio_engine.get_state_dict.assert_called_once()

    def test_get_playback_status_container_not_initialized(self, mock_playlist_service):
        """Test playback status when container not initialized."""
        # Arrange
        container = Mock()
        container.is_initialized = False
        service = AudioApplicationService(container, mock_playlist_service)

        # Act
        result = service.get_playback_status_use_case()

        # Assert
        assert result["status"] == "error"
        assert "not initialized" in result["message"].lower()
        assert result["error_type"] == "service_unavailable"

    # ================================================================================
    # Test set_volume_use_case()
    # ================================================================================

    @pytest.mark.asyncio
    async def test_set_volume_success(self, audio_service, mock_audio_container):
        """Test successful volume setting."""
        # Arrange
        volume = 75
        mock_audio_container.audio_engine.set_volume.return_value = True

        # Act
        result = await audio_service.set_volume_use_case(volume)

        # Assert
        assert result["status"] == "success"
        assert result["volume"] == volume
        mock_audio_container.audio_engine.set_volume.assert_called_once_with(volume)

    @pytest.mark.asyncio
    async def test_set_volume_broadcasts_state(self, audio_service_with_state_manager, mock_audio_container, mock_state_manager):
        """Test volume setting broadcasts state change."""
        # Arrange
        volume = 50
        mock_audio_container.audio_engine.set_volume.return_value = True

        # Act
        result = await audio_service_with_state_manager.set_volume_use_case(volume)

        # Assert
        assert result["status"] == "success"
        mock_state_manager.broadcast_volume_changed.assert_called_once_with(volume)

    @pytest.mark.asyncio
    async def test_set_volume_min_value(self, audio_service, mock_audio_container):
        """Test volume setting with minimum value."""
        # Arrange
        mock_audio_container.audio_engine.set_volume.return_value = True

        # Act
        result = await audio_service.set_volume_use_case(0)

        # Assert
        assert result["status"] == "success"
        assert result["volume"] == 0

    @pytest.mark.asyncio
    async def test_set_volume_max_value(self, audio_service, mock_audio_container):
        """Test volume setting with maximum value."""
        # Arrange
        mock_audio_container.audio_engine.set_volume.return_value = True

        # Act
        result = await audio_service.set_volume_use_case(100)

        # Assert
        assert result["status"] == "success"
        assert result["volume"] == 100

    @pytest.mark.asyncio
    async def test_set_volume_below_min(self, audio_service):
        """Test volume setting below minimum."""
        # Act
        result = await audio_service.set_volume_use_case(-1)

        # Assert
        assert result["status"] == "error"
        assert "between 0 and 100" in result["message"]
        assert result["error_type"] == "validation_error"

    @pytest.mark.asyncio
    async def test_set_volume_above_max(self, audio_service):
        """Test volume setting above maximum."""
        # Act
        result = await audio_service.set_volume_use_case(101)

        # Assert
        assert result["status"] == "error"
        assert "between 0 and 100" in result["message"]
        assert result["error_type"] == "validation_error"

    @pytest.mark.asyncio
    async def test_set_volume_engine_failure(self, audio_service, mock_audio_container):
        """Test volume setting when engine fails."""
        # Arrange
        mock_audio_container.audio_engine.set_volume.return_value = False

        # Act
        result = await audio_service.set_volume_use_case(50)

        # Assert
        assert result["status"] == "error"
        assert "Failed to set volume" in result["message"]
        assert result["error_type"] == "audio_error"

    @pytest.mark.asyncio
    async def test_set_volume_container_not_initialized(self, mock_playlist_service):
        """Test volume setting when container not initialized."""
        # Arrange
        container = Mock()
        container.is_initialized = False
        service = AudioApplicationService(container, mock_playlist_service)

        # Act
        result = await service.set_volume_use_case(50)

        # Assert
        assert result["status"] == "error"
        assert "not initialized" in result["message"].lower()
        assert result["error_type"] == "service_unavailable"

    @pytest.mark.asyncio
    async def test_set_volume_exception_handling(self, audio_service, mock_audio_container):
        """Test volume setting handles exceptions."""
        # Arrange
        mock_audio_container.audio_engine.set_volume.side_effect = Exception("Hardware error")

        # Act
        result = await audio_service.set_volume_use_case(50)

        # Assert
        assert result["status"] == "error"
        assert "Volume control failed" in result["message"]
        assert result["error_type"] == "application_error"
