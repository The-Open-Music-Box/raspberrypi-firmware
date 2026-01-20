# GPIO Configuration Documentation Index

This directory contains comprehensive documentation about GPIO pin usage, configuration, and management in TheOpenMusicBox RPi Firmware.

## Document Overview

### 1. GPIO_ANALYSIS.md
**Purpose:** Comprehensive technical analysis of all GPIO usage
**Audience:** Developers, technical architects
**Contents:**
- Detailed breakdown of all GPIO pins and their purposes
- Configuration mechanisms (hardcoded defaults vs. environment overrides)
- I2C and SPI communication details
- Backend driver information
- Complete file location references with line numbers

**Best for:**
- Understanding the complete GPIO architecture
- Identifying all hardware components and their pin assignments
- Learning about configuration validation and loading order

---

### 2. GPIO_QUICK_REFERENCE.md
**Purpose:** Quick how-to guide for GPIO configuration
**Audience:** Users, developers doing hardware customization
**Contents:**
- Quick setup instructions for overriding GPIO pins
- Step-by-step guide to modify configuration
- Common GPIO pin conflicts on Raspberry Pi
- Debugging tips and troubleshooting
- Example .env configurations

**Best for:**
- Quickly finding how to change GPIO pin assignments
- Understanding available configuration options
- Troubleshooting GPIO-related issues
- Adding new configurable pins (LED GPIO example provided)

---

### 3. LED_COLOR_CODES.md
**Purpose:** Complete LED indicator system documentation
**Audience:** Users, developers, hardware integrators
**Contents:**
- LED hardware configuration (GPIO pins)
- Color codes for each system state
- Animation types and descriptions
- Priority-based state management
- Quick visual reference guide

**Best for:**
- Understanding what each LED color/animation means
- Debugging LED behavior issues
- Customizing LED feedback
- Hardware integration reference

---

### 4. GPIO_CODE_EVIDENCE.md
**Purpose:** Detailed code snippets with exact line references
**Audience:** Developers, code reviewers
**Contents:**
- Actual code snippets from configuration files
- Method implementations with line numbers
- Configuration loading order in code
- Backend selection logic
- Validation logic

**Best for:**
- Reviewing actual implementation code
- Understanding initialization sequence
- Finding where specific logic is implemented
- Code review and maintenance

---

## Quick Start

### To change GPIO pin assignments:

1. **Read:** GPIO_QUICK_REFERENCE.md → "How to Override GPIO Pin Configuration"
2. **Edit:** `/back/.env` file
3. **Set:** Environment variables like `GPIO_BUTTON_BT0=<pin_number>`
4. **Restart:** Application

### To understand GPIO architecture:

1. **Read:** GPIO_ANALYSIS.md → "Summary" section
2. **Review:** GPIO_ANALYSIS.md → "GPIO Pin Definitions and Usage"
3. **Deep dive:** GPIO_CODE_EVIDENCE.md for implementation details

### To add LED GPIO configuration:

1. **Read:** GPIO_QUICK_REFERENCE.md → "Adding Support for LED GPIO Configuration"
2. **Follow:** Code example provided
3. **Modify:** `app_config.py` in `_load_subconfig_overrides()` method
4. **Test:** Set environment variables and verify in logs

---

## GPIO Pin Reference

### Currently Configurable (8 pins)
```
Button pins:
  GPIO 5   (BT4) - Next track       → GPIO_BUTTON_BT4
  GPIO 6   (BT3) - Debug print      → GPIO_BUTTON_BT3
  GPIO 22  (BT2) - Debug print      → GPIO_BUTTON_BT2
  GPIO 23  (BT0) - Debug print      → GPIO_BUTTON_BT0
  GPIO 27  (BT1) - Previous track   → GPIO_BUTTON_BT1

Encoder pins:
  GPIO 16  (SW)  - Play/Pause       → GPIO_VOLUME_SW
  GPIO 26  (CLK) - Volume control   → GPIO_VOLUME_CLK
  GPIO 13  (DT)  - Volume control   → GPIO_VOLUME_DT
```

### Currently Hardcoded (3 pins)
```
LED pins (RGB):
  GPIO 25 - Red
  GPIO 12 - Green
  GPIO 24 - Blue
```

### Communication Buses
```
I2C Bus 1:
  - WM8960 DAC (Audio)  @ 0x1A
  - PN532 NFC Reader    @ 0x24

SPI Bus 0: (configured but not used)
  - Device 0, Speed 1 MHz
```

---

## Key Files Referenced

