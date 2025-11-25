# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
GPIO Physical Controls Implementation.

Real hardware implementation using gpiozero for buttons and rotary encoder.
"""

import os
from typing import Dict, Optional, List, Any
from datetime import datetime
from threading import Lock

from .base_controls_implementation import BaseControlsImplementation
from app.src.domain.protocols.physical_controls_protocol import PhysicalControlEvent
from app.src.domain.events.physical_control_events import (
    ButtonPressedEvent,
    EncoderRotatedEvent,
    PhysicalControlErrorEvent,
)
from app.src.config.button_actions_config import ButtonActionConfig

import logging

logger = logging.getLogger(__name__)

# Check if we're in mock mode or if GPIO is available
USE_MOCK_HARDWARE = os.getenv("USE_MOCK_HARDWARE", "false").lower() == "true"
GPIO_AVAILABLE = False
GPIO_FALLBACK_REASON: str | None = None  # Track why GPIO is not available

if not USE_MOCK_HARDWARE:
    # Try different GPIO backends in order of preference
    # lgpio is tried first as it's more modern and doesn't have RPi.GPIO's edge detection locking issues
    gpio_backend_initialized = False

    # First try lgpio (modern, recommended backend)
    try:
        from gpiozero import Button, RotaryEncoder, Device  # noqa: F811
        from gpiozero.pins.lgpio import LGPIOFactory
        Device.pin_factory = LGPIOFactory()
        logger.info("✅ GPIO hardware available - using lgpio backend")
        GPIO_AVAILABLE = True
        gpio_backend_initialized = True
    except ImportError as e:
        logger.debug(f"lgpio backend not available: {e}")
    except Exception as e:
        logger.debug(f"lgpio initialization failed: {e}")

    # If lgpio didn't work, try RPi.GPIO (legacy backend)
    if not gpio_backend_initialized:
        try:
            from gpiozero import Button, RotaryEncoder, Device  # noqa: F811
            from gpiozero.pins.rpigpio import RPiGPIOFactory
            Device.pin_factory = RPiGPIOFactory()
            logger.info("✅ GPIO hardware available - using RPi.GPIO backend")
            GPIO_AVAILABLE = True
            gpio_backend_initialized = True
        except ImportError as e:
            logger.debug(f"RPi.GPIO backend not available: {e}")
        except Exception as e:
            logger.debug(f"RPi.GPIO initialization failed: {e}")

    # If neither worked, try pigpio (requires pigpiod daemon)
    if not gpio_backend_initialized:
        try:
            from gpiozero import Button, RotaryEncoder, Device  # noqa: F811
            from gpiozero.pins.pigpio import PiGPIOFactory
            Device.pin_factory = PiGPIOFactory()
            logger.info("✅ GPIO hardware available - using pigpio backend")
            GPIO_AVAILABLE = True
            gpio_backend_initialized = True
        except ImportError as e:
            logger.debug(f"pigpio backend not available: {e}")
        except Exception as e:
            logger.debug(f"pigpio initialization failed: {e}")

    # If still no backend available, fall back to mock
    if not gpio_backend_initialized:
        GPIO_FALLBACK_REASON = "No GPIO backend available (gpiozero, RPi.GPIO, lgpio, pigpio all failed)"
        logger.warning(
            f"⚠️ {GPIO_FALLBACK_REASON} - PHYSICAL BUTTONS WILL NOT WORK! "
            "Install GPIO libraries or set USE_MOCK_HARDWARE=true to suppress this warning."
        )
        GPIO_AVAILABLE = False
else:
    GPIO_FALLBACK_REASON = "USE_MOCK_HARDWARE=true (intentional)"
    logger.info("🧪 Mock hardware mode enabled (USE_MOCK_HARDWARE=true)")
    GPIO_AVAILABLE = False


class GPIOPhysicalControls(BaseControlsImplementation):
    """GPIO-based implementation of physical controls with configurable buttons.

    Inherits common controls functionality from BaseControlsImplementation.
    """

    def __init__(
        self,
        hardware_config: Any,
        button_configs: Optional[List[ButtonActionConfig]] = None
    ):
        """Initialize GPIO physical controls.

        Args:
            hardware_config: Hardware configuration with pin assignments
            button_configs: Optional list of button configurations
        """
        super().__init__(hardware_config, button_configs)

        # GPIO-specific state
        self._devices = {}
        self._lock = Lock()
        self._mock_mode_active = False  # Track if running in mock mode

        # Encoder state tracking
        self._encoder_last_position = 0

    async def initialize(self) -> bool:
        """Initialize GPIO devices."""
        try:
            with self._lock:
                if self._is_initialized:
                    logger.warning("GPIO controls already initialized")
                    return True

                # Validate hardware configuration
                self.config.validate()

                if not GPIO_AVAILABLE:
                    # Log at WARNING level if this is an unintentional fallback
                    if USE_MOCK_HARDWARE:
                        logger.info("🧪 Mock mode: GPIO controls initialized (USE_MOCK_HARDWARE=true)")
                    else:
                        logger.warning(
                            "⚠️ GPIO UNAVAILABLE - Physical controls running in mock mode! "
                            f"Reason: {GPIO_FALLBACK_REASON}. Buttons/encoder will NOT respond to input."
                        )
                    self._is_initialized = True
                    self._mock_mode_active = True
                    return True

                logger.info("🔌 Initializing GPIO physical controls...")

                # Aggressive GPIO cleanup before initialization
                # This helps recover from crashed processes that left GPIO in bad state
                try:
                    import RPi.GPIO as GPIO_Direct
                    GPIO_Direct.setwarnings(False)
                    logger.debug("🧹 Cleaning up all GPIO pins before initialization...")
                    GPIO_Direct.cleanup()  # Clean ALL pins
                    logger.debug("✅ GPIO cleanup completed")
                except Exception as e:
                    logger.debug(f"GPIO cleanup attempt (may be expected): {e}")

                # Count successful initializations
                initial_device_count = len(self._devices)

                # Initialize configurable buttons (don't fail if some buttons fail)
                try:
                    self._init_configurable_buttons()
                except Exception as e:
                    logger.warning(f"⚠️ Button initialization had errors: {e}")

                # Initialize encoder switch (play/pause button on encoder)
                try:
                    self._init_encoder_switch()
                except Exception as e:
                    logger.warning(f"⚠️ Encoder switch initialization failed: {e}")

                # Initialize rotary encoder (don't fail if encoder fails)
                try:
                    self._init_encoder()
                except Exception as e:
                    logger.warning(f"⚠️ Encoder initialization failed: {e}")

                # Check if at least some devices were initialized
                final_device_count = len(self._devices)
                if final_device_count > initial_device_count:
                    self._is_initialized = True
                    logger.info(
                        f"✅ GPIO physical controls partially initialized "
                        f"({final_device_count - initial_device_count} devices)"
                    )
                    return True
                else:
                    logger.warning("⚠️ No GPIO devices could be initialized")
                    return False

        except Exception as e:
            logger.error(f"❌ Failed to initialize GPIO controls: {e}")
            await self._emit_error_event(f"Initialization failed: {e}", "initialization", "gpio_controls")
            return False

    def _init_configurable_buttons(self) -> None:
        """Initialize configurable buttons based on button_configs."""
        if not GPIO_AVAILABLE:
            return

        # Clean up any existing GPIO state first
        try:
            import RPi.GPIO as GPIO_Direct
            GPIO_Direct.setmode(GPIO_Direct.BCM)
            GPIO_Direct.setwarnings(False)

            # Clean up the specific pins we'll use from button configs
            pins_to_use = [config.gpio_pin for config in self._button_configs if config.enabled]
            for pin in pins_to_use:
                try:
                    GPIO_Direct.cleanup(pin)
                except Exception:
                    pass  # Pin might not have been initialized

            logger.debug(f"GPIO pins cleaned before initialization: {pins_to_use}")
        except Exception as e:
            logger.debug(f"GPIO cleanup attempt: {e}")

        # Initialize each configured button
        for config in self._button_configs:
            if not config.enabled:
                logger.debug(f"Skipping disabled button {config.button_id}")
                continue

            device_name = f"button_{config.button_id}"
            pin = config.gpio_pin
            description = config.description or f"Button {config.button_id}"

            # Create handler that will trigger the appropriate event
            def make_handler(button_id):
                """Factory function to create button handler with proper closure."""
                def handler():
                    self._on_button_pressed(button_id)
                return handler

            try:
                # Try with pull_up=True (most common for buttons)
                self._devices[device_name] = Button(
                    pin,
                    pull_up=True,
                    bounce_time=self.config.button_debounce_time,
                    hold_time=self.config.button_hold_time
                )
                self._devices[device_name].when_pressed = make_handler(config.button_id)
                logger.info(
                    f"✅ {description} initialized on GPIO {pin} "
                    f"(button_id={config.button_id}, action={config.action_name})"
                )

            except Exception as e:
                logger.warning(f"⚠️ Failed to init {description} on GPIO {pin} with pull_up: {e}")

                # Try without pull_up if the pin might have external pull-up
                try:
                    self._devices[device_name] = Button(
                        pin,
                        pull_up=False,
                        bounce_time=self.config.button_debounce_time
                    )
                    self._devices[device_name].when_pressed = make_handler(config.button_id)
                    logger.info(f"✅ {description} initialized on GPIO {pin} (no pull_up)")

                except Exception as e2:
                    logger.error(f"❌ Failed to init {description} on GPIO {pin}: {e2}")
                    # Continue with other buttons even if one fails

    def _init_encoder_switch(self) -> None:
        """Initialize encoder switch button (play/pause)."""
        if not GPIO_AVAILABLE:
            return

        try:
            # Clean up encoder switch pin first
            try:
                import RPi.GPIO as GPIO_Direct
                GPIO_Direct.setmode(GPIO_Direct.BCM)
                GPIO_Direct.setwarnings(False)
                GPIO_Direct.cleanup(self.config.gpio_volume_encoder_sw)
            except Exception:
                pass

            # Initialize the encoder switch as a button
            self._devices['encoder_switch'] = Button(
                self.config.gpio_volume_encoder_sw,
                pull_up=True,
                bounce_time=self.config.button_debounce_time,
                hold_time=self.config.button_hold_time
            )

            # Set the play/pause handler
            self._devices['encoder_switch'].when_pressed = self._on_encoder_switch_pressed

            logger.info(
                f"✅ Encoder switch (Play/Pause) initialized on GPIO {self.config.gpio_volume_encoder_sw}"
            )

        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize encoder switch: {e}")
            logger.info("Play/Pause via encoder switch will not be available")
            # Don't raise - allow system to work without switch

    def _init_encoder(self) -> None:
        """Initialize rotary encoder for volume control."""
        if not GPIO_AVAILABLE:
            return

        try:
            # Clean up encoder pins first
            try:
                import RPi.GPIO as GPIO_Direct
                GPIO_Direct.setmode(GPIO_Direct.BCM)
                GPIO_Direct.setwarnings(False)
                GPIO_Direct.cleanup(self.config.gpio_volume_encoder_clk)
                GPIO_Direct.cleanup(self.config.gpio_volume_encoder_dt)
            except Exception:
                pass

            # Try to initialize the rotary encoder
            # NOTE: Using wrap=True and max_steps=0 allows tracking individual detent positions
            # The encoder generates 4 pulses per full rotation but has 16 detents
            # By monitoring the 'steps' property, we detect each detent click
            self._devices['volume_encoder'] = RotaryEncoder(
                self.config.gpio_volume_encoder_clk,
                self.config.gpio_volume_encoder_dt,
                bounce_time=0.001,  # 1ms bounce time for maximum responsiveness
                max_steps=0,  # No step limit - unlimited rotation
                wrap=False  # Don't wrap around
            )

            # Store previous step value to detect any change (not just full pulses)
            self._encoder_last_value = 0

            # Set encoder event handlers using when_rotated for any rotation
            self._devices['volume_encoder'].when_rotated = self._on_encoder_rotated

            logger.info(
                f"✅ Volume encoder initialized on GPIO {self.config.gpio_volume_encoder_clk}/"
                f"{self.config.gpio_volume_encoder_dt}"
            )

        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize encoder: {e}")
            logger.info("Volume control via encoder will not be available")
            # Don't raise - allow system to work without encoder

    def _on_button_pressed(self, button_id: int) -> None:
        """Handle generic button press for configurable buttons.

        Args:
            button_id: ID of the button that was pressed (0-4)
        """
        logger.info(f"🔘 [GPIO] Button {button_id} pressed - HARDWARE EVENT DETECTED")

        # Find the button config to get GPIO pin
        config = next((c for c in self._button_configs if c.button_id == button_id), None)
        if config:
            logger.info(f"🔘 [GPIO] Button {button_id} config found: GPIO {config.gpio_pin}, action={config.action_name}")
            self._emit_button_event(f"button_{button_id}", config.gpio_pin)
        else:
            logger.error(f"❌ [GPIO] No config found for button {button_id}")

        # Trigger the corresponding generic button event
        event_map = {
            0: PhysicalControlEvent.BUTTON_0,
            1: PhysicalControlEvent.BUTTON_1,
            2: PhysicalControlEvent.BUTTON_2,
            3: PhysicalControlEvent.BUTTON_3,
            4: PhysicalControlEvent.BUTTON_4,
        }

        event = event_map.get(button_id)
        if event:
            logger.info(f"🔘 [GPIO] Triggering event {event} for button {button_id}")
            self._trigger_event(event)
        else:
            logger.warning(f"⚠️ [GPIO] No event mapping for button {button_id}")

    def _on_encoder_switch_pressed(self) -> None:
        """Handle encoder switch press (play/pause button)."""
        logger.info(f"🎮 [GPIO] Encoder switch pressed - HARDWARE EVENT DETECTED (GPIO {self.config.gpio_volume_encoder_sw})")
        self._emit_button_event("encoder_switch", self.config.gpio_volume_encoder_sw)
        logger.info(f"🎮 [GPIO] Triggering ENCODER_SWITCH event for play/pause")
        self._trigger_event(PhysicalControlEvent.ENCODER_SWITCH)

    def _on_encoder_rotated(self) -> None:
        """Handle any encoder rotation by checking step changes.

        This detects every detent click, not just full pulses.
        The encoder has 16 detents but only 4 pulses per rotation,
        so we need to detect fractional step changes.
        """
        encoder = self._devices.get('volume_encoder')
        if not encoder:
            return

        current_value = encoder.steps

        # Detect direction based on value change
        if current_value > self._encoder_last_value:
            # Clockwise rotation (volume up)
            logger.info(f"🔊 [GPIO] Volume encoder: UP - step {self._encoder_last_value} → {current_value}")
            self._emit_encoder_event("up", self.config.gpio_volume_encoder_clk)
            self._trigger_event(PhysicalControlEvent.ENCODER_VOLUME_UP)
        elif current_value < self._encoder_last_value:
            # Counter-clockwise rotation (volume down)
            logger.info(f"🔉 [GPIO] Volume encoder: DOWN - step {self._encoder_last_value} → {current_value}")
            self._emit_encoder_event("down", self.config.gpio_volume_encoder_dt)
            self._trigger_event(PhysicalControlEvent.ENCODER_VOLUME_DOWN)

        # Update last value
        self._encoder_last_value = current_value

    def _emit_button_event(self, button_type: str, pin: int) -> None:
        """Emit a button pressed event."""
        event = ButtonPressedEvent(
            timestamp=datetime.now(),
            source_pin=pin,
            button_type=button_type
        )
        logger.debug(f"Button event emitted: {button_type} on pin {pin}")

    def _emit_encoder_event(self, direction: str, pin: int) -> None:
        """Emit an encoder rotated event."""
        event = EncoderRotatedEvent(
            timestamp=datetime.now(),
            source_pin=pin,
            direction=direction,
            steps=1
        )
        logger.debug(f"Encoder event emitted: {direction} on pin {pin}")

    async def _emit_error_event(self, message: str, error_type: str, component: str) -> None:
        """Emit an error event."""
        event = PhysicalControlErrorEvent(
            timestamp=datetime.now(),
            error_message=message,
            error_type=error_type,
            component=component
        )
        logger.error(f"Control error event: {message}")

    def _trigger_event(self, event_type: PhysicalControlEvent) -> None:
        """Trigger a registered event handler."""
        handler = self._event_handlers.get(event_type)
        if handler:
            try:
                logger.info(f"🎯 [GPIO] Calling handler for event {event_type}")
                handler()
                logger.info(f"✅ [GPIO] Handler for {event_type} completed successfully")
            except Exception as e:
                logger.error(f"❌ [GPIO] Error in event handler for {event_type}: {e}", exc_info=True)
        else:
            logger.warning(f"⚠️ [GPIO] No handler registered for event: {event_type}")
            logger.warning(f"⚠️ [GPIO] Available handlers: {list(self._event_handlers.keys())}")

    async def cleanup(self) -> None:
        """Clean up GPIO resources."""
        try:
            with self._lock:
                if not self._is_initialized:
                    return

                logger.info("🧹 Cleaning up GPIO controls...")

                # Close all GPIO devices
                for device_name, device in self._devices.items():
                    try:
                        if hasattr(device, 'close'):
                            device.close()
                        logger.debug(f"Device {device_name} closed")
                    except Exception as e:
                        logger.error(f"Error closing {device_name}: {e}")

                self._devices.clear()
                self._event_handlers.clear()
                self._is_initialized = False

                logger.info("✅ GPIO controls cleanup completed")

        except Exception as e:
            logger.error(f"❌ Error during GPIO controls cleanup: {e}")

    def get_status(self) -> dict:
        """Get current status of GPIO controls.

        Uses base class helper for button info.
        """
        # Get button info from base class helper
        button_info = self._build_button_info()

        return {
            "initialized": self._is_initialized,
            "mock_mode": self._mock_mode_active,
            "mock_mode_intentional": USE_MOCK_HARDWARE,
            "fallback_reason": GPIO_FALLBACK_REASON,
            "devices_count": len(self._devices),
            "event_handlers_count": len(self._event_handlers),
            "gpio_available": GPIO_AVAILABLE,
            "configurable_buttons": button_info,
            "encoder": {
                "volume_encoder_clk": self.config.gpio_volume_encoder_clk,
                "volume_encoder_dt": self.config.gpio_volume_encoder_dt,
            } if self._is_initialized else {}
        }
