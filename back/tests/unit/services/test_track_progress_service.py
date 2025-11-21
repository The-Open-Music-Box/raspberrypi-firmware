# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Tests for track progress service."""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.src.services.track_progress_service import TrackProgressService
from app.src.domain.audio.engine.state_manager import StateManager


class MockAudioController:
    """Mock AudioController for testing."""

    def __init__(self, playback_status=None):
        self._playback_status = playback_status or {}
        self.get_playback_status = Mock(return_value=self._playback_status)
        self.auto_advance_to_next = Mock(return_value=True)
        self._audio_service = Mock()
        self._audio_service.get_current_track_info = Mock(return_value={
            "title": "Test Track",
            "track_id": "track-123"
        })


class MockAsyncAudioController:
    """Mock AudioController with async methods for testing."""

    def __init__(self, playback_status=None):
        self._playback_status = playback_status or {}
        self.get_playback_status = AsyncMock(return_value=self._playback_status)
        self.auto_advance_to_next = Mock(return_value=True)
        self._audio_service = Mock()
        self._audio_service.get_current_track_info = Mock(return_value={
            "title": "Test Track",
            "track_id": "track-123"
        })


class MockPlaybackCoordinator:
    """Mock PlaybackCoordinator for testing."""

    def __init__(self, playback_status=None):
        self._playback_status = playback_status or {}
        self.get_playback_status = Mock(return_value=self._playback_status)
        self.toggle_pause = Mock()
        self.next_track = Mock(return_value=True)
        self._current_playlist_id = "playlist-123"
        self._audio_service = Mock()
        self._audio_service.get_current_track_info = Mock(return_value={
            "title": "Test Track",
            "track_id": "track-123"
        })


class TestTrackProgressServiceInit:
    """Test TrackProgressService initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        state_manager = Mock(spec=StateManager)
        audio_controller = MockAudioController()

        service = TrackProgressService(state_manager, audio_controller)

        assert service.state_manager == state_manager
        assert service.audio_controller == audio_controller
        assert service._running is False
        assert service._task is None
        assert service._error_count == 0
        assert service._max_consecutive_errors == 10

    def test_init_with_custom_interval(self):
        """Test initialization with custom interval."""
        state_manager = Mock(spec=StateManager)
        audio_controller = MockAudioController()

        service = TrackProgressService(state_manager, audio_controller, interval=0.5)

        assert service.interval == 0.5

    def test_init_without_audio_controller(self):
        """Test initialization without audio controller."""
        state_manager = Mock(spec=StateManager)

        service = TrackProgressService(state_manager, None)

        assert service.audio_controller is None
        assert service._controller_type == "None"

    def test_detect_controller_type_audio_controller(self):
        """Test controller type detection for AudioController."""
        state_manager = Mock(spec=StateManager)
        audio_controller = MockAudioController()

        service = TrackProgressService(state_manager, audio_controller)

        assert service._controller_type == "AudioController"

    def test_detect_controller_type_playback_coordinator(self):
        """Test controller type detection for PlaybackCoordinator."""
        state_manager = Mock(spec=StateManager)
        coordinator = MockPlaybackCoordinator()

        service = TrackProgressService(state_manager, coordinator)

        assert service._controller_type == "PlaybackCoordinator"

    def test_detect_controller_type_none(self):
        """Test controller type detection when no controller."""
        state_manager = Mock(spec=StateManager)

        service = TrackProgressService(state_manager, None)

        assert service._controller_type == "None"


class TestTrackProgressServiceStartStop:
    """Test service start and stop."""

    @pytest.mark.asyncio
    async def test_start(self):
        """Test starting the service."""
        state_manager = Mock(spec=StateManager)
        audio_controller = MockAudioController()

        service = TrackProgressService(state_manager, audio_controller, interval=0.1)

        await service.start()

        assert service._running is True
        assert service._task is not None

        # Clean up
        await service.stop()

    @pytest.mark.asyncio
    async def test_start_already_running(self):
        """Test starting service that's already running."""
        state_manager = Mock(spec=StateManager)
        audio_controller = MockAudioController()

        service = TrackProgressService(state_manager, audio_controller, interval=0.1)

        await service.start()
        initial_task = service._task

        # Try to start again
        await service.start()

        # Task should be the same
        assert service._task == initial_task

        # Clean up
        await service.stop()

    @pytest.mark.asyncio
    async def test_stop(self):
        """Test stopping the service."""
        state_manager = Mock(spec=StateManager)
        audio_controller = MockAudioController()

        service = TrackProgressService(state_manager, audio_controller, interval=0.1)

        await service.start()
        await asyncio.sleep(0.05)  # Let it run briefly
        await service.stop()

        assert service._running is False
        assert service._error_count == 0
        assert service._last_progress == {}

    @pytest.mark.asyncio
    async def test_stop_not_running(self):
        """Test stopping service that's not running."""
        state_manager = Mock(spec=StateManager)
        audio_controller = MockAudioController()

        service = TrackProgressService(state_manager, audio_controller)

        # Should not raise an error
        await service.stop()

        assert service._running is False


