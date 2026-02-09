---
title: "GPIO Pin Configuration Analysis"
status: active
category: hardware
last_reviewed: 2026-02-09
review_cycle: 6months
---

# TheOpenMusicBox GPIO Pin Configuration Analysis

## Summary
The TheOpenMusicBox project uses GPIO pins for physical controls (buttons), volume control (rotary encoder), and RGB LED indicator. All GPIO pins are configurable via environment variables in the `.env` file and can be overridden at runtime.

---

## GPIO Pin Definitions and Usage

### 1. PHYSICAL BUTTONS (5 buttons - BT0 through BT4)

| Button ID | GPIO Pin (BCM) | Default Purpose | Environment Variable | Configurable |
|-----------|---|---|---|---|
| BT0 | 23 | Debug print | `GPIO_BUTTON_BT0` | Yes |
| BT1 | 27 | Previous track | `GPIO_BUTTON_BT1` | Yes |
| BT2 | 22 | Debug print | `GPIO_BUTTON_BT2` | Yes |
| BT3 | 6 | Debug print | `GPIO_BUTTON_BT3` | Yes |
| BT4 | 5 | Next track | `GPIO_BUTTON_BT4` | Yes |

**Location (Default Values):**
- `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/config/hardware_config.py` (lines 23-27)

**Location (Button Actions):**
- `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/config/button_actions_config.py` (lines 48-79)

**Configuration Override Mechanism:**
- Implemented in: `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/config/app_config.py` (lines 532-542)
- Method: `_load_subconfig_overrides()`

**Hardware Implementation:**
- `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/infrastructure/hardware/controls/gpio_controls_implementation.py` (lines 170-240)

**Button Configuration Details:**
- Debounce time: 10ms (adjustable via `button_debounce_time` in hardware_config)
- Hold time: 2.0 seconds (adjustable via `button_hold_time` in hardware_config)
- Valid GPIO range: 0-27 (BCM numbering)
- Pull-up configuration: Attempted with `pull_up=True`, falls back to `pull_up=False` if needed

---

### 2. ROTARY ENCODER (Volume Control)

| Component | GPIO Pin (BCM) | Purpose | Environment Variable | Configurable |
|-----------|---|---|---|---|
| CLK (Channel A) | 26 | Volume direction | `GPIO_VOLUME_CLK` | Yes |
| DT (Channel B) | 13 | Volume direction | `GPIO_VOLUME_DT` | Yes |
| SW (Switch) | 16 | Play/Pause button | `GPIO_VOLUME_SW` | Yes |

**Location (Default Values):**
- `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/config/hardware_config.py` (lines 30-32)

**Configuration Override Mechanism:**
- Implemented in: `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/config/app_config.py` (lines 544-550)
- Method: `_load_subconfig_overrides()`

**Hardware Implementation:**
- `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/infrastructure/hardware/controls/gpio_controls_implementation.py`
  - Encoder switch initialization: lines 241-274
  - Encoder rotation initialization: lines 276-312
  - Clockwise (volume up) handler: lines 353-357
  - Counter-clockwise (volume down) handler: lines 359-363

**Encoder Configuration Details:**
- Step threshold: 2 steps required to register a turn
- Acceleration: Enabled for fast turns
- Bounce time: 0.01 seconds for encoder
- No maximum step limit

---

### 3. RGB LED (Status Indicator - SMD5050)

| LED Channel | GPIO Pin (BCM) | Environment Variable | Configurable |
|-----------|---|---|---|
| Red | 25 | `GPIO_LED_RED` | **NO** |
| Green | 12 | `GPIO_LED_GREEN` | **NO** |
| Blue | 24 | `GPIO_LED_BLUE` | **NO** |

**Location (Default Values):**
- `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/config/hardware_config.py` (lines 35-37)

**Hardware Implementation:**
- `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/infrastructure/hardware/leds/rgb_led_controller.py` (lines 63-141)

**LED Configuration Details:**
- PWM Frequency: 1000 Hz (default)
- Default brightness: 0.1 (10%, adjustable via `led_default_brightness` in hardware_config)
- Animation speed: 0.5 seconds (adjustable via `led_animation_speed` in hardware_config)
- Supported animations: SOLID, PULSE, BLINK_SLOW, BLINK_FAST, FLASH, DOUBLE_BLINK

