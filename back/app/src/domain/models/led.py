# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
LED Models (Domain Layer).

Defines LED states, colors, animations, and priorities for the indicator light system.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class LEDState(Enum):
    """
    LED states representing different system conditions.

    Each state has an associated default color, animation, and priority.
    """
    # Critical states
    ERROR_CRASH = "error_crash"                # Solid red - Priority 99 (app crash)
    ERROR_CRITICAL = "error_critical"          # Red blinking - Priority 100
    ERROR_BOOT_HARDWARE = "error_boot_hardware"  # Slow blink red - Priority 98 (boot error)
    ERROR_PLAYBACK = "error_playback"          # Orange blinking - Priority 90

    # NFC states (status vs events architecture)
    # STATUS: Persistent state during association session
    NFC_ASSOCIATION_MODE = "nfc_association_mode"  # Pulse blue - Priority 85 (status)
    # EVENTS: Temporary notifications that auto-revert to status
    NFC_SUCCESS = "nfc_success"                # Green flash - Priority 95 (event)
    NFC_ERROR = "nfc_error"                    # Red flash - Priority 95 (event)
    NFC_TAG_UNASSOCIATED = "nfc_tag_unassociated"  # Orange double blink - Priority 95 (event)

    # Playback states
    PLAYING = "playing"                        # Green solid - Priority 50
    PAUSED = "paused"                          # Yellow solid - Priority 40
    STOPPED = "stopped"                        # Off - Priority 35

    # System states
    STARTING = "starting"                      # White pulsing - Priority 30

    # Default state
    IDLE = "idle"                              # Solid white - Priority 10
    OFF = "off"                                # Off - Priority 0


class LEDAnimation(Enum):
    """Animation types for LED states."""
    SOLID = "solid"                 # Constant color
    PULSE = "pulse"                 # Smooth breathing effect
    BLINK_SLOW = "blink_slow"       # 1Hz blinking
    BLINK_FAST = "blink_fast"       # 3Hz blinking
    FLASH = "flash"                 # Single quick flash then off
    DOUBLE_BLINK = "double_blink"   # Two quick blinks, 100ms each, 100ms gap, 600ms pause


class LEDPriority(Enum):
    """
    Priority levels for LED states.

    Higher priority states override lower priority states.

    Architecture:
    - CRITICAL ERRORS (99-100): Permanent critical states
    - EVENTS (90-95): Temporary notifications that auto-revert to status
    - STATUS (10-85): Persistent states (IDLE, PLAYING, ASSOCIATION_MODE, etc.)
    """
    # Critical errors (permanent)
    CRITICAL = 100                  # System critical errors
    ERROR_CRASH = 99                # Application crash
    ERROR_BOOT = 98                 # Boot errors (missing hardware)

    # Events (temporary notifications with timeout)
    NFC_EVENT = 95                  # NFC scan events (success/warning/error) - auto-revert to status
    ERROR = 90                      # Playback errors

    # Status (persistent states)
    NFC_ASSOCIATION_MODE = 85       # NFC association mode status (persistent during session)
    PLAYBACK_ACTIVE = 50            # Playing state
    PLAYBACK_INACTIVE = 40          # Paused state
    PLAYBACK_STOPPED = 35           # Stopped state
    SYSTEM_STARTING = 30            # Startup
    IDLE = 10                       # Idle/ready
    OFF = 0                         # Disabled


