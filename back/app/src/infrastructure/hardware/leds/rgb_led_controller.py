# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
RGB LED Controller (Infrastructure Layer).

Real hardware implementation using gpiozero PWMLED for RGB LED control.
"""

import os
import asyncio
import math
from threading import Thread, Event, Lock
from typing import Optional, Dict, Any
import logging

from app.src.domain.protocols.indicator_lights_protocol import IndicatorLightsProtocol
from app.src.domain.models.led import LEDColor, LEDAnimation, LEDColors

logger = logging.getLogger(__name__)

# Check if we're in mock mode or if GPIO is available
USE_MOCK_HARDWARE = os.getenv("USE_MOCK_HARDWARE", "false").lower() == "true"
GPIO_AVAILABLE = False

if not USE_MOCK_HARDWARE:
    try:
        from gpiozero import PWMLED, Device
        from gpiozero.pins.rpigpio import RPiGPIOFactory
        Device.pin_factory = RPiGPIOFactory()
        GPIO_AVAILABLE = True
        logger.info("✅ GPIO hardware available for RGB LED - using RPi.GPIO backend")
    except ImportError as e:
        logger.debug(f"RPi.GPIO backend not available: {e}")
        # Try lgpio
        try:
            from gpiozero import PWMLED, Device
            from gpiozero.pins.lgpio import LgpioFactory
            Device.pin_factory = LgpioFactory()
            GPIO_AVAILABLE = True
            logger.info("✅ GPIO hardware available for RGB LED - using lgpio backend")
        except ImportError:
            logger.warning("⚠️ No GPIO backend available - falling back to mock mode")
            GPIO_AVAILABLE = False
    except Exception as e:
        logger.warning(f"⚠️ GPIO initialization failed: {e}")
        GPIO_AVAILABLE = False
else:
    logger.info("🧪 Mock hardware mode enabled for RGB LED")
    GPIO_AVAILABLE = False


class RGBLEDController(IndicatorLightsProtocol):
    """
    RGB LED controller using PWM for color mixing.

    Controls an RGB LED (like SMD5050) using three GPIO pins with PWM.
    Supports animations through a background thread.
    """

    def __init__(
        self,
        red_pin: int,
        green_pin: int,
        blue_pin: int,
        pwm_frequency: int = 1000,
        default_brightness: float = 1.0
    ):
        """
        Initialize RGB LED controller.

        Args:
            red_pin: GPIO pin for red channel (BCM numbering)
            green_pin: GPIO pin for green channel (BCM numbering)
            blue_pin: GPIO pin for blue channel (BCM numbering)
            pwm_frequency: PWM frequency in Hz (default: 1000)
            default_brightness: Initial brightness (0.0-1.0)
        """
        self._red_pin = red_pin
        self._green_pin = green_pin
        self._blue_pin = blue_pin
        self._pwm_frequency = pwm_frequency
        self._brightness = default_brightness

        self._is_initialized = False
        self._lock = Lock()

        # GPIO devices
        self._red_led: Optional['PWMLED'] = None
        self._green_led: Optional['PWMLED'] = None
        self._blue_led: Optional['PWMLED'] = None

        # Animation control
        self._animation_thread: Optional[Thread] = None
        self._animation_stop_event = Event()
        self._current_color = LEDColors.OFF
        self._current_animation = LEDAnimation.SOLID
        self._animation_speed = 1.0

    async def initialize(self) -> bool:
        """Initialize PWM LED hardware."""
        try:
            with self._lock:
                if self._is_initialized:
                    logger.warning("RGB LED already initialized")
                    return True

                if not GPIO_AVAILABLE:
                    logger.info("🧪 Mock mode: RGB LED initialized (no real hardware)")
                    self._is_initialized = True
                    return True

                logger.info(f"🔌 Initializing RGB LED on GPIO R:{self._red_pin} G:{self._green_pin} B:{self._blue_pin}")

                # Clean up any existing GPIO state
                try:
                    import RPi.GPIO as GPIO_Direct
                    GPIO_Direct.setmode(GPIO_Direct.BCM)
                    GPIO_Direct.setwarnings(False)
                    for pin in [self._red_pin, self._green_pin, self._blue_pin]:
                        try:
                            GPIO_Direct.cleanup(pin)
                        except:
                            pass
                    logger.debug("GPIO pins cleaned before LED initialization")
                except Exception as e:
                    logger.debug(f"GPIO cleanup attempt: {e}")

                # Initialize PWM LEDs
                from gpiozero import PWMLED
                self._red_led = PWMLED(self._red_pin, frequency=self._pwm_frequency)
                self._green_led = PWMLED(self._green_pin, frequency=self._pwm_frequency)
                self._blue_led = PWMLED(self._blue_pin, frequency=self._pwm_frequency)

                # Initialize to off
                await self.turn_off()

                self._is_initialized = True
                logger.info(f"✅ RGB LED initialized successfully")
                return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize RGB LED: {e}")
            return False

    async def cleanup(self) -> None:
        """Clean up LED resources."""
        try:
            with self._lock:
                if not self._is_initialized:
                    return

                logger.info("🧹 Cleaning up RGB LED...")

                # Stop any running animation
                self.stop_animation()

                # Turn off LED directly (don't use await inside lock)
                if self._red_led:
                    self._red_led.value = 0
                    self._green_led.value = 0
                    self._blue_led.value = 0

                # Close GPIO devices
                if GPIO_AVAILABLE and self._red_led:
                    self._red_led.close()
                    self._green_led.close()
                    self._blue_led.close()

                self._red_led = None
                self._green_led = None
                self._blue_led = None
                self._is_initialized = False

                logger.info("✅ RGB LED cleanup completed")

        except Exception as e:
            logger.error(f"❌ Error during RGB LED cleanup: {e}")

    async def set_color(self, color: LEDColor) -> bool:
        """Set LED to solid color."""
        if not self._is_initialized:
            logger.warning("RGB LED not initialized")
            return False

        try:
            # Stop any running animation first
            self.stop_animation()

            with self._lock:
                self._current_color = color
                self._current_animation = LEDAnimation.SOLID

                if GPIO_AVAILABLE:
                    # Apply brightness scaling
                    scaled = color.scaled(self._brightness)

                    # Set PWM values (0.0-1.0)
                    self._red_led.value = scaled.red / 255.0
                    self._green_led.value = scaled.green / 255.0
                    self._blue_led.value = scaled.blue / 255.0

                logger.debug(f"LED color set to RGB({color.red}, {color.green}, {color.blue})")
                return True

        except Exception as e:
            logger.error(f"❌ Error setting LED color: {e}")
            return False

    async def set_animation(
        self,
        color: LEDColor,
        animation: LEDAnimation,
        speed: float = 1.0
    ) -> bool:
        """Set LED with animation."""
        if not self._is_initialized:
            logger.warning("RGB LED not initialized")
            return False

        try:
            # Stop any existing animation
            self.stop_animation()

            with self._lock:
                self._current_color = color
                self._current_animation = animation
                self._animation_speed = speed

            # For SOLID animation, just set the color
            if animation == LEDAnimation.SOLID:
                return await self.set_color(color)

            # Start animation thread for other animations
            self._animation_stop_event.clear()
            self._animation_thread = Thread(
                target=self._run_animation,
                args=(color, animation, speed),
                daemon=True
            )
            self._animation_thread.start()

            logger.debug(f"LED animation started: {animation.value} at speed {speed}x")
            return True

        except Exception as e:
            logger.error(f"❌ Error setting LED animation: {e}")
            return False

    def _run_animation(self, color: LEDColor, animation: LEDAnimation, speed: float):
        """Run animation in background thread."""
        try:
            if animation == LEDAnimation.PULSE:
                self._animate_pulse(color, speed)
            elif animation == LEDAnimation.BLINK_SLOW:
                self._animate_blink(color, 1.0, speed)  # 1Hz
            elif animation == LEDAnimation.BLINK_FAST:
                self._animate_blink(color, 3.0, speed)  # 3Hz
            elif animation == LEDAnimation.FLASH:
                self._animate_flash(color, speed)
            elif animation == LEDAnimation.DOUBLE_BLINK:
                self._animate_double_blink(color, speed)

        except Exception as e:
            logger.error(f"❌ Error in animation thread: {e}")

    def _animate_pulse(self, color: LEDColor, speed: float):
        """Smooth breathing/pulsing effect."""
        step_duration = 0.02 / speed  # 20ms steps adjusted by speed
        steps = int(1.0 / step_duration)  # One full cycle

        while not self._animation_stop_event.is_set():
            # Fade in
            for i in range(steps):
                if self._animation_stop_event.is_set():
                    return

                # Smooth sine wave
                brightness = (math.sin((i / steps) * math.pi * 2 - math.pi / 2) + 1) / 2
                brightness *= self._brightness

                if GPIO_AVAILABLE:
                    scaled = color.scaled(brightness)
                    self._red_led.value = scaled.red / 255.0
                    self._green_led.value = scaled.green / 255.0
                    self._blue_led.value = scaled.blue / 255.0

                self._animation_stop_event.wait(step_duration)

    def _animate_blink(self, color: LEDColor, frequency: float, speed: float):
        """Blinking on/off effect."""
        period = (1.0 / frequency) / speed  # Total period adjusted by speed
        on_time = period * 0.5  # 50% duty cycle

        while not self._animation_stop_event.is_set():
            # Turn on
            if GPIO_AVAILABLE:
                scaled = color.scaled(self._brightness)
                self._red_led.value = scaled.red / 255.0
                self._green_led.value = scaled.green / 255.0
                self._blue_led.value = scaled.blue / 255.0

            if self._animation_stop_event.wait(on_time):
                return

            # Turn off
            if GPIO_AVAILABLE:
                self._red_led.value = 0
                self._green_led.value = 0
                self._blue_led.value = 0

            if self._animation_stop_event.wait(on_time):
                return

    def _animate_flash(self, color: LEDColor, speed: float):
        """Single quick flash then off."""
        flash_duration = 0.2 / speed  # 200ms flash adjusted by speed

        # Flash on
        if GPIO_AVAILABLE:
            scaled = color.scaled(self._brightness)
            self._red_led.value = scaled.red / 255.0
            self._green_led.value = scaled.green / 255.0
            self._blue_led.value = scaled.blue / 255.0

        self._animation_stop_event.wait(flash_duration)

        # Turn off
        if GPIO_AVAILABLE:
            self._red_led.value = 0
            self._green_led.value = 0
            self._blue_led.value = 0

    def _animate_double_blink(self, color: LEDColor, speed: float):
        """
        Double blink effect: two quick blinks then pause.

        Pattern: ON (100ms) → OFF (100ms) → ON (100ms) → OFF (100ms) → PAUSE (600ms)
        Total cycle: 1000ms = 1 second
        """
        # Adjust timings by speed multiplier
        blink_duration = 0.1 / speed  # 100ms blink
        pause_duration = 0.6 / speed  # 600ms pause

        while not self._animation_stop_event.is_set():
            # First blink
            # Turn on
            if GPIO_AVAILABLE:
                scaled = color.scaled(self._brightness)
                self._red_led.value = scaled.red / 255.0
                self._green_led.value = scaled.green / 255.0
                self._blue_led.value = scaled.blue / 255.0

            if self._animation_stop_event.wait(blink_duration):
                return

            # Turn off
            if GPIO_AVAILABLE:
                self._red_led.value = 0
                self._green_led.value = 0
                self._blue_led.value = 0

            if self._animation_stop_event.wait(blink_duration):
                return

            # Second blink
            # Turn on
            if GPIO_AVAILABLE:
                scaled = color.scaled(self._brightness)
                self._red_led.value = scaled.red / 255.0
                self._green_led.value = scaled.green / 255.0
                self._blue_led.value = scaled.blue / 255.0

            if self._animation_stop_event.wait(blink_duration):
                return

            # Turn off
            if GPIO_AVAILABLE:
                self._red_led.value = 0
                self._green_led.value = 0
                self._blue_led.value = 0

            # Pause before repeating
            if self._animation_stop_event.wait(pause_duration):
                return

    def stop_animation(self) -> None:
        """Stop any running animation."""
        if self._animation_thread and self._animation_thread.is_alive():
            self._animation_stop_event.set()
            self._animation_thread.join(timeout=1.0)
            self._animation_thread = None

    async def turn_off(self) -> bool:
        """Turn off LED completely."""
        return await self.set_color(LEDColors.OFF)

    async def set_brightness(self, brightness: float) -> bool:
        """Set global brightness level."""
        if not 0.0 <= brightness <= 1.0:
            logger.warning(f"Invalid brightness {brightness}, must be 0.0-1.0")
            return False

        with self._lock:
            self._brightness = brightness

        # Reapply current color with new brightness
        if self._current_animation == LEDAnimation.SOLID:
            return await self.set_color(self._current_color)

        logger.debug(f"LED brightness set to {brightness:.1%}")
        return True

    def is_initialized(self) -> bool:
        """Check if LED is initialized."""
        return self._is_initialized

    def get_status(self) -> Dict[str, Any]:
        """Get current LED status."""
        return {
            "initialized": self._is_initialized,
            "gpio_available": GPIO_AVAILABLE,
            "current_color": self._current_color.to_tuple() if self._current_color else (0, 0, 0),
            "current_animation": self._current_animation.value if self._current_animation else "none",
            "brightness": self._brightness,
            "animation_running": self._animation_thread is not None and self._animation_thread.is_alive(),
            "gpio_pins": {
                "red": self._red_pin,
                "green": self._green_pin,
                "blue": self._blue_pin,
            } if self._is_initialized else {}
        }
