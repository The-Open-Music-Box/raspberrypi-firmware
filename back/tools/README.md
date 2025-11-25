# GPIO Testing Tools - TheOpenMusicBox

This directory contains standalone diagnostic scripts for testing physical GPIO controls on the Raspberry Pi.

## Overview

These tools allow you to test GPIO hardware independently from the main application, making it easier to diagnose wiring issues, verify functionality, and troubleshoot problems.

## Available Test Scripts

### 1. Button Testing

#### `test_buttons_standalone.py`

Comprehensive button testing script for all physical buttons.

**What it tests:**
- All configured buttons (BT0-BT4)
- Encoder switch (Play/Pause)
- Button debouncing
- Press counting and timing

**Usage:**
```bash
cd /home/admin/tomb/
source venv/bin/activate
python tools/test_buttons_standalone.py
```

**See also:** [README_BUTTON_TEST.md](README_BUTTON_TEST.md) for detailed button testing documentation.

---

### 2. Rotary Encoder Testing

#### `test_rotary_encoder.py`

Standalone test for the rotary encoder (volume control).

**What it tests:**
- Encoder rotation detection (clockwise/counter-clockwise)
- Encoder switch (Play/Pause button)
- Rotation counting
- Direction accuracy

**Hardware tested:**
- GPIO 26: Encoder CLK (Channel A)
- GPIO 13: Encoder DT (Channel B)
- GPIO 16: Encoder Switch

**Usage:**
```bash
cd /home/admin/tomb/
source venv/bin/activate

# Run with default 10-second test
python tools/test_rotary_encoder.py

# Run with custom duration
python tools/test_rotary_encoder.py --duration 30
```

**Expected output:**
```
============================================================
🎛️  Rotary Encoder Test Script
============================================================

Hardware Configuration:
  - Switch (Play/Pause): GPIO 16
  - CLK (Channel A):     GPIO 26
  - DT (Channel B):      GPIO 13

Test Duration: 10 seconds
------------------------------------------------------------
✅ Using lgpio backend (modern, recommended)

🔧 Creating RotaryEncoder(26, 13)...
✅ Encoder created successfully!
🔧 Creating Button(16)...
✅ Switch button created successfully!

============================================================
🎯 TEST STARTED - Rotate encoder and press switch NOW!
============================================================
🔊 CW rotation #1 (CW: 1, CCW: 0)
🔉 CCW rotation #2 (CW: 1, CCW: 1)
🎵 Switch pressed (press #1)
🎵 Switch released

============================================================
📊 TEST RESULTS
============================================================
Total Rotations: 2
  - Clockwise (CW):        1
  - Counter-Clockwise:     1
Switch Presses:      1
------------------------------------------------------------
✅ SUCCESS! Encoder is working correctly
```

**Troubleshooting:**

If no events are detected:

1. **Check wiring connections:**
   - GPIO 26 (pin 37) → Encoder CLK pin
   - GPIO 13 (pin 33) → Encoder DT pin
   - GPIO 16 (pin 36) → Encoder SW pin
   - GND → Encoder GND pin

2. **Verify encoder power** (if 5V/3.3V required)

3. **Install required libraries:**
   ```bash
   pip install lgpio
   ```

4. **Check GPIO permissions:**
   ```bash
   sudo usermod -aG gpio $USER
   # Log out and back in
   ```

---

### 3. Simple GPIO Tests

#### `gpio_simple_test.py`

Basic GPIO functionality test.

#### `gpio_diagnostic.py`

Detailed GPIO diagnostic with pin state monitoring.

#### `gpio_tester.py`

Interactive GPIO pin tester.

---

## GPIO Pin Configuration

### Current Hardware Setup

| Component | GPIO | Pin | Function |
|-----------|------|-----|----------|
| **Buttons** |
| BT0 | 23 | 16 | Debug/Custom |
| BT1 | 27 | 13 | Previous Track |
| BT2 | 22 | 15 | Debug/Custom |
| BT3 | 6 | 31 | Debug/Custom |
| BT4 | 5 | 29 | Next Track |
| **Rotary Encoder** |
| Encoder CLK | 26 | 37 | Rotation Detection (Channel A) |
| Encoder DT | 13 | 33 | Rotation Detection (Channel B) |
| Encoder SW | 16 | 36 | Play/Pause Switch |

### GPIO Backend

These scripts use **lgpio** as the primary GPIO backend:
- Modern, actively maintained
- No kernel-level pin locking issues
- Better compatibility with recent Raspberry Pi OS versions
- Fallback to RPi.GPIO if lgpio unavailable

---

## Common Issues and Solutions

### Issue: "No GPIO backend available"

**Solution:**
```bash
# Install lgpio
pip install lgpio

# Or system-wide
sudo apt-get install python3-lgpio
```

### Issue: "Permission denied" errors

**Solution:**
```bash
# Add user to gpio group
sudo usermod -aG gpio $USER

# Reboot or re-login
```

### Issue: Encoder detects rotations but volume doesn't change enough

The encoder sensitivity is controlled by two parameters in the main application:

1. **`volume_step`** in `back/app/src/config/audio_config.py`:
   - Current: 10% per rotation
   - Adjust range: 5-20%

2. **`bounce_time`** in `back/app/src/infrastructure/hardware/controls/gpio_controls_implementation.py`:
   - Current: 0.002 seconds (2ms)
   - Lower = more sensitive
   - Higher = less sensitive but more stable

### Issue: Buttons register multiple presses

**Cause:** Mechanical bounce (contact oscillation)

**Solution:**
- Increase `bounce_time` in configuration
- Current default: 0.05 seconds (50ms)
- Recommended range: 0.02-0.1 seconds

### Issue: "Failed to add edge detection"

**Cause:** RPi.GPIO backend locking pins after crash

**Solution:**
```bash
# Cleanup GPIO state
python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); GPIO.cleanup()"

# Or restart the Pi
sudo reboot
```

**Better:** Use lgpio backend (automatically prioritized in new code)

---

## Development Workflow

### 1. Hardware Setup
1. Connect buttons and encoder to GPIO pins
2. Verify wiring with multimeter
3. Check power supply (3.3V or 5V as needed)

### 2. Initial Testing
```bash
# Test rotary encoder
python tools/test_rotary_encoder.py

# Test all buttons
python tools/test_buttons_standalone.py
```

### 3. Fine-Tuning
- Adjust encoder sensitivity in config files
- Modify button debounce times
- Update pin assignments if needed

### 4. Integration Testing
```bash
# Run full application
python start_app.py

# Monitor logs
tail -f /tmp/tomb.log
```

---

## Additional Resources

- **Main README**: [../../README.md](../../README.md)
- **Hardware Documentation**: [../app/documentation/HARDWARE.md](../app/documentation/HARDWARE.md)
- **Button Test Details**: [README_BUTTON_TEST.md](README_BUTTON_TEST.md)
- **Configuration Files**:
  - GPIO pins: `back/app/src/config/hardware_config.py`
  - Audio/volume: `back/app/src/config/audio_config.py`
  - Button actions: `back/app/src/config/button_actions_config.py`

---

## Other Tools

### `convert_flac_to_mp3.sh`
Batch convert FLAC audio files to MP3.

### `fix_audio_permissions.sh`
Fix ALSA audio permissions and device access.

### `diagnose_boot_issue.py`
Diagnose application startup problems.

---

**Note:** All test scripts are designed to be independent of the main application and can be run without starting the full TheOpenMusicBox service.
