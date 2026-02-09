---
title: "GPIO Configuration Code Evidence"
status: active
category: hardware
last_reviewed: 2026-02-09
review_cycle: 6months
---

# GPIO Configuration - Code Evidence

## 1. Default GPIO Pin Definitions (Hardcoded)

**File:** `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/config/hardware_config.py`

```python
# Lines 21-37
# GPIO Pin Assignments (BCM numbering)
# Physical buttons
gpio_button_bt4: int = 5    # Next track
gpio_button_bt3: int = 6    # To be defined (debug print)
gpio_button_bt2: int = 22   # To be defined (debug print)
gpio_button_bt1: int = 27   # Previous track
gpio_button_bt0: int = 23   # To be defined (debug print)

# Rotary encoder for volume control
gpio_volume_encoder_sw: int = 16   # Play/Pause
gpio_volume_encoder_clk: int = 26  # Channel A (swapped for correct direction)
gpio_volume_encoder_dt: int = 13   # Channel B (swapped for correct direction)

# RGB LED pins (SMD5050) - User specified wiring
gpio_led_red: int = 25
gpio_led_green: int = 12
gpio_led_blue: int = 24  # As per user's physical wiring

# I2C settings
i2c_bus: int = 1  # I2C bus number
i2c_address_dac: int = 0x1A  # WM8960 DAC I2C address

# SPI settings (for NFC if using SPI)
spi_bus: int = 0  # SPI bus number
spi_device: int = 0  # SPI device number
spi_speed_hz: int = 1000000  # SPI speed in Hz
```

## 2. Environment Variable Overrides

**File:** `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/config/app_config.py`

**Lines 532-550 (Button GPIO Overrides):**
```python
# Button GPIO overrides
if "GPIO_BUTTON_BT0" in os.environ:
    self.hardware.gpio_button_bt0 = int(os.environ["GPIO_BUTTON_BT0"])
if "GPIO_BUTTON_BT1" in os.environ:
    self.hardware.gpio_button_bt1 = int(os.environ["GPIO_BUTTON_BT1"])
if "GPIO_BUTTON_BT2" in os.environ:
    self.hardware.gpio_button_bt2 = int(os.environ["GPIO_BUTTON_BT2"])
if "GPIO_BUTTON_BT3" in os.environ:
    self.hardware.gpio_button_bt3 = int(os.environ["GPIO_BUTTON_BT3"])
if "GPIO_BUTTON_BT4" in os.environ:
    self.hardware.gpio_button_bt4 = int(os.environ["GPIO_BUTTON_BT4"])

# Encoder GPIO overrides
if "GPIO_VOLUME_CLK" in os.environ:
    self.hardware.gpio_volume_encoder_clk = int(os.environ["GPIO_VOLUME_CLK"])
if "GPIO_VOLUME_DT" in os.environ:
    self.hardware.gpio_volume_encoder_dt = int(os.environ["GPIO_VOLUME_DT"])
if "GPIO_VOLUME_SW" in os.environ:
    self.hardware.gpio_volume_encoder_sw = int(os.environ["GPIO_VOLUME_SW"])
```

**NOTE:** LED GPIO pins (gpio_led_red, gpio_led_green, gpio_led_blue) are NOT overridable via env vars.

## 3. Button Actions Configuration

**File:** `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/config/button_actions_config.py`

```python
# Lines 48-79 - Default button configuration
DEFAULT_BUTTON_CONFIGS: List[ButtonActionConfig] = [
    ButtonActionConfig(
        button_id=0,
        gpio_pin=23,
        action_name="print_debug",
        description="BT0 (GPIO23) - To be defined (debug print)"
    ),
    ButtonActionConfig(
        button_id=1,
        gpio_pin=27,
        action_name="previous_track",
        description="BT1 (GPIO27) - Previous track"
    ),
    ButtonActionConfig(
        button_id=2,
        gpio_pin=22,
        action_name="print_debug",
        description="BT2 (GPIO22) - To be defined (debug print)"
    ),
    ButtonActionConfig(
        button_id=3,
        gpio_pin=6,
        action_name="print_debug",
        description="BT3 (GPIO6) - To be defined (debug print)"
    ),
    ButtonActionConfig(
        button_id=4,
        gpio_pin=5,
        action_name="next_track",
        description="BT4 (GPIO5) - Next track"
    ),
]
```

## 4. GPIO Implementation - Button Initialization

**File:** `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/infrastructure/hardware/controls/gpio_controls_implementation.py`

```python
# Lines 170-240 - Button initialization using configurable pins
def _init_configurable_buttons(self) -> None:
    """Initialize configurable buttons based on button_configs."""
    # ...
    for config in self._button_configs:
        if not config.enabled:
            continue
        
        device_name = f"button_{config.button_id}"
        pin = config.gpio_pin  # Gets pin from config (which may be from env var)
        description = config.description or f"Button {config.button_id}"
        
        self._devices[device_name] = Button(
            pin,
            pull_up=True,
            bounce_time=self.config.button_debounce_time,
            hold_time=self.config.button_hold_time
        )
```

## 5. GPIO Implementation - Encoder Initialization

