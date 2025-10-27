# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""WM8960 Audio Backend Implementation.

This module provides a clean WM8960 audio backend implementation for Raspberry Pi hardware.
It implements the AudioBackendProtocol interface and provides real hardware audio playback
through the WM8960 codec using pygame for reliable audio format handling.
"""

import os
import asyncio
import subprocess
import time
from pathlib import Path
from typing import Optional

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

try:
    import mutagen
    from mutagen import File as MutagenFile
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    mutagen = None
    MutagenFile = None

from app.src.config import config
from app.src.monitoring import get_logger
from app.src.domain.decorators.error_handler import handle_domain_errors as handle_errors
from app.src.domain.protocols.notification_protocol import PlaybackNotifierProtocol as PlaybackSubject

from .base_audio_backend import BaseAudioBackend

logger = get_logger(__name__)


class WM8960AudioBackend(BaseAudioBackend):
    """WM8960 audio backend for Raspberry Pi hardware.

    This implementation provides real audio playback through the WM8960 codec
    using ALSA and subprocess-based audio control.
    """

    def __init__(self, playback_subject: Optional[PlaybackSubject] = None):
        """Initialize the WM8960 audio backend."""
        super().__init__(playback_subject)
        self._is_paused = False
        self._play_start_time = None
        self._pause_time = None

        # Track current file and its duration
        self._current_file_path = None
        self._current_file_duration = None  # in seconds

        # Initialize hardware
        self._initialize_wm8960_hardware()

        # Initialize pygame mixer for proper audio handling
        self._pygame_initialized = False
        if PYGAME_AVAILABLE:
            # Simple default pygame initialization on startup
            self._pygame_initialized = self._init_pygame_simple()
            if not self._pygame_initialized:
                logger.error("🔊 WM8960: Failed to initialize pygame mixer - audio device is busy or unavailable")
                raise RuntimeError("WM8960 audio backend initialization failed: pygame mixer could not be initialized")
        else:
            logger.warning("🔊 WM8960: pygame not available - audio will not work")
            raise RuntimeError("WM8960 audio backend initialization failed: pygame not available")

        logger.info("🔊 WM8960 Audio Backend initialized successfully")

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

        logger.info(f"🔊 WM8960: pygame.mixer.pre_init called with freq=48000, size=-16, channels=2, buffer=2048")

        try:
            pygame.mixer.init()
            logger.info(f"🔊 WM8960: pygame.mixer.init() successful")
        except Exception as e:
            logger.error(f"🔊 WM8960: pygame.mixer.init() failed: {e}")
            return False

        # Verify initialization
        if pygame.mixer.get_init():
            init_info = pygame.mixer.get_init()
            logger.info(f"🔊 WM8960: pygame mixer initialized successfully with {init_info} (simple default)"
            )
            return True
        else:
            logger.error("🔊 WM8960: pygame mixer failed to initialize")
            return False

    @handle_errors("_detect_wm8960_device")
    def _detect_wm8960_device(self) -> str:
        """Detect WM8960 audio device automatically.

        Returns:
            str: ALSA device identifier for WM8960
        """
        try:
            # Try to get list of audio devices
            result = subprocess.run(["aplay", "-l"], capture_output=True, text=True)
        except FileNotFoundError:
            # aplay not found (e.g., on macOS), use default
            logger.info("🔊 WM8960: aplay not found, using default device")
            return "plughw:1,0"  # fallback when aplay not found
        if result.returncode == 0:
            output = result.stdout
            # Look for WM8960 card
            for line in output.split("\n"):
                if "wm8960" in line.lower():
                    # Extract card number for hw:X,0 format
                    if "card" in line.lower():
                        # Parse "card X: cardname" to get card number
                        parts = line.split("card")
                        if len(parts) >= 2:
                            card_part = parts[1].split(":")[0].strip()  # Get number part
                            if card_part.isdigit():
                                # Use plughw for better compatibility with different audio formats
                                device = f"plughw:{card_part},0"
                                logger.info(f"🔊 WM8960: Detected audio device: {device}"
                                )
                                return device
                            else:
                                # Fallback: try card name format
                                card_name = (
                                    parts[1].split(":")[1].strip().split()[0]
                                )  # Get card name
                                device = f"hw:{card_name},0"
                                logger.info(f"🔊 WM8960: Using card name format: {device}"
                                )
                                return device
            # Fallback: look for any card with wm8960 in name and extract number
            for line in output.split("\n"):
                if "wm8960soundcard" in line.lower():
                    # Try to extract card number from any line containing wm8960soundcard
                    if "card" in line:
                        card_num = line.split("card")[1].split(":")[0].strip()
                        if card_num.isdigit():
                            # Use plughw for better format compatibility
                            device = f"plughw:{card_num},0"
                            logger.info(f"🔊 WM8960: Fallback detected: {device}")
                            return device
        # Final fallback
        device = "plughw:0,0"
        logger.info(f"🔊 WM8960: Using fallback device: {device}")
        return device

    def _get_file_duration(self, file_path: str) -> Optional[float]:
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
                else:
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

    @handle_errors("play_file")
    def play_file(self, file_path: str, duration_ms: Optional[int] = None) -> bool:
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
            return self._play_with_pygame(str(path), duration_ms)

    @handle_errors("_play_with_pygame")
    def _play_with_pygame(self, file_path: str, duration_ms: Optional[int] = None) -> bool:
        """Play audio file using pygame.mixer.music (preferred method)."""
        logger.info(f"🔊 WM8960: Using pygame.mixer.music for playback of {file_path}")

        # Check pygame mixer state before loading
        mixer_init = pygame.mixer.get_init()
        logger.info(f"🔊 WM8960: pygame.mixer state before load: {mixer_init}")

        try:
            # Load and play the audio file with pygame.mixer.music
            logger.info(f"🔊 WM8960: Loading audio file: {file_path}")
            pygame.mixer.music.load(file_path)
            logger.info(f"🔊 WM8960: Audio file loaded successfully")

            logger.info(f"🔊 WM8960: Starting playback...")
            pygame.mixer.music.play()
            logger.info(f"🔊 WM8960: pygame.mixer.music.play() called")

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
            else:
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
            else:
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
            elif position > 7200:  # More than 2 hours is suspicious
                logger.warning(f"🔊 WM8960: Suspiciously large position ({position:.2f}s), might indicate timing issue",
                )
            return position

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
            # Set pygame volume (0.0 to 1.0)
            if PYGAME_AVAILABLE and pygame.mixer.get_init():
                pygame_volume = self._volume / 100.0
                pygame.mixer.music.set_volume(pygame_volume)
                logger.debug(f"🔊 WM8960: pygame volume set to {pygame_volume}")

                # Try to set system volume via ALSA (optional - pygame is the primary control)
                try:
                    volume_percent = f"{self._volume}%"
                    subprocess.run(
                        ["amixer", "sset", "Master", volume_percent],
                        check=True,
                        capture_output=True,
                        timeout=1.0  # Don't hang if amixer is slow
                    )
                    logger.debug(f"🔊 WM8960: ALSA volume set to {self._volume}%")
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
                    # ALSA control failed - this is OK, pygame volume is still set
                    logger.debug(f"🔊 WM8960: ALSA volume control unavailable (using pygame only): {e}")

                return True
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
    async def pause(self) -> bool:
        """Async wrapper for pause method.

        Returns:
            bool: True if pause was successful
        """
        return self.pause_sync()

    async def resume(self) -> bool:
        """Async wrapper for resume method.

        Returns:
            bool: True if resume was successful
        """
        return self.resume_sync()

    async def stop(self) -> bool:
        """Async wrapper for stop method.

        Returns:
            bool: True if stop was successful
        """
        return self.stop_sync()

    async def set_volume(self, volume: int) -> bool:
        """Async wrapper for set_volume method.

        Args:
            volume: Volume level (0-100)

        Returns:
            bool: True if volume was set successfully
        """
        return self.set_volume_sync(volume)

    async def get_position(self) -> Optional[int]:
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
        return self.set_position(position_s)

    def get_duration(self) -> float:
        """Get duration of current track in seconds (for unified_audio_player compatibility).

        Returns:
            float: Duration in seconds or 0.0 if not available
        """
        if self._current_file_duration and self._current_file_duration > 0:
            logger.debug(f"🔊 WM8960: Returning duration: {self._current_file_duration:.1f}s")
            return self._current_file_duration
        return 0.0

    async def get_duration_ms(self) -> Optional[int]:
        """Get duration of current track in milliseconds (for async operations).

        Returns:
            int: Duration in milliseconds or None if not available
        """
        if self._current_file_duration and self._current_file_duration > 0:
            duration_ms = int(self._current_file_duration * 1000)
            logger.debug(f"🔊 WM8960: Returning duration: {duration_ms}ms ({self._current_file_duration:.1f}s)")
            return duration_ms
        return None

    def _detect_file_duration(self, file_path: str) -> Optional[float]:
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
