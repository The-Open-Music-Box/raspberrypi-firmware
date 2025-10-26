# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
PlaybackCoordinator - Orchestrates playlist and audio playback.

This coordinator combines playlist management and audio control,
ensuring single source of truth while maintaining separation of concerns.
"""

from typing import Optional, Dict, Any
import logging
from .playlist_controller import PlaylistController
from .audio_player_controller import AudioPlayer
from .track_resolver_controller import TrackResolver

logger = logging.getLogger(__name__)


class PlaybackCoordinator:
    """
    Coordinates between playlist management and audio playback.

    This is the main facade that orchestrates:
    - Playlist operations (via PlaylistController)
    - Audio playback (via AudioPlayer)
    - Auto-advance logic
    - Unified state reporting

    This provides the API that routes will use.
    """

    def __init__(self, audio_backend, playlist_service=None, upload_folder=None, socketio=None, data_application_service=None):
        """
        Initialize the playback coordinator.

        Args:
            audio_backend: Audio backend for playback
            playlist_service: Domain playlist service (auto-injected if None)
            upload_folder: Base folder for track files
            socketio: Socket.IO server for state broadcasting (optional)
            data_application_service: Data application service for NFC lookups (optional)
        """
        # Initialize components
        self._track_resolver = TrackResolver(upload_folder)

        # Require playlist service to be provided via dependency injection
        if playlist_service is None:
            raise ValueError("PlaybackCoordinator requires playlist_service to be injected")

        self._playlist_controller = PlaylistController(self._track_resolver, playlist_service)
        self._audio_player = AudioPlayer(audio_backend)

        # Auto-advance tracking
        self._auto_advance_enabled = True
        self._last_position = 0.0

        # Store socketio for state broadcasting
        self._socketio = socketio

        # Store data application service for NFC lookups
        self._data_application_service = data_application_service

        logger.info("✅ PlaybackCoordinator initialized")

    # --- Main Playback Controls ---

    def play(self, track_id: Optional[str] = None) -> bool:
        """
        Start playback or resume if paused.

        Args:
            track_id: Specific track ID to play, or None for current track

        Returns:
            bool: True if playback started successfully
        """
        try:
            # CRITICAL FIX: If audio is paused, resume instead of restarting
            if self._audio_player.is_paused():
                logger.info("🔄 Resuming paused playback")
                return self.resume()

            # If no track specified, use current track
            if track_id is None:
                current_track = self._playlist_controller.get_current_track()
                if not current_track:
                    # Try to start current playlist if available
                    if self._playlist_controller.has_playlist():
                        return self.start_playlist()
                    else:
                        logger.warning("No track or playlist to play")
                        return False
            else:
                # Find track in current playlist
                current_track = self._find_track_by_id(track_id)
                if not current_track:
                    logger.error(f"Track {track_id} not found in current playlist")
                    return False

            # Play the track
            if current_track.file_path:
                success = self._audio_player.play_file(current_track.file_path, current_track.duration_ms)
                if success:
                    logger.info(f"▶️ Playing: {current_track.title}")
                return success
            else:
                logger.error(f"Track {current_track.title} has no valid file path")
                return False

        except Exception as e:
            logger.error(f"Error starting playback: {e}")
            return False

    def pause(self) -> bool:
        """Pause current playback."""
        return self._audio_player.pause()

    def resume(self) -> bool:
        """Resume paused playback."""
        return self._audio_player.resume()

    def stop(self) -> bool:
        """Stop current playback."""
        return self._audio_player.stop()

    def toggle_pause(self) -> bool:
        """Toggle between play and pause."""
        # Check if audio is currently playing or paused
        if self._audio_player.is_playing() or self._audio_player.is_paused():
            # There's active audio, toggle its state
            return self._audio_player.toggle_pause()
        else:
            # No active audio, try to start playback
            logger.info("🔄 No active playback, attempting to start")
            return self.play()

    # --- Playlist Controls ---

    async def load_playlist(self, playlist_id: str) -> bool:
        """
        Load a playlist (async).

        Args:
            playlist_id: ID of the playlist to load

        Returns:
            bool: True if playlist loaded successfully
        """
        return await self._playlist_controller.load_playlist(playlist_id)

    def start_playlist(self, track_number: int = 1) -> bool:
        """
        Start playing a playlist from a specific track.

        Args:
            track_number: Track number to start from (1-based)

        Returns:
            bool: True if playback started successfully
        """
        if not self._playlist_controller.has_tracks():
            logger.warning("No playlist loaded or playlist is empty")
            return False

        # Move to specified track
        track = self._playlist_controller.goto_track(track_number)
        if not track:
            logger.error(f"Cannot start playlist at track {track_number}")
            return False

        # Start playback
        return self.play()

    def next_track(self) -> bool:
        """
        Move to and play next track.

        Returns:
            bool: True if moved to next track successfully
        """
        next_track = self._playlist_controller.next_track()
        if next_track:
            return self.play()
        else:
            logger.info("End of playlist reached")
            self.stop()
            return False

    def previous_track(self) -> bool:
        """
        Move to and play previous track.

        Returns:
            bool: True if moved to previous track successfully
        """
        prev_track = self._playlist_controller.previous_track()
        if prev_track:
            return self.play()
        else:
            logger.info("Beginning of playlist reached")
            return False

    def goto_track(self, track_number: int) -> bool:
        """
        Go to specific track and play it.

        Args:
            track_number: Track number (1-based)

        Returns:
            bool: True if moved to track successfully
        """
        track = self._playlist_controller.goto_track(track_number)
        if track:
            return self.play()
        else:
            logger.error(f"Invalid track number: {track_number}")
            return False

    # --- Volume Control ---

    def set_volume(self, volume: int) -> bool:
        """Set playback volume."""
        return self._audio_player.set_volume(volume)

    def get_volume(self) -> int:
        """Get current volume."""
        return self._audio_player.get_volume()

    # --- Seek Control ---

    def seek(self, position_seconds: float) -> bool:
        """Seek to specific position."""
        return self._audio_player.seek(position_seconds)

    def seek_to_position(self, position_ms: int) -> bool:
        """Seek to specific position in milliseconds."""
        position_seconds = position_ms / 1000.0
        return self.seek(position_seconds)

    # --- Playback Modes ---

    def set_repeat_mode(self, mode: str) -> bool:
        """Set repeat mode (none, one, all)."""
        return self._playlist_controller.set_repeat_mode(mode)

    def set_shuffle(self, enabled: bool) -> bool:
        """Enable/disable shuffle mode."""
        return self._playlist_controller.set_shuffle(enabled)

    def set_auto_advance(self, enabled: bool) -> None:
        """Enable/disable auto-advance to next track."""
        self._auto_advance_enabled = enabled
        logger.info(f"Auto-advance {'enabled' if enabled else 'disabled'}")

    # --- State Queries ---

    def get_playback_status(self) -> Dict[str, Any]:
        """
        Get complete playback status.

        Returns:
            Dict[str, Any]: Complete status including playlist and audio state
        """
        # Get states from components
        audio_state = self._audio_player.get_state()
        playlist_info = self._playlist_controller.get_playlist_info()

        # Check for auto-advance
        if self._auto_advance_enabled and self._should_auto_advance():
            self._handle_auto_advance()

        # Extract track for field name mapping
        current_track = playlist_info["current_track"]

        # Combine states with frontend-expected field names
        return {
            # Audio state
            "is_playing": audio_state["is_playing"],
            "is_paused": audio_state["is_paused"],
            "position_ms": int(audio_state["position"] * 1000) if audio_state["position"] is not None else 0,  # Convert to milliseconds
            "duration": audio_state["duration"],
            "duration_ms": int(audio_state["duration"] * 1000) if audio_state["duration"] is not None else 0,  # Duration in milliseconds for TrackProgressService
            "volume": audio_state["volume"],

            # Playlist state (using frontend-expected field names)
            "active_playlist_id": playlist_info["playlist_id"],
            "active_playlist_title": playlist_info["playlist_name"],
            "active_track": current_track,
            "active_track_id": current_track.get("id") if current_track else None,
            "track_index": playlist_info["current_track_number"],
            "track_count": playlist_info["total_tracks"],
            "can_next": playlist_info["can_next"],
            "can_prev": playlist_info["can_previous"],  # Map can_previous to can_prev for contract compliance
            "repeat_mode": playlist_info["repeat_mode"],
            "shuffle_enabled": playlist_info["shuffle_enabled"],

            # Coordinator state
            "auto_advance_enabled": self._auto_advance_enabled
        }

    def get_current_track(self) -> Optional[Dict[str, Any]]:
        """Get current track information."""
        track = self._playlist_controller.get_current_track()
        return track.to_dict() if track else None

    # --- Auto-advance Logic ---

    def update_auto_advance(self) -> None:
        """
        Update auto-advance logic.

        Should be called periodically by progress tracking service.
        """
        if self._auto_advance_enabled and self._should_auto_advance():
            self._handle_auto_advance()

    def _should_auto_advance(self) -> bool:
        """Check if should auto-advance to next track."""
        if not self._auto_advance_enabled:
            return False

        if not self._audio_player.is_playing():
            return False

        # Check if track has finished
        return self._audio_player.has_finished()

    def _handle_auto_advance(self) -> None:
        """Handle auto-advance to next track."""
        logger.info("🔄 Auto-advancing to next track")

        # Try to advance to next track
        if not self.next_track():
            # End of playlist - stop playback
            logger.info("📄 End of playlist - stopping playback")
            self.stop()

    # --- Helper Methods ---

    def _find_track_by_id(self, track_id: str) -> Optional[Any]:
        """Find track by ID in current playlist."""
        state = self._playlist_controller.get_state()
        if not state["playlist"]:
            return None

        for track in state["playlist"]["tracks"]:
            if track["id"] == track_id:
                # Convert back to Track object
                from .playlist_state_manager_controller import Track
                return Track(
                    id=track["id"],
                    title=track["title"],
                    filename=track["filename"],
                    duration_ms=track["duration_ms"],
                    file_path=track["file_path"]
                )

        return None

    # --- Component Access ---

    @property
    def playlist_controller(self) -> PlaylistController:
        """Get playlist controller for advanced operations."""
        return self._playlist_controller

    @property
    def audio_player(self) -> AudioPlayer:
        """Get audio player for advanced operations."""
        return self._audio_player

    # --- NFC Integration ---

    async def handle_tag_scanned(self, tag_uid: str, tag_data: Optional[Dict[str, Any]] = None) -> None:
        """Handle NFC tag scanned event.

        Args:
            tag_uid: The UID of the scanned NFC tag
            tag_data: Optional additional tag data
        """
        try:
            logger.info(f"🏷️ NFC tag scanned: {tag_uid}")

            # Try to find a playlist associated with this NFC tag
            logger.info(f"🔍 Looking for playlist associated with NFC tag: {tag_uid}")

            # Check if data application service is available
            if not self._data_application_service:
                logger.warning("⚠️ Data application service not injected, cannot look up NFC playlist")
                return

            # Use the injected DDD service to find playlist by NFC tag
            try:
                # This returns the playlist dict directly (or None)
                playlist = await self._data_application_service.get_playlist_by_nfc_use_case(tag_uid)

                if playlist:
                    playlist_title = playlist.get("title", playlist.get("name", "Unknown"))
                    playlist_id = playlist.get("id")

                    logger.info(f"🎵 Found playlist '{playlist_title}' for NFC tag")

                    # Load and start the playlist (async)
                    load_success = await self.load_playlist(playlist_id)
                    if load_success:
                        # Start playing from track 1
                        play_success = self.start_playlist(1)
                        if play_success:
                            logger.info(f"🎵 Started playing playlist '{playlist_title}'")

                            # CRITICAL FIX: Broadcast playlist started event via Socket.IO
                            # This ensures the frontend receives state updates just like in the UI flow
                            await self._broadcast_playlist_started(playlist_id)
                        else:
                            logger.warning(f"⚠️ Failed to start playing playlist '{playlist_title}'")
                    else:
                        logger.warning(f"⚠️ Failed to load playlist '{playlist_title}'")
                else:
                    logger.warning(f"⚠️ No playlist found for NFC tag: {tag_uid}")

            except Exception as service_error:
                logger.error(f"❌ Error accessing playlist service: {service_error}")
                logger.warning(f"⚠️ No playlist found for NFC tag: {tag_uid}")

            logger.info(f"✅ NFC tag handling completed for: {tag_uid}")

        except Exception as e:
            logger.error(f"❌ Error handling NFC tag {tag_uid}: {e}")

    async def _broadcast_playlist_started(self, playlist_id: str) -> None:
        """Broadcast playlist started event via Socket.IO.

        This method ensures the frontend receives state updates when a playlist
        is started via NFC, matching the behavior of the UI flow.

        Args:
            playlist_id: ID of the playlist that was started
        """
        if not self._socketio:
            logger.warning("⚠️ Socket.IO not available, cannot broadcast playlist started event")
            return

        try:
            # Import application layer services only (no API layer dependencies)
            from app.src.application.services.unified_state_manager import UnifiedStateManager
            from app.src.common.socket_events import StateEventType

            # Create state manager
            state_manager = UnifiedStateManager(self._socketio)

            # Broadcast playlist started event directly via state manager
            await state_manager.broadcast_state_change(
                StateEventType.PLAYLIST_STARTED,
                {
                    "playlist_id": playlist_id,
                    "source": "nfc"
                }
            )
            logger.info(f"✅ Broadcasted playlist started event for: {playlist_id}")

            # Also broadcast complete player state for client synchronization
            player_status = self.get_playback_status()
            await state_manager.broadcast_state_change(
                StateEventType.PLAYER_STATE,
                {
                    "state": "playing",
                    "player_status": player_status,
                    "operation": "playlist_started"
                }
            )
            logger.info(f"✅ Broadcasted complete player state for: {playlist_id}")

        except Exception as e:
            logger.error(f"❌ Error broadcasting playlist started event: {e}")

    def cleanup(self) -> None:
        """Cleanup coordinator resources."""
        self.stop()
        logger.info("PlaybackCoordinator cleaned up")