**NOTE:** LED GPIO pins are NOT currently overridable via environment variables. Override would require code changes in:
- `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/config/app_config.py` (add to `_load_subconfig_overrides()` method)

---

### 4. I2C COMMUNICATION

| Component | I2C Bus | I2C Address | Environment Variable | Configurable |
|-----------|---------|-------------|---|---|
| WM8960 DAC (Audio) | 1 | 0x1A | Not currently | NO |
| PN532 NFC Reader | 1 | 0x24 | Not currently | NO |

**Location (I2C Configuration):**
- Hardware I2C bus: `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/config/hardware_config.py` (lines 51-53)
- NFC I2C bus: `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/config/nfc_config.py` (lines 42-43)

**Audio DAC Implementation:**
- Uses direct I2C communication with WM8960 codec
- Address: 0x1A (7-bit addressing)

**NFC Reader Implementation:**
- `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/infrastructure/hardware/nfc/pn532_nfc_hardware.py`
- Uses Adafruit PN532 library
- I2C address: 0x24 (PN532 default)
- Initialization: lines 54-71

---

### 5. SPI COMMUNICATION

| Component | SPI Bus | SPI Device | SPI Speed | Environment Variable | Configurable |
|-----------|---------|------------|-----------|---|---|
| NFC (if SPI) | 0 | 0 | 1000000 Hz (1 MHz) | Not currently | NO |

**Location:**
- `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/config/hardware_config.py` (lines 55-58)

**NOTE:** Currently NFC uses I2C by default (`use_spi: bool = False` in nfc_config.py). SPI configuration exists but is not actively used.

---

## Configuration Mechanism

### Method 1: Hardcoded Defaults (HardwareConfig Dataclass)
Location: `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/config/hardware_config.py`

All GPIO pins have hardcoded default values in the `HardwareConfig` dataclass:
```python
gpio_button_bt0: int = 23
gpio_button_bt1: int = 27
gpio_button_bt2: int = 22
gpio_button_bt3: int = 6
gpio_button_bt4: int = 5
gpio_volume_encoder_sw: int = 16
gpio_volume_encoder_clk: int = 26
gpio_volume_encoder_dt: int = 13
gpio_led_red: int = 25
gpio_led_green: int = 12
gpio_led_blue: int = 24
```

### Method 2: Environment Variable Overrides (AppConfig)
Location: `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/config/app_config.py`
Method: `_load_subconfig_overrides()` (lines 514-565)

The following environment variables override the hardcoded defaults:

**Button GPIO Overrides:**
```
GPIO_BUTTON_BT0  (overrides gpio_button_bt0: default 23)
GPIO_BUTTON_BT1  (overrides gpio_button_bt1: default 27)
GPIO_BUTTON_BT2  (overrides gpio_button_bt2: default 22)
GPIO_BUTTON_BT3  (overrides gpio_button_bt3: default 6)
GPIO_BUTTON_BT4  (overrides gpio_button_bt4: default 5)
```

**Encoder GPIO Overrides:**
```
GPIO_VOLUME_CLK  (overrides gpio_volume_encoder_clk: default 26)
GPIO_VOLUME_DT   (overrides gpio_volume_encoder_dt: default 13)
GPIO_VOLUME_SW   (overrides gpio_volume_encoder_sw: default 16)
```

### Method 3: .env File
Location: `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/.env`

The `.env` file is loaded by `dotenv` library (line 17 in app_config.py).
Configuration path resolution:
1. `/back/.env` (development)
2. `/.env` (production at project root)
3. `./` (current working directory fallback)

### Method 4: Hardware Configuration Validation
Location: `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/config/hardware_config.py` (lines 66-99)

The `HardwareConfig.validate()` method ensures:
- All GPIO pins are in valid range (0-27)
- No duplicate GPIO pin assignments
- Button timing parameters are valid

---

## GPIO Backend Support

The GPIO implementation supports multiple backends (in order of preference):

Location: `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/infrastructure/hardware/controls/gpio_controls_implementation.py` (lines 33-84)

1. **RPi.GPIO** (preferred)
   - Uses `RPiGPIOFactory` from gpiozero
   - Native Raspberry Pi library

2. **lgpio** (fallback)
   - Uses `LgpioFactory` from gpiozero
   - Modern alternative for newer RPi OS

3. **pigpio** (fallback)
   - Uses `PiGPIOFactory` from gpiozero
   - Requires pigpiod daemon running

