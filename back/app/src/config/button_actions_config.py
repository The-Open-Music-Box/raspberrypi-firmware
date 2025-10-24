# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Button Actions Configuration.

Defines the mapping between physical buttons and their assigned actions.
This allows flexible configuration of button behavior without changing code.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ButtonActionConfig:
    """
    Configuration for a single button and its assigned action.

    Attributes:
        button_id: Logical button identifier (0-4)
        gpio_pin: Physical GPIO pin number (BCM numbering)
        action_name: Name of the action to execute (e.g., "play_pause", "volume_up")
        enabled: Whether this button is active
        description: Human-readable description of the button's purpose
    """
    button_id: int
    gpio_pin: int
    action_name: str
    enabled: bool = True
    description: Optional[str] = None

    def __post_init__(self):
        """Validate button configuration."""
        if not 0 <= self.button_id <= 4:
            raise ValueError(f"button_id must be between 0 and 4, got {self.button_id}")

        if not 0 <= self.gpio_pin <= 27:
            raise ValueError(f"gpio_pin must be between 0 and 27, got {self.gpio_pin}")

        if not self.action_name:
            raise ValueError("action_name cannot be empty")


# Default button configuration matching the requested GPIO assignments
DEFAULT_BUTTON_CONFIGS: List[ButtonActionConfig] = [
    ButtonActionConfig(
        button_id=0,
        gpio_pin=23,
        action_name="print_debug",
        description="Print debug information"
    ),
    ButtonActionConfig(
        button_id=1,
        gpio_pin=20,
        action_name="volume_down",
        description="Decrease volume"
    ),
    ButtonActionConfig(
        button_id=2,
        gpio_pin=16,
        action_name="previous_track",
        description="Go to previous track"
    ),
    ButtonActionConfig(
        button_id=3,
        gpio_pin=26,
        action_name="next_track",
        description="Skip to next track"
    ),
    ButtonActionConfig(
        button_id=4,
        gpio_pin=19,
        action_name="volume_up",
        description="Increase volume"
    ),
]


# Available action names for validation
AVAILABLE_ACTIONS = {
    "play",
    "pause",
    "play_pause",
    "next_track",
    "previous_track",
    "volume_up",
    "volume_down",
    "stop",
    "print_debug",
}


def validate_button_configs(configs: List[ButtonActionConfig]) -> List[str]:
    """
    Validate a list of button configurations.

    Args:
        configs: List of button configurations to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Check for duplicate button IDs
    button_ids = [c.button_id for c in configs]
    if len(button_ids) != len(set(button_ids)):
        errors.append("Duplicate button IDs detected")

    # Check for duplicate GPIO pins
    gpio_pins = [c.gpio_pin for c in configs if c.enabled]
    if len(gpio_pins) != len(set(gpio_pins)):
        errors.append("Duplicate GPIO pin assignments detected")

    # Check for invalid action names
    for config in configs:
        if config.action_name not in AVAILABLE_ACTIONS:
            errors.append(
                f"Unknown action '{config.action_name}' for button {config.button_id}. "
                f"Available actions: {', '.join(sorted(AVAILABLE_ACTIONS))}"
            )

    return errors


def get_button_config_by_id(button_id: int, configs: Optional[List[ButtonActionConfig]] = None) -> Optional[ButtonActionConfig]:
    """
    Get button configuration by button ID.

    Args:
        button_id: Button ID to look up
        configs: Optional list of configs (uses DEFAULT_BUTTON_CONFIGS if None)

    Returns:
        ButtonActionConfig if found, None otherwise
    """
    configs = configs or DEFAULT_BUTTON_CONFIGS
    for config in configs:
        if config.button_id == button_id and config.enabled:
            return config
    return None


def get_button_config_by_pin(gpio_pin: int, configs: Optional[List[ButtonActionConfig]] = None) -> Optional[ButtonActionConfig]:
    """
    Get button configuration by GPIO pin.

    Args:
        gpio_pin: GPIO pin number to look up
        configs: Optional list of configs (uses DEFAULT_BUTTON_CONFIGS if None)

    Returns:
        ButtonActionConfig if found, None otherwise
    """
    configs = configs or DEFAULT_BUTTON_CONFIGS
    for config in configs:
        if config.gpio_pin == gpio_pin and config.enabled:
            return config
    return None
