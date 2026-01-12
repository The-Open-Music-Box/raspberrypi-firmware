# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""WM8960 Audio Backend Implementation.

This module provides a clean WM8960 audio backend implementation for Raspberry Pi hardware.
It implements the AudioBackendProtocol interface and provides real hardware audio playback
through the WM8960 codec using pygame for reliable audio format handling.

Features:
- Audio playback via pygame mixer
- Hardware volume control via ALSA
- Headphone jack detection with automatic speaker muting
"""

import asyncio
import os
import subprocess  # nosec B404 - subprocess required for ALSA audio device detection and control
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

try:
    from mutagen import File as MutagenFile
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    MutagenFile = None

from app.src.domain.decorators.error_handler import (
    handle_domain_errors as handle_errors,
)
from app.src.domain.protocols.jack_detection_protocol import (
    JackDetectionProtocol,
    JackState,
)
from app.src.domain.protocols.notification_protocol import (
    PlaybackNotifierProtocol as PlaybackSubject,
)
from app.src.monitoring import get_logger

from .base_audio_backend import BaseAudioBackend

logger = get_logger(__name__)

# Default speaker volume when headphones are unplugged
DEFAULT_SPEAKER_VOLUME = 122  # ALSA volume level (0-127)


class WM8960AudioBackend(BaseAudioBackend):
    """WM8960 audio backend for Raspberry Pi hardware.

    This implementation provides real audio playback through the WM8960 codec
    using ALSA and subprocess-based audio control. Supports automatic speaker
    muting when headphones are connected via jack detection.
    """

    def __init__(
        self,
        playback_subject: PlaybackSubject | None = None,
        allow_graceful_degradation: bool = True,
        jack_detection: JackDetectionProtocol | None = None,
    ):
        """Initialize the WM8960 audio backend.

        Args:
            playback_subject: Optional subject for playback notifications
            allow_graceful_degradation: If True, allows initialization to succeed even if hardware fails
            jack_detection: Optional jack detection service for headphone plug/unplug events
        """
        super().__init__(playback_subject)
        self._is_paused = False
        self._play_start_time = None
        self._pause_time = None

        # Track current file and its duration
        self._current_file_path = None
        self._current_file_duration = None  # in seconds

        # Track hardware availability
        self._hardware_available = False
        self._initialization_error = None

        # Jack detection for automatic speaker muting
        self._jack_detection = jack_detection
        self._headphone_connected = False
        self._headphone_state_change_callback: Callable[[bool], None] | None = None

        # Initialize hardware
        self._initialize_wm8960_hardware()

        # Initialize jack detection if provided
        if self._jack_detection is not None:
            self._setup_jack_detection()

        # Initialize pygame mixer for proper audio handling
        self._pygame_initialized = False
        if PYGAME_AVAILABLE:
            # Simple default pygame initialization on startup
            self._pygame_initialized = self._init_pygame_simple()
            if not self._pygame_initialized:
                error_msg = "🔊 WM8960: Failed to initialize pygame mixer - audio device is busy or unavailable"
                logger.error(error_msg)
                self._initialization_error = "pygame mixer could not be initialized"

                if not allow_graceful_degradation:
                    raise RuntimeError("WM8960 audio backend initialization failed: pygame mixer could not be initialized")

                logger.warning("🔊 WM8960: Continuing with degraded mode - audio playback unavailable")
            else:
                self._hardware_available = True
                logger.info("🔊 WM8960 Audio Backend initialized successfully")
        else:
            error_msg = "🔊 WM8960: pygame not available - audio will not work"
            logger.warning(error_msg)
            self._initialization_error = "pygame not available"

            if not allow_graceful_degradation:
                raise RuntimeError("WM8960 audio backend initialization failed: pygame not available")

            logger.warning("🔊 WM8960: Continuing with degraded mode - audio playback unavailable")

    @handle_errors("_init_pygame_simple")
    def _init_pygame_simple(self) -> bool:
        """Initialize pygame mixer with simple default configuration (like main branch)."""
        logger.info("🔊 WM8960: Initializing pygame mixer with simple default configuration")

        # Clear any existing pygame state
        if pygame.mixer.get_init():
            pygame.mixer.quit()

        # Clean up any SDL environment variables that might interfere
        if 'SDL_AUDIODRIVER' in os.environ:
            del os.environ['SDL_AUDIODRIVER']
        if 'SDL_AUDIODEV' in os.environ:
            del os.environ['SDL_AUDIODEV']

        # Simple solution: Use direct hardware access like aplay -D plughw:wm8960soundcard,0
        # This bypasses dmix configuration issues and matches working aplay command
        os.environ['SDL_AUDIODRIVER'] = 'alsa'
        device = f'plughw:{self._audio_device.split(":")[1] if ":" in self._audio_device else "wm8960soundcard,0"}'
        os.environ['SDL_AUDIODEV'] = device

        logger.info(f"🔊 WM8960: SDL_AUDIODRIVER={os.environ.get('SDL_AUDIODRIVER')}")
        logger.info(f"🔊 WM8960: SDL_AUDIODEV={os.environ.get('SDL_AUDIODEV')}")

        # Use audio parameters that match WM8960 hardware capabilities
        # Based on aplay working format: 48000Hz, Signed 16 bit Little Endian, 2 channels
        pygame.mixer.pre_init(frequency=48000, size=-16, channels=2, buffer=2048)

        logger.info("🔊 WM8960: pygame.mixer.pre_init called with freq=48000, size=-16, channels=2, buffer=2048")

        try:
            pygame.mixer.init()
            logger.info("🔊 WM8960: pygame.mixer.init() successful")
        except Exception as e:
            logger.error(f"🔊 WM8960: pygame.mixer.init() failed: {e}")
            return False

        # Verify initialization
        if pygame.mixer.get_init():
            init_info = pygame.mixer.get_init()
            logger.info(f"🔊 WM8960: pygame mixer initialized successfully with {init_info} (simple default)"
                        )
            return True
        logger.error("🔊 WM8960: pygame mixer failed to initialize")
        return False

    @handle_errors("_detect_wm8960_device")
    def _detect_wm8960_device(self) -> str:
        """Detect WM8960 audio device automatically using stable card NAME (not card number).

        Detection priority:
        1. AUDIO_DEVICE_NAME environment variable
        2. Auto-detect card name from aplay -l output
        3. Fallback to "wm8960soundcard" (default WM8960 card name)

        Returns:
            str: ALSA device identifier for WM8960 using card NAME (e.g., "plughw:wm8960soundcard")
        """
        # Priority 1: Check environment variable override
        env_device = os.environ.get("AUDIO_DEVICE_NAME")
        if env_device:
            device = f"plughw:{env_device}"
            logger.info(f"🔊 WM8960: Using device from AUDIO_DEVICE_NAME env var: {device}")
            return device

        # Priority 2: Auto-detect card name from aplay -l
        try:
            # Try to get list of audio devices (hardcoded command, not user input)
            result = subprocess.run(["aplay", "-l"], check=False, capture_output=True, text=True)  # nosec B603 B607

            if result.returncode == 0:
                output = result.stdout
                # Look for WM8960 card and extract card NAME (not number)
                for line in output.split("\n"):
                    if "wm8960" in line.lower():
                        # Try to extract card name from "card X: cardname [...]" format
                        if "card" in line.lower() and ":" in line:
                            parts = line.split(":")
                            if len(parts) >= 2:
                                # Extract card name (second part after first colon, before brackets)
                                card_name_part = parts[1].strip()
                                # Card name is typically before any brackets or dashes
                                card_name = card_name_part.split("[")[0].split("-")[0].strip()
                                if card_name:
                                    device = f"plughw:{card_name}"
                                    logger.info(f"🔊 WM8960: Auto-detected device by card name: {device}")
                                    return device
        except FileNotFoundError:
            # aplay not found (e.g., on macOS), use fallback
            logger.info("🔊 WM8960: aplay not found, using fallback device")
        except Exception as e:
            logger.warning(f"🔊 WM8960: Error detecting device: {e}, using fallback")

        # Priority 3: Fallback to default WM8960 card name
        device = "plughw:wm8960soundcard"
        logger.info(f"🔊 WM8960: Using fallback device (stable card name): {device}")
        return device

    def _get_card_name(self) -> str:
        """Extract ALSA card name from the detected audio device.

        The _audio_device is in format 'plughw:cardname' or 'plughw:cardname,0'.
        For amixer commands, we need just the card name without device suffix.

        Returns:
            str: ALSA card name (e.g., 'wm8960soundcard')
        """
        if self._audio_device and ":" in self._audio_device:
            # Extract card name from "plughw:cardname" or "plughw:cardname,0" format
            card_part = self._audio_device.split(":")[-1]
            # Strip device suffix like ",0" if present
            if "," in card_part:
                card_part = card_part.split(",")[0]
            return card_part
        # Fallback to default WM8960 card name
        return "wm8960soundcard"

    def _get_file_duration(self, file_path: str) -> float | None:
        """Get the duration of an audio file using mutagen.

        Args:
            file_path: Path to the audio file

        Returns:
            float: Duration in seconds, or None if not available
        """
        if not MUTAGEN_AVAILABLE:
            logger.warning("🔊 WM8960: mutagen not available for duration detection")
            return None

        try:
            audio_file = MutagenFile(file_path)
            if audio_file is not None and hasattr(audio_file, 'info'):
                duration = getattr(audio_file.info, 'length', None)
                if duration and duration > 0:
                    logger.debug(f"🔊 WM8960: Duration detected: {duration:.1f}s for {Path(file_path).name}")
                    return float(duration)
                logger.warning(f"🔊 WM8960: Invalid duration for {Path(file_path).name}")
            else:
                logger.warning(f"🔊 WM8960: Could not read audio metadata for {Path(file_path).name}")
        except Exception as e:
            logger.warning(f"🔊 WM8960: Error reading duration for {Path(file_path).name}: {e}")

        return None

    @handle_errors("_initialize_wm8960_hardware")
    def _initialize_wm8960_hardware(self) -> bool:
        """Initialize WM8960 hardware settings.

        Returns:
            bool: True if initialization was successful
        """
        # Detect the correct audio device for pygame configuration
        self._audio_device = self._detect_wm8960_device()
        logger.info(f"🔊 WM8960: Detected audio device: {self._audio_device}")
        return True

    def _setup_jack_detection(self) -> None:
        """Set up jack detection callback and read initial state."""
        if self._jack_detection is None:
            return

        # Register callback for jack state changes
        self._jack_detection.set_state_change_handler(self._on_jack_state_changed)

        # Read and apply initial state
        initial_state = self._jack_detection.get_state()
        if initial_state != JackState.UNKNOWN:
            self._headphone_connected = initial_state == JackState.CONNECTED
            self._update_speaker_state()
            logger.info(
                f"🎧 WM8960: Initial headphone state: "
                f"{'connected' if self._headphone_connected else 'disconnected'}"
            )

    def _on_jack_state_changed(self, new_state: JackState) -> None:
        """Handle jack state change events.

        Args:
            new_state: The new jack state.
        """
        was_connected = self._headphone_connected
        self._headphone_connected = new_state == JackState.CONNECTED

        if was_connected != self._headphone_connected:
            logger.info(
                f"🎧 WM8960: Headphone {'connected' if self._headphone_connected else 'disconnected'}"
            )
            self._update_speaker_state()

            # Notify external callback if registered
            if self._headphone_state_change_callback is not None:
                try:
                    self._headphone_state_change_callback(self._headphone_connected)
                except Exception as e:
                    logger.error(f"Error in headphone state change callback: {e}")

    def _update_speaker_state(self) -> None:
        """Update speaker mute state based on headphone connection."""
        if self._headphone_connected:
            self._mute_speakers()
        else:
            self._unmute_speakers()

    @handle_errors("_mute_speakers")
    def _mute_speakers(self) -> bool:
        """Mute the speakers via ALSA when headphones are connected.

        Returns:
            bool: True if successful.
        """
        try:
            card_name = self._get_card_name()
            # Mute speaker output via amixer
            subprocess.run(  # nosec B603 B607
                ["amixer", "-c", card_name, "sset", "Speaker", "0"],
                check=True,
                capture_output=True,
                timeout=2.0,
            )
            logger.info(f"🔇 WM8960: Speakers muted on {card_name} (headphones connected)")
            return True
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to mute speakers: {e}")
            return False
        except FileNotFoundError:
            logger.warning("amixer not found - speaker mute unavailable")
            return False
        except subprocess.TimeoutExpired:
            logger.warning("amixer timeout while muting speakers")
            return False

    @handle_errors("_unmute_speakers")
    def _unmute_speakers(self) -> bool:
        """Unmute the speakers via ALSA when headphones are disconnected.

        Returns:
            bool: True if successful.
        """
        try:
            card_name = self._get_card_name()
            # Restore speaker output via amixer
            subprocess.run(  # nosec B603 B607
                ["amixer", "-c", card_name, "sset", "Speaker", str(DEFAULT_SPEAKER_VOLUME)],
                check=True,
                capture_output=True,
                timeout=2.0,
            )
            logger.info(f"🔊 WM8960: Speakers unmuted on {card_name} (volume={DEFAULT_SPEAKER_VOLUME})")
            return True
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to unmute speakers: {e}")
            return False
        except FileNotFoundError:
            logger.warning("amixer not found - speaker unmute unavailable")
            return False
        except subprocess.TimeoutExpired:
            logger.warning("amixer timeout while unmuting speakers")
            return False

    def set_headphone_state_change_callback(
        self, callback: Callable[[bool], None]
    ) -> None:
        """Set callback for headphone state changes.

        This allows external components (like Socket.IO) to be notified
        when headphones are plugged/unplugged.

        The callback is immediately invoked with the current state to ensure
        clients receive the initial headphone status at boot.

        Args:
            callback: Function that receives True when headphones connected,
                     False when disconnected.
        """
        self._headphone_state_change_callback = callback
        logger.debug("Headphone state change callback registered")

        # Immediately notify of current state (important for boot state broadcast)
        if self._jack_detection is not None:
            try:
                callback(self._headphone_connected)
                logger.info(
                    f"🎧 Initial headphone state broadcast: "
                    f"{'connected' if self._headphone_connected else 'disconnected'}"
                )
            except Exception as e:
                logger.error(f"Error broadcasting initial headphone state: {e}")

    def is_headphone_connected(self) -> bool:
        """Check if headphones are currently connected.

        Returns:
            bool: True if headphones are connected.
        """
        return self._headphone_connected

    def get_jack_detection_status(self) -> dict[str, Any]:
        """Get jack detection status information.

        Returns:
            dict: Status including enabled, connected state, etc.
        """
        if self._jack_detection is None:
            return {
                "enabled": False,
                "available": False,
                "headphone_connected": False,
            }

        status = self._jack_detection.get_status()
        status["headphone_connected"] = self._headphone_connected
        return status

    def is_hardware_available(self) -> bool:
        """Check if audio hardware is available and functional.

        Returns:
            bool: True if hardware is operational, False otherwise
        """
        return self._hardware_available

    def get_hardware_status(self) -> dict[str, Any]:
        """Get detailed hardware status information.

        Returns:
            dict: Hardware status including availability, device name, and any errors
        """
        return {
            "available": self._hardware_available,
            "device": self._audio_device if hasattr(self, '_audio_device') else None,
            "initialized": self._pygame_initialized,
            "error": self._initialization_error,
            "backend_type": "WM8960AudioBackend"
        }

    @handle_errors("play_file")
    def play_file(self, file_path: str, duration_ms: int | None = None) -> bool:
        """Play a single audio file through WM8960 using pygame.

        Args:
            file_path: Path to the audio file to play
            duration_ms: Optional track duration in milliseconds from playlist

        Returns:
            bool: True if playback started successfully, False otherwise
        """
        path = self._validate_file_path(file_path)
        if not path:
            return False

        with self._state_lock:
            # Check if pygame was initialized successfully
            if not self._pygame_initialized:
                logger.error("🔊 WM8960: pygame mixer not initialized - cannot play audio")
                return False

            # Stop current playback if any
            self._stop_current_playback()
            # Use pygame for reliable audio playback
            if not PYGAME_AVAILABLE:
                logger.error("🔊 WM8960: pygame not available - cannot play audio")
                return False
            if not pygame.mixer.get_init():
                logger.warning("🔊 WM8960: pygame mixer not initialized, attempting to initialize",
                               )
                if not self._init_pygame_simple():
                    logger.error("🔊 WM8960: Failed to initialize pygame mixer")
                    return False
            return cast(bool, self._play_with_pygame(str(path), duration_ms))

    @handle_errors("_play_with_pygame")
    def _play_with_pygame(self, file_path: str, duration_ms: int | None = None) -> bool:
        """Play audio file using pygame.mixer.music (preferred method)."""
        logger.info(f"🔊 WM8960: Using pygame.mixer.music for playback of {file_path}")

        # Check pygame mixer state before loading
        mixer_init = pygame.mixer.get_init()
        logger.info(f"🔊 WM8960: pygame.mixer state before load: {mixer_init}")

        try:
            # Load and play the audio file with pygame.mixer.music
            logger.info(f"🔊 WM8960: Loading audio file: {file_path}")
            pygame.mixer.music.load(file_path)
            logger.info("🔊 WM8960: Audio file loaded successfully")

            logger.info("🔊 WM8960: Starting playback...")
            pygame.mixer.music.play()
            logger.info("🔊 WM8960: pygame.mixer.music.play() called")

            # Check if playback started
            is_busy = pygame.mixer.music.get_busy()
            logger.info(f"🔊 WM8960: pygame.mixer.music.get_busy() = {is_busy}")

            self._current_file_path = file_path
            self._is_playing = True
            self._is_paused = False
            self._play_start_time = time.time()
            self._pause_time = None

            # Use duration from playlist if provided, otherwise detect it from file
            if duration_ms:
                self._current_file_duration = duration_ms / 1000.0
            else:
                # Try to detect file duration automatically
                self._current_file_duration = self._detect_file_duration(file_path)

            logger.info(f"🔊 WM8960: Playback state set - playing={self._is_playing}, busy={is_busy}")
            return True

        except Exception as e:
            logger.error(f"🔊 WM8960: Error during pygame playback: {e}")
            return False

    @handle_errors("stop_sync")
    def stop_sync(self) -> bool:
        """Stop playback.

        Returns:
            bool: True if stopped successfully, False otherwise
        """
        with self._state_lock:
            self._stop_current_playback()
        logger.info("🔊 WM8960: Playback stopped")
        return True

    @handle_errors("pause_sync")
    def pause_sync(self) -> bool:
        """Pause playback using pygame.mixer.music.pause().

        Returns:
            bool: True if paused successfully, False otherwise
        """
        if not self._is_playing or self._is_paused:
            return False

        with self._state_lock:
            if PYGAME_AVAILABLE and pygame.mixer.get_init():
                # Proper pause with pygame.mixer.music
                pygame.mixer.music.pause()
                self._is_playing = False
                self._is_paused = True
                self._pause_time = time.time()
                logger.info("🔊 WM8960: Playback paused")
                return True
            return False

    @handle_errors("resume_sync")
    def resume_sync(self) -> bool:
        """Resume paused playback using pygame.mixer.music.unpause().

        Returns:
            bool: True if resumed successfully, False otherwise
        """
        if not self._is_paused:
            return False

        with self._state_lock:
            if PYGAME_AVAILABLE and pygame.mixer.get_init():
                # Proper unpause with pygame.mixer.music
                pygame.mixer.music.unpause()
                self._is_playing = True
                self._is_paused = False
                # Adjust play start time to account for pause duration
                if self._pause_time and self._play_start_time:
                    pause_duration = time.time() - self._pause_time
                    self._play_start_time += pause_duration
                self._pause_time = None
                logger.info("🔊 WM8960: Playback resumed")
                return True
            return False

    @handle_errors("get_position_sync")
    def get_position_sync(self) -> float:
        """Get current playback position in seconds.

        Returns:
            float: Current position in seconds
        """
        with self._state_lock:
            if not self._play_start_time:
                return 0.0
            if self._is_paused and self._pause_time:
                # If paused, return position at pause time
                position = self._pause_time - self._play_start_time
            elif self._is_playing:
                # If playing, return current elapsed time
                position = time.time() - self._play_start_time
            else:
                return 0.0
            # Validate position - should not be negative or extremely large
            if position < 0:
                logger.warning(f"🔊 WM8960: Negative position detected ({position:.2f}s), resetting to 0",
                               )
                return 0.0
            if position > 7200:  # More than 2 hours is suspicious
                logger.warning(f"🔊 WM8960: Suspiciously large position ({position:.2f}s), might indicate timing issue",
                               )
            return cast(float, position)

    @handle_errors("set_position")
    def set_position(self, position: float) -> bool:
        """Set playback position (seek functionality).

        Args:
            position: Position in seconds to seek to

        Returns:
            bool: True if position was set successfully, False otherwise

        Note: pygame.mixer.music doesn't support direct seeking, so we restart
        playback from the beginning and use pygame.mixer.music.set_pos() if available.
        """
        if not self._current_file_path:
            return False

        with self._state_lock:
            if PYGAME_AVAILABLE and pygame.mixer.get_init():
                was_playing = self._is_playing
                was_paused = self._is_paused
                # Stop current playback
                pygame.mixer.music.stop()
                # Reload and start playback
                pygame.mixer.music.load(self._current_file_path)
                # Try to use pygame's set_pos if available (pygame 2.0+)
                seek_success = False
                try:
                    # Test if pygame supports the start parameter first
                    import inspect

                    play_sig = inspect.signature(pygame.mixer.music.play)
                    has_start_param = "start" in play_sig.parameters
                    if has_start_param:
                        # Try to use the start parameter
                        pygame.mixer.music.play(start=position)
                        # Assume seeking worked for now - pygame doesn't give us feedback
                        seek_success = True
                        logger.info(f"🔊 WM8960: Attempted seek to {position:.1f}s using play(start=)",
                                    )
                    else:
                        # No start parameter available
                        pygame.mixer.music.play()
                        seek_success = False
                        logger.warning("🔊 WM8960: pygame.mixer.music.play() doesn't support start parameter",
                                       )
                except Exception as e:
                    # Fallback to simple play without seeking
                    pygame.mixer.music.play()
                    seek_success = False
                    logger.warning(f"🔊 WM8960: Seek failed, playing from start: {e}")

                return seek_success
            return False

    @handle_errors("set_volume_sync")
    def set_volume_sync(self, volume: int) -> bool:
        """Set playback volume through pygame and ALSA.

        Args:
            volume: Volume level (0-100)

        Returns:
            bool: True if volume was set successfully, False otherwise
        """
        with self._state_lock:
            self._volume = max(0, min(100, volume))
            logger.info(f"🔊 WM8960: set_volume_sync called with volume={self._volume}")

            # Check pygame availability
            if not PYGAME_AVAILABLE:
                logger.error("🔊 WM8960: pygame not available, cannot set volume")
                return False

            mixer_init = pygame.mixer.get_init()
            logger.info(f"🔊 WM8960: pygame.mixer.get_init() = {mixer_init}")

            # Set pygame volume (0.0 to 1.0)
            if mixer_init:
                pygame_volume = self._volume / 100.0
                pygame.mixer.music.set_volume(pygame_volume)
                actual_volume = pygame.mixer.music.get_volume()
                logger.info(f"🔊 WM8960: pygame volume set to {pygame_volume:.2f}, actual={actual_volume:.2f}")

                # Try to set system volume via ALSA (optional - pygame is the primary control)
                try:
                    volume_percent = f"{self._volume}%"
                    # Hardcoded amixer command for volume control, not user input
                    subprocess.run(  # nosec B603 B607
                        ["amixer", "sset", "Master", volume_percent],
                        check=True,
                        capture_output=True,
                        timeout=1.0  # Don't hang if amixer is slow
                    )
                    logger.info(f"🔊 WM8960: ALSA volume set to {self._volume}%")
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
                    # ALSA control failed - this is OK, pygame volume is still set
                    logger.info(f"🔊 WM8960: ALSA volume control unavailable (using pygame only): {e}")

                return True
            logger.error("🔊 WM8960: pygame.mixer not initialized, cannot set volume")
            return False

    @property
    def is_paused(self) -> bool:
        """Check if audio is currently paused.

        Returns:
            bool: True if paused, False otherwise
        """
        return getattr(self, "_is_paused", False)

    @property
    def is_playing(self) -> bool:
        """Check if audio is currently playing.

        Returns:
            bool: True if playing, False otherwise
        """
        with self._state_lock:
            # Check pygame.mixer.music playback status
            if PYGAME_AVAILABLE and self._is_playing and not self._is_paused:
                if not pygame.mixer.music.get_busy():
                    # pygame music finished
                    self._is_playing = False
                    self._is_paused = False
                    self._play_start_time = None
                    logger.debug("🔊 WM8960: pygame track finished")

            return self._is_playing

    @property
    def is_busy(self) -> bool:
        """Check if the backend is busy.

        This is used by PlaylistController to detect when a track has finished playing.

        Returns:
            bool: True if backend is busy, False if idle/finished
        """
        with self._state_lock:
            # Check if pygame.mixer.music is still playing
            if PYGAME_AVAILABLE and self._is_playing and not self._is_paused:
                if not pygame.mixer.music.get_busy():
                    # Track finished
                    self._is_playing = False
                    self._is_paused = False
                    self._play_start_time = None
                    logger.debug("🔊 WM8960: Track ended, backend no longer busy")
                    return False

            return self._is_playing

    # Async methods required by AudioBackendProtocol
    async def pause(self) -> bool:  # type: ignore[override]
        """Async wrapper for pause method.

        Returns:
            bool: True if pause was successful
        """
        return cast(bool, self.pause_sync())

    async def resume(self) -> bool:  # type: ignore[override]
        """Async wrapper for resume method.

        Returns:
            bool: True if resume was successful
        """
        return cast(bool, self.resume_sync())

    async def stop(self) -> bool:  # type: ignore[override]
        """Async wrapper for stop method.

        Returns:
            bool: True if stop was successful
        """
        return cast(bool, self.stop_sync())

    async def set_volume(self, volume: int) -> bool:
        """Async wrapper for set_volume method.

        Args:
            volume: Volume level (0-100)

        Returns:
            bool: True if volume was set successfully
        """
        return cast(bool, self.set_volume_sync(volume))

    async def get_position(self) -> int | None:  # type: ignore[override]
        """Get current playback position.

        Returns:
            int: Current position in milliseconds or None if not playing
        """
        position_s = self.get_position_sync()
        if position_s > 0:
            return int(position_s * 1000)
        return None

    async def play(self, file_path: str) -> bool:
        """Async wrapper for play_file method.

        Args:
            file_path: Path to the audio file to play

        Returns:
            bool: True if playback started successfully
        """
        return await asyncio.get_running_loop().run_in_executor(None, self.play_file, file_path)

    async def get_volume(self) -> int:
        """Get current volume level.

        Returns:
            int: Current volume (0-100)
        """
        return self._volume

    async def seek(self, position_ms: int) -> bool:
        """Seek to a specific position.

        Args:
            position_ms: Position in milliseconds

        Returns:
            bool: True if seek was successful
        """
        position_s = position_ms / 1000.0
        return cast(bool, self.set_position(position_s))

    def get_duration(self) -> float:
        """Get duration of current track in seconds (for unified_audio_player compatibility).

        Returns:
            float: Duration in seconds or 0.0 if not available
        """
        if self._current_file_duration and self._current_file_duration > 0:
            logger.debug(f"🔊 WM8960: Returning duration: {self._current_file_duration:.1f}s")
            return cast(float, self._current_file_duration)
        return 0.0

    async def get_duration_ms(self) -> int | None:
        """Get duration of current track in milliseconds (for async operations).

        Returns:
            int: Duration in milliseconds or None if not available
        """
        if self._current_file_duration and self._current_file_duration > 0:
            duration_ms = int(self._current_file_duration * 1000)
            logger.debug(f"🔊 WM8960: Returning duration: {duration_ms}ms ({self._current_file_duration:.1f}s)")
            return duration_ms
        return None

    def _detect_file_duration(self, file_path: str) -> float | None:
        """Detect duration of audio file using mutagen.

        Args:
            file_path: Path to audio file

        Returns:
            float: Duration in seconds or None if detection fails
        """
        try:
            # Try to use mutagen to get file duration
            from mutagen import File
            audio_file = File(file_path)
            if audio_file and hasattr(audio_file, 'info') and hasattr(audio_file.info, 'length'):
                duration = float(audio_file.info.length)
                logger.info(f"🔊 WM8960: Detected file duration: {duration:.1f}s for {file_path}")
                return duration
        except ImportError:
            logger.warning("🔊 WM8960: mutagen not available for duration detection")
        except Exception as e:
            logger.debug(f"🔊 WM8960: Could not detect duration for {file_path}: {e}")

        return None

    @handle_errors("cleanup")
    def cleanup(self) -> None:
        """Clean up audio resources."""
        logger.info("🔊 Cleaning up WM8960 audio backend")
        with self._state_lock:
            self._stop_current_playback()

        # Clean up jack detection (note: async cleanup is handled by the service owner)
        if self._jack_detection is not None:
            self._jack_detection.set_state_change_handler(lambda _: None)  # Remove callback
            logger.debug("🔊 WM8960: Jack detection callback removed")

        # Clean up any SDL environment variables we might have set
        if 'SDL_AUDIODRIVER' in os.environ:
            del os.environ['SDL_AUDIODRIVER']
            logger.debug("🔊 WM8960: Cleared SDL_AUDIODRIVER environment variable")
        if 'SDL_AUDIODEV' in os.environ:
            del os.environ['SDL_AUDIODEV']
            logger.debug("🔊 WM8960: Cleared SDL_AUDIODEV environment variable")

        logger.info("🔊 WM8960 audio backend cleanup completed")

    @handle_errors("_stop_current_playback")
    def _stop_current_playback(self) -> None:
        """Stop the current pygame.mixer.music playback."""
        # Stop pygame.mixer.music if active
        if PYGAME_AVAILABLE and pygame.mixer.get_init():
            pygame.mixer.music.stop()
            logger.debug("🔊 WM8960: Stopped pygame.mixer.music playback")
        self._is_playing = False
        self._is_paused = False
        self._play_start_time = None
        self._pause_time = None
        self._current_file_path = None
        self._current_file_duration = None