```python
# Lines 276-312 - Encoder initialization using configurable pins
def _init_encoder(self) -> None:
    """Initialize rotary encoder for volume control."""
    self._devices['volume_encoder'] = RotaryEncoder(
        self.config.gpio_volume_encoder_clk,  # From config (env var overridable)
        self.config.gpio_volume_encoder_dt,   # From config (env var overridable)
        bounce_time=0.01,
        max_steps=0
    )
    
    self._devices['volume_encoder'].when_rotated_clockwise = self._on_volume_up
    self._devices['volume_encoder'].when_rotated_counter_clockwise = self._on_volume_down
```

## 6. LED Implementation

**File:** `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/infrastructure/hardware/leds/rgb_led_controller.py`

```python
# Lines 63-89 - LED controller initialization
def __init__(
    self,
    red_pin: int,
    green_pin: int,
    blue_pin: int,
    pwm_frequency: int = 1000,
    default_brightness: float = 1.0
):
    super().__init__(default_brightness)
    
    self._red_pin = red_pin
    self._green_pin = green_pin
    self._blue_pin = blue_pin
    self._pwm_frequency = pwm_frequency
```

**LED pins are passed from factory (which uses hardware_config):**
```python
# Lines 61-66 in led_controller_factory.py
controller = RGBLEDController(
    red_pin=hardware_config.gpio_led_red,
    green_pin=hardware_config.gpio_led_green,
    blue_pin=hardware_config.gpio_led_blue,
    default_brightness=brightness
)
```

LED pins are NOT overridable - they are only read from hardware_config.

## 7. NFC Configuration

**File:** `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/config/nfc_config.py`

```python
# Lines 42-43
# NFC hardware interface
use_spi: bool = False  # Use SPI interface (False = I2C)
i2c_bus: int = 1  # I2C bus number
i2c_address: int = 0x24  # NFC reader I2C address
```

These are NOT environment variable overridable.

## 8. Hardware Validation

**File:** `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/config/hardware_config.py`

```python
# Lines 66-99 - Validation at startup
def validate(self) -> None:
    """Validate hardware configuration values."""
    # Validate GPIO pins are in valid range (0-27 for most Pi models)
    gpio_pins = [
        self.gpio_button_bt0,
        self.gpio_button_bt1,
        self.gpio_button_bt2,
        self.gpio_button_bt3,
        self.gpio_button_bt4,
        self.gpio_volume_encoder_clk,
        self.gpio_volume_encoder_dt,
        self.gpio_volume_encoder_sw,
        self.gpio_led_red,
        self.gpio_led_green,
        self.gpio_led_blue,
    ]
    
    for pin in gpio_pins:
        if not 0 <= pin <= 27:
            raise ValueError(f"GPIO pin {pin} is out of valid range (0-27)")
    
    # Check for duplicate pin assignments
    if len(gpio_pins) != len(set(gpio_pins)):
        raise ValueError("Duplicate GPIO pin assignments detected")
```

## 9. Configuration Loading Order

**File:** `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/config/app_config.py`

```python
# Lines 65-84 - Initialization order
def __init__(self):
    self._values = {}
    self._load_environment()                  # Step 1: Load from .env
    self._validate_required_keys()
    self._validate_directories()
    
    # Step 2: Initialize sub-configurations (HardwareConfig with defaults)
    self.audio = AudioConfig()
    self.hardware = HardwareConfig()
    self.nfc = NFCConfig()
    
    # Step 3: Override sub-config values from environment variables
    self._load_subconfig_overrides()         # Applies env vars like GPIO_BUTTON_BT0
    
    # Step 4: Validate all configurations
    self._validate_configs()
```

## 10. GPIO Backend Selection

**File:** `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back/app/src/infrastructure/hardware/controls/gpio_controls_implementation.py`

```python
# Lines 33-84 - Backend auto-selection
if not USE_MOCK_HARDWARE:
    # First try gpiozero with native pin factory (RPi.GPIO backend)
    try:
        from gpiozero import Button, RotaryEncoder, Device
        from gpiozero.pins.rpigpio import RPiGPIOFactory
        Device.pin_factory = RPiGPIOFactory()
        GPIO_AVAILABLE = True
    except Exception:
        pass
    
    # If RPi.GPIO didn't work, try lgpio
    if not gpio_backend_initialized:
        try:
            from gpiozero.pins.lgpio import LgpioFactory
            Device.pin_factory = LgpioFactory()
            GPIO_AVAILABLE = True
        except Exception:
            pass
    
    # ... similar for pigpio ...
```

---

## Summary of Code Evidence

| Feature | Location | Configurable | Evidence |
|---------|----------|--------------|----------|
| Button GPIO pins (BT0-BT4) | hardware_config.py + app_config.py | YES | Lines 23-27 + 532-542 |
| Encoder CLK/DT/SW pins | hardware_config.py + app_config.py | YES | Lines 30-32 + 544-550 |
| LED RGB pins | hardware_config.py only | NO | Lines 35-37 (no override in app_config) |
| I2C bus/addresses | hardware_config.py + nfc_config.py | NO | Lines 51-53 (no override mechanism) |
| SPI configuration | hardware_config.py | NO | Lines 55-58 (no override mechanism) |
| Button debounce/hold | hardware_config.py | PARTIAL | Lines 40-41 (static, not env var) |
| Encoder step/accel | hardware_config.py | PARTIAL | Lines 44-45 (static, not env var) |
| LED brightness/speed | hardware_config.py | PARTIAL | Lines 48-49 (static, not env var) |

