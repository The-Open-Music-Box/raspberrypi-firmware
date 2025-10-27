# LED System Integration Guide

Complete guide for the RGB LED indicator system integrated into TheOpenMusicBox.

## 📋 Overview

The LED system provides visual feedback for all major application events using a priority-based state management system with automatic fallbacks.

**Hardware:** SMD5050 RGB LED
**GPIO Pins:** Red=25, Green=12, Blue=24
**States:** 17 total LED states
**Animations:** 6 animation types
**Test Coverage:** 133 tests (100% pass rate)

## 🎨 LED States Reference

### Critical Error States (Priority 98-100)
| State | Color | Animation | Priority | Trigger Event |
|-------|-------|-----------|----------|---------------|
| `ERROR_CRITICAL` | Red | Fast Blink | 100 | Critical system errors |
| `ERROR_CRASH` | Red | Solid | 99 | Application crash |
| `ERROR_BOOT_HARDWARE` | Red | Slow Blink | 98 | Boot: audio/NFC missing |
| `ERROR_PLAYBACK` | Orange | Slow Blink | 90 | Playback errors |

### NFC Association States (Priority 75-85)
| State | Color | Animation | Priority | Trigger Event |
|-------|-------|-----------|----------|---------------|
| `NFC_ASSOCIATION_MODE` | Blue | Slow Blink | 85 | Association mode active |
| `NFC_TAG_DETECTED` | Blue | Double Blink | 82 | Tag scanned during association |
| `NFC_SCANNING` | Blue | Pulse | 80 | NFC system scanning |
| `NFC_TAG_UNASSOCIATED` | Orange | Double Blink | 78 | Unassociated tag warning |
| `NFC_ASSOCIATION_SUCCESS` | Green | Double Blink | 77 | Association validated |
| `NFC_SUCCESS` | Green | Flash | 75 | Tag scan successful |
| `NFC_ERROR` | Red | Flash | 75 | NFC scan error |

### Playback States (Priority 40-50)
| State | Color | Animation | Priority | Trigger Event |
|-------|-------|-----------|----------|---------------|
| `PLAYING` | Green | Solid | 50 | Music playing |
| `PAUSED` | Yellow | Solid | 40 | Playback paused |

**Note on STOPPED state**: When playback stops (`PlaybackState.STOPPED`), the LED event handler clears PLAYING/PAUSED states and explicitly sets IDLE (solid white, priority 10) to maintain visual feedback that the system is ready. The `LEDState.STOPPED` (off, priority 35) is no longer used in normal operation.

### System States (Priority 10-95)
| State | Color | Animation | Priority | Trigger Event |
|-------|-------|-----------|----------|---------------|
| `SHUTTING_DOWN` | Red | Pulse | 95 | System shutdown |
| `STARTING` | White | Slow Blink | 30 | System starting |
| `IDLE` | White | Solid | 10 | System ready/idle |
| `OFF` | Off | Solid | 0 | LED disabled |

## 🎬 Animation Types

### Standard Animations
- **SOLID**: Constant color, no animation
- **PULSE**: Smooth breathing effect (sine wave)
- **BLINK_SLOW**: 1Hz blinking (50% duty cycle)
- **BLINK_FAST**: 3Hz blinking (50% duty cycle)
- **FLASH**: Single quick flash (200ms) then off

### Special Animations
- **DOUBLE_BLINK**: Two quick blinks with pause
  * Pattern: ON (100ms) → OFF (100ms) → ON (100ms) → OFF (100ms) → PAUSE (600ms)
  * Total cycle: 1000ms (1 second)
  * Used for: Tag detected, association success, unassociated tag warning

## 🔌 Integration Points

### 1. NFC Events (FULLY INTEGRATED ✅)

**File:** `app/src/application/services/nfc_application_service.py`

```python
# NFC scan started
await led_event_handler.on_nfc_scan_started()

# Association mode
await led_event_handler.on_nfc_association_mode_started()

# Tag detected during association
await led_event_handler.on_nfc_tag_detected()

# Association successful
await led_event_handler.on_nfc_association_success()

# Unassociated tag scanned
await led_event_handler.on_nfc_tag_unassociated()

# Tag scan successful (normal mode)
await led_event_handler.on_nfc_scan_success()

# NFC error
await led_event_handler.on_nfc_scan_error()
```

