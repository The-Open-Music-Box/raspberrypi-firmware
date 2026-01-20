# LED Color Codes Reference

This document describes the LED indicator system used on TheOpenMusicBox RPI firmware, including color codes, animations, and their meanings.

## Hardware Configuration

| Channel | GPIO Pin | Type |
|---------|----------|------|
| Red     | 25       | PWM  |
| Green   | 12       | PWM  |
| Blue    | 24       | PWM  |

**LED Type:** SMD5050 RGB (common anode)

> **Note:** LED GPIO pins are currently hardcoded. See [GPIO_QUICK_REFERENCE.md](./GPIO_QUICK_REFERENCE.md) for instructions on making them configurable via environment variables.

---

## LED States and Color Codes

The LED system uses a **priority-based state stack**. Higher priority states override lower priority states. When a temporary state expires, the next highest priority state is displayed.

### Critical Error States (Priority 98-100)

| State | Color | Animation | Priority | Timeout | Description |
|-------|-------|-----------|----------|---------|-------------|
| `ERROR_CRITICAL` | Red | Fast blink (3Hz) | 100 | Permanent | Critical system error |
| `ERROR_CRASH` | Red | Solid | 99 | Permanent | Application crash - requires manual intervention |
| `ERROR_BOOT_HARDWARE` | Red | Slow blink (1Hz) | 98 | Permanent | Hardware error during boot (missing components) |

### Playback Error States (Priority 90)

| State | Color | Animation | Priority | Timeout | Description |
|-------|-------|-----------|----------|---------|-------------|
| `ERROR_PLAYBACK` | Orange | Slow blink (1Hz) | 90 | 5 seconds | Audio playback error |

### NFC States (Priority 85-95)

#### NFC Events (Temporary - Priority 95)

| State | Color | Animation | Priority | Timeout | Description |
|-------|-------|-----------|----------|---------|-------------|
| `NFC_SUCCESS` | Green | Flash | 95 | 0.5s | NFC tag successfully read and associated |
| `NFC_ERROR` | Red | Flash | 95 | 0.5s | NFC read error |
| `NFC_TAG_UNASSOCIATED` | Orange | Double blink | 95 | 1s | NFC tag detected but not associated with content |

#### NFC Status (Persistent - Priority 85)

| State | Color | Animation | Priority | Timeout | Description |
|-------|-------|-----------|----------|---------|-------------|
| `NFC_ASSOCIATION_MODE` | Blue | Pulse | 85 | Permanent | NFC association mode active (waiting for tag) |

### Playback States (Priority 35-50)

| State | Color | Animation | Priority | Timeout | Description |
|-------|-------|-----------|----------|---------|-------------|
| `PLAYING` | Green | Solid | 50 | Permanent | Audio playback in progress |
| `PAUSED` | Yellow | Solid | 40 | Permanent | Playback paused |
| `STOPPED` | Off | - | 35 | Permanent | Playback stopped |

### System States (Priority 10-30)

| State | Color | Animation | Priority | Timeout | Description |
|-------|-------|-----------|----------|---------|-------------|
| `STARTING` | White | Slow blink (1Hz) | 30 | Until ready | System starting up |
| `IDLE` | White | Solid | 10 | Permanent | System ready and waiting |
| `OFF` | Off | - | 0 | Permanent | LED disabled |

---

## Color Palette

### Primary Colors

| Name | R | G | B | Hex | Usage |
|------|---|---|---|-----|-------|
| RED | 255 | 0 | 0 | `#FF0000` | Errors, NFC errors |
| GREEN | 0 | 255 | 0 | `#00FF00` | Success, playing |
| BLUE | 0 | 0 | 255 | `#0000FF` | NFC association mode |

### Secondary Colors

| Name | R | G | B | Hex | Usage |
|------|---|---|---|-----|-------|
| YELLOW | 255 | 255 | 0 | `#FFFF00` | Paused state |
| CYAN | 0 | 255 | 255 | `#00FFFF` | Reserved |
| MAGENTA | 255 | 0 | 255 | `#FF00FF` | Reserved |

### Tertiary Colors

| Name | R | G | B | Hex | Usage |
|------|---|---|---|-----|-------|
| ORANGE | 255 | 128 | 0 | `#FF8000` | Warnings, playback errors, unassociated tags |
| PURPLE | 128 | 0 | 255 | `#8000FF` | Reserved |

### Neutral Colors

| Name | R | G | B | Hex | Usage |
|------|---|---|---|-----|-------|
| WHITE | 255 | 255 | 255 | `#FFFFFF` | Idle, starting |
| WARM_WHITE | 255 | 200 | 150 | `#FFC896` | Reserved |
| OFF | 0 | 0 | 0 | `#000000` | LED off |

---

## Animation Types

| Animation | Description | Speed |
|-----------|-------------|-------|
| `SOLID` | Constant color, no animation | - |
| `PULSE` | Smooth breathing effect (sine wave) | Configurable |
| `BLINK_SLOW` | On/off blinking | 1 Hz (1 cycle/sec) |
| `BLINK_FAST` | Rapid on/off blinking | 3 Hz (3 cycles/sec) |
| `FLASH` | Single quick flash then off | 200ms |
| `DOUBLE_BLINK` | Two quick blinks then pause | ON(100ms) OFF(100ms) ON(100ms) OFF(100ms) PAUSE(600ms) |

---

## Priority System

The LED state manager uses a priority-based stack system:

```
Priority Levels:
  100 ─────────── CRITICAL (errors)
   99 ─────────── ERROR_CRASH
   98 ─────────── ERROR_BOOT
   95 ─────────── NFC_EVENT (temporary)
   90 ─────────── ERROR_PLAYBACK
   85 ─────────── NFC_ASSOCIATION_MODE (persistent)
   50 ─────────── PLAYBACK_ACTIVE (playing)
   40 ─────────── PLAYBACK_INACTIVE (paused)
   35 ─────────── PLAYBACK_STOPPED
   30 ─────────── SYSTEM_STARTING
   10 ─────────── IDLE
    0 ─────────── OFF
```

**Rules:**
- Higher priority states always override lower priority states
- Temporary states (with timeout) automatically revert to the next highest state
- Permanent states remain until explicitly cleared
- Multiple states can exist in the stack simultaneously

---

## Quick Visual Reference

```
RED solid         = App crashed (critical)
RED fast blink    = System error (critical)
RED slow blink    = Boot error (hardware missing)
RED flash         = NFC read failed

ORANGE slow blink = Playback error
ORANGE dbl blink  = NFC tag not associated

BLUE pulse        = NFC association mode active

GREEN solid       = Playing music
GREEN flash       = NFC success

YELLOW solid      = Paused

WHITE slow blink  = System starting
WHITE solid       = Ready (idle)

OFF               = Stopped / disabled
```

---

## Code References

- **LED Model Definitions:** `back/app/src/domain/models/led.py`
- **LED Controller:** `back/app/src/infrastructure/hardware/leds/rgb_led_controller.py`
- **LED State Manager:** `back/app/src/application/services/led_state_manager_application_service.py`
- **GPIO Configuration:** `back/app/src/config/hardware_config.py`

---

## See Also

- [GPIO_QUICK_REFERENCE.md](./GPIO_QUICK_REFERENCE.md) - GPIO pin configuration
- [GPIO_ANALYSIS.md](./GPIO_ANALYSIS.md) - Complete GPIO technical analysis
- [GPIO_DOCUMENTATION_INDEX.md](./GPIO_DOCUMENTATION_INDEX.md) - Documentation index

---

**Last Updated:** 2025-01-20
**Source:** `back/app/src/domain/models/led.py`
