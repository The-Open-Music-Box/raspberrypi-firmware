# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Base Audio Backend Implementation.

This module provides a base class for audio backends that implements common functionality
and provides a foundation for all audio backend implementations.
"""

import threading
import time
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from app.src.monitoring import get_logger
from app.src.domain.protocols.notification_protocol import PlaybackNotifierProtocol as PlaybackSubject

# Resource manager functionality will be added later if needed

from app.src.domain.protocols.audio_backend_protocol import AudioBackendProtocol
from app.src.domain.decorators.error_handler import handle_domain_errors as handle_errors

logger = get_logger(__name__)


class BaseAudioBackend(AudioBackendProtocol):
    """Base class for all audio backends.

    This class provides common functionality and state management that is shared
    across all audio backend implementations.
    """

    def __init__(self, playback_subject: Optional[PlaybackSubject] = None):
        """Initialize the base audio backend."""
        self._playback_subject = playback_subject
        self._state_lock = threading.RLock()
        self._is_playing = False
        self._current_file_path: Optional[str] = None
        self._volume = 70  # Default volume
        self._backend_name = self.__class__.__name__

    @handle_errors("_validate_file_path")
    def _validate_file_path(self, file_path: str) -> Optional[Path]:
        """Validate that the file path exists and is accessible.

        Args:
            file_path: Path to the audio file

        Returns:
            Path: Valid Path object if file exists, None otherwise
        """
        path = Path(file_path)
        if not path.exists():
            logger.error(f"{self._backend_name}: Audio file not found: {path}")
            return None
        if not path.is_file():
            logger.error(f"{self._backend_name}: Path is not a file: {path}")
            return None
        return path

    def _clamp_volume(self, volume: int) -> int:
        """Clamp volume to valid range (0-100).

        Args:
            volume: Volume level to clamp

        Returns:
            int: Clamped volume level
        """
        return max(0, min(100, volume))

    @handle_errors("_notify_playback_event")
    def _notify_playback_event(self, event: str, data: Optional[dict] = None) -> None:
        """Notify playback events through the subject.

        Args:
            event: Event name
            data: Optional event data
        """
        if self._playback_subject:
            event_data = {"event": event, "backend": self._backend_name}
            if data:
                event_data.update(data)
            self._playback_subject.notify(event_data)

    @handle_errors("_safe_operation")
    def _safe_operation(self, operation_name: str, operation_func, *args, **kwargs):
        """Safely execute an operation with error handling.

        Args:
            operation_name: Name of the operation for logging
            operation_func: Function to execute
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the operation, or None if failed
        """
        return operation_func(*args, **kwargs)

    def get_position(self) -> float:
        """Get current playback position in seconds.

        Base implementation returns 0.0. Override in subclasses for position tracking.

        Returns:
            float: Current position in seconds, 0.0 by default
        """
        return 0.0

    @handle_errors("set_volume")
    def set_volume(self, volume: int) -> bool:
        """Set playback volume.

        Base implementation just stores the volume. Override in subclasses for actual control.

        Args:
            volume: Volume level (0-100)

        Returns:
            bool: True if volume was set successfully
        """
        with self._state_lock:
            self._volume = self._clamp_volume(volume)
        logger.debug(f"{self._backend_name}: Volume set to {self._volume}%")
        return True

    @handle_errors("cleanup")
    def cleanup(self) -> None:
        """Clean up audio resources.

        Base implementation resets state. Override in subclasses for resource cleanup.
        """
        logger.info(f"🧹 Cleaning up {self._backend_name}")
        with self._state_lock:
            self._is_playing = False
            self._current_file_path = None
        logger.info(f"✅ {self._backend_name} cleanup completed")

    @contextmanager
    def _acquire_audio_resource(self, resource_type: str):
        """Acquire audio resource with automatic cleanup and proper resource management.

        Args:
            resource_type: Type of resource to acquire

        Yields:
            Resource instance
        """
        # Implement proper resource management with tracking and cleanup
        resource_id = f"{resource_type}_{id(self)}"
        logger.debug(f"🔒 Acquiring audio resource: {resource_id}")

        resource = self._create_audio_resource(resource_type)

        # Track resource usage for monitoring
        start_time = time.time()

        try:
            yield resource
        except Exception as e:
            logger.error(f"❌ Error using audio resource {resource_id}: {e}")
            raise
        finally:
            # Clean up and log resource usage
            usage_time = time.time() - start_time
            logger.debug(f"🔓 Releasing audio resource: {resource_id} (used {usage_time:.2f}s)")
            self._cleanup_audio_resource(resource_type, resource)

    def _create_audio_resource(self, resource_type: str):
        """Create an audio resource of the specified type.

        Override in subclasses to provide specific resource creation logic.

        Args:
            resource_type: Type of resource to create

        Returns:
            Created resource or None if failed
        """
        logger.debug(f"{self._backend_name}: Creating {resource_type} resource")
        return f"mock_{resource_type}_resource"

    def _cleanup_audio_resource(self, resource_type: str, resource):
        """Cleanup an audio resource.

        Override in subclasses to provide specific cleanup logic.

        Args:
            resource_type: Type of resource being cleaned up
            resource: Resource instance to cleanup
        """
        logger.debug(f"{self._backend_name}: Cleaning up {resource_type} resource")
        # Base implementation does nothing
        pass

    # Abstract methods that must be implemented by subclasses
    def play_file(self, file_path: str) -> bool:
        """Play a single audio file.

        Must be implemented by subclasses.

        Args:
            file_path: Path to the audio file to play

        Returns:
            bool: True if playback started successfully, False otherwise
        """
        raise NotImplementedError(f"{self._backend_name} must implement play_file()")

    def stop(self) -> bool:
        """Stop playback.

        Must be implemented by subclasses.

        Returns:
            bool: True if stopped successfully, False otherwise
        """
        raise NotImplementedError(f"{self._backend_name} must implement stop()")

    def pause(self) -> bool:
        """Pause playback.

        Must be implemented by subclasses.

        Returns:
            bool: True if paused successfully, False otherwise
        """
        raise NotImplementedError(f"{self._backend_name} must implement pause()")

    def resume(self) -> bool:
        """Resume paused playback.

        Must be implemented by subclasses.

        Returns:
            bool: True if resumed successfully, False otherwise
        """
        raise NotImplementedError(f"{self._backend_name} must implement resume()")

    @property
    def is_playing(self) -> bool:
        """Check if audio is currently playing.

        Must be implemented by subclasses.

        Returns:
            bool: True if playing, False otherwise
        """
        raise NotImplementedError(f"{self._backend_name} must implement is_playing property")

    @property
    def is_busy(self) -> bool:
        """Check if the backend is busy.

        Must be implemented by subclasses.

        Returns:
            bool: True if backend is busy, False if idle/finished
        """
        raise NotImplementedError(f"{self._backend_name} must implement is_busy property")