class TestTrackProgressServiceValidation:
    """Test position validation."""

    def test_validate_position_data_valid(self):
        """Test validation with valid position data."""
        state_manager = Mock(spec=StateManager)
        audio_controller = MockAudioController()
        service = TrackProgressService(state_manager, audio_controller)

        assert service._validate_position_data(10.0, 100.0, "track-123") is True

    def test_validate_position_data_none_time(self):
        """Test validation with None current_time."""
        state_manager = Mock(spec=StateManager)
        audio_controller = MockAudioController()
        service = TrackProgressService(state_manager, audio_controller)

        assert service._validate_position_data(None, 100.0, "track-123") is False

    def test_validate_position_data_negative_time(self):
        """Test validation with negative current_time."""
        state_manager = Mock(spec=StateManager)
        audio_controller = MockAudioController()
        service = TrackProgressService(state_manager, audio_controller)

        assert service._validate_position_data(-5.0, 100.0, "track-123") is False

    def test_validate_position_data_overflow(self):
        """Test validation with current_time exceeding duration."""
        state_manager = Mock(spec=StateManager)
        audio_controller = MockAudioController()
        service = TrackProgressService(state_manager, audio_controller)

        assert service._validate_position_data(110.0, 100.0, "track-123") is False

    def test_validate_position_data_small_overflow_allowed(self):
        """Test validation allows small overflow (< 1 second)."""
        state_manager = Mock(spec=StateManager)
        audio_controller = MockAudioController()
        service = TrackProgressService(state_manager, audio_controller)

        # 100.5 seconds with duration 100.0 should be valid (within 1 second buffer)
        assert service._validate_position_data(100.5, 100.0, "track-123") is True

    def test_validate_position_data_no_track_id(self):
        """Test validation with missing track_id is allowed."""
        state_manager = Mock(spec=StateManager)
        audio_controller = MockAudioController()
        service = TrackProgressService(state_manager, audio_controller)

        # None or empty track_id should be allowed temporarily
        assert service._validate_position_data(10.0, 100.0, None) is True
        assert service._validate_position_data(10.0, 100.0, "") is True

    def test_validate_position_data_no_duration(self):
        """Test validation with zero duration."""
        state_manager = Mock(spec=StateManager)
        audio_controller = MockAudioController()
        service = TrackProgressService(state_manager, audio_controller)

        # Zero duration should not cause false negatives
        assert service._validate_position_data(10.0, 0, "track-123") is True


