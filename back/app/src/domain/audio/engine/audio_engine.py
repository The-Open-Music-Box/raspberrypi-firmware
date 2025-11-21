# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Unified audio engine implementation."""

import time
from typing import Dict, Any, Optional

from app.src.monitoring import get_logger
from app.src.domain.decorators.error_handler import handle_domain_errors as handle_errors
from app.src.domain.data.models.playlist import Playlist

from app.src.domain.protocols.audio_backend_protocol import AudioBackendProtocol
from app.src.domain.protocols.audio_engine_protocol import AudioEngineProtocol
from app.src.domain.protocols.event_bus_protocol import EventBusProtocol
from app.src.domain.protocols.state_manager_protocol import StateManagerProtocol, PlaybackState
# PlaylistManagerProtocol removed - use data domain services

from ..events.audio_events import (
    TrackStartedEvent,
    PlaylistLoadedEvent,
    PlaybackStateChangedEvent,
    VolumeChangedEvent,
    ErrorEvent,
)

logger = get_logger(__name__)


class AudioEngine(AudioEngineProtocol):
    """Unified audio engine coordinating all audio operations."""

    def __init__(
        self,
        backend: AudioBackendProtocol,
        event_bus: EventBusProtocol,
        state_manager: StateManagerProtocol,
    ):
        """Initialize the audio engine.

        Args:
            backend: Audio backend implementation
            event_bus: Event bus for notifications
            state_manager: State management
        """
        self._backend = backend
        self._event_bus = event_bus
        self._state_manager = state_manager
        self._is_running = False
        self._startup_time: Optional[float] = None
        self._playlist_manager = None  # Initialize as None for safe operations
        self._is_stopping = False  # Flag to prevent recursive shutdown

        # Validate state manager has required methods
        if not hasattr(state_manager, "set_state"):
            logger.error(f"❌ Invalid StateManager type: {type(state_manager).__name__} lacks set_state method",
            )
            raise ValueError(
                f"StateManager must have set_state method, got {type(state_manager).__name__}"
            )

        # Subscribe to state changes for event generation
        self._setup_event_subscriptions()

        logger.info(f"AudioEngine initialized with {type(backend).__name__} and {type(state_manager).__name__}",
        )

    def _has_playlist_manager(self) -> bool:
        """Check if playlist manager is available and has current playlist."""
        return (
            hasattr(self, '_playlist_manager')
            and self._playlist_manager is not None
            and hasattr(self._playlist_manager, 'current_playlist')
            and self._playlist_manager.current_playlist is not None
        )

    @handle_errors("_safe_set_state")
    def _safe_set_state(self, state: PlaybackState) -> None:
        """Safely set state with validation."""
        if hasattr(self._state_manager, "set_state"):
            self._state_manager.set_state(state)
        else:
            logger.error(f"❌ StateManager {type(self._state_manager).__name__} lacks set_state method",
            )

    @handle_errors("_safe_get_current_state")
    def _safe_get_current_state(self) -> PlaybackState:
        """Safely get current state with fallback."""
        if hasattr(self._state_manager, "get_current_state"):
            return self._state_manager.get_current_state()
        else:
            logger.warning(f"⚠️ StateManager {type(self._state_manager).__name__} lacks get_current_state method",
            )
            return PlaybackState.STOPPED  # Safe fallback

    def _setup_event_subscriptions(self) -> None:
        """Set up internal event subscriptions."""
        # We'll add event handlers here as needed
        pass

    # MARK: - AudioEngineProtocol Implementation

    @handle_errors("play_track_by_path")
    async def play_track_by_path(self, file_path: str, track_id: Optional[str] = None) -> bool:
        """Play a track by file path."""
        try:
            success = await self._backend.play(file_path)
            if success:
                # Fire event
                await self._event_bus.publish(
                    TrackStartedEvent("AudioEngine", file_path)
                )
            return success
        except Exception as e:
            await self._event_bus.publish(
                ErrorEvent("AudioEngine", f"Failed to play track: {e}")
            )
            return False

    @handle_errors("get_playback_state")
    def get_playback_state(self) -> Dict[str, Any]:
        """Get current playback state."""
        return {
            "is_playing": self._backend.is_playing() if hasattr(self._backend, 'is_playing') else False,
            "volume": 50,  # Default volume
            "backend_type": type(self._backend).__name__
        }

    @handle_errors("seek_to_position")
    async def seek_to_position(self, position_ms: int) -> bool:
        """Seek to a specific position."""
        try:
            return await self._backend.seek(position_ms)
        except Exception as e:
            await self._event_bus.publish(
                ErrorEvent("AudioEngine", f"Failed to seek: {e}")
            )
            return False

    @handle_errors("start")
    async def start(self) -> None:
        """Start the audio engine."""
        if self._is_running:
            return

        self._safe_set_state(PlaybackState.LOADING)
        self._is_running = True
        self._startup_time = time.time()
        self._safe_set_state(PlaybackState.STOPPED)
        logger.info("🎛️ AudioEngine started successfully")

    @handle_errors("stop")
    async def stop(self) -> None:
        """Stop the audio engine."""
        if not self._is_running or self._is_stopping:
            return

        self._is_stopping = True
        try:
            # Stop any current playback
            await self.stop_playback()
            # Cleanup backend
            if hasattr(self._backend, 'cleanup'):
                self._backend.cleanup()
            self._is_running = False
            self._safe_set_state(PlaybackState.STOPPED)
            logger.info("🎛️ AudioEngine stopped")
        except Exception as e:
            logger.error(f"Error during audio engine stop: {e}")
            # Don't re-raise during shutdown to prevent recursion
        finally:
            self._is_stopping = False

    @property
    def is_running(self) -> bool:
        """Check if engine is running."""
        return self._is_running

    @property
    def event_bus(self) -> EventBusProtocol:
        """Get the event bus instance."""
        return self._event_bus

    @property
    def state_manager(self) -> StateManagerProtocol:
        """Get the state manager instance."""
        return self._state_manager

    # === Playlist Operations ===

    async def load_playlist(self, playlist: Playlist) -> bool:
        """Load a playlist for playback."""
        if not self._is_running:
            logger.error("Engine not running")
            return False

        try:
            # Since we don't have a playlist manager, just validate the playlist
            success = playlist and len(playlist.tracks) > 0

            if success:
                # Update state
                self._state_manager.update_playlist_info(
                    {
                        "playlist_id": getattr(playlist, "id", None),
                        "title": playlist.title,
                        "track_count": len(playlist.tracks),
                    }
                )

                # Fire event
                await self._event_bus.publish(
                    PlaylistLoadedEvent(
                        "AudioEngine",
                        playlist_id=getattr(playlist, "id", None),
                        playlist_title=playlist.title,
                        track_count=len(playlist.tracks),
                    )
                )

            return success

        except Exception as e:
            await self._event_bus.publish(
                ErrorEvent("AudioEngine", f"Failed to load playlist: {e}")
            )
            return False

    async def play_playlist(self, playlist: Playlist) -> bool:
        """Load and start playing a playlist."""
        if not playlist or not playlist.tracks:
            logger.error("No playlist or empty playlist")
            return False

        for idx, track in enumerate(playlist.tracks):
            if track and hasattr(track, 'file_path') and track.file_path:
                logger.info(f"Playing track {idx} from playlist: {track.file_path}")
                success = await self.play_file(track.file_path)
                if success:
                    # Update playlist info in state manager
                    self._state_manager.update_playlist_info({
                        "playlist_title": getattr(playlist, 'name', 'Unknown'),
                        "track_count": len(playlist.tracks),
                        "current_track_index": idx
                    })
                    return True

        logger.error("No valid tracks found in playlist")
        return False

    @handle_errors("set_playlist")
    def set_playlist(self, playlist: Playlist) -> bool:
        """Legacy compatibility method for PlaylistService.

        This method provides backwards compatibility for legacy code that expects
        a synchronous set_playlist method.

        Args:
            playlist: Playlist to load and play

        Returns:
            bool: True if playlist was loaded and started successfully
        """
        import asyncio

        # Check if we're in an async context
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, create a task
            logger.info(f"✅ In async context, creating task to play playlist: {playlist.name}")
            task = loop.create_task(self.play_playlist(playlist))
            # For legacy compatibility, we return immediately
            # The actual result will be handled asynchronously
            logger.info(f"✅ AudioEngine.set_playlist called for playlist: {playlist.name}"
            )
            return True
        except RuntimeError:
            # Not in an async context, handle synchronously
            logger.warning("AudioEngine.set_playlist called outside async context")

            # For test compatibility, attempt synchronous playback directly
            if not self._is_running:
                logger.error("AudioEngine not running")
                return False

            if not playlist:
                logger.error("No playlist provided")
                return False

            if not playlist.tracks:
                logger.error(f"Playlist '{getattr(playlist, 'name', 'unknown')}' has no tracks")
                return False

            logger.info(f"Playlist has {len(playlist.tracks)} tracks")

            # Get first valid track
            for idx, track in enumerate(playlist.tracks):
                logger.debug(f"Checking track {idx}: {track}")
                if track and hasattr(track, 'file_path') and track.file_path:
                    logger.info(f"Playing track {idx}: {track.file_path}")
                    try:
                        # Direct backend playback
                        success = self._backend.play_file(track.file_path)
                        logger.info(f"Backend play_file returned: {success}")
                        if success:
                            self._safe_set_state(PlaybackState.PLAYING)
                            # Update state manager with playlist and track info for test compatibility
                            playlist_info = {
                                "playlist_title": playlist.name,
                                "track_count": len(playlist.tracks),
                                "current_track_index": 0
                            }
                            self._state_manager.update_playlist_info(playlist_info)

                            track_info = {
                                "file_path": track.file_path,
                                "title": track.title,
                                "artist": getattr(track, 'artist', ''),
                                "album": getattr(track, 'album', ''),
                                "duration_ms": getattr(track, 'duration_ms', 0)
                            }
                            self._state_manager.update_track_info(track_info)
                            return True
                    except Exception as e:
                        logger.error(f"Failed to play track: {e}")
                        continue

            return False

    async def next_track(self) -> bool:
        """Advance to next track.

        Note: This method is not implemented at the AudioEngine level because
        playlist navigation is the responsibility of the PlaybackCoordinator
        in the application layer. The AudioEngine (domain layer) only handles
        audio playback of individual files.

        For playlist navigation, use PlaybackCoordinator.next_track() instead.

        Returns:
            bool: Always False - playlist navigation not supported at this level
        """
        if not self._is_running:
            return False

        logger.debug(
            "next_track() called on AudioEngine - "
            "playlist navigation should use PlaybackCoordinator"
        )
        return False

    async def previous_track(self) -> bool:
        """Go to previous track.

        Note: This method is not implemented at the AudioEngine level because
        playlist navigation is the responsibility of the PlaybackCoordinator
        in the application layer. The AudioEngine (domain layer) only handles
        audio playback of individual files.

        For playlist navigation, use PlaybackCoordinator.previous_track() instead.

        Returns:
            bool: Always False - playlist navigation not supported at this level
        """
        if not self._is_running:
            return False

        logger.debug(
            "previous_track() called on AudioEngine - "
            "playlist navigation should use PlaybackCoordinator"
        )
        return False

    async def play_track_by_index(self, index: int) -> bool:
        """Play track by index.

        Note: This method is not implemented at the AudioEngine level because
        playlist navigation is the responsibility of the PlaybackCoordinator
        in the application layer. The AudioEngine (domain layer) only handles
        audio playback of individual files.

        For playlist navigation, use PlaybackCoordinator.goto_track() instead.

        Args:
            index: Track index (not used at this level)

        Returns:
            bool: Always False - playlist navigation not supported at this level
        """
        if not self._is_running:
            return False

        logger.debug(
            f"play_track_by_index({index}) called on AudioEngine - "
            "playlist navigation should use PlaybackCoordinator"
        )
        return False

    # === Direct Playback Operations ===

    async def play_file(self, file_path: str) -> bool:
        """Play a single audio file."""
        logger.info(f"AudioEngine.play_file called with: {file_path}")

        if not self._is_running:
            logger.error("AudioEngine not running")
            return False

        try:
            logger.debug(f"Getting current state...")
            old_state = self._safe_get_current_state()
            logger.debug(f"Current state: {old_state}")

            logger.info(f"Calling backend.play_file({file_path})")
            success = self._backend.play_file(file_path)
            logger.info(f"Backend play_file returned: {success}")

            if success:
                self._safe_set_state(PlaybackState.PLAYING)
                self._state_manager.update_track_info(
                    {
                        "file_path": file_path,
                        "title": file_path.split("/")[-1],  # Basic title from filename
                    }
                )

                # Fire events
                await self._event_bus.publish(
                    PlaybackStateChangedEvent("AudioEngine", old_state, PlaybackState.PLAYING)
                )
                await self._event_bus.publish(TrackStartedEvent("AudioEngine", file_path))

            return success

        except Exception as e:
            await self._event_bus.publish(ErrorEvent("AudioEngine", f"Failed to play file: {e}"))
            return False

    async def pause_playback(self) -> bool:
        """Pause current playback."""
        if not self._is_running:
            return False

        try:
            old_state = self._safe_get_current_state()

            # Use direct backend since we don't have playlist manager
            success = self._backend.pause()

            if success:
                self._safe_set_state(PlaybackState.PAUSED)
                await self._event_bus.publish(
                    PlaybackStateChangedEvent("AudioEngine", old_state, PlaybackState.PAUSED)
                )

            return success

        except Exception as e:
            await self._event_bus.publish(ErrorEvent("AudioEngine", f"Failed to pause: {e}"))
            return False

    async def resume_playback(self) -> bool:
        """Resume paused playback."""
        if not self._is_running:
            return False

        try:
            old_state = self._safe_get_current_state()

            # Use direct backend since we don't have playlist manager
            success = self._backend.resume()

            if success:
                self._safe_set_state(PlaybackState.PLAYING)
                await self._event_bus.publish(
                    PlaybackStateChangedEvent("AudioEngine", old_state, PlaybackState.PLAYING)
                )

            return success

        except Exception as e:
            await self._event_bus.publish(ErrorEvent("AudioEngine", f"Failed to resume: {e}"))
            return False

    @handle_errors("stop_playback")
    async def stop_playback(self) -> bool:
        """Stop current playback."""
        if not self._is_running or self._is_stopping:
            return False

        try:
            old_state = self._safe_get_current_state()
            # Use direct backend since we don't have playlist manager
            success = self._backend.stop()
            if success:
                self._safe_set_state(PlaybackState.STOPPED)
                if hasattr(self._state_manager, "update_position"):
                    self._state_manager.update_position(0.0)
                await self._event_bus.publish(
                    PlaybackStateChangedEvent("AudioEngine", old_state, PlaybackState.STOPPED)
                )
            return success
        except Exception as e:
            logger.error(f"Error stopping playback: {e}")
            # Still set stopped state on error
            self._safe_set_state(PlaybackState.STOPPED)
            return False

    async def set_volume(self, volume: int) -> bool:
        """Set playback volume."""
        if not self._is_running:
            return False

        try:
            old_volume = self._backend.get_volume()
            success = self._backend.set_volume(volume)

            if success:
                self._state_manager.update_volume(volume)
                await self._event_bus.publish(VolumeChangedEvent("AudioEngine", old_volume, volume))

            return success

        except Exception as e:
            await self._event_bus.publish(ErrorEvent("AudioEngine", f"Failed to set volume: {e}"))
            return False

    # === State Access ===

    def get_state_dict(self) -> Dict[str, Any]:
        """Get current state as dictionary."""
        base_state = self._state_manager.get_state_dict()

        # Note: Playlist state tracking is handled by PlaybackStateManager
        # in the application layer, not at the AudioEngine (domain) level

        # Add engine metadata
        base_state.update(
            {
                "engine_running": self._is_running,
                "uptime_seconds": time.time() - self._startup_time if self._startup_time else 0,
                "backend_type": type(self._backend).__name__,
            }
        )

        return base_state

    def get_engine_statistics(self) -> Dict[str, Any]:
        """Get comprehensive engine statistics."""
        return {
            "engine": {
                "is_running": self._is_running,
                "uptime_seconds": time.time() - self._startup_time if self._startup_time else 0,
                "backend_type": type(self._backend).__name__,
            },
            "event_bus": getattr(self._event_bus, "get_statistics", lambda: {})(),
            "current_state": self.get_state_dict(),
        }
