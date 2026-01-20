# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Track progress service for real-time playback position monitoring.

Provides lightweight, high-frequency position updates via WebSocket events
for smooth frontend playback tracking. Handles track changes, auto-advance
detection, and error recovery with configurable update intervals.
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any

from app.src.common.socket_events import StateEventType
from app.src.config.socket_config import socket_config
from app.src.monitoring import get_logger
from app.src.services.error.unified_error_decorator import handle_service_errors

logger = get_logger(__name__)


class TrackProgressService:
    """Service for lightweight track position updates via WebSocket events.

    This service monitors playback position and emits state:track_position events
    at high frequency (200ms default) for smooth frontend playback tracking.
    Uses the new lightweight position format for minimal bandwidth and latency.
    """

    def __init__(
        self, state_manager: Any, audio_controller: Any | None = None, interval: float | None = None
    ):
        """Initialize the track progress service.

        Args:
            state_manager: StateManager instance for broadcasting events
            audio_controller: Audio controller or PlaybackCoordinator for getting playback status
            interval: Progress update interval in seconds (default: from socket_config)
        """
        self.state_manager = state_manager
        self.audio_controller = audio_controller
        self._controller_type = self._detect_controller_type()
        self.interval = interval or (socket_config.POSITION_UPDATE_INTERVAL_MS / 1000.0)
        self._running = False
        self._task: asyncio.Task | None = None
        self._last_progress: dict = {}
        self._error_count = 0
        self._max_consecutive_errors = 10
        self._recovery_delay = 5.0  # seconds
        self._last_track_end_time: float = 0.0  # Track last auto-advance to prevent duplicates

        # Diagnostic tracking - will be reset periodically to prevent memory leaks
        self._diagnostic_reset_interval = 100  # Reset every 100 iterations (100 seconds at 1000ms)
        self._last_diagnostic_reset: float = 0.0

        # Position tracking for stuck detection
        self._last_position_logged: float = 0.0
        self._last_position_time: float = 0.0

        logger.info(f"TrackProgressService initialized with {self._controller_type}")

    def _detect_controller_type(self) -> str:
        """Detect which type of controller we're using."""
        if not self.audio_controller:
            return "None"
        # Check for PlaybackCoordinator methods
        if hasattr(self.audio_controller, 'toggle_pause') and hasattr(self.audio_controller, 'get_playback_status'):
            return "PlaybackCoordinator"
        # Default to AudioController
        return "AudioController"

    async def start(self):
        """Start the periodic track progress emission."""
        if self._running:
            logger.warning("TrackProgressService already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._progress_loop())
        logger.info(f"✅ TrackProgressService STARTED - interval: {self.interval}s (should emit every {int(self.interval * 1000)}ms)",
                    )

    @handle_service_errors("track_progress")
    async def stop(self):
        """Stop the periodic track progress emission safely."""
        if not self._running:
            logger.debug("TrackProgressService already stopped")
            return

        logger.info("Stopping TrackProgressService...")
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except (TimeoutError, asyncio.CancelledError):
                # Task was cancelled or timed out, which is expected
                pass
        # Reset state including diagnostic attributes
        self._error_count = 0
        self._last_progress = {}
        self._reset_diagnostic_attributes()
        logger.info("TrackProgressService stopped successfully")

    @handle_service_errors("track_progress")
    async def _progress_loop(self):
        """Main loop for periodic progress emission with error recovery."""
        logger.info("🔄 TrackProgressService loop STARTED - will emit position events"
                    )

        loop_counter = 0
        last_playing_state = False

        while self._running:
            loop_counter += 1

            # Get current playback status first
            if self.audio_controller:
                # Handle both sync and async get_playback_status
                if asyncio.iscoroutinefunction(self.audio_controller.get_playback_status):
                    status = await self.audio_controller.get_playback_status()
                else:
                    # PlaybackCoordinator has sync get_playback_status
                    status = self.audio_controller.get_playback_status()
                is_playing = status.get("is_playing", False) if status else False

                # Only emit if playing OR state changed (for UI updates)
                if is_playing or (is_playing != last_playing_state):
                    await self._emit_progress()
                    last_playing_state = is_playing

                    # Reset error count on successful emission
                    if self._error_count > 0:
                        logger.info("✅ Track progress service recovered from errors")
                        self._error_count = 0

            # Log every 100 loops ONLY if playing (reduce logging frequency)
            if loop_counter % 100 == 0 and last_playing_state:
                logger.debug(f"📍 Progress loop alive - iteration {loop_counter}, errors: {self._error_count}",
                             )

            # Sleep for the configured interval (critical!)
            await asyncio.sleep(self.interval)

    @handle_service_errors("track_progress")
    async def _emit_progress(self):
        """Emit lightweight position updates for smooth playback tracking."""
        async with self._safe_operation_context("emit_progress"):
            if not self._validate_service_state():
                return

            self._update_diagnostic_counters()
            status = await self._get_playback_status()

            if not status:
                return

            position_data = self._extract_position_data(status)
            await self._handle_track_events(status, position_data)
            self._log_progress_diagnostics(position_data)

            if not self._validate_and_log_position(position_data):
                return

            await self._broadcast_position(position_data)

    def _validate_service_state(self) -> bool:
        """Validate service state before emitting progress."""
        if not self._running:
            logger.warning("❌ TrackProgressService not running - no position updates will be sent")
            return False

        if not self.state_manager:
            logger.error("❌ No StateManager available - cannot broadcast position updates")
            return False

        if not self.audio_controller:
            logger.debug("No audio controller available for progress emission")
            return False

        return True

    def _update_diagnostic_counters(self) -> None:
        """Update diagnostic counters and reset periodically."""
        if not hasattr(self, "_emission_attempt_count"):
            self._emission_attempt_count = 0
        self._emission_attempt_count += 1

        # Reset diagnostic attributes periodically to prevent memory accumulation
        if self._emission_attempt_count % self._diagnostic_reset_interval == 0:
            self._reset_diagnostic_attributes(preserve_counters=True)
            logger.info(
                f"🧹 Diagnostic attributes reset at iteration {self._emission_attempt_count}"
            )

    async def _get_playback_status(self) -> dict | None:
        """Get playback status from audio controller."""
        # Handle both sync and async get_playback_status
        if asyncio.iscoroutinefunction(self.audio_controller.get_playback_status):
            status = await self.audio_controller.get_playback_status()
        else:
            status = self.audio_controller.get_playback_status()

        # Log first status for debugging
        if not hasattr(self, "_first_status_logged"):
            logger.info(f"🎵 FIRST playback status: {status}")
            self._first_status_logged = True

        if not status:
            if not hasattr(self, "_no_status_logged"):
                logger.warning(
                    f"⚠️️ No status returned from audio controller "
                    f"(attempt #{self._emission_attempt_count})"
                )
                self._no_status_logged = True

        return status

    def _extract_position_data(self, status: dict) -> dict:
        """Extract position data from playback status."""
        # Get position and duration - prioritize _ms fields for consistency
        current_time_ms = status.get("position_ms") or status.get("current_time", 0)
        duration_ms = status.get("duration_ms") or status.get("duration", 0)

        # Convert to seconds for internal processing (legacy compatibility)
        current_time = current_time_ms / 1000.0 if current_time_ms else 0.0
        duration = duration_ms / 1000.0 if duration_ms else 0.0

        # Use correct field names from PlaybackCoordinator status
        is_playing = status.get("is_playing", False)
        track_id = status.get("active_track_id")

        return {
            "current_time_ms": current_time_ms,
            "duration_ms": duration_ms,
            "current_time": current_time,
            "duration": duration,
            "is_playing": is_playing,
            "track_id": track_id,
        }

    async def _handle_track_events(self, status: dict, position_data: dict) -> None:
        """Handle track change and track end events."""
        await self._check_for_track_change(status)
        await self._check_for_track_end(
            position_data["current_time"],
            position_data["duration"],
            position_data["is_playing"]
        )

    def _log_progress_diagnostics(self, position_data: dict) -> None:
        """Log diagnostic information for progress tracking."""
        if not hasattr(self, "_emit_counter"):
            self._emit_counter = 0
        self._emit_counter += 1

        # Log every 50th emission
        if self._emit_counter % 50 == 0:
            logger.debug(
                f"📍 Progress emission #{self._emit_counter}: "
                f"pos={position_data['current_time']:.1f}s/{position_data['duration']:.1f}s, "
                f"playing={position_data['is_playing']}, track_id={position_data['track_id']}"
            )

        # Check for stuck position
        self._check_stuck_position(position_data["current_time"], position_data["is_playing"])

    def _check_stuck_position(self, current_time: float, is_playing: bool) -> None:
        """Check if playback position is stuck."""
        if hasattr(self, "_last_position_logged") and hasattr(self, "_last_position_time"):
            if current_time == self._last_position_logged and is_playing:
                stuck_duration = time.time() - self._last_position_time
                if stuck_duration > 5.0:
                    logger.warning(
                        f"⚠️ Position seems stuck at {current_time:.1f}s "
                        f"for {stuck_duration:.1f}s while playing"
                    )

        self._last_position_logged = current_time
        self._last_position_time = time.time()

    def _validate_and_log_position(self, position_data: dict) -> bool:
        """Validate position data and log validation status."""
        if not self._validate_position_data(
            position_data["current_time"],
            position_data["duration"],
            position_data["track_id"]
        ):
            if not hasattr(self, "_validation_fail_logged"):
                logger.warning(
                    f"❌ VALIDATION FAILED (attempt #{self._emission_attempt_count}): "
                    f"time={position_data['current_time']}, "
                    f"duration={position_data['duration']}, "
                    f"track_id={position_data['track_id']}"
                )
                self._validation_fail_logged = True
            return False

        # Log first successful validation
        if not hasattr(self, "_first_valid_logged"):
            logger.info(
                f"✅ FIRST VALID position: time={position_data['current_time']:.1f}s, "
                f"duration={position_data['duration']:.1f}s, "
                f"track_id={position_data['track_id']}, playing={position_data['is_playing']}"
            )
            self._first_valid_logged = True

        return True

    async def _broadcast_position(self, position_data: dict) -> None:
        """Broadcast position update to clients."""
        # Log first broadcast attempt
        if not hasattr(self, "_first_broadcast_logged"):
            logger.info(
                f"📡 FIRST BROADCAST attempt: pos={position_data['current_time_ms']}ms, "
                f"track={position_data['track_id']}, playing={position_data['is_playing']}"
            )
            self._first_broadcast_logged = True

        result = await self.state_manager.broadcast_position_update(
            position_ms=position_data["current_time_ms"],
            track_id=str(position_data["track_id"]) if position_data["track_id"] else "unknown",
            is_playing=position_data["is_playing"],
            duration_ms=position_data["duration_ms"] if position_data["duration_ms"] > 0 else None,
        )

        self._track_broadcast_result(result)

    def _track_broadcast_result(self, result) -> None:
        """Track broadcast result for diagnostic purposes."""
        if not hasattr(self, "_successful_broadcast_count"):
            self._successful_broadcast_count = 0

        if result is not None:
            self._successful_broadcast_count += 1

        # Log if broadcast was throttled
        if result is None and not hasattr(self, "_throttle_logged"):
            logger.warning("⚠️️ Position update THROTTLED by StateManager")
            self._throttle_logged = True
        elif result and not hasattr(self, "_broadcast_success_logged"):
            logger.info(f"✅ FIRST BROADCAST SUCCESS: {result.get('event_type', 'unknown')}")
            self._broadcast_success_logged = True

    def _validate_position_data(self, current_time: float, duration: float, track_id) -> bool:
        """Validate position data before emission."""
        # DIAGNOSTIC: Track validation failures
        if not hasattr(self, "_validation_check_count"):
            self._validation_check_count = 0
        self._validation_check_count += 1

        # Allow track_id to be None or empty string temporarily
        if current_time is None:
            return False

        if current_time < 0:
            return False

        # Allow small overflow
        return not (duration and duration > 0 and current_time > duration + 1)

    @asynccontextmanager
    @handle_service_errors("track_progress")
    async def _safe_operation_context(self, operation_name: str):
        """Context manager for safe operation execution with error handling."""
        yield

    @handle_service_errors("track_progress")
    async def emit_immediate_position(self):
        """Emit position immediately (useful for track changes or seek operations)."""
        await self._emit_progress()

    @property
    def is_running(self) -> bool:
        """Check if the service is currently running."""
        return self._running

    @property
    def error_count(self) -> int:
        """Get current error count for monitoring."""
        return self._error_count

    def reset_error_count(self):
        """Reset error count manually (for external recovery mechanisms)."""
        old_count = self._error_count
        self._error_count = 0
        if old_count > 0:
            logger.info(f"Error count reset from {old_count} to 0")

    def configure_error_handling(
        self, max_consecutive_errors: int | None = None, recovery_delay: float | None = None
    ):
        """Configure error handling parameters."""
        if max_consecutive_errors is not None:
            self._max_consecutive_errors = max_consecutive_errors
        if recovery_delay is not None:
            self._recovery_delay = recovery_delay

        logger.info(f"Error handling configured: max_errors={self._max_consecutive_errors}, "
                    f"recovery_delay={self._recovery_delay}s",
                    )

    def _reset_diagnostic_attributes(self, preserve_counters: bool = False):
        """Reset diagnostic tracking attributes to prevent memory accumulation.

        Args:
            preserve_counters: If True, preserve main counters but reset one-time flags
        """
        # One-time logging flags that can be safely reset
        diagnostic_flags = [
            "_first_status_logged",
            "_no_status_logged",
            "_validation_fail_logged",
            "_first_valid_logged",
            "_first_broadcast_logged",
            "_broadcast_success_logged",
            "_throttle_logged",
            "_envelopeLogged",
            "_domDispatchLogged",
        ]

        reset_count = 0
        for flag in diagnostic_flags:
            if hasattr(self, flag):
                delattr(self, flag)
                reset_count += 1

        if not preserve_counters:
            # Reset all counters - only when completely stopping service
            counter_attrs = [
                "_emission_attempt_count",
                "_emit_counter",
                "_validation_check_count",
                "_successful_broadcast_count",
            ]
            for attr in counter_attrs:
                if hasattr(self, attr):
                    delattr(self, attr)
                    reset_count += 1

        self._last_diagnostic_reset = time.time()
        if reset_count > 0:
            logger.debug(f"Reset {reset_count} diagnostic attributes")

    @handle_service_errors("track_progress")
    async def _check_for_track_change(self, status: dict):
        """Check for track changes and emit state:track events to frontend."""
        track_number = status.get("track_number", status.get("number"))
        track_id = status.get("active_track_id")  # CRITICAL FIX: Use correct field name
        # Initialize last track info if needed
        if not hasattr(self, "_last_track_number"):
            self._last_track_number = None
            self._last_track_id = None
        # Check if track has changed (by number or ID)
        track_changed = track_number != self._last_track_number or track_id != self._last_track_id
        if track_changed and track_number is not None:
            logger.info(f"🎵 Track change detected: {self._last_track_number} → {track_number}",
                        )
            # Get full track info from audio controller
            if self.audio_controller and hasattr(self.audio_controller, "_audio_service"):
                track_info = self.audio_controller._audio_service.get_current_track_info()
                # Get playlist_id from audio controller
                playlist_id = getattr(self.audio_controller, "_current_playlist_id", None)
                # Broadcast state:track event via StateManager
                await self.state_manager.broadcast_state_change(
                    event_type=StateEventType.TRACK_SNAPSHOT,
                    data={"track": track_info, "timestamp": time.time()},
                    playlist_id=playlist_id,
                    immediate=True,  # Send immediately for UI responsiveness
                )
                logger.info(f"✅ Broadcasted state:track event for '{track_info.get('title', 'Unknown')}'",
                            )

    async def _check_for_track_end(self, current_time: float, duration: float, is_playing: bool):
        """Check if track has ended and trigger auto-advance if appropriate."""
        try:
            # Only check for auto-advance if we're playing and have valid duration
            if not is_playing or not duration or duration <= 0:
                return

            # Additional safeguards:
            # 1. Don't trigger if duration is suspiciously short (< 1 second)
            if duration < 1.0:
                return

            # 2. Don't trigger if current_time is 0 (track just started)
            if current_time <= 0.5:
                return

            # 3. Require track to be at least 90% complete (not just near the end)
            if current_time < (duration * 0.9):
                return

            # Check if track has ended (with small buffer for timing precision)
            if current_time >= duration - 0.1:
                # Prevent duplicate auto-advance within 2 seconds
                current_timestamp = time.time()
                if current_timestamp - self._last_track_end_time < 2.0:
                    return

                self._last_track_end_time = current_timestamp
                logger.info(f"🔚 Track end detected: {current_time:.1f}s >= {duration:.1f}s"
                            )

                # Trigger auto-advance via controller
                if self._controller_type == "PlaybackCoordinator":
                    # PlaybackCoordinator uses next_track for auto-advance
                    if self.audio_controller and hasattr(self.audio_controller, "next_track"):
                        success = await asyncio.get_running_loop().run_in_executor(
                            None, self.audio_controller.next_track
                        )
                        if success:
                            logger.info("✅ Auto-advance to next track successful via PlaybackCoordinator")

                            # CRITICAL FIX: Broadcast player state change after auto-advance
                            # This ensures frontend UI updates when track changes automatically
                            await self._broadcast_player_state_after_auto_advance()
                        else:
                            logger.info("🔚 End of playlist reached")
                elif self.audio_controller and hasattr(self.audio_controller, "auto_advance_to_next"):
                    # AudioController has dedicated auto_advance_to_next method
                    success = await asyncio.get_event_loop().run_in_executor(
                        None, self.audio_controller.auto_advance_to_next
                    )
                    if success:
                        logger.info("✅ Auto-advance to next track successful via AudioController")

                        # CRITICAL FIX: Broadcast player state change after auto-advance
                        await self._broadcast_player_state_after_auto_advance()
                    else:
                        logger.info("🔚 End of playlist reached")
                else:
                    logger.warning(f"⚠️️ {self._controller_type} doesn't support auto-advance")

        except Exception as e:
            logger.error(f"❌ Error in track end detection: {e!s}")

    @handle_service_errors("track_progress")
    async def _broadcast_player_state_after_auto_advance(self):
        """Broadcast complete player state after auto-advance.

        This ensures the frontend UI updates with the new track information
        when auto-advance happens (track automatically moves to next).
        """
        try:
            # Get current playback status with new track info
            if not self.audio_controller:
                logger.warning("⚠️ No audio controller available after auto-advance")
                return

            if asyncio.iscoroutinefunction(self.audio_controller.get_playback_status):
                status = await self.audio_controller.get_playback_status()
            else:
                status = self.audio_controller.get_playback_status()

            if not status:
                logger.warning("⚠️ No status available after auto-advance")
                return

            # Broadcast full player state change via StateManager
            # This mimics what the API layer does when user clicks "next"
            await self.state_manager.broadcast_state_change(
                event_type=StateEventType.PLAYER_STATE,
                data=status,
                immediate=True  # Send immediately for UI responsiveness
            )

            track_title = status.get("current_track", {}).get("title", "Unknown") if status.get("current_track") else "Unknown"
            logger.info(f"✅ Broadcasted player state after auto-advance: track='{track_title}', playing={status.get('is_playing', False)}")

        except Exception as e:
            logger.error(f"❌ Failed to broadcast player state after auto-advance: {e!s}")