class TestTrackProgressServiceProperties:
    """Test service properties."""

    def test_is_running_false(self):
        """Test is_running property when not running."""
        state_manager = Mock(spec=StateManager)
        audio_controller = MockAudioController()
        service = TrackProgressService(state_manager, audio_controller)

        assert service.is_running is False

    @pytest.mark.asyncio
    async def test_is_running_true(self):
        """Test is_running property when running."""
        state_manager = Mock(spec=StateManager)
        audio_controller = MockAudioController()
        service = TrackProgressService(state_manager, audio_controller, interval=0.1)

        await service.start()

        assert service.is_running is True

        # Clean up
        await service.stop()

    def test_error_count_initial(self):
        """Test error_count property initial value."""
        state_manager = Mock(spec=StateManager)
        audio_controller = MockAudioController()
        service = TrackProgressService(state_manager, audio_controller)

        assert service.error_count == 0

    def test_reset_error_count(self):
        """Test reset_error_count method."""
        state_manager = Mock(spec=StateManager)
        audio_controller = MockAudioController()
        service = TrackProgressService(state_manager, audio_controller)

        # Manually set error count
        service._error_count = 5

        service.reset_error_count()

        assert service.error_count == 0


class TestTrackProgressServiceErrorHandling:
    """Test error handling configuration."""

    def test_configure_error_handling_max_errors(self):
        """Test configuring max consecutive errors."""
        state_manager = Mock(spec=StateManager)
        audio_controller = MockAudioController()
        service = TrackProgressService(state_manager, audio_controller)

        service.configure_error_handling(max_consecutive_errors=20)

        assert service._max_consecutive_errors == 20

    def test_configure_error_handling_recovery_delay(self):
        """Test configuring recovery delay."""
        state_manager = Mock(spec=StateManager)
        audio_controller = MockAudioController()
        service = TrackProgressService(state_manager, audio_controller)

        service.configure_error_handling(recovery_delay=10.0)

        assert service._recovery_delay == 10.0

    def test_configure_error_handling_both(self):
        """Test configuring both parameters."""
        state_manager = Mock(spec=StateManager)
        audio_controller = MockAudioController()
        service = TrackProgressService(state_manager, audio_controller)

        service.configure_error_handling(max_consecutive_errors=15, recovery_delay=7.5)

        assert service._max_consecutive_errors == 15
        assert service._recovery_delay == 7.5


class TestTrackProgressServiceDiagnostics:
    """Test diagnostic tracking and reset."""

    def test_reset_diagnostic_attributes_all(self):
        """Test resetting all diagnostic attributes."""
        state_manager = Mock(spec=StateManager)
        audio_controller = MockAudioController()
        service = TrackProgressService(state_manager, audio_controller)

        # Set some diagnostic attributes
        service._first_status_logged = True
        service._emission_attempt_count = 50
        service._emit_counter = 100

        service._reset_diagnostic_attributes(preserve_counters=False)

        # All should be reset
        assert not hasattr(service, "_first_status_logged")
        assert not hasattr(service, "_emission_attempt_count")
        assert not hasattr(service, "_emit_counter")

    def test_reset_diagnostic_attributes_preserve_counters(self):
        """Test resetting diagnostic attributes while preserving counters."""
        state_manager = Mock(spec=StateManager)
        audio_controller = MockAudioController()
        service = TrackProgressService(state_manager, audio_controller)

        # Set some diagnostic attributes
        service._first_status_logged = True
        service._emission_attempt_count = 50
        service._emit_counter = 100

        service._reset_diagnostic_attributes(preserve_counters=True)

        # Flags should be reset, counters preserved
        assert not hasattr(service, "_first_status_logged")
        assert hasattr(service, "_emission_attempt_count")
        assert hasattr(service, "_emit_counter")


