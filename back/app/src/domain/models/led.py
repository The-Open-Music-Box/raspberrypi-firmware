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
    ERROR_CRITICAL = "error_critical"          # Red blinking - Priority 100
    ERROR_PLAYBACK = "error_playback"          # Orange blinking - Priority 90

    # Temporary interactive states
    NFC_SCANNING = "nfc_scanning"              # Blue pulsing - Priority 80
    NFC_SUCCESS = "nfc_success"                # Green flash - Priority 75
    NFC_ERROR = "nfc_error"                    # Red flash - Priority 75

    # Playback states
    PLAYING = "playing"                        # Green solid - Priority 50
    PAUSED = "paused"                          # Yellow solid - Priority 40
    STOPPED = "stopped"                        # Off - Priority 35

    # System states
    STARTING = "starting"                      # White pulsing - Priority 30
    SHUTTING_DOWN = "shutting_down"            # Red pulsing - Priority 95

    # Default state
    IDLE = "idle"                              # Dim green - Priority 10
    OFF = "off"                                # Off - Priority 0


class LEDAnimation(Enum):
    """Animation types for LED states."""
    SOLID = "solid"                 # Constant color
    PULSE = "pulse"                 # Smooth breathing effect
    BLINK_SLOW = "blink_slow"       # 1Hz blinking
    BLINK_FAST = "blink_fast"       # 3Hz blinking
    FLASH = "flash"                 # Single quick flash then off


class LEDPriority(Enum):
    """
    Priority levels for LED states.

    Higher priority states override lower priority states.
    """
    CRITICAL = 100          # System critical errors
    SHUTDOWN = 95           # System shutdown
    ERROR = 90              # Playback errors
    NFC_INTERACTION = 80    # NFC scanning/interaction
    NFC_RESULT = 75         # NFC scan results
    PLAYBACK_ACTIVE = 50    # Playing state
    PLAYBACK_INACTIVE = 40  # Paused state
    PLAYBACK_STOPPED = 35   # Stopped state
    SYSTEM_STARTING = 30    # Startup
    IDLE = 10               # Idle/ready
    OFF = 0                 # Disabled


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
    LEDState.ERROR_CRITICAL: LEDStateConfig(
        state=LEDState.ERROR_CRITICAL,
        color=LEDColors.RED,
        animation=LEDAnimation.BLINK_FAST,
        priority=LEDPriority.CRITICAL.value,
        timeout_seconds=None  # Permanent until cleared
    ),
    LEDState.ERROR_PLAYBACK: LEDStateConfig(
        state=LEDState.ERROR_PLAYBACK,
        color=LEDColors.ORANGE,
        animation=LEDAnimation.BLINK_SLOW,
        priority=LEDPriority.ERROR.value,
        timeout_seconds=5.0  # Clear after 5 seconds
    ),
    LEDState.NFC_SCANNING: LEDStateConfig(
        state=LEDState.NFC_SCANNING,
        color=LEDColors.BLUE,
        animation=LEDAnimation.PULSE,
        priority=LEDPriority.NFC_INTERACTION.value,
        timeout_seconds=3.0,  # Clear after 3 seconds
        animation_speed=1.5
    ),
    LEDState.NFC_SUCCESS: LEDStateConfig(
        state=LEDState.NFC_SUCCESS,
        color=LEDColors.GREEN,
        animation=LEDAnimation.FLASH,
        priority=LEDPriority.NFC_RESULT.value,
        timeout_seconds=0.5  # Quick flash
    ),
    LEDState.NFC_ERROR: LEDStateConfig(
        state=LEDState.NFC_ERROR,
        color=LEDColors.RED,
        animation=LEDAnimation.FLASH,
        priority=LEDPriority.NFC_RESULT.value,
        timeout_seconds=0.5  # Quick flash
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
        animation=LEDAnimation.PULSE,
        priority=LEDPriority.SYSTEM_STARTING.value,
        timeout_seconds=None,  # Cleared by application when ready
        animation_speed=0.8
    ),
    LEDState.SHUTTING_DOWN: LEDStateConfig(
        state=LEDState.SHUTTING_DOWN,
        color=LEDColors.RED,
        animation=LEDAnimation.PULSE,
        priority=LEDPriority.SHUTDOWN.value,
        timeout_seconds=None,
        animation_speed=0.5
    ),
    LEDState.IDLE: LEDStateConfig(
        state=LEDState.IDLE,
        color=LEDColors.DIM_GREEN,
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