@dataclass(frozen=True)
class LEDColor:
    """
    RGB color representation.

    Values are 0-255 for each channel.
    """
    red: int
    green: int
    blue: int

    def __post_init__(self):
        """Validate color values."""
        for component, value in [("red", self.red), ("green", self.green), ("blue", self.blue)]:
            if not 0 <= value <= 255:
                raise ValueError(f"{component} must be between 0 and 255, got {value}")

    def to_tuple(self) -> Tuple[int, int, int]:
        """Convert to RGB tuple."""
        return (self.red, self.green, self.blue)

    def scaled(self, brightness: float) -> 'LEDColor':
        """
        Scale color by brightness factor (0.0-1.0).

        Args:
            brightness: Scaling factor (0.0 = off, 1.0 = full)

        Returns:
            New LEDColor with scaled values
        """
        if not 0.0 <= brightness <= 1.0:
            raise ValueError(f"Brightness must be between 0.0 and 1.0, got {brightness}")

        return LEDColor(
            red=int(self.red * brightness),
            green=int(self.green * brightness),
            blue=int(self.blue * brightness)
        )

    @classmethod
    def from_hex(cls, hex_color: str) -> 'LEDColor':
        """
        Create color from hex string.

        Args:
            hex_color: Hex color string (e.g., "#FF0000" or "FF0000")

        Returns:
            LEDColor instance
        """
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            raise ValueError(f"Hex color must be 6 characters, got {len(hex_color)}")

        return cls(
            red=int(hex_color[0:2], 16),
            green=int(hex_color[2:4], 16),
            blue=int(hex_color[4:6], 16)
        )


# Predefined colors
class LEDColors:
    """Common LED colors."""
    OFF = LEDColor(0, 0, 0)

    # Primary colors
    RED = LEDColor(255, 0, 0)
    GREEN = LEDColor(0, 255, 0)
    BLUE = LEDColor(0, 0, 255)

    # Secondary colors
    YELLOW = LEDColor(255, 255, 0)
    CYAN = LEDColor(0, 255, 255)
    MAGENTA = LEDColor(255, 0, 255)

    # Tertiary colors
    ORANGE = LEDColor(255, 128, 0)
    PURPLE = LEDColor(128, 0, 255)

    # White variations
    WHITE = LEDColor(255, 255, 255)
    WARM_WHITE = LEDColor(255, 200, 150)

    # Dimmed versions
    DIM_RED = LEDColor(50, 0, 0)
    DIM_GREEN = LEDColor(0, 50, 0)
    DIM_BLUE = LEDColor(0, 0, 50)


@dataclass
class LEDStateConfig:
    """
    Configuration for an LED state.

    Defines the visual representation and behavior of a state.
    """
    state: LEDState
    color: LEDColor
    animation: LEDAnimation
    priority: int
    timeout_seconds: Optional[float] = None  # None = permanent
    animation_speed: float = 1.0  # Speed multiplier for animations

    def __post_init__(self):
        """Validate configuration."""
        if self.priority < 0 or self.priority > 100:
            raise ValueError(f"Priority must be between 0 and 100, got {self.priority}")

        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError(f"Timeout must be positive, got {self.timeout_seconds}")

        if self.animation_speed <= 0:
            raise ValueError(f"Animation speed must be positive, got {self.animation_speed}")


