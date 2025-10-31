# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Button Action Definitions (Domain Layer).

Defines actions that can be triggered by physical buttons.
Each action encapsulates a specific operation on the PlaybackCoordinator.

This follows the Command Pattern:
- ButtonAction = Command interface
- Concrete actions = Command implementations
- PlaybackCoordinator = Receiver
- ButtonActionDispatcher = Invoker
"""

from abc import ABC, abstractmethod
from typing import Optional
import logging

from app.src.domain.protocols.playback_coordinator_protocol import PlaybackCoordinatorProtocol

logger = logging.getLogger(__name__)


class ButtonAction(ABC):
    """
    Abstract base class for button actions.

    Each action represents a specific operation that can be
    triggered by a physical button press.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the action name for identification and logging."""
        pass

    @abstractmethod
    async def execute(self, coordinator: PlaybackCoordinatorProtocol) -> bool:
        """
        Execute the action.

        Args:
            coordinator: PlaybackCoordinator to perform the action on

        Returns:
            True if action executed successfully, False otherwise
        """
        pass

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"


class PlayAction(ButtonAction):
    """Start or resume playback."""

    @property
    def name(self) -> str:
        return "play"

    async def execute(self, coordinator: PlaybackCoordinatorProtocol) -> bool:
        logger.info(f"▶️  [ACTION:play] Starting playback")
        result = coordinator.play()
        logger.debug(f"[ACTION:play] Coordinator.play() returned: {result}")
        return result


class PauseAction(ButtonAction):
    """Pause current playback."""

    @property
    def name(self) -> str:
        return "pause"

    async def execute(self, coordinator: PlaybackCoordinatorProtocol) -> bool:
        logger.info(f"⏸️  [ACTION:pause] Pausing playback")
        result = coordinator.pause()
        logger.debug(f"[ACTION:pause] Coordinator.pause() returned: {result}")
        return result


class PlayPauseAction(ButtonAction):
    """Toggle between play and pause."""

    @property
    def name(self) -> str:
        return "play_pause"

    async def execute(self, coordinator: PlaybackCoordinatorProtocol) -> bool:
        logger.info(f"⏯️  [ACTION:play_pause] Toggling play/pause")
        result = coordinator.toggle_pause()
        logger.debug(f"[ACTION:play_pause] Coordinator.toggle_pause() returned: {result}")
        return result


class StopAction(ButtonAction):
    """Stop current playback."""

    @property
    def name(self) -> str:
        return "stop"

    async def execute(self, coordinator: PlaybackCoordinatorProtocol) -> bool:
        logger.info(f"⏹️  [ACTION:stop] Stopping playback")
        result = coordinator.stop()
        logger.debug(f"[ACTION:stop] Coordinator.stop() returned: {result}")
        return result


class NextTrackAction(ButtonAction):
    """Skip to next track in playlist."""

    @property
    def name(self) -> str:
        return "next_track"

    async def execute(self, coordinator: PlaybackCoordinatorProtocol) -> bool:
        logger.info(f"⏭️  [ACTION:next_track] Skipping to next track")
        result = coordinator.next_track()
        logger.debug(f"[ACTION:next_track] Coordinator.next_track() returned: {result}")
        return result


class PreviousTrackAction(ButtonAction):
    """Go to previous track in playlist."""

    @property
    def name(self) -> str:
        return "previous_track"

    async def execute(self, coordinator: PlaybackCoordinatorProtocol) -> bool:
        logger.info(f"⏮️  [ACTION:previous_track] Going to previous track")
        result = coordinator.previous_track()
        logger.debug(f"[ACTION:previous_track] Coordinator.previous_track() returned: {result}")
        return result


class VolumeUpAction(ButtonAction):
    """Increase volume by a fixed step."""

    VOLUME_STEP = 5  # Volume change in percentage

    @property
    def name(self) -> str:
        return "volume_up"

    async def execute(self, coordinator: PlaybackCoordinatorProtocol) -> bool:
        logger.info(f"🔊 [ACTION:volume_up] Increasing volume")
        current_volume = coordinator.get_volume()
        logger.debug(f"[ACTION:volume_up] Current volume: {current_volume}%")
        new_volume = min(100, current_volume + self.VOLUME_STEP)
        logger.debug(f"[ACTION:volume_up] Target volume: {new_volume}%")

        if new_volume != current_volume:
            success = await coordinator.set_volume(new_volume)
            if success:
                logger.info(f"✅ [ACTION:volume_up] Volume increased: {current_volume}% → {new_volume}%")
            else:
                logger.warning(f"⚠️  [ACTION:volume_up] Failed to set volume to {new_volume}%")
            return success
        else:
            logger.info(f"ℹ️  [ACTION:volume_up] Volume already at maximum (100%)")
            return True  # Not an error, just at limit


class VolumeDownAction(ButtonAction):
    """Decrease volume by a fixed step."""

    VOLUME_STEP = 5  # Volume change in percentage

    @property
    def name(self) -> str:
        return "volume_down"

    async def execute(self, coordinator: PlaybackCoordinatorProtocol) -> bool:
        logger.info(f"🔉 [ACTION:volume_down] Decreasing volume")
        current_volume = coordinator.get_volume()
        logger.debug(f"[ACTION:volume_down] Current volume: {current_volume}%")
        new_volume = max(0, current_volume - self.VOLUME_STEP)
        logger.debug(f"[ACTION:volume_down] Target volume: {new_volume}%")

        if new_volume != current_volume:
            success = await coordinator.set_volume(new_volume)
            if success:
                logger.info(f"✅ [ACTION:volume_down] Volume decreased: {current_volume}% → {new_volume}%")
            else:
                logger.warning(f"⚠️  [ACTION:volume_down] Failed to set volume to {new_volume}%")
            return success
        else:
            logger.info(f"ℹ️  [ACTION:volume_down] Volume already at minimum (0%)")
            return True  # Not an error, just at limit


class PrintDebugAction(ButtonAction):
    """Print debug information about current playback state."""

    @property
    def name(self) -> str:
        return "print_debug"

    async def execute(self, coordinator: PlaybackCoordinatorProtocol) -> bool:
        logger.info(f"🎮 Executing action: {self.name}")

        try:
            # Get complete playback status
            status = coordinator.get_playback_status()

            # Format debug output
            debug_lines = [
                "=" * 60,
                "🐛 DEBUG: Playback State",
                "=" * 60,
                f"Playing: {status.get('is_playing', False)}",
                f"Paused: {status.get('is_paused', False)}",
                f"Volume: {status.get('volume', 0)}%",
                f"Position: {status.get('position_ms', 0)}ms / {status.get('duration_ms', 0)}ms",
                "",
                f"Playlist: {status.get('active_playlist_title', 'None')}",
                f"Track: {status.get('track_index', 0)}/{status.get('track_count', 0)}",
                f"Current Track: {status.get('active_track', {}).get('title', 'None')}",
                "",
                f"Repeat: {status.get('repeat_mode', 'none')}",
                f"Shuffle: {status.get('shuffle_enabled', False)}",
                f"Auto-advance: {status.get('auto_advance_enabled', True)}",
                "=" * 60,
            ]

            # Log each line
            for line in debug_lines:
                logger.info(line)

            return True

        except Exception as e:
            logger.error(f"❌ Error printing debug info: {e}")
            return False
