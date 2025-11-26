# GPIO Quick Reference Guide

## How to Override GPIO Pin Configuration

### Option 1: Using Environment Variables in .env
Edit `back/.env`:

```bash
# Button pins (optional - shows defaults)
GPIO_BUTTON_BT0=23
GPIO_BUTTON_BT1=27
GPIO_BUTTON_BT2=22
GPIO_BUTTON_BT3=6
GPIO_BUTTON_BT4=5

# Encoder pins (optional - shows defaults)
GPIO_VOLUME_CLK=26
GPIO_VOLUME_DT=13
GPIO_VOLUME_SW=16

# Enable mock hardware if needed
USE_MOCK_HARDWARE=false
```

### Option 2: Using Environment Variables at Runtime
```bash
export GPIO_BUTTON_BT0=24
export GPIO_BUTTON_BT1=25
export GPIO_VOLUME_CLK=27
python -m app.main  # Run application
```

## Code Locations for Configuration

### Defining GPIO Pins (Defaults)
File: `back/app/src/config/hardware_config.py`
- Lines 21-37: All GPIO pin assignments

### Loading Environment Overrides
File: `back/app/src/config/app_config.py`
- Lines 514-565: Method `_load_subconfig_overrides()`
- This method checks for env vars: GPIO_BUTTON_*, GPIO_VOLUME_*

### Button Action Mapping
File: `back/app/src/config/button_actions_config.py`
- Lines 48-79: Default button to action mappings

## Adding Support for LED GPIO Configuration

To make LED GPIO pins configurable via environment variables, modify:

**File:** `back/app/src/config/app_config.py`

**Add to `_load_subconfig_overrides()` method (after line 550):**

```python
# LED GPIO overrides (if adding support)
if "GPIO_LED_RED" in os.environ:
    self.hardware.gpio_led_red = int(os.environ["GPIO_LED_RED"])
if "GPIO_LED_GREEN" in os.environ:
    self.hardware.gpio_led_green = int(os.environ["GPIO_LED_GREEN"])
if "GPIO_LED_BLUE" in os.environ:
    self.hardware.gpio_led_blue = int(os.environ["GPIO_LED_BLUE"])
```

Then use in .env:
```bash
GPIO_LED_RED=25
GPIO_LED_GREEN=12
GPIO_LED_BLUE=24
```

## Current Default Configuration

```
Buttons:
  BT0 (Debug print)      -> GPIO 23
  BT1 (Previous track)   -> GPIO 27
  BT2 (Debug print)      -> GPIO 22
  BT3 (Debug print)      -> GPIO 6
  BT4 (Next track)       -> GPIO 5

Encoder:
  CLK (Volume up/down)   -> GPIO 26
  DT (Volume up/down)    -> GPIO 13
  SW (Play/Pause)        -> GPIO 16

LED (RGB - SMD5050):
  Red                    -> GPIO 25
  Green                  -> GPIO 12
  Blue                   -> GPIO 24

I2C:
  Bus 1 (shared):
    - WM8960 DAC (Audio) -> Address 0x1A
    - PN532 NFC Reader   -> Address 0x24
```

## GPIO Backend Auto-Selection

The system automatically tries backends in this order:
1. RPi.GPIO (preferred)
2. lgpio (modern RPi OS)
3. pigpio (daemon mode)
4. Mock mode (fallback)

Force mock mode: `USE_MOCK_HARDWARE=true` in .env

## Hardware Validation

All GPIO pins are validated at startup:
- Valid range: 0-27 (BCM numbering)
- No duplicate assignments
- Button timing parameters checked

## Implementation Stack

```
app_config.py
   ↓
hardware_config.py (HardwareConfig dataclass)
   ↓
controls_factory.py (PhysicalControlsFactory)
   ↓
gpio_controls_implementation.py (GPIOPhysicalControls)
   ↓
gpiozero library (Button, RotaryEncoder, PWMLED)
```

## Testing Hardware Configuration

Check if GPIO is available at startup:
```python
from app.src.infrastructure.hardware.controls.gpio_controls_implementation import GPIO_AVAILABLE
print(f"GPIO Available: {GPIO_AVAILABLE}")
```

Get current hardware status:
```python
# After initialization
status = controls.get_status()
print(f"GPIO devices initialized: {status['devices_count']}")
print(f"Mock mode: {status['mock_mode']}")
```

## Debugging Tips

1. Check logs for GPIO backend selection:
   ```
   grep "GPIO backend" /path/to/logs/app.log
   ```

2. Check hardware initialization:
   ```
   grep "Initializing GPIO" /path/to/logs/app.log
   ```

3. Verify pin configuration:
   ```
   grep "GPIO {pin}" /path/to/logs/app.log
   ```

4. Force mock mode to test without physical GPIO:
   ```
   USE_MOCK_HARDWARE=true python -m app.main
   ```

## Common GPIO Pin Conflicts

Raspberry Pi GPIO considerations:
- GPIO 2, 3: Reserved for I2C (SCL, SDA)
- GPIO 27: Sometimes used for alternate I2C
- GPIO 0, 1: Reserved for HAT EEPROM

Current configuration avoids these reserved pins.