### 2. System Lifecycle Events (FULLY INTEGRATED ✅)

**File:** `app/src/application/bootstrap.py`

```python
# System starting
await led_event_handler.on_system_starting()

# System ready
await led_event_handler.on_system_ready()

# System shutting down
await led_event_handler.on_system_shutting_down()
```

### 3. Boot Error Detection (IMPLEMENTED ✅)

**File:** `app/src/application/bootstrap.py`

```python
# Audio hardware initialization failure
try:
    await audio_domain_container.start()
except Exception as e:
    await led_event_handler.on_boot_error(f"Audio initialization failed: {str(e)}")
    raise
```

**Additional boot error points to implement:**
```python
# NFC hardware initialization failure
try:
    await self._nfc_handler.initialize()
except Exception as e:
    await led_event_handler.on_boot_error(f"NFC reader not found: {str(e)}")
    raise

# Database initialization failure
try:
    db_manager.initialize()
except Exception as e:
    await led_event_handler.on_boot_error(f"Database initialization failed: {str(e)}")
    raise
```

### 4. Playback State Events (TO IMPLEMENT)

**File:** `app/src/application/services/player_application_service.py` or state manager

```python
# When playback state changes
from app.src.common.data_models import PlaybackState

async def on_state_change(new_state: PlaybackState):
    led_handler = container.get("led_event_handler")
    await led_handler.on_playback_state_changed(new_state)
```

### 5. Crash Error Detection (TO IMPLEMENT)

**Option 1: Global Exception Handler**

**File:** `app/main.py`

```python
import sys

def global_exception_handler(exc_type, exc_value, exc_traceback):
    """Catch uncaught exceptions and show crash LED."""
    logger.critical(f"CRASH: {exc_type.__name__}: {exc_value}")

    # Try to show crash LED
    try:
        import asyncio
        from app.src.infrastructure.di.container import get_container
        container = get_container()
        led_handler = container.get("led_event_handler")
        asyncio.run(led_handler.on_crash_error(f"{exc_type.__name__}: {exc_value}"))
    except:
        pass  # LED indication failed, but we're already crashing

    # Call default handler
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

# Install handler
sys.excepthook = global_exception_handler
```

**Option 2: FastAPI Exception Handler**

**File:** `app/main.py`

```python
from fastapi import Request, status
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.critical(f"CRASH: {type(exc).__name__}: {exc}")

    # Show crash LED
    try:
        led_handler = request.app.container.get("led_event_handler")
        await led_handler.on_crash_error(f"{type(exc).__name__}: {exc}")
    except:
        pass

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )
```

## 📊 Priority System & Fallback Behavior

The LED system uses a priority-based stack:
- **Higher priority states override lower priority states**
- **When high-priority state ends/times out, lower priority state automatically shows**
- **Multiple states can be active simultaneously**

### Example Scenario

```
1. App starts → STARTING (priority 30, white blink)
2. App ready → IDLE (priority 10, solid white)
   - STARTING cleared, IDLE shows
3. Start playing → PLAYING (priority 50, green solid)
   - PLAYING overrides IDLE
4. NFC scan → NFC_SCANNING (priority 80, blue pulse)
   - NFC_SCANNING overrides PLAYING
5. Scan timeout (3s) → falls back to PLAYING (green solid)
6. Stop playback → PLAYING/PAUSED cleared, IDLE set → IDLE (white solid)
```

### Timeout Behavior

| State | Timeout | Behavior |
|-------|---------|----------|
| NFC_SCANNING | 3s | Auto-clear, fallback to previous state |
| NFC_TAG_DETECTED | 1s | Auto-clear, fallback |
| NFC_TAG_UNASSOCIATED | 1.5s | Auto-clear, fallback |
| NFC_ASSOCIATION_SUCCESS | 1s | Auto-clear, fallback |
| NFC_SUCCESS | 0.5s | Quick flash, fallback |
| NFC_ERROR | 0.5s | Quick flash, fallback |
| ERROR_PLAYBACK | 5s | Auto-clear, fallback |
| All others | None | Manual clear required |

