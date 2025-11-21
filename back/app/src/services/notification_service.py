# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Notification service for Socket.IO event broadcasting.

Provides notification classes for download progress events, playback status
updates, and track progress monitoring. Includes singleton pattern implementation
for centralized event management and Socket.IO integration.
"""

from typing import Any, Dict
import logging

from app.src.services.error.unified_error_decorator import handle_service_errors

logger = logging.getLogger(__name__)


class DownloadNotifier:
    """Notifier for download progress events via Socket.IO."""

    def __init__(self, socketio, download_id: str):
        self.socketio = socketio
        self.download_id = download_id

    @handle_service_errors("notification")
    async def notify(self, status: str, **data):
        """Emit canonical YouTube download events.

        Events: `youtube:progress` during lifecycle, `youtube:complete` on success,
        `youtube:error` on failure. Always includes `task_id`.
        """
        canonical = {"task_id": self.download_id, "status": status, **data}
        if not self.socketio:
            return
        if status.lower() in ("pending", "downloading", "processing", "saving_playlist"):
            await self.socketio.emit("youtube:progress", canonical)
        elif status.lower() == "complete":
            # Emit complete event with playlist info when available
            await self.socketio.emit("youtube:complete", canonical)
        elif status.lower() == "error":
            message = data.get("message") or data.get("error") or "Download error"
            await self.socketio.emit(
                "youtube:error", {"task_id": self.download_id, "message": message}
            )
        else:
            # Default to progress for unrecognized statuses
            await self.socketio.emit("youtube:progress", canonical)


class PlaybackEvent:
    """Event representing playback status or progress."""

    def __init__(self, event_type: str, data: Dict[str, Any]):
        self.event_type = event_type
        self.data = data


class PlaybackSubject:
    """Subject for broadcasting playback events to Socket.IO clients.

    Implements a singleton pattern for managing playback status and progress events.
    """

    # Global static instance for direct reference
    _instance = None
    _socketio = None

    @classmethod
    def set_socketio(cls, socketio):
        """Set the global Socket.IO instance for event emission."""
        cls._socketio = socketio

    @classmethod
    def get_instance(cls):
        """Return the singleton instance of PlaybackSubject."""
        if cls._instance is None:
            cls._instance = PlaybackSubject()
        return cls._instance

    def __init__(self):
        """Initialize the PlaybackSubject singleton instance."""
        self._last_status_event = None
        self._last_progress_event = None
        self._last_progress_emit_time = 0  # Used to throttle progress event emission frequency
        if PlaybackSubject._instance is not None and PlaybackSubject._instance is not self:
            raise RuntimeError(
                "PlaybackSubject singleton instance already exists. Use get_instance()."
            )
        if PlaybackSubject._instance is None:
            PlaybackSubject._instance = self

    @handle_service_errors("notification")
    def notify_playback_status(
        self, status: str, playlist_info: Dict = None, track_info: Dict = None
    ):
        """Store playback status event for internal use only.

        Socket.IO emission now handled exclusively by StateManager.

        Args:
            status: Playback status ('playing', 'paused', 'stopped').
            playlist_info: Information about the current playlist.
            track_info: Information about the current track.
        """
        event_data = {
            "status": status,
            "playlist": playlist_info,
            "current_track": track_info,
        }
        event = PlaybackEvent("status", event_data)
        self._last_status_event = event
        # Socket.IO emission removed - StateManager handles all real-time events
        logger.debug(f"Playback status stored internally: {status}")

    @handle_service_errors("notification")
    def notify_track_progress(
        self,
        elapsed: float,
        total: float,
        track_number: int,
        track_info: dict = None,
        playlist_info: dict = None,
        is_playing: bool = True,
    ):
        """Store track progress event for internal use only.

        Socket.IO emission now handled exclusively by StateManager.

        Args:
            elapsed: Elapsed time in seconds.
            total: Total duration in seconds.
            track_number: Track number in playlist.
            track_info: Dictionary with track metadata.
            playlist_info: Dictionary with playlist metadata (optional).
            is_playing: True if playback is active.
        """
        event_data = {
            "track": track_info,
            "playlist": playlist_info,
            "current_time": elapsed,
            "duration": total,
            "is_playing": is_playing,
        }
        event = PlaybackEvent("progress", event_data)
        self._last_progress_event = event
        # Socket.IO emission removed - StateManager handles all real-time events
        logger.debug(f"Track progress stored internally: {elapsed:.1f}s/{total:.1f}s")

    def get_last_status_event(self):
        """Return the last emitted playback status event."""
        return self._last_status_event

    def get_last_progress_event(self):
        """Return the last emitted track progress event."""
        return self._last_progress_event

    # Socket.IO emission method removed - StateManager handles all real-time events