4. **Mock Hardware** (fallback)
   - Used when `USE_MOCK_HARDWARE=true` or GPIO unavailable
   - Location: `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/infrastructure/hardware/controls/mock_controls_implementation.py`

---

## Mock Hardware Mode

**Activation:**
- Set `USE_MOCK_HARDWARE=true` in `.env` file
- Or set environment variable: `USE_MOCK_HARDWARE=true`

**Scope:**
- GPIO physical controls
- RGB LED controller
- NFC reader (alternative implementation exists)

**Controlled by:**
- `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/config/app_config.py` (line 525-530)

---

## Summary: Configurable vs. Non-Configurable

### FULLY CONFIGURABLE (via environment variables):
- Button BT0 (GPIO 23) → GPIO_BUTTON_BT0
- Button BT1 (GPIO 27) → GPIO_BUTTON_BT1
- Button BT2 (GPIO 22) → GPIO_BUTTON_BT2
- Button BT3 (GPIO 6) → GPIO_BUTTON_BT3
- Button BT4 (GPIO 5) → GPIO_BUTTON_BT4
- Encoder CLK (GPIO 26) → GPIO_VOLUME_CLK
- Encoder DT (GPIO 13) → GPIO_VOLUME_DT
- Encoder SW (GPIO 16) → GPIO_VOLUME_SW

### HARDCODED (NOT configurable via environment):
- LED Red (GPIO 25)
- LED Green (GPIO 12)
- LED Blue (GPIO 24)
- I2C Bus number (1)
- I2C Address - WM8960 DAC (0x1A)
- I2C Address - PN532 NFC (0x24)
- SPI Bus/Device/Speed (0/0/1000000)

### PARTIALLY CONFIGURABLE (via HardwareConfig dataclass, not .env):
- Button debounce time (default: 0.01s)
- Button hold time (default: 2.0s)
- Encoder step threshold (default: 2)
- Encoder acceleration (default: True)
- LED default brightness (default: 0.1)
- LED animation speed (default: 0.5)
- NFC read timeout, retry delay, max retries, tag cooldown, etc.

---

## Files Summary

### Configuration Files:
- `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/config/hardware_config.py` - GPIO pin definitions
- `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/config/app_config.py` - Configuration loading and overrides
- `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/config/button_actions_config.py` - Button action mapping
- `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/config/nfc_config.py` - NFC configuration
- `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/.env` - Environment variables file

### Implementation Files:
- `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/infrastructure/hardware/controls/gpio_controls_implementation.py` - Button/encoder implementation
- `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/infrastructure/hardware/controls/mock_controls_implementation.py` - Mock implementation
- `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/infrastructure/hardware/leds/rgb_led_controller.py` - LED implementation
- `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/infrastructure/hardware/leds/led_controller_factory.py` - LED factory
- `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/infrastructure/hardware/controls/controls_factory.py` - Controls factory
- `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/infrastructure/hardware/nfc/pn532_nfc_hardware.py` - NFC implementation

---

## GPIO Pin Summary Table

| GPIO Pin | Component | Purpose | Default Config | Env Variable | Type |
|----------|-----------|---------|---|---|---|
| 23 | BT0 | Debug print | hardware_config | GPIO_BUTTON_BT0 | Input |
| 27 | BT1 | Previous track | hardware_config | GPIO_BUTTON_BT1 | Input |
| 22 | BT2 | Debug print | hardware_config | GPIO_BUTTON_BT2 | Input |
| 6 | BT3 | Debug print | hardware_config | GPIO_BUTTON_BT3 | Input |
| 5 | BT4 | Next track | hardware_config | GPIO_BUTTON_BT4 | Input |
| 16 | Encoder SW | Play/Pause | hardware_config | GPIO_VOLUME_SW | Input |
| 26 | Encoder CLK | Volume up/down | hardware_config | GPIO_VOLUME_CLK | Input |
| 13 | Encoder DT | Volume up/down | hardware_config | GPIO_VOLUME_DT | Input |
| 25 | LED Red | Status indicator | hardware_config | NONE | Output (PWM) |
| 12 | LED Green | Status indicator | hardware_config | NONE | Output (PWM) |
| 24 | LED Blue | Status indicator | hardware_config | NONE | Output (PWM) |

**Total GPIO pins used: 11**