### Configuration Files
- `back/app/src/config/hardware_config.py` - Default GPIO pins
- `back/app/src/config/app_config.py` - Environment variable loading
- `back/app/src/config/button_actions_config.py` - Button mappings
- `back/app/src/config/nfc_config.py` - NFC settings
- `back/.env` - Environment variables

### Implementation Files
- `back/app/src/infrastructure/hardware/controls/gpio_controls_implementation.py` - Button/encoder driver
- `back/app/src/infrastructure/hardware/leds/rgb_led_controller.py` - LED driver
- `back/app/src/infrastructure/hardware/leds/led_controller_factory.py` - LED factory
- `back/app/src/infrastructure/hardware/nfc/pn532_nfc_hardware.py` - NFC driver

---

## Configuration Methods

### Method 1: Environment Variables (Recommended)
- Edit `.env` file or set at runtime
- Easiest for non-default pin assignments
- No code changes needed

### Method 2: Hardcoded Defaults
- Defined in `hardware_config.py`
- Used when no environment variables set
- Requires code modification

### Method 3: Mock Hardware Mode
- Set `USE_MOCK_HARDWARE=true`
- Useful for development/testing
- Falls back automatically if GPIO unavailable

### Method 4: Custom Code
- Modify configuration classes directly
- Required for non-standard configurations
- Not recommended for regular use

---

## Validation & Safety

All GPIO configurations are validated at startup:
- Pin number range: 0-27 (Raspberry Pi BCM numbering)
- No duplicate pin assignments
- Button timing parameters validation
- Hardware availability checks

**Validation errors terminate application startup with clear error messages.**

---

## Hardware Backend Support

The GPIO implementation automatically selects the best available backend:

1. **RPi.GPIO** (preferred)
   - Native Raspberry Pi library
   - Best performance

2. **lgpio** (modern)
   - Modern alternative for newer RPi OS
   - Better hardware support

3. **pigpio** (daemon-based)
   - Requires pigpiod daemon
   - Remote GPIO support

4. **Mock Hardware** (fallback)
   - Simulated GPIO
   - No hardware required
   - Useful for testing

---

## ESP32 Firmware

No ESP32 firmware found in this project. GPIO configuration is specific to:
- Raspberry Pi (main platform)
- Compatible SBCs with GPIO headers
- I2C/SPI communication protocols

---

## Related Documentation

For related topics, see:
- Audio configuration: `back/app/src/config/audio_config.py`
- NFC configuration: `back/app/src/config/nfc_config.py`
- Application startup: `back/app/main.py`
- Hardware factory: `back/app/src/infrastructure/hardware/` directory

---

## Support & Troubleshooting

### Common Issues

**GPIO not working?**
- Check logs for backend selection: `grep "GPIO backend" logs/app.log`
- Verify pins in valid range: 0-27
- Ensure no duplicate pin assignments
- Try mock mode: `USE_MOCK_HARDWARE=true`

**Pins not changing from defaults?**
- Verify environment variable names match exactly
- Check `.env` file is in correct location
- Ensure .env file is loaded before application starts
- Review logs: `grep "GPIO_" logs/app.log`

**Pin conflicts?**
- GPIO 2, 3 reserved for I2C (SCL, SDA)
- GPIO 0, 1 reserved for HAT EEPROM
- Current configuration avoids reserved pins
- Use GPIO_ANALYSIS.md pin reference to find alternatives

**LED pins not configurable?**
- Not yet implemented
- See GPIO_QUICK_REFERENCE.md "Adding Support for LED GPIO Configuration"
- Code example provided for implementation

---

## Version Information

- **Project:** TheOpenMusicBox RPI Firmware
- **Analysis Date:** 2025-11-21
- **GPIO Library:** gpiozero
- **Target Platform:** Raspberry Pi (GPIO 0-27, BCM numbering)
- **Python Version:** 3.11+

---

## Document Maintenance

These documents are auto-generated from codebase analysis.
To update:
1. Review source files mentioned in each document
2. Update code references if files have moved
3. Verify line numbers match current code
4. Test configuration examples

---

## See Also

For more information on Raspberry Pi GPIO:
- [Raspberry Pi GPIO Documentation](https://www.raspberrypi.com/documentation/computers/gpio.html)
- [gpiozero Library](https://gpiozero.readthedocs.io/)
- [BCM Pin Numbering](https://pinout.xyz/)

---

**Last Updated:** 2025-11-21
**Maintainer:** TheOpenMusicBox Project
**Status:** Current