# Default state configurations
DEFAULT_LED_STATE_CONFIGS = {
    # Critical error states
    LEDState.ERROR_CRITICAL: LEDStateConfig(
        state=LEDState.ERROR_CRITICAL,
        color=LEDColors.RED,
        animation=LEDAnimation.BLINK_FAST,
        priority=LEDPriority.CRITICAL.value,
        timeout_seconds=None  # Permanent until cleared
    ),
    LEDState.ERROR_CRASH: LEDStateConfig(
        state=LEDState.ERROR_CRASH,
        color=LEDColors.RED,
        animation=LEDAnimation.SOLID,
        priority=LEDPriority.ERROR_CRASH.value,
        timeout_seconds=None  # Permanent - requires manual intervention
    ),
    LEDState.ERROR_BOOT_HARDWARE: LEDStateConfig(
        state=LEDState.ERROR_BOOT_HARDWARE,
        color=LEDColors.RED,
        animation=LEDAnimation.BLINK_SLOW,
        priority=LEDPriority.ERROR_BOOT.value,
        timeout_seconds=None  # Permanent until hardware issue resolved
    ),
    LEDState.ERROR_PLAYBACK: LEDStateConfig(
        state=LEDState.ERROR_PLAYBACK,
        color=LEDColors.ORANGE,
        animation=LEDAnimation.BLINK_SLOW,
        priority=LEDPriority.ERROR.value,
        timeout_seconds=5.0  # Clear after 5 seconds
    ),
    # NFC states (status vs events architecture)
    # STATUS: NFC Association Mode (persistent state during session)
    LEDState.NFC_ASSOCIATION_MODE: LEDStateConfig(
        state=LEDState.NFC_ASSOCIATION_MODE,
        color=LEDColors.BLUE,
        animation=LEDAnimation.PULSE,
        priority=LEDPriority.NFC_ASSOCIATION_MODE.value,  # Priority 85 (status)
        timeout_seconds=None,  # Permanent until association session ends
        animation_speed=1.0
    ),
    # EVENTS: NFC Scan Results (temporary notifications with auto-revert)
    LEDState.NFC_SUCCESS: LEDStateConfig(
        state=LEDState.NFC_SUCCESS,
        color=LEDColors.GREEN,
        animation=LEDAnimation.FLASH,
        priority=LEDPriority.NFC_EVENT.value,  # Priority 95 (event) - overrides status
        timeout_seconds=0.5  # Quick flash then auto-revert to status
    ),
    LEDState.NFC_ERROR: LEDStateConfig(
        state=LEDState.NFC_ERROR,
        color=LEDColors.RED,
        animation=LEDAnimation.FLASH,
        priority=LEDPriority.NFC_EVENT.value,  # Priority 95 (event) - overrides status
        timeout_seconds=0.5  # Quick flash then auto-revert to status
    ),
    LEDState.NFC_TAG_UNASSOCIATED: LEDStateConfig(
        state=LEDState.NFC_TAG_UNASSOCIATED,
        color=LEDColors.ORANGE,
        animation=LEDAnimation.DOUBLE_BLINK,
        priority=LEDPriority.NFC_EVENT.value,  # Priority 95 (event) - overrides status
        timeout_seconds=1.0  # Double blink warning then auto-revert to status
    ),
    LEDState.PLAYING: LEDStateConfig(
        state=LEDState.PLAYING,
        color=LEDColors.GREEN,
        animation=LEDAnimation.SOLID,
        priority=LEDPriority.PLAYBACK_ACTIVE.value,
        timeout_seconds=None  # Permanent
    ),
    LEDState.PAUSED: LEDStateConfig(
        state=LEDState.PAUSED,
        color=LEDColors.YELLOW,
        animation=LEDAnimation.SOLID,
        priority=LEDPriority.PLAYBACK_INACTIVE.value,
        timeout_seconds=None  # Permanent
    ),
    LEDState.STOPPED: LEDStateConfig(
        state=LEDState.STOPPED,
        color=LEDColors.OFF,
        animation=LEDAnimation.SOLID,
        priority=LEDPriority.PLAYBACK_STOPPED.value,
        timeout_seconds=None  # Permanent
    ),
    LEDState.STARTING: LEDStateConfig(
        state=LEDState.STARTING,
        color=LEDColors.WHITE,
        animation=LEDAnimation.BLINK_SLOW,  # White blinking during startup
        priority=LEDPriority.SYSTEM_STARTING.value,
        timeout_seconds=None,  # Cleared by application when ready
        animation_speed=1.0
    ),
    LEDState.IDLE: LEDStateConfig(
        state=LEDState.IDLE,
        color=LEDColors.WHITE,  # Solid white when app is ready
        animation=LEDAnimation.SOLID,
        priority=LEDPriority.IDLE.value,
        timeout_seconds=None  # Permanent
    ),
    LEDState.OFF: LEDStateConfig(
        state=LEDState.OFF,
        color=LEDColors.OFF,
        animation=LEDAnimation.SOLID,
        priority=LEDPriority.OFF.value,
        timeout_seconds=None  # Permanent
    ),
}
