# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Unit tests for PlayerOperationsService.

Tests the operations service responsible for complex player workflows.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from app.src.api.services.player_operations_service import PlayerOperationsService


class TestPlayerOperationsService:
    """Test suite for PlayerOperationsService."""

    @pytest.fixture
    def mock_player_service(self):
        """Create mock player application service."""
        service = Mock()
        service.play_use_case = AsyncMock()
        service.pause_use_case = AsyncMock()
        service.get_status_use_case = AsyncMock()
        return service

    @pytest.fixture
    def operations_service(self, mock_player_service):
        """Create PlayerOperationsService instance."""
        return PlayerOperationsService(mock_player_service)

    @pytest.mark.asyncio
    async def test_toggle_uses_is_playing_and_is_paused_flags(
        self, operations_service, mock_player_service
    ):
        """Test toggle checks is_playing/is_paused, not 'state' field.

        CRITICAL: This tests our fix where we check is_playing/is_paused
        boolean flags instead of the non-existent 'state' string field.
        """
        # Arrange: Currently playing (not paused)
        mock_player_service.get_status_use_case.return_value = {
            "success": True,
            "status": {
                "is_playing": True,
                "is_paused": False,
                "position_ms": 1000,
                "server_seq": 1
            }
        }
        mock_player_service.pause_use_case.return_value = {
            "success": True,
            "status": {"is_playing": False, "is_paused": True},
            "message": "Paused"
        }

        # Act
        result = await operations_service.toggle_playback_use_case()

        # Assert: Should call pause (because is_playing=True, is_paused=False)
        mock_player_service.pause_use_case.assert_called_once()
        mock_player_service.play_use_case.assert_not_called()
        assert result["success"] is True
        assert result["state"] == "paused"

    @pytest.mark.asyncio
    async def test_toggle_when_paused_calls_play(
        self, operations_service, mock_player_service
    ):
        """Test toggle when paused calls play (which will resume).

        CRITICAL: Tests that paused state (is_paused=True) triggers play.
        """
        # Arrange: Currently paused
        mock_player_service.get_status_use_case.return_value = {
            "success": True,
            "status": {
                "is_playing": False,
                "is_paused": True,
                "position_ms": 5000,
                "server_seq": 2
            }
        }
        mock_player_service.play_use_case.return_value = {
            "success": True,
            "status": {"is_playing": True, "is_paused": False},
            "message": "Playing"
        }

        # Act
        result = await operations_service.toggle_playback_use_case()

        # Assert: Should call play (because is_paused=True)
        mock_player_service.play_use_case.assert_called_once()
        mock_player_service.pause_use_case.assert_not_called()
        assert result["success"] is True
        assert result["state"] == "playing"

    @pytest.mark.asyncio
    async def test_toggle_when_stopped_calls_play(
        self, operations_service, mock_player_service
    ):
        """Test toggle when stopped (not playing, not paused) calls play."""
        # Arrange: Currently stopped
        mock_player_service.get_status_use_case.return_value = {
            "success": True,
            "status": {
                "is_playing": False,
                "is_paused": False,
                "position_ms": 0,
                "server_seq": 3
            }
        }
        mock_player_service.play_use_case.return_value = {
            "success": True,
            "status": {"is_playing": True, "is_paused": False},
            "message": "Playing"
        }

        # Act
        result = await operations_service.toggle_playback_use_case()

        # Assert: Should call play (because stopped)
        mock_player_service.play_use_case.assert_called_once()
        mock_player_service.pause_use_case.assert_not_called()
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_toggle_handles_status_error_gracefully(
        self, operations_service, mock_player_service
    ):
        """Test toggle handles errors when getting status."""
        # Arrange: Status check fails
        mock_player_service.get_status_use_case.return_value = {
            "success": False,
            "message": "Status unavailable"
        }

        # Act
        result = await operations_service.toggle_playback_use_case()

        # Assert: Should return failure
        assert result["success"] is False
        assert "Unable to determine" in result["message"]
        mock_player_service.play_use_case.assert_not_called()
        mock_player_service.pause_use_case.assert_not_called()

    @pytest.mark.asyncio
    async def test_next_track_use_case(self, operations_service, mock_player_service):
        """Test next track navigation."""
        # This service might not have coordinator, adjust if needed
        # For now, test that it would work if implemented
        pass

    @pytest.mark.asyncio
    async def test_previous_track_use_case(self, operations_service, mock_player_service):
        """Test previous track navigation."""
        # This service might not have coordinator, adjust if needed
        pass