class TestTrackProgressServiceEmission:
    """Test progress emission functionality."""

    @pytest.mark.asyncio
    async def test_emit_immediate_position(self):
        """Test immediate position emission."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_position_update = AsyncMock(return_value={"event_type": "state:track_position"})

        audio_controller = MockAudioController({
            "position_ms": 10000,
            "duration_ms": 100000,
            "is_playing": True,
            "active_track_id": "track-123"
        })

        service = TrackProgressService(state_manager, audio_controller)
        service._running = True  # Must be running to emit

        await service.emit_immediate_position()

        # Should have called broadcast_position_update
        state_manager.broadcast_position_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_emit_progress_no_controller(self):
        """Test emission with no audio controller."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_position_update = AsyncMock()

        service = TrackProgressService(state_manager, None)

        await service._emit_progress()

        # Should not broadcast without controller
        state_manager.broadcast_position_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_emit_progress_no_state_manager(self):
        """Test emission with no state manager."""
        audio_controller = MockAudioController({
            "position_ms": 10000,
            "duration_ms": 100000,
            "is_playing": True,
            "active_track_id": "track-123"
        })

        service = TrackProgressService(None, audio_controller)
        service._running = True

        # Should not raise an error
        await service._emit_progress()

    @pytest.mark.asyncio
    async def test_emit_progress_with_async_controller(self):
        """Test emission with async audio controller."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_position_update = AsyncMock(return_value={"event_type": "state:track_position"})

        audio_controller = MockAsyncAudioController({
            "position_ms": 15000,
            "duration_ms": 120000,
            "is_playing": True,
            "active_track_id": "track-456"
        })

        service = TrackProgressService(state_manager, audio_controller)
        service._running = True

        await service._emit_progress()

        # Should have called async get_playback_status
        audio_controller.get_playback_status.assert_called_once()
        state_manager.broadcast_position_update.assert_called_once()


class TestTrackProgressServiceTrackChange:
    """Test track change detection."""

    @pytest.mark.asyncio
    async def test_check_for_track_change_first_track(self):
        """Test track change detection for first track."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()

        coordinator = MockPlaybackCoordinator()
        service = TrackProgressService(state_manager, coordinator)

        status = {
            "track_number": 1,
            "active_track_id": "track-123"
        }

        await service._check_for_track_change(status)

        # First track should trigger broadcast (track changed from None to 1)
        state_manager.broadcast_state_change.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_for_track_change_track_changed(self):
        """Test track change detection when track changes."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()

        coordinator = MockPlaybackCoordinator()
        service = TrackProgressService(state_manager, coordinator)

        # Set initial track
        service._last_track_number = 1
        service._last_track_id = "track-123"

        # Change to new track
        status = {
            "track_number": 2,
            "active_track_id": "track-456"
        }

        await service._check_for_track_change(status)

        # Should broadcast state change when track changes
        state_manager.broadcast_state_change.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_for_track_change_no_change(self):
        """Test track change detection when track hasn't changed."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()

        coordinator = MockPlaybackCoordinator()
        service = TrackProgressService(state_manager, coordinator)

        # Set initial track
        service._last_track_number = 1
        service._last_track_id = "track-123"

        # Same track
        status = {
            "track_number": 1,
            "active_track_id": "track-123"
        }

        await service._check_for_track_change(status)

        # Should not broadcast
        state_manager.broadcast_state_change.assert_not_called()


