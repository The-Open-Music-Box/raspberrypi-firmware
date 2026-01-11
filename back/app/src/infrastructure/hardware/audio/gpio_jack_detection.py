# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
GPIO Jack Detection Implementation.

Real hardware implementation using gpiozero for headphone jack detection.
Monitors the HP_DET GPIO pin from the WM8960 codec to detect
headphone plug/unplug events.
"""

import os
from typing import Any

from app.src.config.hardware_config import HardwareConfig
from app.src.domain.protocols.jack_detection_protocol import JackState
from app.src.monitoring import get_logger

from .base_jack_detection import BaseJackDetection

logger = get_logger(__name__)

# Check if GPIO is available
USE_MOCK_HARDWARE = os.getenv("USE_MOCK_HARDWARE", "false").lower() == "true"
GPIO_AVAILABLE = False
GPIO_FALLBACK_REASON: str | None = None

if not USE_MOCK_HARDWARE:
    gpio_backend_initialized = False

    # Try lgpio first (modern backend)
    try:
        from gpiozero import Button, Device
        from gpiozero.pins.lgpio import LGPIOFactory

        Device.pin_factory = LGPIOFactory()
        GPIO_AVAILABLE = True
        gpio_backend_initialized = True
        logger.debug("GPIO jack detection using lgpio backend")
    except ImportError:
        pass
    except Exception:
        pass

    # Try RPi.GPIO (legacy backend)
    if not gpio_backend_initialized:
        try:
            from gpiozero import Button, Device
            from gpiozero.pins.rpigpio import RPiGPIOFactory

            Device.pin_factory = RPiGPIOFactory()
            GPIO_AVAILABLE = True
            gpio_backend_initialized = True
            logger.debug("GPIO jack detection using RPi.GPIO backend")
        except ImportError:
            pass
        except Exception:
            pass

    # Try pigpio (requires pigpiod daemon)
    if not gpio_backend_initialized:
        try:
            from gpiozero import Button, Device
            from gpiozero.pins.pigpio import PiGPIOFactory

            Device.pin_factory = PiGPIOFactory()
            GPIO_AVAILABLE = True
            gpio_backend_initialized = True
            logger.debug("GPIO jack detection using pigpio backend")
        except ImportError:
            pass
        except Exception:
            pass

    if not gpio_backend_initialized:
        GPIO_FALLBACK_REASON = "No GPIO backend available for jack detection"
        logger.debug(f"GPIO not available for jack detection: {GPIO_FALLBACK_REASON}")
else:
    GPIO_FALLBACK_REASON = "USE_MOCK_HARDWARE=true"
    logger.debug("Mock hardware mode - GPIO jack detection disabled")


class GPIOJackDetection(BaseJackDetection):
    """GPIO-based headphone jack detection using WM8960 HP_DET signal.

    Monitors a GPIO pin connected to the HP_DET output of the WM8960 codec
    to detect when headphones are plugged or unplugged.
    """

    def __init__(self, hardware_config: HardwareConfig) -> None:
        """Initialize GPIO jack detection.

        Args:
            hardware_config: Hardware configuration containing GPIO settings.
        """
        super().__init__(enabled=hardware_config.headphone_detect_enabled)

        self._config = hardware_config
        self._gpio_pin = hardware_config.gpio_headphone_detect
        self._debounce_ms = hardware_config.headphone_detect_debounce_ms
        self._active_low = hardware_config.headphone_detect_active_low
        self._button: Any = None  # gpiozero Button instance

    async def initialize(self) -> bool:
        """Initialize GPIO jack detection hardware.

        Returns:
            True if initialization was successful.
        """
        if not self._enabled:
            logger.info("Jack detection disabled in configuration")
            self._initialized = True
            self._state = JackState.UNKNOWN
            return True

        if not GPIO_AVAILABLE:
            logger.warning(
                f"GPIO not available for jack detection: {GPIO_FALLBACK_REASON}. "
                "Jack detection will be disabled."
            )
            self._enabled = False
            self._initialized = True
            self._state = JackState.UNKNOWN
            return True  # Graceful degradation

        try:
            from gpiozero import Button

            # Configure GPIO pin as input with pull-up resistor
            # bounce_time is in seconds, convert from ms
            bounce_time = self._debounce_ms / 1000.0

            self._button = Button(
                self._gpio_pin,
                pull_up=True,
                bounce_time=bounce_time,
            )

            # Set up event handlers
            self._button.when_pressed = self._on_gpio_low
            self._button.when_released = self._on_gpio_high

            # Read initial state
            self._read_initial_state()

            self._initialized = True
            logger.info(
                f"GPIO jack detection initialized on GPIO {self._gpio_pin} "
                f"(active_low={self._active_low}, debounce={self._debounce_ms}ms)"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to initialize GPIO jack detection: {e}")
            self._enabled = False
            self._initialized = True
            self._state = JackState.UNKNOWN
            return True  # Graceful degradation

    def _read_initial_state(self) -> None:
        """Read and set the initial jack state from GPIO."""
        if self._button is None:
            return

        # Read current GPIO state
        is_pressed = self._button.is_pressed  # True if GPIO is LOW

        if self._active_low:
            # Active low: LOW = connected, HIGH = disconnected
            new_state = JackState.CONNECTED if is_pressed else JackState.DISCONNECTED
        else:
            # Active high: HIGH = connected, LOW = disconnected
            new_state = JackState.DISCONNECTED if is_pressed else JackState.CONNECTED

        self._state = new_state
        logger.info(f"Initial jack state: {new_state.value}")

    def _on_gpio_low(self) -> None:
        """Handle GPIO going LOW (button pressed in gpiozero terms)."""
        if self._active_low:
            # Active low: LOW = headphone connected
            self._update_state(JackState.CONNECTED)
        else:
            # Active high: LOW = headphone disconnected
            self._update_state(JackState.DISCONNECTED)

    def _on_gpio_high(self) -> None:
        """Handle GPIO going HIGH (button released in gpiozero terms)."""
        if self._active_low:
            # Active low: HIGH = headphone disconnected
            self._update_state(JackState.DISCONNECTED)
        else:
            # Active high: HIGH = headphone connected
            self._update_state(JackState.CONNECTED)

    async def cleanup(self) -> None:
        """Clean up GPIO resources."""
        if self._button is not None:
            try:
                self._button.close()
                logger.debug("GPIO jack detection cleaned up")
            except Exception as e:
                logger.warning(f"Error cleaning up GPIO jack detection: {e}")
            finally:
                self._button = None

        self._initialized = False
        self._state = JackState.UNKNOWN

    def get_status(self) -> dict:
        """Get current status of GPIO jack detection.

        Returns:
            Dictionary containing status information.
        """
        status = super().get_status()
        status.update({
            "gpio_pin": self._gpio_pin,
            "debounce_ms": self._debounce_ms,
            "active_low": self._active_low,
            "gpio_available": GPIO_AVAILABLE,
            "gpio_fallback_reason": GPIO_FALLBACK_REASON,
        })
        return status
