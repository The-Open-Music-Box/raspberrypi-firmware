#!/usr/bin/env python3
# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Rotary Encoder Test Script

Tests the rotary encoder (volume control) on TheOpenMusicBox hardware.

Hardware Configuration:
- GPIO 16: Encoder switch (Play/Pause button)
- GPIO 26: Encoder CLK (Channel A - rotation detection)
- GPIO 13: Encoder DT (Channel B - rotation detection)

Usage:
    python test_rotary_encoder.py [--duration SECONDS]

Options:
    --duration SECONDS    Test duration in seconds (default: 10)

Expected Behavior:
- Rotating clockwise: Should print "🔊 CW rotation"
- Rotating counter-clockwise: Should print "🔉 CCW rotation"
- Pressing switch: Should print "🎵 Switch pressed"
- Releasing switch: Should print "🎵 Switch released"

Troubleshooting:
- If no events are detected, check wiring:
  - GPIO 26 connected to encoder CLK pin
  - GPIO 13 connected to encoder DT pin
  - GPIO 16 connected to encoder SW pin
  - GND connected to encoder GND
- Ensure lgpio library is installed: pip install lgpio
"""

import sys
import time
import argparse
from typing import Optional

# GPIO pin configuration (from hardware_config.py)
ENCODER_SWITCH_PIN = 16  # gpio_volume_encoder_sw
ENCODER_CLK_PIN = 26     # gpio_volume_encoder_clk (Channel A)
ENCODER_DT_PIN = 13      # gpio_volume_encoder_dt (Channel B)

# Test statistics
rotation_count = 0
cw_count = 0
ccw_count = 0
press_count = 0


def main(duration: int = 10) -> int:
    """
    Test rotary encoder functionality.

    Args:
        duration: Test duration in seconds

    Returns:
        0 if encoder works, 1 if no events detected
    """
    global rotation_count, cw_count, ccw_count, press_count

    print("=" * 60)
    print("🎛️  Rotary Encoder Test Script")
    print("=" * 60)
    print(f"\nHardware Configuration:")
    print(f"  - Switch (Play/Pause): GPIO {ENCODER_SWITCH_PIN}")
    print(f"  - CLK (Channel A):     GPIO {ENCODER_CLK_PIN}")
    print(f"  - DT (Channel B):      GPIO {ENCODER_DT_PIN}")
    print(f"\nTest Duration: {duration} seconds")
    print("-" * 60)

    try:
        # Import gpiozero and configure lgpio backend
        from gpiozero import RotaryEncoder, Button, Device
        from gpiozero.pins.lgpio import LGPIOFactory

        # Force lgpio backend (recommended for Raspberry Pi)
        Device.pin_factory = LGPIOFactory()
        print("✅ Using lgpio backend (modern, recommended)")

    except ImportError as e:
        print(f"❌ Error importing GPIO libraries: {e}")
        print("   Install required library: pip install lgpio")
        return 1
    except Exception as e:
        print(f"❌ Error initializing GPIO backend: {e}")
        return 1

    encoder: Optional[RotaryEncoder] = None
    switch: Optional[Button] = None

    try:
        # Create rotary encoder
        print(f"\n🔧 Creating RotaryEncoder({ENCODER_CLK_PIN}, {ENCODER_DT_PIN})...")
        encoder = RotaryEncoder(
            ENCODER_CLK_PIN,
            ENCODER_DT_PIN,
            bounce_time=0.002,  # 2ms for good responsiveness
            max_steps=0  # Unlimited steps
        )
        print("✅ Encoder created successfully!")

        # Create switch button
        print(f"🔧 Creating Button({ENCODER_SWITCH_PIN})...")
        switch = Button(
            ENCODER_SWITCH_PIN,
            pull_up=True,
            bounce_time=0.02  # 20ms debounce for switch
        )
        print("✅ Switch button created successfully!")

        # Define event handlers
        def on_cw():
            """Handle clockwise rotation."""
            global rotation_count, cw_count
            rotation_count += 1
            cw_count += 1
            print(f"🔊 CW rotation #{rotation_count} (CW: {cw_count}, CCW: {ccw_count})")

        def on_ccw():
            """Handle counter-clockwise rotation."""
            global rotation_count, ccw_count
            rotation_count += 1
            ccw_count += 1
            print(f"🔉 CCW rotation #{rotation_count} (CW: {cw_count}, CCW: {ccw_count})")

        def on_press():
            """Handle switch press."""
            global press_count
            press_count += 1
            print(f"🎵 Switch pressed (press #{press_count})")

        def on_release():
            """Handle switch release."""
            print(f"🎵 Switch released")

        # Attach event handlers
        encoder.when_rotated_clockwise = on_cw
        encoder.when_rotated_counter_clockwise = on_ccw
        switch.when_pressed = on_press
        switch.when_released = on_release

        # Run test
        print("\n" + "=" * 60)
        print(f"🎯 TEST STARTED - Rotate encoder and press switch NOW!")
        print("=" * 60)

        time.sleep(duration)

        # Show results
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS")
        print("=" * 60)
        print(f"Total Rotations: {rotation_count}")
        print(f"  - Clockwise (CW):        {cw_count}")
        print(f"  - Counter-Clockwise:     {ccw_count}")
        print(f"Switch Presses:      {press_count}")
        print("-" * 60)

        if rotation_count > 0 or press_count > 0:
            print("✅ SUCCESS! Encoder is working correctly")
            print("\nThe rotary encoder is functional and ready for use.")
            return 0
        else:
            print("❌ FAIL: No events detected")
            print("\n⚠️  Troubleshooting checklist:")
            print("   1. Verify wiring connections:")
            print(f"      - GPIO {ENCODER_CLK_PIN} (pin 37) → Encoder CLK pin")
            print(f"      - GPIO {ENCODER_DT_PIN} (pin 33)  → Encoder DT pin")
            print(f"      - GPIO {ENCODER_SWITCH_PIN} (pin 36) → Encoder SW pin")
            print("      - GND → Encoder GND pin")
            print("   2. Check encoder power (if required)")
            print("   3. Ensure lgpio library installed: pip install lgpio")
            print("   4. Verify GPIO permissions (user in gpio group)")
            return 1

    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        return 0

    except Exception as e:
        print(f"\n❌ Error during test: {type(e).__name__}: {e}")
        return 1

    finally:
        # Cleanup
        print("\n🧹 Cleaning up GPIO resources...")
        if encoder:
            encoder.close()
        if switch:
            switch.close()
        print("✅ Cleanup completed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Test rotary encoder functionality on TheOpenMusicBox hardware",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_rotary_encoder.py              # Run 10-second test
  python test_rotary_encoder.py --duration 5  # Run 5-second test
  python test_rotary_encoder.py --duration 30 # Run 30-second test

Hardware Info:
  The rotary encoder has 3 connections tested by this script:
  - CLK (Channel A): Detects rotation direction
  - DT (Channel B):  Detects rotation direction
  - SW (Switch):     Detects button press
        """
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=10,
        help="Test duration in seconds (default: 10)"
    )

    args = parser.parse_args()

    if args.duration < 1:
        print("Error: Duration must be at least 1 second")
        sys.exit(1)

    sys.exit(main(args.duration))
