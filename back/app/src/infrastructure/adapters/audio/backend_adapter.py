# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Backend adapter to use existing audio backends with new protocols."""

from typing import Optional, Any

from app.src.monitoring import get_logger
from app.src.domain.decorators.error_handler import handle_domain_errors as handle_errors
from app.src.domain.protocols.audio_backend_protocol import AudioBackendProtocol

logger = get_logger(__name__)


class BackendAdapter(AudioBackendProtocol):
    """Adapter to make existing backends compatible with new protocol."""

    def __init__(self, backend: Any):
        """Initialize adapter with existing backend.

        Args:
            backend: Existing backend implementation
        """
        self._backend = backend
        logger.info(f"BackendAdapter wrapping {type(backend).__name__}")

    # AudioBackendProtocol async methods
    @handle_errors("play")
    async def play(self, file_path: str) -> bool:
        """Play an audio file (async interface)."""
        return self.play_file(file_path)

    @handle_errors("pause")
    async def pause(self) -> bool:
        """Pause current playback (async interface)."""
        return self.pause_playback()

    @handle_errors("resume")
    async def resume(self) -> bool:
        """Resume paused playback (async interface)."""
        return self.resume_playback()

    @handle_errors("stop")
    async def stop(self) -> bool:
        """Stop current playback (async interface)."""
        return self.stop_playback()

    @handle_errors("set_volume")
    async def set_volume(self, volume: int) -> bool:
        """Set playback volume (async interface)."""
        return self.set_volume_sync(volume)

    @handle_errors("get_volume")
    async def get_volume(self) -> int:
        """Get current volume level (async interface)."""
        return self.get_volume_sync()

    @handle_errors("seek")
    async def seek(self, position_ms: int) -> bool:
        """Seek to a specific position (async interface)."""
        return self.seek_to_position(position_ms)

    @handle_errors("get_position")
    async def get_position(self) -> Optional[int]:
        """Get current playback position (async interface)."""
        return self.get_position_sync()

    @handle_errors("get_duration")
    async def get_duration(self) -> Optional[int]:
        """Get duration of current track (async interface)."""
        return self.get_duration_sync()

    @property
    @handle_errors("is_playing")
    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        if hasattr(self._backend, "is_playing"):
            attr = getattr(self._backend, "is_playing")
            return attr() if callable(attr) else bool(attr)
        return False

    @property
    @handle_errors("is_paused")
    def is_paused(self) -> bool:
        """Check if audio is currently paused."""
        if hasattr(self._backend, "is_paused"):
            attr = getattr(self._backend, "is_paused")
            return attr() if callable(attr) else bool(attr)
        return False

    @property
    @handle_errors("is_busy")
    def is_busy(self) -> bool:
        """Check if backend is busy processing."""
        if hasattr(self._backend, "is_busy"):
            attr = getattr(self._backend, "is_busy")
            return attr() if callable(attr) else bool(attr)
        # Fallback: consider busy if playing
        return self.is_playing

    @handle_errors("play_file")
    def play_file(self, file_path: str) -> bool:
        """Play an audio file."""
        if hasattr(self._backend, "play_file"):
            result = self._backend.play_file(file_path)
            return bool(result) if result is not None else True
        elif hasattr(self._backend, "play"):
            self._backend.play(file_path)
            return True
        else:
            logger.error("Backend does not support play_file")
            return False

    @handle_errors("pause_playback")
    def pause_playback(self) -> bool:
        """Pause current playback."""
        if hasattr(self._backend, "pause"):
            result = self._backend.pause()
            return bool(result) if result is not None else True
        else:
            logger.warning("Backend does not support pause")
            return False

    @handle_errors("resume_playback")
    def resume_playback(self) -> bool:
        """Resume paused playback."""
        if hasattr(self._backend, "resume"):
            result = self._backend.resume()
            return bool(result) if result is not None else True
        else:
            logger.warning("Backend does not support resume")
            return False

    @handle_errors("stop_playback")
    def stop_playback(self) -> bool:
        """Stop current playback."""
        if hasattr(self._backend, "stop"):
            result = self._backend.stop()
            return bool(result) if result is not None else True
        else:
            logger.warning("Backend does not support stop")
            return False

    @handle_errors("set_volume_sync")
    def set_volume_sync(self, volume: int) -> bool:
        """Set playback volume."""
        if hasattr(self._backend, "set_volume"):
            result = self._backend.set_volume(volume)
            return bool(result) if result is not None else True
        else:
            logger.warning("Backend does not support set_volume")
            return False

    @handle_errors("get_volume_sync")
    def get_volume_sync(self) -> int:
        """Get current volume level."""
        if hasattr(self._backend, "get_volume"):
            volume = self._backend.get_volume()
            return int(volume) if volume is not None else 50
        else:
            return 50  # Default volume

    @handle_errors("get_position_sync")
    def get_position_sync(self) -> Optional[int]:
        """Get current playback position in milliseconds."""
        if hasattr(self._backend, "get_position"):
            position = self._backend.get_position()
            if position is not None:
                # Convert to milliseconds if needed
                pos_ms = int(position * 1000) if isinstance(position, float) else int(position)
                return pos_ms
        return None

    @handle_errors("seek_to_position")
    def seek_to_position(self, position_ms: int) -> bool:
        """Set playback position (seek)."""
        if hasattr(self._backend, "set_position"):
            # Convert ms to seconds
            position_seconds = position_ms / 1000.0
            result = self._backend.set_position(position_seconds)
            return bool(result) if result is not None else True
        else:
            logger.warning("Backend does not support set_position")
            return False

    @handle_errors("get_duration_sync")
    def get_duration_sync(self) -> Optional[int]:
        """Get duration of current track in milliseconds."""
        if hasattr(self._backend, "get_duration"):
            duration = self._backend.get_duration()
            if duration is not None:
                # Convert to milliseconds if needed
                duration_ms = int(duration * 1000) if isinstance(duration, float) else int(duration)
                return duration_ms
        return None

    @handle_errors("get_duration")
    def get_duration(self) -> Optional[float]:
        """Get duration of current track in seconds."""
        if hasattr(self._backend, "get_duration"):
            duration = self._backend.get_duration()
            return float(duration) if duration is not None else None
        else:
            return None

    def cleanup(self) -> None:
        """Clean up backend resources."""
        try:
            if hasattr(self._backend, "cleanup"):
                self._backend.cleanup()
            logger.debug("Backend cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
