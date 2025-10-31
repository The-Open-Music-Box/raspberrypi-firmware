#!/usr/bin/env python3
# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Standalone Button Test Script

Tests all physical buttons connected to the Raspberry Pi GPIO pins.
This script is independent from the main application and can be used
to verify hardware connections and button functionality.

Usage:
    python tools/test_buttons_standalone.py

Controls:
    - Press any configured button to see its status
    - Press Ctrl+C to exit

GPIO Pin Assignments (BCM numbering):
    BT0 (GPIO23) - To be defined (debug print)
    BT1 (GPIO27) - Previous track
    BT2 (GPIO22) - To be defined (debug print)
    BT3 (GPIO6)  - To be defined (debug print)
    BT4 (GPIO5)  - Next track
    SW  (GPIO16) - Play/Pause (encoder switch)
"""

import sys
import os
import time
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Try to import GPIO libraries
try:
    from gpiozero import Button, RotaryEncoder, Device
    from gpiozero.pins.rpigpio import RPiGPIOFactory
    Device.pin_factory = RPiGPIOFactory()
    GPIO_AVAILABLE = True
    logger.info("✅ GPIO hardware available - using RPi.GPIO backend")
except ImportError as e:
    logger.error(f"❌ gpiozero library not available: {e}")
    GPIO_AVAILABLE = False
except Exception as e:
    logger.warning(f"⚠️ RPi.GPIO backend failed, trying lgpio: {e}")
    try:
        from gpiozero import Button, RotaryEncoder, Device
        from gpiozero.pins.lgpio import LgpioFactory
        Device.pin_factory = LgpioFactory()
        GPIO_AVAILABLE = True
        logger.info("✅ GPIO hardware available - using lgpio backend")
    except Exception as e2:
        logger.error(f"❌ No GPIO backend available: {e2}")
        GPIO_AVAILABLE = False


class ButtonTester:
    """Test harness for physical buttons."""

    def __init__(self):
        """Initialize the button tester with current GPIO configuration."""
        # Button configuration matching the current hardware setup
        self.button_configs = {
            'BT0': {'gpio': 23, 'description': 'To be defined (debug print)'},
            'BT1': {'gpio': 27, 'description': 'Previous track'},
            'BT2': {'gpio': 22, 'description': 'To be defined (debug print)'},
            'BT3': {'gpio': 6, 'description': 'To be defined (debug print)'},
            'BT4': {'gpio': 5, 'description': 'Next track'},
            'SW': {'gpio': 16, 'description': 'Play/Pause (encoder switch)'},
        }

        # Rotary encoder configuration
        self.encoder_config = {
            'clk': 13,  # Channel A
            'dt': 26,   # Channel B
        }

        self.buttons = {}
        self.encoder = None
        self.press_counts = {name: 0 for name in self.button_configs.keys()}
        self.last_press_times = {name: None for name in self.button_configs.keys()}

        # Encoder rotation tracking
        self.volume_up_count = 0
        self.volume_down_count = 0
        self.last_volume_change = None

    def on_button_pressed(self, button_name: str):
        """Handle button press event."""
        now = datetime.now()
        self.press_counts[button_name] += 1
        self.last_press_times[button_name] = now

        config = self.button_configs[button_name]
        logger.info(
            f"🔘 [{button_name}] PRESSED - GPIO {config['gpio']} "
            f"({config['description']}) - Total presses: {self.press_counts[button_name]}"
        )

        # Print visual separator for clarity
        print("─" * 80)

    def on_volume_up(self):
        """Handle volume encoder rotation clockwise (volume up)."""
        now = datetime.now()
        self.volume_up_count += 1
        self.last_volume_change = now

        logger.info(
            f"🔊 [VOLUME UP] Encoder rotated clockwise - "
            f"Total volume increases: {self.volume_up_count}"
        )
        print("─" * 80)

    def on_volume_down(self):
        """Handle volume encoder rotation counter-clockwise (volume down)."""
        now = datetime.now()
        self.volume_down_count += 1
        self.last_volume_change = now

        logger.info(
            f"🔉 [VOLUME DOWN] Encoder rotated counter-clockwise - "
            f"Total volume decreases: {self.volume_down_count}"
        )
        print("─" * 80)

    def initialize_buttons(self):
        """Initialize all configured buttons."""
        if not GPIO_AVAILABLE:
            logger.error("❌ GPIO not available - cannot initialize buttons")
            return False

        logger.info("🔌 Initializing buttons...")
        print("=" * 80)

        # Clean up GPIO pins first
        try:
            import RPi.GPIO as GPIO_Direct
            GPIO_Direct.setmode(GPIO_Direct.BCM)
            GPIO_Direct.setwarnings(False)

            for name, config in self.button_configs.items():
                try:
                    GPIO_Direct.cleanup(config['gpio'])
                except:
                    pass

            logger.debug("GPIO pins cleaned before initialization")
        except Exception as e:
            logger.debug(f"GPIO cleanup attempt: {e}")

        # Initialize each button
        success_count = 0
        for name, config in self.button_configs.items():
            try:
                # Try with pull_up=True first (most common for buttons)
                self.buttons[name] = Button(
                    config['gpio'],
                    pull_up=True,
                    bounce_time=0.3,  # 300ms debounce
                )

                # Set up the callback
                def make_handler(btn_name):
                    """Factory to create handler with proper closure."""
                    def handler():
                        self.on_button_pressed(btn_name)
                    return handler

                self.buttons[name].when_pressed = make_handler(name)

                logger.info(
                    f"✅ [{name}] initialized on GPIO {config['gpio']} - {config['description']}"
                )
                success_count += 1

            except Exception as e:
                logger.warning(f"⚠️ Failed to init [{name}] on GPIO {config['gpio']}: {e}")

                # Try without pull_up if external pull-up is present
                try:
                    self.buttons[name] = Button(
                        config['gpio'],
                        pull_up=False,
                        bounce_time=0.3,
                    )

                    def make_handler(btn_name):
                        def handler():
                            self.on_button_pressed(btn_name)
                        return handler

                    self.buttons[name].when_pressed = make_handler(name)

                    logger.info(
                        f"✅ [{name}] initialized on GPIO {config['gpio']} (no pull_up) - {config['description']}"
                    )
                    success_count += 1

                except Exception as e2:
                    logger.error(f"❌ Failed to init [{name}] on GPIO {config['gpio']}: {e2}")

        # Initialize rotary encoder
        try:
            self._init_encoder()
            success_count += 1
        except Exception as e:
            logger.warning(f"⚠️ Encoder initialization had errors: {e}")

        print("=" * 80)
        logger.info(f"✅ Initialized {success_count}/{len(self.button_configs) + 1} devices (buttons + encoder)")
        return success_count > 0

    def _init_encoder(self):
        """Initialize rotary encoder for volume control."""
        if not GPIO_AVAILABLE:
            return

        try:
            # Clean up encoder pins first
            try:
                import RPi.GPIO as GPIO_Direct
                GPIO_Direct.setmode(GPIO_Direct.BCM)
                GPIO_Direct.setwarnings(False)
                GPIO_Direct.cleanup(self.encoder_config['clk'])
                GPIO_Direct.cleanup(self.encoder_config['dt'])
            except:
                pass

            # Initialize the rotary encoder
            self.encoder = RotaryEncoder(
                self.encoder_config['clk'],
                self.encoder_config['dt'],
                bounce_time=0.01,  # Small bounce time for encoder
                max_steps=0  # No step limit
            )

            # Set encoder event handlers
            self.encoder.when_rotated_clockwise = self.on_volume_up
            self.encoder.when_rotated_counter_clockwise = self.on_volume_down

            logger.info(
                f"✅ [ENCODER] Volume encoder initialized on GPIO {self.encoder_config['clk']}/"
                f"{self.encoder_config['dt']} (CLK/DT)"
            )

        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize encoder: {e}")
            logger.info("Volume control via encoder will not be available")

    def cleanup(self):
        """Clean up GPIO resources."""
        logger.info("🧹 Cleaning up GPIO resources...")

        # Close all buttons
        for name, button in self.buttons.items():
            try:
                if button and hasattr(button, 'close'):
                    button.close()
                    logger.debug(f"Closed button {name}")
            except Exception as e:
                logger.error(f"Error closing button {name}: {e}")

        self.buttons.clear()

        # Close encoder
        if self.encoder:
            try:
                if hasattr(self.encoder, 'close'):
                    self.encoder.close()
                    logger.debug("Closed encoder")
            except Exception as e:
                logger.error(f"Error closing encoder: {e}")

        logger.info("✅ Cleanup completed")

    def print_status(self):
        """Print current test status."""
        print("\n" + "=" * 80)
        print("📊 BUTTON & ENCODER TEST STATUS")
        print("=" * 80)

        # Print button status
        for name in sorted(self.button_configs.keys()):
            config = self.button_configs[name]
            count = self.press_counts[name]
            last_press = self.last_press_times[name]

            status_line = f"[{name}] GPIO {config['gpio']:2d} - {config['description']:40s}"

            if count > 0:
                time_str = last_press.strftime('%H:%M:%S') if last_press else 'N/A'
                status_line += f" | Presses: {count:3d} | Last: {time_str}"
            else:
                status_line += " | Not pressed yet"

            print(status_line)

        # Print encoder status
        print("-" * 80)
        encoder_status = f"[ENCODER] GPIO {self.encoder_config['clk']}/{self.encoder_config['dt']} (CLK/DT) - Volume control"
        if self.volume_up_count > 0 or self.volume_down_count > 0:
            time_str = self.last_volume_change.strftime('%H:%M:%S') if self.last_volume_change else 'N/A'
            encoder_status += f"\n  🔊 Volume UP:   {self.volume_up_count:3d} rotations"
            encoder_status += f"\n  🔉 Volume DOWN: {self.volume_down_count:3d} rotations"
            encoder_status += f"\n  ⏱️  Last change: {time_str}"
        else:
            encoder_status += "\n  Not rotated yet"

        print(encoder_status)
        print("=" * 80)

    def run(self):
        """Run the button test."""
        if not GPIO_AVAILABLE:
            logger.error("❌ Cannot run test - GPIO not available")
            return

        print("\n" + "=" * 80)
        print("🎮 BUTTON & ENCODER TEST - TheOpenMusicBox")
        print("=" * 80)
        print("\nPress any button to test it.")
        print("Rotate the encoder to test volume control (clockwise = up, counter-clockwise = down).")
        print("Press Ctrl+C to exit and see final statistics.")
        print("=" * 80 + "\n")

        if not self.initialize_buttons():
            logger.error("❌ Failed to initialize any buttons")
            return

        try:
            # Keep the script running and listening for button presses
            logger.info("👂 Listening for button presses... (Press Ctrl+C to exit)")
            while True:
                time.sleep(0.1)  # Small delay to reduce CPU usage

        except KeyboardInterrupt:
            print("\n\n🛑 Test interrupted by user")

        finally:
            # Print final statistics
            self.print_status()
            self.cleanup()


def main():
    """Main entry point."""
    tester = ButtonTester()

    try:
        tester.run()
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
