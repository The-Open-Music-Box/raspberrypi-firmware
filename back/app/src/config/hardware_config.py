# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Hardware configuration settings for TheOpenMusicBox.
"""

from dataclasses import dataclass


@dataclass
class HardwareConfig:
    """
    Configuration parameters for hardware components.

    This is the single source of truth for all hardware pin assignments and hardware-
    related settings.
    """

    # GPIO Pin Assignments (BCM numbering) - Updated to avoid SPI conflicts
    gpio_next_track_button: int = 16
    gpio_previous_track_button: int = 26
    gpio_volume_encoder_clk: int = 7
    gpio_volume_encoder_dt: int = 24
    gpio_volume_encoder_sw: int = 23
    # Button settings
    button_debounce_time: float = 0.3  # Debounce time in seconds
    button_hold_time: float = 2.0  # Time to register a long press

    # Rotary encoder settings
    encoder_step_threshold: int = 2  # Steps required to register a turn
    encoder_acceleration: bool = True  # Enable acceleration on fast turns

    # LED settings (if applicable)
    led_brightness: int = 100  # LED brightness (0-255)
    led_animation_speed: float = 0.5  # Animation speed in seconds

    # I2C settings
    i2c_bus: int = 1  # I2C bus number
    i2c_address_dac: int = 0x1A  # WM8960 DAC I2C address

    # SPI settings (for NFC if using SPI)
    spi_bus: int = 0  # SPI bus number
    spi_device: int = 0  # SPI device number
    spi_speed_hz: int = 1000000  # SPI speed in Hz

    # Audio settings - removed alsa_device as we now use dmix 'default' device

    # Hardware detection
    mock_hardware: bool = False  # Use mock hardware for testing
    auto_detect_hardware: bool = True  # Auto-detect hardware on startup

    def validate(self) -> None:
        """
        Validate hardware configuration values.
        """
        # Validate GPIO pins are in valid range (0-27 for most Pi models)
        gpio_pins = [
            self.gpio_next_track_button,
            self.gpio_previous_track_button,
            self.gpio_volume_encoder_clk,
            self.gpio_volume_encoder_dt,
            self.gpio_volume_encoder_sw,
        ]

        for pin in gpio_pins:
            if not 0 <= pin <= 27:
                raise ValueError(f"GPIO pin {pin} is out of valid range (0-27)")

        # Check for duplicate pin assignments
        if len(gpio_pins) != len(set(gpio_pins)):
            raise ValueError("Duplicate GPIO pin assignments detected")

        # Validate timing parameters
        if self.button_debounce_time < 0:
            raise ValueError("button_debounce_time must be positive")

        if self.button_hold_time < self.button_debounce_time:
            raise ValueError("button_hold_time must be greater than debounce_time")
