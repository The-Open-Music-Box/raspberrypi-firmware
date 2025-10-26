# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Comprehensive tests for audio backend implementations.

These tests verify that audio backends implement the protocol correctly
and handle various edge cases and error conditions properly.
"""

import pytest
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock

from app.src.domain.audio.backends.implementations.mock_audio_backend import MockAudioBackend
from app.src.domain.protocols.notification_protocol import PlaybackNotifierProtocol


class TestMockAudioBackend:
    """Test the mock audio backend implementation."""

    def setup_method(self):
        """Set up test dependencies."""
        # Create a mock PlaybackSubject with notify method
        self.mock_playback_subject = Mock()
        self.mock_playback_subject.notify = Mock()
        self.backend = MockAudioBackend(self.mock_playback_subject)

    def test_initialization(self):
        """Test mock backend initialization."""
        assert self.backend._playback_subject == self.mock_playback_subject
        assert self.backend._backend_name == "MockAudioBackend"
        assert self.backend.initialize() is True

    @pytest.mark.asyncio
    async def test_play_file_success(self):
        """Test successful file playback."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_path = temp_file.name

        try:
            result = await self.backend.play(temp_path)
            assert result is True
            assert self.backend.is_playing is True
            assert self.backend.get_current_file() == temp_path

            # Verify notification was sent
            self.mock_playback_subject.notify.assert_called()
        finally:
            Path(temp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_play_file_nonexistent(self):
        """Test playing non-existent file."""
        result = await self.backend.play("/nonexistent/file.mp3")
        assert result is False
        assert self.backend.is_playing is False

    @pytest.mark.asyncio
    async def test_pause_when_playing(self):
        """Test pausing during playback."""
        # Start playing first
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_path = temp_file.name

        try:
            await self.backend.play(temp_path)
            assert self.backend.is_playing is True

            result = await self.backend.pause()
            assert result is True
            assert self.backend.is_playing is False
        finally:
            Path(temp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_pause_when_not_playing(self):
        """Test pausing when not playing."""
        result = await self.backend.pause()
        assert result is False

    @pytest.mark.asyncio
    async def test_resume_when_paused(self):
        """Test resuming after pause."""
        # Start playing and then pause
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_path = temp_file.name

        try:
            await self.backend.play(temp_path)
            await self.backend.pause()
            assert self.backend.is_playing is False

            result = await self.backend.resume()
            assert result is True
            assert self.backend.is_playing is True
        finally:
            Path(temp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_resume_when_not_paused(self):
        """Test resuming when not paused."""
        result = await self.backend.resume()
        assert result is False

    @pytest.mark.asyncio
    async def test_stop_when_playing(self):
        """Test stopping during playback."""
        # Start playing first
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_path = temp_file.name

        try:
            await self.backend.play(temp_path)
            assert self.backend.is_playing is True

            result = await self.backend.stop()
            assert result is True
            assert self.backend.is_playing is False
            assert self.backend.get_current_file() is None
        finally:
            Path(temp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_stop_when_not_playing(self):
        """Test stopping when not playing."""
        result = await self.backend.stop()
        assert result is True  # Stop should always succeed in Mock
        assert self.backend.is_playing is False

    @pytest.mark.asyncio
    async def test_set_volume_valid_range(self):
        """Test setting volume within valid range."""
        result = await self.backend.set_volume(85)
        assert result is True

        volume = await self.backend.get_volume()
        assert volume == 85

    @pytest.mark.asyncio
    async def test_set_volume_below_minimum(self):
        """Test setting volume below minimum."""
        result = await self.backend.set_volume(-10)
        assert result is False  # Should reject invalid values

    @pytest.mark.asyncio
    async def test_set_volume_above_maximum(self):
        """Test setting volume above maximum."""
        result = await self.backend.set_volume(150)
        assert result is False  # Should reject invalid values

    @pytest.mark.asyncio
    async def test_set_volume_boundary_values(self):
        """Test setting volume at boundary values."""
        # Minimum boundary
        result_min = await self.backend.set_volume(0)
        assert result_min is True
        volume_min = await self.backend.get_volume()
        assert volume_min == 0

        # Maximum boundary
        result_max = await self.backend.set_volume(100)
        assert result_max is True
        volume_max = await self.backend.get_volume()
        assert volume_max == 100

    @pytest.mark.asyncio
    async def test_notification_subject_integration(self):
        """Test integration with notification subject."""
        # Create a temp file for testing
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_path = temp_file.name

        try:
            # Play a file and verify notification
            await self.backend.play(temp_path)

            # Check that notify was called
            self.mock_playback_subject.notify.assert_called()

            # Get the call arguments
            call_args = self.mock_playback_subject.notify.call_args[0][0]
            assert 'event' in call_args
            assert call_args['event'] == 'track_started'
            assert 'file_path' in call_args
        finally:
            Path(temp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_get_position(self):
        """Test getting playback position."""
        # When not playing
        position = await self.backend.get_position()
        assert position is None

        # When playing
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_path = temp_file.name

        try:
            await self.backend.play(temp_path)
            await asyncio.sleep(0.1)  # Let some time pass

            position = await self.backend.get_position()
            assert position is not None
            assert position >= 0
        finally:
            Path(temp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_get_duration(self):
        """Test getting track duration."""
        # When no track is loaded
        duration = await self.backend.get_duration()
        assert duration is None

        # When track is loaded
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_path = temp_file.name

        try:
            await self.backend.play(temp_path)

            duration = await self.backend.get_duration()
            assert duration is not None
            assert duration > 0  # Mock duration in milliseconds
        finally:
            Path(temp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_seek(self):
        """Test seeking to position."""
        # Seek to valid position
        result = await self.backend.seek(5000)  # 5 seconds
        assert result is True

        # Seek to negative position (should fail)
        result = await self.backend.seek(-1000)
        assert result is False

    def test_cleanup(self):
        """Test backend cleanup."""
        # Set up some state
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_path = temp_file.name

        try:
            self.backend.play_file(temp_path)
            assert self.backend.is_playing is True

            # Cleanup should reset state
            self.backend.cleanup()
            assert self.backend.is_playing is False
            assert self.backend.get_current_file() is None
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_is_busy_property(self):
        """Test the is_busy property for track completion detection."""
        # When not playing, should not be busy
        assert self.backend.is_busy is False

        # When playing, should be busy initially
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_path = temp_file.name

        try:
            self.backend.play_file(temp_path)
            assert self.backend.is_busy is True

            # The mock backend simulates track completion after duration
            # We can't easily test the full duration in unit tests
        finally:
            Path(temp_path).unlink(missing_ok=True)