class TestTrackProgressServiceTrackEnd:
    """Test track end detection and auto-advance."""

    @pytest.mark.asyncio
    async def test_check_for_track_end_not_playing(self):
        """Test track end check when not playing."""
        state_manager = Mock(spec=StateManager)
        coordinator = MockPlaybackCoordinator()
        service = TrackProgressService(state_manager, coordinator)

        # Not playing - should not auto-advance
        await service._check_for_track_end(95.0, 100.0, is_playing=False)

        coordinator.next_track.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_for_track_end_not_near_end(self):
        """Test track end check when not near end."""
        state_manager = Mock(spec=StateManager)
        coordinator = MockPlaybackCoordinator()
        service = TrackProgressService(state_manager, coordinator)

        # Only at 50% - should not auto-advance
        await service._check_for_track_end(50.0, 100.0, is_playing=True)

        coordinator.next_track.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_for_track_end_short_duration(self):
        """Test track end check with suspiciously short duration."""
        state_manager = Mock(spec=StateManager)
        coordinator = MockPlaybackCoordinator()
        service = TrackProgressService(state_manager, coordinator)

        # Duration < 1 second - should not auto-advance
        await service._check_for_track_end(0.9, 0.95, is_playing=True)

        coordinator.next_track.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_for_track_end_track_started(self):
        """Test track end check when track just started."""
        state_manager = Mock(spec=StateManager)
        coordinator = MockPlaybackCoordinator()
        service = TrackProgressService(state_manager, coordinator)

        # current_time = 0 - should not auto-advance
        await service._check_for_track_end(0.0, 100.0, is_playing=True)

        coordinator.next_track.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_for_track_end_success_playback_coordinator(self):
        """Test successful track end with PlaybackCoordinator."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()

        coordinator = MockPlaybackCoordinator({
            "is_playing": True,
            "current_track": {"title": "Next Track"}
        })
        service = TrackProgressService(state_manager, coordinator)

        # At end of track (99.95 out of 100 seconds, >= duration - 0.1)
        await service._check_for_track_end(99.95, 100.0, is_playing=True)

        # Should call next_track
        coordinator.next_track.assert_called_once()
        # Should broadcast state change
        state_manager.broadcast_state_change.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_for_track_end_duplicate_prevention(self):
        """Test duplicate auto-advance prevention."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()

        coordinator = MockPlaybackCoordinator({
            "is_playing": True,
            "current_track": {"title": "Next Track"}
        })
        service = TrackProgressService(state_manager, coordinator)

        # First auto-advance (must be >= duration - 0.1)
        await service._check_for_track_end(99.95, 100.0, is_playing=True)

        # Try again immediately - should be prevented
        await service._check_for_track_end(99.95, 100.0, is_playing=True)

        # Should only be called once due to duplicate prevention
        assert coordinator.next_track.call_count == 1

    @pytest.mark.asyncio
    async def test_check_for_track_end_end_of_playlist(self):
        """Test track end when at end of playlist."""
        state_manager = Mock(spec=StateManager)
        coordinator = MockPlaybackCoordinator()
        coordinator.next_track = Mock(return_value=False)  # No next track

        service = TrackProgressService(state_manager, coordinator)

        # At end of track (must be >= duration - 0.1)
        await service._check_for_track_end(99.95, 100.0, is_playing=True)

        # Should try next_track but not broadcast state change (no next track)
        coordinator.next_track.assert_called_once()


class TestTrackProgressServiceBroadcast:
    """Test broadcast after auto-advance."""

    @pytest.mark.asyncio
    async def test_broadcast_player_state_after_auto_advance(self):
        """Test broadcasting player state after auto-advance."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()

        coordinator = MockPlaybackCoordinator({
            "is_playing": True,
            "current_track": {"title": "New Track"}
        })
        service = TrackProgressService(state_manager, coordinator)

        await service._broadcast_player_state_after_auto_advance()

        # Should broadcast state change with new status
        state_manager.broadcast_state_change.assert_called_once()
        call_args = state_manager.broadcast_state_change.call_args
        assert call_args[1]["immediate"] is True

    @pytest.mark.asyncio
    async def test_broadcast_player_state_no_status(self):
        """Test broadcasting when no status available."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()

        coordinator = MockPlaybackCoordinator()
        coordinator.get_playback_status = Mock(return_value=None)

        service = TrackProgressService(state_manager, coordinator)

        await service._broadcast_player_state_after_auto_advance()

        # Should not broadcast when no status
        state_manager.broadcast_state_change.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcast_player_state_async_controller(self):
        """Test broadcasting with async audio controller."""
        state_manager = Mock(spec=StateManager)
        state_manager.broadcast_state_change = AsyncMock()

        controller = MockAsyncAudioController({
            "is_playing": True,
            "current_track": {"title": "Async Track"}
        })
        service = TrackProgressService(state_manager, controller)

        await service._broadcast_player_state_after_auto_advance()

        # Should call async get_playback_status
        controller.get_playback_status.assert_called_once()
        state_manager.broadcast_state_change.assert_called_once()