## 🧪 Testing the LED System

### 1. Basic Hardware Test

```bash
cd /Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/back
python3 test_led.py
```

Tests: 7 colors, blinking, pulsation, double blink

### 2. Integration Test

```bash
python3 test_led_integration.py
```

Tests: Bootstrap startup, LED state transitions, DI injection

### 3. Unit Tests

```bash
USE_MOCK_HARDWARE=true python -m pytest tests/unit/infrastructure/hardware/leds/ -v
USE_MOCK_HARDWARE=true python -m pytest tests/unit/application/services/test_led_event_handler_application_service.py -v
```

All 133 LED tests should pass (100%)

## 🔧 Troubleshooting

### LED Not Working

1. **Check GPIO permissions:**
   ```bash
   sudo usermod -a -G gpio $USER
   ```

2. **Verify pin connections:**
   - Red LED → GPIO 25
   - Green LED → GPIO 12
   - Blue LED → GPIO 24
   - Common Anode/Cathode wired correctly

3. **Test basic LED:**
   ```bash
   python3 test_led.py
   ```

4. **Check logs:**
   ```bash
   grep "LED" /path/to/app.log
   ```

### LED Shows Wrong State

1. Check priority levels - higher priority always wins
2. Check if state has timeout - might be auto-clearing
3. Verify state is being set: add logging to event handlers

### LED Events Not Triggering

1. Verify LED event handler is injected:
   ```python
   from app.src.infrastructure.di.container import get_container
   container = get_container()
   led_handler = container.get("led_event_handler")
   print(f"LED handler: {led_handler}")
   ```

2. Check error logs for LED event failures (non-critical warnings)

3. Verify bootstrap has LED components:
   ```python
   bootstrap = container.get("domain_bootstrap")
   print(f"LED event handler: {bootstrap.led_event_handler}")
   ```

## 📚 Architecture

```
┌─────────────────────────────────────────┐
│         Application Events              │
│  (NFC, Playback, System, Errors)        │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│     LEDEventHandler (Application)       │
│  Translates events → LED states         │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│     LEDStateManager (Application)       │
│  Priority-based state stack             │
│  Automatic fallbacks & timeouts         │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│    RGBLEDController (Infrastructure)    │
│  GPIO control, animations, PWM          │
└─────────────────────────────────────────┘
```

## 🎯 Implementation Status

- ✅ LED State Definitions (17 states)
- ✅ LED Animations (6 types including DOUBLE_BLINK)
- ✅ LED State Manager (priority stack, timeouts)
- ✅ LED Event Handler (15 event methods)
- ✅ RGB LED Controller (GPIO + Mock)
- ✅ NFC Integration (7 events connected)
- ✅ System Lifecycle Integration (3 events)
- ✅ Boot Error Detection (audio hardware)
- ⏳ Playback State Integration (ready, not connected)
- ⏳ Crash Error Detection (documented, not implemented)
- ✅ Test Coverage (133 tests, 100% pass)
- ✅ Documentation (complete)

## 📝 Next Steps

1. **Connect Playback States:**
   - Wire state manager to LED event handler
   - Test PLAYING → PAUSED → STOPPED transitions

2. **Expand Boot Error Detection:**
   - Add NFC hardware check
   - Add database initialization check

3. **Implement Crash Detection:**
   - Add global exception handler
   - Test crash LED with simulated errors

4. **Hardware Validation:**
   - Test all 17 states on real hardware
   - Verify animation timing
   - Test state priorities and fallbacks
   - Measure power consumption

5. **Performance Optimization:**
   - Profile animation thread CPU usage
   - Optimize PWM update frequency
   - Test under high system load

## 🤝 Contributing

When adding new LED states or events:

1. **Define the state** in `app/src/domain/models/led.py`
2. **Add event handler** in `led_event_handler_application_service.py`
3. **Write tests** in `test_led_event_handler_application_service.py`
4. **Connect trigger** at the appropriate application integration point
5. **Document** in this guide
6. **Test on hardware** before committing

---

**Last Updated:** 2025-01-25
**Version:** 1.0
**Author:** Claude Code (TDD Implementation)
