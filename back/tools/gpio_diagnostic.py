#!/usr/bin/env python3
"""
GPIO Diagnostic Tool for Raspberry Pi

Tests which GPIO backend is available and functional.
"""

import sys
import os

print("=" * 60)
print("🔍 GPIO DIAGNOSTIC TOOL")
print("=" * 60)

# System info
print("\n📊 System Information:")
print(f"   Python: {sys.version}")
print(f"   Platform: {sys.platform}")

# Check if on Raspberry Pi
is_rpi = False
try:
    with open('/proc/cpuinfo', 'r') as f:
        if 'Raspberry' in f.read():
            is_rpi = True
            print("   Hardware: ✅ Raspberry Pi detected")
        else:
            print("   Hardware: ⚠️  Not a Raspberry Pi")
except:
    print("   Hardware: ⚠️  Could not determine hardware")

# Test different GPIO backends
print("\n🧪 Testing GPIO Backends:")
print("-" * 40)

backends_tested = []

# 1. Test RPi.GPIO
print("\n1. RPi.GPIO:")
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    # Try to setup a pin (non-destructive test)
    GPIO.setup(26, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.cleanup()
    print("   ✅ RPi.GPIO is available and functional")
    backends_tested.append("RPi.GPIO")
except ImportError as e:
    print(f"   ❌ Not installed: {e}")
except Exception as e:
    print(f"   ⚠️  Installed but error: {e}")

# 2. Test gpiozero with different pin factories
print("\n2. gpiozero:")
try:
    import gpiozero
    print(f"   ✅ gpiozero version {gpiozero.__version__} installed")

    # Test different pin factories
    from gpiozero import Device

    # Test RPiGPIOFactory
    print("\n   Testing RPiGPIOFactory:")
    try:
        from gpiozero.pins.rpigpio import RPiGPIOFactory
        Device.pin_factory = RPiGPIOFactory()
        from gpiozero import Button
        btn = Button(26)
        btn.close()
        print("      ✅ RPiGPIOFactory works")
        backends_tested.append("gpiozero (RPiGPIOFactory)")
    except Exception as e:
        print(f"      ❌ RPiGPIOFactory failed: {e}")

    # Test lgpio
    print("\n   Testing LgpioFactory:")
    try:
        from gpiozero.pins.lgpio import LgpioFactory
        Device.pin_factory = LgpioFactory()
        from gpiozero import Button
        btn = Button(26)
        btn.close()
        print("      ✅ LgpioFactory works")
        backends_tested.append("gpiozero (LgpioFactory)")
    except Exception as e:
        print(f"      ❌ LgpioFactory failed: {e}")

    # Test pigpio
    print("\n   Testing PiGPIOFactory:")
    try:
        from gpiozero.pins.pigpio import PiGPIOFactory
        Device.pin_factory = PiGPIOFactory()
        from gpiozero import Button
        btn = Button(26)
        btn.close()
        print("      ✅ PiGPIOFactory works")
        backends_tested.append("gpiozero (PiGPIOFactory)")
    except Exception as e:
        print(f"      ❌ PiGPIOFactory failed: {e}")

except ImportError as e:
    print(f"   ❌ gpiozero not installed: {e}")

# 3. Test pigpio directly
print("\n3. pigpio:")
try:
    import pigpio
    pi = pigpio.pi()
    if pi.connected:
        print("   ✅ pigpio connected to daemon")
        pi.stop()
        backends_tested.append("pigpio")
    else:
        print("   ⚠️  pigpio installed but daemon not running")
        print("      Run: sudo systemctl start pigpiod")
except ImportError:
    print("   ❌ pigpio not installed")
except Exception as e:
    print(f"   ⚠️  pigpio error: {e}")

# 4. Check lgpio (the problematic one)
print("\n4. lgpio:")
try:
    import lgpio
    print(f"   ✅ lgpio imported successfully")
    backends_tested.append("lgpio")
except ImportError as e:
    if "GLIBC" in str(e):
        print(f"   ❌ GLIBC version mismatch: {e}")
        print("      Your system has an older GLIBC version")
        print("      Use RPi.GPIO or pigpio instead")
    else:
        print(f"   ❌ Not installed: {e}")

# Summary
print("\n" + "=" * 60)
print("📋 SUMMARY:")
print("-" * 40)

if backends_tested:
    print("✅ Available GPIO backends:")
    for backend in backends_tested:
        print(f"   - {backend}")
    print("\n🎉 Your system can use physical GPIO controls!")
    print("\n📌 Recommended backend: " + backends_tested[0])
else:
    print("❌ No working GPIO backends found!")
    print("\n🔧 To fix this, run:")
    print("   ./setup_gpio_rpi.sh")
    print("\nOr install manually:")
    print("   sudo apt-get install python3-rpi.gpio")
    print("   pip3 install RPi.GPIO gpiozero")

print("\n" + "=" * 60)