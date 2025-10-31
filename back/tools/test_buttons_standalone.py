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
    from gpiozero import Button, Device
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
        from gpiozero import Button, Device
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

        self.buttons = {}
        self.press_counts = {name: 0 for name in self.button_configs.keys()}
        self.last_press_times = {name: None for name in self.button_configs.keys()}

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

        print("=" * 80)
        logger.info(f"✅ Initialized {success_count}/{len(self.button_configs)} buttons")
        return success_count > 0

    def cleanup(self):
        """Clean up GPIO resources."""
        logger.info("🧹 Cleaning up GPIO resources...")

        for name, button in self.buttons.items():
            try:
                if button and hasattr(button, 'close'):
                    button.close()
                    logger.debug(f"Closed button {name}")
            except Exception as e:
                logger.error(f"Error closing button {name}: {e}")

        self.buttons.clear()
        logger.info("✅ Cleanup completed")

    def print_status(self):
        """Print current test status."""
        print("\n" + "=" * 80)
        print("📊 BUTTON TEST STATUS")
        print("=" * 80)

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

        print("=" * 80)

    def run(self):
        """Run the button test."""
        if not GPIO_AVAILABLE:
            logger.error("❌ Cannot run test - GPIO not available")
            return

        print("\n" + "=" * 80)
        print("🎮 BUTTON TEST - TheOpenMusicBox")
        print("=" * 80)
        print("\nPress any button to test it.")
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
