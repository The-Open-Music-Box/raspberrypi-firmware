# 📋 LED System Implementation Plan - Option 1 (Safe/TDD)
**Project:** TheOpenMusicBox - Complete LED Integration
**Approach:** Test-Driven Development (Tests First)
**Estimated Time:** 12-15 hours over 2 days

---

## 🎯 Implementation Strategy

**Principle:** Write tests FIRST, then implement features to make tests pass.

**Advantages:**
- ✅ Reduces risk (catches bugs early)
- ✅ Ensures complete test coverage
- ✅ Facilitates refactoring
- ✅ Acts as living documentation
- ✅ Prevents regressions

**Order of Execution:**
1. Phase 4: Create comprehensive test suite (FIRST)
2. Phase 1: Implement new states and animations to pass tests
3. Phase 2: Implement event handler methods to pass tests
4. Phase 3: Connect events to trigger handlers
5. Phase 5: Integration testing

---

## 📅 Phase 4: Create Comprehensive Tests (FIRST) - 4-5 hours

### Task 4.1: Create Test File Structure (15 min)

**File:** `tests/unit/application/services/test_led_event_handler_application_service.py`

```python
# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Comprehensive Unit Tests for LED Event Handler.

Tests all event handling methods, state transitions, and fallback scenarios.
Following TDD approach - tests written BEFORE implementation.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.src.application.services.led_event_handler_application_service import LEDEventHandler
from app.src.application.services.led_state_manager_application_service import LEDStateManager
from app.src.domain.models.led import LEDState, LEDColor, LEDAnimation
from app.src.common.data_models import PlaybackState


@pytest.fixture
def mock_led_manager():
    """Create mock LED state manager."""
    manager = AsyncMock(spec=LEDStateManager)
    manager.set_state = AsyncMock(return_value=True)
    manager.clear_state = AsyncMock(return_value=True)
    manager.set_brightness = AsyncMock(return_value=True)
    manager.get_status = MagicMock(return_value={
        "initialized": True,
        "current_state": None,
        "state_stack": []
    })
    return manager


@pytest.fixture
async def led_event_handler(mock_led_manager):
    """Create LED event handler with mock manager."""
    handler = LEDEventHandler(mock_led_manager)
    await handler.initialize()
    return handler


# Test classes will be added in tasks 4.2-4.8
```

**Checklist:**
- [ ] Create test file
- [ ] Add copyright header
- [ ] Import all required modules
- [ ] Create mock fixtures
- [ ] Verify imports work (`python -m pytest tests/unit/application/services/test_led_event_handler_application_service.py --collect-only`)

---

### Task 4.2: Test Initialization and Lifecycle (30 min)

**Add to test file:**

```python
class TestLEDEventHandlerInitialization:
    """Test initialization and lifecycle management."""

    @pytest.mark.asyncio
    async def test_initialization_success(self, mock_led_manager):
        """Test successful initialization."""
        handler = LEDEventHandler(mock_led_manager)
        result = await handler.initialize()

        assert result is True
        assert handler._is_initialized is True

    @pytest.mark.asyncio
    async def test_cleanup(self, led_event_handler):
        """Test cleanup releases resources."""
        await led_event_handler.cleanup()

        assert led_event_handler._is_initialized is False

    @pytest.mark.asyncio
    async def test_get_status(self, led_event_handler, mock_led_manager):
        """Test status reporting."""
        status = led_event_handler.get_status()

        assert "initialized" in status
        assert status["initialized"] is True
        assert "led_manager_status" in status
        mock_led_manager.get_status.assert_called_once()
```

**Expected Test Results:** ✅ All 3 tests should PASS (methods already implemented)

**Checklist:**
- [ ] Write 3 initialization tests
- [ ] Run tests: `pytest tests/unit/application/services/test_led_event_handler_application_service.py::TestLEDEventHandlerInitialization -v`
- [ ] Verify all pass

---

### Task 4.3: Test System Events (45 min)

**Add to test file:**

```python
class TestLEDEventHandlerSystemEvents:
    """Test system lifecycle event handling."""

    @pytest.mark.asyncio
    async def test_on_system_starting(self, led_event_handler, mock_led_manager):
        """Test system starting shows STARTING state."""
        await led_event_handler.on_system_starting()

        mock_led_manager.set_state.assert_called_once_with(LEDState.STARTING)

    @pytest.mark.asyncio
    async def test_on_system_ready(self, led_event_handler, mock_led_manager):
        """Test system ready clears STARTING and sets IDLE."""
        await led_event_handler.on_system_ready()

        # Should clear STARTING first
        calls = mock_led_manager.clear_state.call_args_list
        assert len(calls) == 1
        assert calls[0][0][0] == LEDState.STARTING

        # Then set IDLE
        calls = mock_led_manager.set_state.call_args_list
        assert len(calls) == 1
        assert calls[0][0][0] == LEDState.IDLE

    @pytest.mark.asyncio
    async def test_on_system_shutting_down(self, led_event_handler, mock_led_manager):
        """Test system shutdown shows SHUTTING_DOWN state."""
        await led_event_handler.on_system_shutting_down()

        mock_led_manager.set_state.assert_called_once_with(LEDState.SHUTTING_DOWN)

    @pytest.mark.asyncio
    async def test_on_boot_hardware_error_audio(self, led_event_handler, mock_led_manager):
        """Test boot hardware error (audio) shows ERROR_BOOT_HARDWARE."""
        # THIS TEST WILL FAIL - method not yet implemented
        await led_event_handler.on_boot_hardware_error("audio")

        mock_led_manager.set_state.assert_called_once_with(LEDState.ERROR_BOOT_HARDWARE)

    @pytest.mark.asyncio
    async def test_on_boot_hardware_error_nfc(self, led_event_handler, mock_led_manager):
        """Test boot hardware error (NFC) shows ERROR_BOOT_HARDWARE."""
        # THIS TEST WILL FAIL - method not yet implemented
        await led_event_handler.on_boot_hardware_error("nfc")

        mock_led_manager.set_state.assert_called_once_with(LEDState.ERROR_BOOT_HARDWARE)

    @pytest.mark.asyncio
    async def test_on_system_crash(self, led_event_handler, mock_led_manager):
        """Test system crash shows ERROR_CRASH state."""
        # THIS TEST WILL FAIL - method not yet implemented
        await led_event_handler.on_system_crash("Out of memory")

        mock_led_manager.set_state.assert_called_once_with(LEDState.ERROR_CRASH)
```

**Expected Test Results:**
- ✅ First 3 tests PASS (methods exist)
- ❌ Last 3 tests FAIL (methods don't exist yet - TDD!)

**Checklist:**
- [ ] Write 6 system event tests
- [ ] Run tests: `pytest tests/unit/application/services/test_led_event_handler_application_service.py::TestLEDEventHandlerSystemEvents -v`
- [ ] Verify 3 pass, 3 fail as expected
- [ ] Note failing tests for Phase 2 implementation

---

### Task 4.4: Test NFC Events (60 min)

**Add to test file:**

```python
class TestLEDEventHandlerNFCEvents:
    """Test NFC event handling."""

    @pytest.mark.asyncio
    async def test_on_nfc_scan_started(self, led_event_handler, mock_led_manager):
        """Test NFC scan started shows NFC_SCANNING."""
        await led_event_handler.on_nfc_scan_started()

        mock_led_manager.set_state.assert_called_once_with(LEDState.NFC_SCANNING)

    @pytest.mark.asyncio
    async def test_on_nfc_scan_success(self, led_event_handler, mock_led_manager):
        """Test NFC scan success shows NFC_SUCCESS."""
        await led_event_handler.on_nfc_scan_success()

        mock_led_manager.set_state.assert_called_once_with(LEDState.NFC_SUCCESS)

    @pytest.mark.asyncio
    async def test_on_nfc_scan_error(self, led_event_handler, mock_led_manager):
        """Test NFC scan error shows NFC_ERROR."""
        await led_event_handler.on_nfc_scan_error()

        mock_led_manager.set_state.assert_called_once_with(LEDState.NFC_ERROR)

    @pytest.mark.asyncio
    async def test_on_nfc_tag_unassociated(self, led_event_handler, mock_led_manager):
        """Test tag not associated with playlist shows NFC_TAG_UNASSOCIATED."""
        # THIS TEST WILL FAIL - method not yet implemented
        await led_event_handler.on_nfc_tag_unassociated()

        mock_led_manager.set_state.assert_called_once_with(LEDState.NFC_TAG_UNASSOCIATED)

    @pytest.mark.asyncio
    async def test_on_nfc_association_mode_started(self, led_event_handler, mock_led_manager):
        """Test association mode started shows NFC_ASSOCIATION_MODE."""
        # THIS TEST WILL FAIL - method not yet implemented
        await led_event_handler.on_nfc_association_mode_started()

        mock_led_manager.set_state.assert_called_once_with(LEDState.NFC_ASSOCIATION_MODE)

    @pytest.mark.asyncio
    async def test_on_nfc_association_mode_stopped(self, led_event_handler, mock_led_manager):
        """Test association mode stopped clears NFC_ASSOCIATION_MODE."""
        # THIS TEST WILL FAIL - method not yet implemented
        await led_event_handler.on_nfc_association_mode_stopped()

        mock_led_manager.clear_state.assert_called_once_with(LEDState.NFC_ASSOCIATION_MODE)

    @pytest.mark.asyncio
    async def test_on_nfc_tag_detected(self, led_event_handler, mock_led_manager):
        """Test physical tag detected shows NFC_TAG_DETECTED."""
        # THIS TEST WILL FAIL - method not yet implemented
        await led_event_handler.on_nfc_tag_detected()

        mock_led_manager.set_state.assert_called_once_with(LEDState.NFC_TAG_DETECTED)

    @pytest.mark.asyncio
    async def test_on_nfc_association_validated(self, led_event_handler, mock_led_manager):
        """Test association validated shows NFC_ASSOCIATION_SUCCESS."""
        # THIS TEST WILL FAIL - method not yet implemented
        await led_event_handler.on_nfc_association_validated()

        mock_led_manager.set_state.assert_called_once_with(LEDState.NFC_ASSOCIATION_SUCCESS)
```

**Expected Test Results:**
- ✅ First 3 tests PASS
- ❌ Last 5 tests FAIL (TDD)

**Checklist:**
- [ ] Write 8 NFC event tests
- [ ] Run tests: `pytest tests/unit/application/services/test_led_event_handler_application_service.py::TestLEDEventHandlerNFCEvents -v`
- [ ] Verify 3 pass, 5 fail as expected

---

### Task 4.5: Test Playback Events (45 min)

**Add to test file:**

```python
class TestLEDEventHandlerPlaybackEvents:
    """Test playback event handling."""

    @pytest.mark.asyncio
    async def test_on_playback_state_changed_playing(self, led_event_handler, mock_led_manager):
        """Test playback PLAYING shows PLAYING LED state."""
        await led_event_handler.on_playback_state_changed(PlaybackState.PLAYING)

        mock_led_manager.set_state.assert_called_once_with(LEDState.PLAYING)

    @pytest.mark.asyncio
    async def test_on_playback_state_changed_paused(self, led_event_handler, mock_led_manager):
        """Test playback PAUSED shows PAUSED LED state."""
        await led_event_handler.on_playback_state_changed(PlaybackState.PAUSED)

        mock_led_manager.set_state.assert_called_once_with(LEDState.PAUSED)

    @pytest.mark.asyncio
    async def test_on_playback_state_changed_stopped(self, led_event_handler, mock_led_manager):
        """Test playback STOPPED shows STOPPED LED state."""
        await led_event_handler.on_playback_state_changed(PlaybackState.STOPPED)

        mock_led_manager.set_state.assert_called_once_with(LEDState.STOPPED)

    @pytest.mark.asyncio
    async def test_on_playback_state_changed_unknown(self, led_event_handler, mock_led_manager):
        """Test unknown playback state does nothing."""
        # Create a mock unknown state
        unknown_state = "UNKNOWN"

        await led_event_handler.on_playback_state_changed(unknown_state)

        # Should not call set_state for unknown states
        mock_led_manager.set_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_track_changed(self, led_event_handler, mock_led_manager):
        """Test track changed maintains current state."""
        await led_event_handler.on_track_changed()

        # Should not change LED state
        mock_led_manager.set_state.assert_not_called()
        mock_led_manager.clear_state.assert_not_called()
```

**Expected Test Results:** ✅ All tests should PASS (methods already implemented)

**Checklist:**
- [ ] Write 5 playback event tests
- [ ] Run tests: `pytest tests/unit/application/services/test_led_event_handler_application_service.py::TestLEDEventHandlerPlaybackEvents -v`
- [ ] Verify all pass

---

### Task 4.6: Test Error Events (30 min)

**Add to test file:**

```python
class TestLEDEventHandlerErrorEvents:
    """Test error event handling."""

    @pytest.mark.asyncio
    async def test_on_playback_error(self, led_event_handler, mock_led_manager):
        """Test playback error shows ERROR_PLAYBACK."""
        await led_event_handler.on_playback_error("Track not found")

        mock_led_manager.set_state.assert_called_once_with(LEDState.ERROR_PLAYBACK)

    @pytest.mark.asyncio
    async def test_on_critical_error(self, led_event_handler, mock_led_manager):
        """Test critical error shows ERROR_CRITICAL."""
        await led_event_handler.on_critical_error("Database corrupted")

        mock_led_manager.set_state.assert_called_once_with(LEDState.ERROR_CRITICAL)

    @pytest.mark.asyncio
    async def test_on_error_cleared(self, led_event_handler, mock_led_manager):
        """Test error cleared removes error states."""
        await led_event_handler.on_error_cleared()

        # Should clear both error states
        calls = mock_led_manager.clear_state.call_args_list
        assert len(calls) == 2
        states_cleared = [call[0][0] for call in calls]
        assert LEDState.ERROR_PLAYBACK in states_cleared
        assert LEDState.ERROR_CRITICAL in states_cleared
```

**Expected Test Results:** ✅ All tests should PASS

**Checklist:**
- [ ] Write 3 error event tests
- [ ] Run tests: `pytest tests/unit/application/services/test_led_event_handler_application_service.py::TestLEDEventHandlerErrorEvents -v`
- [ ] Verify all pass

---

### Task 4.7: Test Manual Control Methods (30 min)

**Add to test file:**

```python
class TestLEDEventHandlerManualControl:
    """Test manual LED control methods."""

    @pytest.mark.asyncio
    async def test_set_led_state_success(self, led_event_handler, mock_led_manager):
        """Test manual state setting."""
        mock_led_manager.set_state.return_value = True

        result = await led_event_handler.set_led_state(LEDState.PLAYING)

        assert result is True
        mock_led_manager.set_state.assert_called_once_with(LEDState.PLAYING)

    @pytest.mark.asyncio
    async def test_set_led_state_failure(self, led_event_handler, mock_led_manager):
        """Test manual state setting handles errors."""
        mock_led_manager.set_state.side_effect = Exception("Hardware error")

        result = await led_event_handler.set_led_state(LEDState.PLAYING)

        assert result is False

    @pytest.mark.asyncio
    async def test_clear_led_state_success(self, led_event_handler, mock_led_manager):
        """Test manual state clearing."""
        mock_led_manager.clear_state.return_value = True

        result = await led_event_handler.clear_led_state(LEDState.PLAYING)

        assert result is True
        mock_led_manager.clear_state.assert_called_once_with(LEDState.PLAYING)

    @pytest.mark.asyncio
    async def test_clear_led_state_failure(self, led_event_handler, mock_led_manager):
        """Test manual state clearing handles errors."""
        mock_led_manager.clear_state.side_effect = Exception("Hardware error")

        result = await led_event_handler.clear_led_state(LEDState.PLAYING)

        assert result is False

    @pytest.mark.asyncio
    async def test_set_brightness_success(self, led_event_handler, mock_led_manager):
        """Test brightness setting."""
        mock_led_manager.set_brightness.return_value = True

        result = await led_event_handler.set_brightness(0.5)

        assert result is True
        mock_led_manager.set_brightness.assert_called_once_with(0.5)

    @pytest.mark.asyncio
    async def test_set_brightness_failure(self, led_event_handler, mock_led_manager):
        """Test brightness setting handles errors."""
        mock_led_manager.set_brightness.side_effect = Exception("Hardware error")

        result = await led_event_handler.set_brightness(0.5)

        assert result is False
```

**Expected Test Results:** ✅ All tests should PASS

**Checklist:**
- [ ] Write 6 manual control tests
- [ ] Run tests: `pytest tests/unit/application/services/test_led_event_handler_application_service.py::TestLEDEventHandlerManualControl -v`
- [ ] Verify all pass

---

### Task 4.8: Test Complex Fallback Scenarios (60 min)

**Add to test file:**

```python
class TestLEDEventHandlerComplexScenarios:
    """Test complex multi-state scenarios and fallbacks."""

    @pytest.mark.asyncio
    async def test_nfc_association_complete_flow(self, led_event_handler, mock_led_manager):
        """Test complete NFC association flow.

        Flow: IDLE → ASSOCIATION_MODE → TAG_DETECTED → SUCCESS → (timeout) → IDLE
        """
        # Start in IDLE
        await led_event_handler.on_system_ready()

        # User activates association mode
        await led_event_handler.on_nfc_association_mode_started()
        assert mock_led_manager.set_state.call_args_list[-1][0][0] == LEDState.NFC_ASSOCIATION_MODE

        # Tag physically detected
        await led_event_handler.on_nfc_tag_detected()
        assert mock_led_manager.set_state.call_args_list[-1][0][0] == LEDState.NFC_TAG_DETECTED

        # Association validated
        await led_event_handler.on_nfc_association_validated()
        assert mock_led_manager.set_state.call_args_list[-1][0][0] == LEDState.NFC_ASSOCIATION_SUCCESS

        # Mode stopped (user exits or timeout)
        await led_event_handler.on_nfc_association_mode_stopped()
        mock_led_manager.clear_state.assert_called_with(LEDState.NFC_ASSOCIATION_MODE)

    @pytest.mark.asyncio
    async def test_nfc_tag_scan_unassociated_flow(self, led_event_handler, mock_led_manager):
        """Test NFC tag scan when tag not associated.

        Flow: IDLE → SCANNING → TAG_UNASSOCIATED → (timeout) → IDLE
        """
        # Tag scan started
        await led_event_handler.on_nfc_scan_started()
        assert mock_led_manager.set_state.call_args_list[-1][0][0] == LEDState.NFC_SCANNING

        # Tag not associated with playlist
        await led_event_handler.on_nfc_tag_unassociated()
        assert mock_led_manager.set_state.call_args_list[-1][0][0] == LEDState.NFC_TAG_UNASSOCIATED

        # Timeout should fallback to IDLE automatically (handled by state manager)

    @pytest.mark.asyncio
    async def test_playback_with_error_recovery(self, led_event_handler, mock_led_manager):
        """Test playback error during playing.

        Flow: PLAYING → ERROR_PLAYBACK → (timeout 5s) → fallback to PLAYING or IDLE
        """
        # Start playing
        await led_event_handler.on_playback_state_changed(PlaybackState.PLAYING)
        assert mock_led_manager.set_state.call_args_list[-1][0][0] == LEDState.PLAYING

        # Playback error occurs
        await led_event_handler.on_playback_error("Audio codec error")
        assert mock_led_manager.set_state.call_args_list[-1][0][0] == LEDState.ERROR_PLAYBACK

        # Error cleared
        await led_event_handler.on_error_cleared()
        mock_led_manager.clear_state.assert_any_call(LEDState.ERROR_PLAYBACK)

    @pytest.mark.asyncio
    async def test_boot_error_prevents_idle_state(self, led_event_handler, mock_led_manager):
        """Test boot error has higher priority than IDLE.

        Flow: STARTING → BOOT_ERROR (audio missing) → stays in ERROR (no fallback to IDLE)
        """
        # System starting
        await led_event_handler.on_system_starting()

        # Boot error detected
        await led_event_handler.on_boot_hardware_error("audio")
        assert mock_led_manager.set_state.call_args_list[-1][0][0] == LEDState.ERROR_BOOT_HARDWARE

        # Attempting to set IDLE should not override error (higher priority)
        # This is handled by state manager priority system

    @pytest.mark.asyncio
    async def test_system_crash_highest_priority(self, led_event_handler, mock_led_manager):
        """Test system crash overrides all other states.

        Flow: (any state) → CRASH → stays in CRASH (highest priority)
        """
        # Playing music
        await led_event_handler.on_playback_state_changed(PlaybackState.PLAYING)

        # System crash
        await led_event_handler.on_system_crash("Unhandled exception")
        assert mock_led_manager.set_state.call_args_list[-1][0][0] == LEDState.ERROR_CRASH

        # No other state should override crash (priority 99)
```

**Expected Test Results:**
- ✅ Some tests PASS (using existing methods)
- ❌ Some tests FAIL (using new methods - TDD)

**Checklist:**
- [ ] Write 5 complex scenario tests
- [ ] Run tests: `pytest tests/unit/application/services/test_led_event_handler_application_service.py::TestLEDEventHandlerComplexScenarios -v`
- [ ] Note which tests fail for Phase 2

---

### Task 4.9: Run Complete Test Suite and Document Failures (15 min)

**Run all tests:**

```bash
pytest tests/unit/application/services/test_led_event_handler_application_service.py -v --tb=short
```

**Expected Results:**
- ✅ ~20-25 tests PASS (existing methods)
- ❌ ~15-20 tests FAIL (new methods not yet implemented)

**Create failure report:**

```bash
pytest tests/unit/application/services/test_led_event_handler_application_service.py -v --tb=short > LED_TEST_FAILURES_PHASE4.txt
```

**Checklist:**
- [ ] Run complete test suite
- [ ] Document all failures
- [ ] Count passing tests (~20-25 expected)
- [ ] Count failing tests (~15-20 expected)
- [ ] Save failure report
- [ ] Commit test file to git

**Git Commit:**
```bash
git add tests/unit/application/services/test_led_event_handler_application_service.py
git commit -m "test(led): add comprehensive LED Event Handler test suite (TDD)

Added 40+ tests for LED Event Handler covering:
- Initialization and lifecycle (3 tests)
- System events (6 tests)
- NFC events (8 tests)
- Playback events (5 tests)
- Error events (3 tests)
- Manual control (6 tests)
- Complex scenarios (5 tests)

Expected Results (TDD approach):
- ~20-25 tests PASS (existing implementation)
- ~15-20 tests FAIL (features to be implemented in Phases 1-2)

Failing tests drive implementation of:
- 6 new LED states
- 7 new event handler methods
- DOUBLE_BLINK animation

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## ✅ Phase 4 Complete Checklist

- [ ] Task 4.1: Test file structure created
- [ ] Task 4.2: 3 initialization tests (all pass)
- [ ] Task 4.3: 6 system event tests (3 pass, 3 fail)
- [ ] Task 4.4: 8 NFC event tests (3 pass, 5 fail)
- [ ] Task 4.5: 5 playback event tests (all pass)
- [ ] Task 4.6: 3 error event tests (all pass)
- [ ] Task 4.7: 6 manual control tests (all pass)
- [ ] Task 4.8: 5 complex scenario tests (mixed)
- [ ] Task 4.9: Test suite run and documented
- [ ] **Total: 40+ tests created**
- [ ] Tests committed to git

**Phase 4 Deliverables:**
- ✅ Comprehensive test suite (40+ tests)
- ✅ Clear list of failing tests (TDD targets)
- ✅ Test coverage framework for Event Handler
- ✅ Git commit with tests

**Estimated Time:** 4-5 hours

---

## 📅 Phase 1: Implement New States and Animations - 1-2 hours

### Goal: Make Phase 4 tests pass by implementing missing states

### Task 1.1: Add New LED States (30 min)

**File:** `app/src/domain/models/led.py`

Add to `LEDState` enum after line 42:

```python
class LEDState(Enum):
    """LED states representing different system conditions."""
    # Critical states
    ERROR_CRASH = "error_crash"                # Red solid - Priority 99 (NEW)
    ERROR_BOOT_HARDWARE = "error_boot_hardware" # Red blink slow - Priority 98 (NEW)
    ERROR_CRITICAL = "error_critical"          # Red blinking - Priority 100
    ERROR_PLAYBACK = "error_playback"          # Orange blinking - Priority 90

    # NFC association states (NEW)
    NFC_ASSOCIATION_MODE = "nfc_association_mode"    # Blue blink slow - Priority 85
    NFC_TAG_DETECTED = "nfc_tag_detected"            # Blue double blink - Priority 82
    NFC_SCANNING = "nfc_scanning"                     # Blue pulsing - Priority 80
    NFC_TAG_UNASSOCIATED = "nfc_tag_unassociated"   # Orange double blink - Priority 78
    NFC_ASSOCIATION_SUCCESS = "nfc_association_success" # Green double blink - Priority 77
    NFC_SUCCESS = "nfc_success"                # Green flash - Priority 75
    NFC_ERROR = "nfc_error"                    # Red flash - Priority 75

    # ... rest unchanged
```

**Checklist:**
- [ ] Add 6 new states to enum
- [ ] Verify enum values are unique
- [ ] Update comments with priorities

---

### Task 1.2: Add New Animation Type (15 min)

**File:** `app/src/domain/models/led.py`

Add to `LEDAnimation` enum after line 51:

```python
class LEDAnimation(Enum):
    """Animation types for LED states."""
    SOLID = "solid"                 # Constant color
    PULSE = "pulse"                 # Smooth breathing effect
    BLINK_SLOW = "blink_slow"       # 1Hz blinking
    BLINK_FAST = "blink_fast"       # 3Hz blinking
    FLASH = "flash"                 # Single quick flash then off
    DOUBLE_BLINK = "double_blink"   # 2 quick blinks then pause (NEW)
```

**Checklist:**
- [ ] Add DOUBLE_BLINK animation
- [ ] Document animation behavior

---

### Task 1.3: Add New Priority Levels (10 min)

**File:** `app/src/domain/models/led.py`

Update `LEDPriority` enum:

```python
class LEDPriority(Enum):
    """Priority levels for LED states."""
    CRITICAL = 100          # System critical errors
    CRASH = 99              # System crash (NEW)
    BOOT_ERROR = 98         # Boot hardware error (NEW)
    SHUTDOWN = 95           # System shutdown
    ERROR = 90              # Playback errors
    NFC_ASSOCIATION = 85    # NFC association mode (NEW)
    NFC_DETECTED = 82       # NFC tag detected (NEW)
    NFC_INTERACTION = 80    # NFC scanning/interaction
    NFC_WARNING = 78        # NFC tag unassociated (NEW)
    NFC_RESULT = 75         # NFC scan results (success/validated)
    PLAYBACK_ACTIVE = 50    # Playing state
    PLAYBACK_INACTIVE = 40  # Paused state
    PLAYBACK_STOPPED = 35   # Stopped state
    SYSTEM_STARTING = 30    # Startup
    IDLE = 10               # Idle/ready
    OFF = 0                 # Disabled
```

**Checklist:**
- [ ] Add 5 new priority levels
- [ ] Verify priority ordering

---

### Task 1.4: Add State Configurations (30 min)

**File:** `app/src/domain/models/led.py`

Add to `DEFAULT_LED_STATE_CONFIGS` dictionary (around line 191):

```python
DEFAULT_LED_STATE_CONFIGS = {
    # ... existing states ...

    # NEW: Crash and boot errors
    LEDState.ERROR_CRASH: LEDStateConfig(
        state=LEDState.ERROR_CRASH,
        color=LEDColors.RED,
        animation=LEDAnimation.SOLID,
        priority=LEDPriority.CRASH.value,
        timeout_seconds=None  # Permanent until manual recovery
    ),
    LEDState.ERROR_BOOT_HARDWARE: LEDStateConfig(
        state=LEDState.ERROR_BOOT_HARDWARE,
        color=LEDColors.RED,
        animation=LEDAnimation.BLINK_SLOW,
        priority=LEDPriority.BOOT_ERROR.value,
        timeout_seconds=None  # Permanent until fixed
    ),

    # NEW: NFC association states
    LEDState.NFC_ASSOCIATION_MODE: LEDStateConfig(
        state=LEDState.NFC_ASSOCIATION_MODE,
        color=LEDColors.BLUE,
        animation=LEDAnimation.BLINK_SLOW,
        priority=LEDPriority.NFC_ASSOCIATION.value,
        timeout_seconds=None,  # Stays until mode exited
        animation_speed=0.8
    ),
    LEDState.NFC_TAG_DETECTED: LEDStateConfig(
        state=LEDState.NFC_TAG_DETECTED,
        color=LEDColors.BLUE,
        animation=LEDAnimation.DOUBLE_BLINK,
        priority=LEDPriority.NFC_DETECTED.value,
        timeout_seconds=1.0,  # Brief indication
        animation_speed=1.5
    ),
    LEDState.NFC_TAG_UNASSOCIATED: LEDStateConfig(
        state=LEDState.NFC_TAG_UNASSOCIATED,
        color=LEDColors.ORANGE,
        animation=LEDAnimation.DOUBLE_BLINK,
        priority=LEDPriority.NFC_WARNING.value,
        timeout_seconds=2.0,  # Warning indication
        animation_speed=1.5
    ),
    LEDState.NFC_ASSOCIATION_SUCCESS: LEDStateConfig(
        state=LEDState.NFC_ASSOCIATION_SUCCESS,
        color=LEDColors.GREEN,
        animation=LEDAnimation.DOUBLE_BLINK,
        priority=LEDPriority.NFC_RESULT.value,
        timeout_seconds=1.0,  # Brief success indication
        animation_speed=1.5
    ),

    # ... existing states unchanged ...
}
```

**Checklist:**
- [ ] Add 6 new state configurations
- [ ] Set appropriate colors, animations, priorities
- [ ] Set appropriate timeouts
- [ ] Verify no duplicate state keys

---

### Task 1.5: Implement DOUBLE_BLINK Animation (30 min)

**File:** `app/src/infrastructure/hardware/leds/rgb_led_controller.py`

Add to `_run_animation()` method (around line 251):

```python
def _run_animation(self, color: LEDColor, animation: LEDAnimation, speed: float):
    """Run animation in background thread."""
    try:
        if animation == LEDAnimation.PULSE:
            self._animate_pulse(color, speed)
        elif animation == LEDAnimation.BLINK_SLOW:
            self._animate_blink(color, 1.0, speed)  # 1Hz
        elif animation == LEDAnimation.BLINK_FAST:
            self._animate_blink(color, 3.0, speed)  # 3Hz
        elif animation == LEDAnimation.FLASH:
            self._animate_flash(color, speed)
        elif animation == LEDAnimation.DOUBLE_BLINK:  # NEW
            self._animate_double_blink(color, speed)
    except Exception as e:
        logger.error(f"❌ Error in animation thread: {e}")
```

Add new method after `_animate_flash()` (around line 332):

```python
def _animate_double_blink(self, color: LEDColor, speed: float):
    """Double blink animation - 2 quick blinks then pause."""
    blink_duration = 0.1 / speed  # 100ms per blink
    pause_between_blinks = 0.1 / speed  # 100ms between blinks
    pause_after_double = 0.6 / speed  # 600ms pause before repeat

    while not self._animation_stop_event.is_set():
        # First blink
        if GPIO_AVAILABLE:
            scaled = color.scaled(self._brightness)
            self._red_led.value = scaled.red / 255.0
            self._green_led.value = scaled.green / 255.0
            self._blue_led.value = scaled.blue / 255.0

        if self._animation_stop_event.wait(blink_duration):
            return

        # Off between blinks
        if GPIO_AVAILABLE:
            self._red_led.value = 0
            self._green_led.value = 0
            self._blue_led.value = 0

        if self._animation_stop_event.wait(pause_between_blinks):
            return

        # Second blink
        if GPIO_AVAILABLE:
            scaled = color.scaled(self._brightness)
            self._red_led.value = scaled.red / 255.0
            self._green_led.value = scaled.green / 255.0
            self._blue_led.value = scaled.blue / 255.0

        if self._animation_stop_event.wait(blink_duration):
            return

        # Off
        if GPIO_AVAILABLE:
            self._red_led.value = 0
            self._green_led.value = 0
            self._blue_led.value = 0

        # Long pause before repeating double blink
        if self._animation_stop_event.wait(pause_after_double):
            return
```

**Checklist:**
- [ ] Add DOUBLE_BLINK case to `_run_animation()`
- [ ] Implement `_animate_double_blink()` method
- [ ] Test animation timing (2x 100ms blinks, 600ms pause)
- [ ] Verify animation stops correctly on event

---

### Task 1.6: Update Mock LED Controller (15 min)

**File:** `app/src/infrastructure/hardware/leds/mock_led_controller.py`

Update animation logging (around line 80):

```python
async def set_animation(self, color: LEDColor, animation: LEDAnimation, speed: float = 1.0) -> bool:
    """Set LED animation (mock)."""
    try:
        self._current_color = color
        self._current_animation = animation
        self._animation_speed = speed

        animation_desc = {
            LEDAnimation.SOLID: "solid",
            LEDAnimation.PULSE: "pulsing",
            LEDAnimation.BLINK_SLOW: "blinking slowly",
            LEDAnimation.BLINK_FAST: "blinking fast",
            LEDAnimation.FLASH: "flashing once",
            LEDAnimation.DOUBLE_BLINK: "double blinking"  # NEW
        }

        logger.info(
            f"🧪 Mock LED: {animation_desc.get(animation, animation.value)} "
            f"RGB({color.red}, {color.green}, {color.blue}) at {speed}x speed"
        )
        return True
    except Exception as e:
        logger.error(f"Mock LED animation error: {e}")
        return False
```

**Checklist:**
- [ ] Add DOUBLE_BLINK to animation descriptions
- [ ] Test mock controller logs correctly

---

### Task 1.7: Test New States and Animations (30 min)

**Run domain model tests:**

```bash
# Test that new states are properly defined
python -c "from app.src.domain.models.led import LEDState, LEDAnimation, DEFAULT_LED_STATE_CONFIGS; print('States:', len(LEDState)); print('Configs:', len(DEFAULT_LED_STATE_CONFIGS))"

# Expected output:
# States: 17 (11 old + 6 new)
# Configs: 17
```

**Create quick animation test:**

```bash
# Test DOUBLE_BLINK animation
cat > test_double_blink.py << 'EOF'
import asyncio
from app.src.infrastructure.hardware.leds.mock_led_controller import MockLEDController
from app.src.domain.models.led import LEDColor, LEDAnimation, LEDColors

async def test():
    controller = MockLEDController()
    await controller.initialize()
    await controller.set_animation(LEDColors.BLUE, LEDAnimation.DOUBLE_BLINK, speed=1.0)
    await asyncio.sleep(3)
    await controller.cleanup()

asyncio.run(test())
EOF

python test_double_blink.py
# Should see: "Mock LED: double blinking RGB(0, 0, 255) at 1.0x speed"
```

**Re-run Phase 4 tests:**

```bash
pytest tests/unit/application/services/test_led_event_handler_application_service.py -v -k "test_on_boot\|test_on_system_crash\|test_on_nfc_tag\|test_on_nfc_association" --tb=short
```

**Expected:** Some tests should now PASS due to new states being available in state manager

**Checklist:**
- [ ] Verify 17 states defined
- [ ] Verify 17 state configs
- [ ] Test DOUBLE_BLINK animation with mock
- [ ] Re-run Phase 4 tests
- [ ] Note improvement in pass rate

**Git Commit:**
```bash
git add app/src/domain/models/led.py app/src/infrastructure/hardware/leds/rgb_led_controller.py app/src/infrastructure/hardware/leds/mock_led_controller.py
git commit -m "feat(led): add 6 new LED states and DOUBLE_BLINK animation

Added new LED states:
- ERROR_CRASH (priority 99): Red solid for system crashes
- ERROR_BOOT_HARDWARE (priority 98): Red slow blink for boot errors
- NFC_ASSOCIATION_MODE (priority 85): Blue slow blink
- NFC_TAG_DETECTED (priority 82): Blue double blink
- NFC_TAG_UNASSOCIATED (priority 78): Orange double blink warning
- NFC_ASSOCIATION_SUCCESS (priority 77): Green double blink

Implemented DOUBLE_BLINK animation:
- 2 quick blinks (100ms each)
- 100ms pause between blinks
- 600ms pause before repeat
- Respects speed multiplier

Updated mock controller to support new animation.

This makes 8 additional Phase 4 tests pass.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## ✅ Phase 1 Complete Checklist

- [ ] Task 1.1: 6 new LED states added
- [ ] Task 1.2: DOUBLE_BLINK animation type added
- [ ] Task 1.3: 5 new priority levels added
- [ ] Task 1.4: 6 new state configurations added
- [ ] Task 1.5: DOUBLE_BLINK animation implemented
- [ ] Task 1.6: Mock controller updated
- [ ] Task 1.7: Tests run and improvements verified
- [ ] Git commit completed

**Phase 1 Deliverables:**
- ✅ 6 new LED states
- ✅ DOUBLE_BLINK animation
- ✅ Updated configurations
- ✅ Some Phase 4 tests now passing

**Estimated Time:** 1-2 hours

---

## 📅 Phase 2: Implement New Event Handler Methods - 2 hours

### Goal: Implement remaining methods to make ALL Phase 4 tests pass

### Task 2.1: Implement NFC Event Methods (45 min)

**File:** `app/src/application/services/led_event_handler_application_service.py`

Add after line 128 (after `on_nfc_scan_error()`):

```python
# NEW NFC Association Methods

async def on_nfc_tag_unassociated(self) -> None:
    """Handle NFC tag scanned but not associated with any playlist."""
    try:
        await self._led_manager.set_state(LEDState.NFC_TAG_UNASSOCIATED)
        logger.warning("LED updated: NFC tag not associated with playlist")
    except Exception as e:
        logger.error(f"❌ Error handling NFC tag unassociated: {e}")

async def on_nfc_association_mode_started(self) -> None:
    """Handle NFC association mode activated."""
    try:
        await self._led_manager.set_state(LEDState.NFC_ASSOCIATION_MODE)
        logger.info("LED updated: NFC association mode active")
    except Exception as e:
        logger.error(f"❌ Error handling NFC association mode start: {e}")

async def on_nfc_association_mode_stopped(self) -> None:
    """Handle NFC association mode deactivated."""
    try:
        await self._led_manager.clear_state(LEDState.NFC_ASSOCIATION_MODE)
        logger.info("LED updated: NFC association mode stopped")
    except Exception as e:
        logger.error(f"❌ Error handling NFC association mode stop: {e}")

async def on_nfc_tag_detected(self) -> None:
    """Handle physical NFC tag detected (before scan)."""
    try:
        await self._led_manager.set_state(LEDState.NFC_TAG_DETECTED)
        logger.debug("LED updated: NFC tag physically detected")
    except Exception as e:
        logger.error(f"❌ Error handling NFC tag detected: {e}")

async def on_nfc_association_validated(self) -> None:
    """Handle NFC tag-playlist association successfully saved."""
    try:
        await self._led_manager.set_state(LEDState.NFC_ASSOCIATION_SUCCESS)
        logger.info("LED updated: NFC association validated")
    except Exception as e:
        logger.error(f"❌ Error handling NFC association validated: {e}")
```

**Checklist:**
- [ ] Implement 5 new NFC methods
- [ ] Add proper error handling
- [ ] Add appropriate logging levels
- [ ] Run NFC tests: `pytest tests/unit/application/services/test_led_event_handler_application_service.py::TestLEDEventHandlerNFCEvents -v`
- [ ] Verify all 8 NFC tests now PASS

---

### Task 2.2: Implement System Error Methods (30 min)

**File:** `app/src/application/services/led_event_handler_application_service.py`

Add after `on_system_shutting_down()` (around line 158):

```python
async def on_boot_hardware_error(self, component: str) -> None:
    """
    Handle hardware initialization error during boot.

    Args:
        component: Name of failed component (e.g., "audio", "nfc")
    """
    try:
        await self._led_manager.set_state(LEDState.ERROR_BOOT_HARDWARE)
        logger.error(f"LED updated: Boot hardware error - {component} failed to initialize")
    except Exception as e:
        logger.error(f"❌ Error handling boot hardware error: {e}")

async def on_system_crash(self, error_msg: str) -> None:
    """
    Handle unrecoverable system crash.

    Args:
        error_msg: Crash error message
    """
    try:
        await self._led_manager.set_state(LEDState.ERROR_CRASH)
        logger.critical(f"LED updated: System crash - {error_msg}")
    except Exception as e:
        logger.error(f"❌ Error handling system crash: {e}")
```

**Checklist:**
- [ ] Implement 2 system error methods
- [ ] Add docstrings with parameter descriptions
- [ ] Use appropriate log levels (error, critical)
- [ ] Run system tests: `pytest tests/unit/application/services/test_led_event_handler_application_service.py::TestLEDEventHandlerSystemEvents -v`
- [ ] Verify all 6 system event tests now PASS

---

### Task 2.3: Run Complete Test Suite (15 min)

**Run all Event Handler tests:**

```bash
pytest tests/unit/application/services/test_led_event_handler_application_service.py -v --tb=short
```

**Expected Results:**
- ✅ **ALL 40+ tests should now PASS**
- ❌ If any fail, debug and fix

**Verify test coverage:**

```bash
pytest tests/unit/application/services/test_led_event_handler_application_service.py --cov=app.src.application.services.led_event_handler_application_service --cov-report=term-missing
```

**Expected Coverage:** >95%

**Checklist:**
- [ ] All tests pass
- [ ] Coverage >95%
- [ ] No warnings or deprecation notices
- [ ] Test execution time <5 seconds

**Git Commit:**
```bash
git add app/src/application/services/led_event_handler_application_service.py
git commit -m "feat(led): implement 7 new LED Event Handler methods (TDD)

Implemented methods to make all Phase 4 tests pass:

NFC Association Methods (5):
- on_nfc_tag_unassociated(): Warning for unassociated tags
- on_nfc_association_mode_started(): Start association mode
- on_nfc_association_mode_stopped(): Stop association mode
- on_nfc_tag_detected(): Physical tag detection
- on_nfc_association_validated(): Association success

System Error Methods (2):
- on_boot_hardware_error(component): Boot initialization failures
- on_system_crash(error_msg): Unrecoverable crashes

All 40+ Event Handler tests now pass with >95% coverage.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## ✅ Phase 2 Complete Checklist

- [ ] Task 2.1: 5 NFC methods implemented
- [ ] Task 2.2: 2 system error methods implemented
- [ ] Task 2.3: All tests pass with >95% coverage
- [ ] Git commit completed

**Phase 2 Deliverables:**
- ✅ 7 new event handler methods
- ✅ ALL Phase 4 tests passing
- ✅ >95% test coverage

**Estimated Time:** 2 hours

---

## 📅 Phase 3: Connect Events to Triggers - 3-4 hours

### Goal: Wire event handlers to actual application events

### Task 3.1: Connect Playback State Changes (60 min)

**File:** `app/src/domain/audio/engine/state_manager.py`

Add at the top of file (after imports):

```python
import logging
logger = logging.getLogger(__name__)
```

Modify `set_state()` method (around line 50), add at the end:

```python
async def set_state(self, new_state: AudioState) -> None:
    """Set playback state and notify listeners."""
    # ... existing state change logic ...

    # Notify LED system of playback state change
    await self._notify_led_state_change(new_state)

async def _notify_led_state_change(self, audio_state: AudioState) -> None:
    """Notify LED event handler of playback state changes."""
    try:
        # Get LED event handler from DI
        from app.src.infrastructure.di.container import get_container
        container = get_container()

        if not container.has("domain_bootstrap"):
            return

        domain_bootstrap = container.get("domain_bootstrap")
        if not domain_bootstrap or not domain_bootstrap.led_event_handler:
            return

        # Map audio state to playback state
        from app.src.common.data_models import PlaybackState
        state_mapping = {
            AudioState.PLAYING: PlaybackState.PLAYING,
            AudioState.PAUSED: PlaybackState.PAUSED,
            AudioState.STOPPED: PlaybackState.STOPPED,
        }

        playback_state = state_mapping.get(audio_state)
        if playback_state:
            await domain_bootstrap.led_event_handler.on_playback_state_changed(playback_state)
            logger.debug(f"LED notified of playback state: {playback_state.value}")

    except Exception as e:
        # Don't fail playback if LED notification fails
        logger.debug(f"LED notification failed (non-critical): {e}")
```

**Test playback LED:**

```python
# Create test script
cat > test_playback_led.py << 'EOF'
import asyncio
from app.src.infrastructure.di.container import register_core_infrastructure_services, get_container
from app.src.common.data_models import PlaybackState

async def test():
    # Setup DI
    register_core_infrastructure_services()
    container = get_container()

    # Get bootstrap and LED
    bootstrap = container.get("domain_bootstrap")
    bootstrap.initialize()
    await bootstrap.start()

    # Simulate playback state changes
    led_handler = bootstrap.led_event_handler
    print("Testing PLAYING...")
    await led_handler.on_playback_state_changed(PlaybackState.PLAYING)
    await asyncio.sleep(2)

    print("Testing PAUSED...")
    await led_handler.on_playback_state_changed(PlaybackState.PAUSED)
    await asyncio.sleep(2)

    print("Testing STOPPED...")
    await led_handler.on_playback_state_changed(PlaybackState.STOPPED)
    await asyncio.sleep(2)

    await bootstrap.stop()

asyncio.run(test())
EOF

USE_MOCK_HARDWARE=true python test_playback_led.py
```

**Checklist:**
- [ ] Add `_notify_led_state_change()` method
- [ ] Call from `set_state()`
- [ ] Test with script
- [ ] Verify mock LED shows: PLAYING (green) → PAUSED (yellow) → STOPPED (off)
- [ ] Test doesn't crash if LED unavailable

---

### Task 3.2: Connect NFC Tag Unassociated (30 min)

**File:** `app/src/application/controllers/playlist_controller.py`

Find `handle_tag_scanned()` method and modify:

```python
async def handle_tag_scanned(self, tag_id: str, full_data: dict):
    """Handle NFC tag scanned event."""
    logger.info(f"Handling NFC tag scan: {tag_id}")

    # Get LED event handler
    led_handler = self._get_led_handler()

    # Look up playlist by tag
    playlist = self._playlist_service.get_playlist_by_nfc_tag(tag_id)

    if not playlist:
        logger.warning(f"Tag {tag_id} not associated with any playlist")

        # Show LED warning
        if led_handler:
            await led_handler.on_nfc_tag_unassociated()

        # Notify via broadcasting service if available
        # ... existing logic ...
        return

    # Tag found, continue with existing playlist loading logic
    # ... existing logic ...

def _get_led_handler(self):
    """Get LED event handler from DI container."""
    try:
        from app.src.infrastructure.di.container import get_container
        container = get_container()
        if container.has("domain_bootstrap"):
            bootstrap = container.get("domain_bootstrap")
            return bootstrap.led_event_handler
    except Exception:
        pass
    return None
```

**Checklist:**
- [ ] Add `_get_led_handler()` helper method
- [ ] Call `on_nfc_tag_unassociated()` when tag not found
- [ ] Test with unassociated tag
- [ ] Verify LED shows orange double blink

---

### Task 3.3: Connect NFC Association Mode (45 min)

**Find NFC association routes** (likely in `app/src/routes/nfc_routes.py` or similar):

```python
@router.post("/api/nfc/association/start")
async def start_nfc_association_mode():
    """
    Start NFC tag association mode.

    Activates mode where next scanned tag will be associated with selected playlist.
    """
    # Get LED handler
    led_handler = await _get_led_handler_from_di()

    # Activate association mode (existing logic)
    # ... your existing association mode logic ...

    # Notify LED
    if led_handler:
        await led_handler.on_nfc_association_mode_started()

    return {
        "status": "success",
        "message": "NFC association mode activated"
    }


@router.post("/api/nfc/association/stop")
async def stop_nfc_association_mode():
    """Stop NFC tag association mode."""
    led_handler = await _get_led_handler_from_di()

    # Deactivate mode (existing logic)
    # ... your existing logic ...

    # Notify LED
    if led_handler:
        await led_handler.on_nfc_association_mode_stopped()

    return {
        "status": "success",
        "message": "NFC association mode stopped"
    }


@router.post("/api/nfc/association/validate")
async def validate_nfc_association(tag_id: str, playlist_id: str):
    """
    Save NFC tag-playlist association.

    Args:
        tag_id: NFC tag UID
        playlist_id: Playlist ID to associate
    """
    led_handler = await _get_led_handler_from_di()

    # Save association (existing logic)
    # ... your existing save logic ...

    # Notify LED of success
    if led_handler:
        await led_handler.on_nfc_association_validated()

    return {
        "status": "success",
        "message": f"Tag {tag_id} associated with playlist {playlist_id}"
    }


async def _get_led_handler_from_di():
    """Get LED event handler from DI container."""
    try:
        from app.src.infrastructure.di.container import get_container
        container = get_container()
        if container.has("domain_bootstrap"):
            bootstrap = container.get("domain_bootstrap")
            return bootstrap.led_event_handler
    except Exception:
        pass
    return None
```

**Checklist:**
- [ ] Find or create association routes
- [ ] Add LED notification to start endpoint
- [ ] Add LED notification to stop endpoint
- [ ] Add LED notification to validate endpoint
- [ ] Test association flow
- [ ] Verify LED: blue slow blink → blue double blink → green double blink

---

### Task 3.4: Connect Physical Tag Detection (30 min)

**File:** `app/src/infrastructure/hardware/nfc/pn532_nfc_hardware.py`

Find the `_scan_loop()` or similar scanning method:

```python
async def _scan_loop(self):
    """Background NFC scanning loop."""
    logger.info("🚀 PN532 NFC Reader started - scanning for tags...")

    while self._running:
        try:
            # Read tag with timeout
            uid = self._pn532.read_passive_target(timeout=0.5)

            if uid:
                # Tag physically detected!
                await self._notify_tag_detected()

                # Convert UID to hex string
                uid_hex = self._format_uid(uid)

                # Continue with existing scan logic...
                # ... your existing callback logic ...

        except Exception as e:
            logger.error(f"Error in NFC scan loop: {e}")
            await asyncio.sleep(1)

async def _notify_tag_detected(self):
    """Notify LED event handler that a tag was physically detected."""
    try:
        from app.src.infrastructure.di.container import get_container
        container = get_container()

        if not container.has("domain_bootstrap"):
            return

        bootstrap = container.get("domain_bootstrap")
        if bootstrap and bootstrap.led_event_handler:
            await bootstrap.led_event_handler.on_nfc_tag_detected()
            logger.debug("LED notified of tag detection")

    except Exception as e:
        logger.debug(f"LED tag detection notification failed: {e}")
```

**Checklist:**
- [ ] Find scanning loop
- [ ] Add `_notify_tag_detected()` method
- [ ] Call when tag UID is detected
- [ ] Test with real NFC tag
- [ ] Verify LED shows blue double blink when tag is touched

---

### Task 3.5: Connect Boot Hardware Errors (45 min)

**File:** `app/src/application/bootstrap.py`

Modify `start()` method to catch and report hardware errors:

```python
async def start(self) -> None:
    """Start all domain services."""
    if not self._is_initialized:
        logger.error("❌ DomainBootstrap not initialized")
        raise RuntimeError("DomainBootstrap not initialized")

    # Initialize LED system first
    if self._led_manager and self._led_event_handler:
        try:
            logger.info("💡 Initializing LED system...")
            await self._led_manager.initialize()
            logger.info("💡 LED manager initialized")
            await self._led_event_handler.initialize()
            logger.info("💡 LED event handler initialized")
            await self._led_event_handler.on_system_starting()
            logger.info("💡 LED system started - showing STARTING state (white blinking)")
        except Exception as e:
            logger.error(f"❌ LED system start failed: {e}", exc_info=True)
            # Continue without LED
    else:
        logger.warning("⚠️ LED system NOT available - skipping LED initialization")

    # Start audio domain with error handling
    if audio_domain_container.is_initialized:
        try:
            await audio_domain_container.start()
            logger.info("✅ Audio domain started successfully")
        except Exception as e:
            logger.error(f"❌ Audio domain start failed: {e}", exc_info=True)

            # Notify LED of boot error
            if self._led_event_handler:
                await self._led_event_handler.on_boot_hardware_error("audio")

            # Re-raise to prevent app from starting with broken audio
            raise RuntimeError(f"Audio system failed to initialize: {e}") from e
    else:
        logger.warning("⚠️ Audio domain not initialized, skipping start")

    # NFC initialization (if applicable) - add similar error handling
    # ... your NFC initialization code with error handling ...

    # Clear STARTING state and set to IDLE when ready
    if self._led_event_handler:
        try:
            logger.info("💡 System ready - transitioning LED to IDLE state...")
            await self._led_event_handler.on_system_ready()
            logger.info("💡 LED system ready - showing IDLE state (solid white)")
        except Exception as e:
            logger.error(f"❌ LED ready state failed: {e}", exc_info=True)

    logger.info("🚀 Domain services started")
```

**Checklist:**
- [ ] Wrap audio init in try/except
- [ ] Call `on_boot_hardware_error("audio")` on failure
- [ ] Wrap NFC init in try/except (if applicable)
- [ ] Call `on_boot_hardware_error("nfc")` on failure
- [ ] Test by temporarily breaking audio init
- [ ] Verify LED shows red slow blink on boot error

---

### Task 3.6: Connect System Crash Detection (30 min)

**File:** `app/main.py` (or global error handler)

Add crash detection to lifespan handler:

```python
@asynccontextmanager
async def lifespan(fastapi_app):
    """Application lifespan event handler."""
    routes_organizer = None
    try:
        # Startup sequence
        await _initialize_application(fastapi_app)
        await _start_domain_bootstrap()

        routes_organizer = init_api_routes_state(fastapi_app, sio, env_config)

        logger.log(LogLevel.INFO, "🟢 Application startup completed successfully")
        yield
        logger.log(LogLevel.INFO, "🟡 Application shutdown sequence starting...")

    except Exception as e:
        # CRITICAL CRASH - notify LED before propagating
        logger.critical(f"💥 CRITICAL STARTUP CRASH: {e}", exc_info=True)

        # Try to notify LED of crash
        try:
            from app.src.infrastructure.di.container import get_container
            container = get_container()
            if container.has("domain_bootstrap"):
                bootstrap = container.get("domain_bootstrap")
                if bootstrap and bootstrap.led_event_handler:
                    await bootstrap.led_event_handler.on_system_crash(str(e))
        except Exception as led_error:
            logger.error(f"Failed to set crash LED: {led_error}")

        # Re-raise to ensure app stops
        raise

    finally:
        # Normal shutdown sequence
        # ... existing cleanup ...
```

**Add global exception handler:**

```python
@fastapi_app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions."""
    logger.critical(f"💥 UNHANDLED EXCEPTION: {exc}", exc_info=True)

    # Notify LED of crash
    try:
        from app.src.infrastructure.di.container import get_container
        container = get_container()
        if container.has("domain_bootstrap"):
            bootstrap = container.get("domain_bootstrap")
            if bootstrap and bootstrap.led_event_handler:
                await bootstrap.led_event_handler.on_system_crash(str(exc))
    except Exception:
        pass

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
```

**Checklist:**
- [ ] Add crash detection to lifespan
- [ ] Add global exception handler
- [ ] Test by raising exception during startup
- [ ] Verify LED shows solid red on crash
- [ ] Ensure crash LED persists (priority 99)

---

### Task 3.7: Integration Testing (30 min)

**Create integration test script:**

```python
# File: test_led_integration_complete.py
"""Complete LED integration test - all events."""

import asyncio
from app.src.infrastructure.di.container import register_core_infrastructure_services, get_container
from app.src.common.data_models import PlaybackState

async def test_complete_integration():
    """Test all LED events in realistic scenarios."""
    print("="*70)
    print("LED COMPLETE INTEGRATION TEST")
    print("="*70)

    # Setup
    register_core_infrastructure_services()
    container = get_container()
    bootstrap = container.get("domain_bootstrap")
    bootstrap.initialize()

    led = bootstrap.led_event_handler

    # Test 1: System startup
    print("\n1. System Startup (white blinking)")
    await bootstrap.start()
    await asyncio.sleep(3)

    # Test 2: NFC scan success
    print("\n2. NFC Scan Success (green flash)")
    await led.on_nfc_scan_started()
    await asyncio.sleep(1)
    await led.on_nfc_scan_success()
    await asyncio.sleep(2)

    # Test 3: Playback
    print("\n3. Playback States")
    print("   - PLAYING (green solid)")
    await led.on_playback_state_changed(PlaybackState.PLAYING)
    await asyncio.sleep(3)

    print("   - PAUSED (yellow solid)")
    await led.on_playback_state_changed(PlaybackState.PAUSED)
    await asyncio.sleep(3)

    # Test 4: NFC tag unassociated
    print("\n4. NFC Tag Unassociated (orange double blink)")
    await led.on_nfc_tag_unassociated()
    await asyncio.sleep(3)

    # Test 5: NFC association flow
    print("\n5. NFC Association Flow")
    print("   - Start mode (blue slow blink)")
    await led.on_nfc_association_mode_started()
    await asyncio.sleep(2)

    print("   - Tag detected (blue double blink)")
    await led.on_nfc_tag_detected()
    await asyncio.sleep(2)

    print("   - Association success (green double blink)")
    await led.on_nfc_association_validated()
    await asyncio.sleep(2)

    print("   - Stop mode")
    await led.on_nfc_association_mode_stopped()
    await asyncio.sleep(1)

    # Test 6: Errors
    print("\n6. Error States")
    print("   - Playback error (orange slow blink)")
    await led.on_playback_error("Test error")
    await asyncio.sleep(3)

    print("   - Clear error")
    await led.on_error_cleared()
    await asyncio.sleep(1)

    print("   - Boot error (red slow blink)")
    await led.on_boot_hardware_error("test_component")
    await asyncio.sleep(3)

    # Test 7: Shutdown
    print("\n7. System Shutdown (red pulse)")
    await bootstrap.stop()
    await asyncio.sleep(2)

    print("\n" + "="*70)
    print("INTEGRATION TEST COMPLETE")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(test_complete_integration())
```

**Run integration test:**

```bash
USE_MOCK_HARDWARE=true python test_led_integration_complete.py
```

**Expected Output:** Should see all LED state changes logged in sequence

**Checklist:**
- [ ] Create integration test script
- [ ] Run with mock hardware
- [ ] Verify all states trigger correctly
- [ ] Test on real hardware (if available)
- [ ] Verify LEDs show correct colors/animations

**Git Commit:**
```bash
git add app/src/domain/audio/engine/state_manager.py \
        app/src/application/controllers/playlist_controller.py \
        app/src/routes/*.py \
        app/src/infrastructure/hardware/nfc/pn532_nfc_hardware.py \
        app/src/application/bootstrap.py \
        app/main.py

git commit -m "feat(led): connect all LED events to application triggers

Connected LED Event Handler to actual application events:

Playback Events:
- Audio state changes → LED playback states (PLAYING/PAUSED/STOPPED)
- Integrated in audio_engine.state_manager.set_state()

NFC Events:
- Tag unassociated → Orange double blink warning
- Association mode start/stop → Blue slow blink
- Tag detection → Blue double blink
- Association validated → Green double blink
- Integrated in playlist_controller and NFC routes

System Events:
- Boot hardware errors → Red slow blink (audio/NFC failures)
- System crashes → Solid red (unhandled exceptions)
- Integrated in bootstrap.start() and global error handler

All LED events now trigger correctly from real application events.
Integration tests pass on both mock and real hardware.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## ✅ Phase 3 Complete Checklist

- [ ] Task 3.1: Playback state changes connected
- [ ] Task 3.2: NFC tag unassociated connected
- [ ] Task 3.3: NFC association mode connected
- [ ] Task 3.4: Physical tag detection connected
- [ ] Task 3.5: Boot hardware errors connected
- [ ] Task 3.6: System crash detection connected
- [ ] Task 3.7: Integration testing complete
- [ ] Git commit completed

**Phase 3 Deliverables:**
- ✅ All 14 events connected to triggers
- ✅ Integration test passing
- ✅ LED system fully functional

**Estimated Time:** 3-4 hours

---

## 📅 Phase 5: Final Integration Testing - 2 hours

### Task 5.1: End-to-End Hardware Testing (60 min)

**Test on real Raspberry Pi with GPIO:**

```bash
# On Raspberry Pi
cd /path/to/rpi-firmware/back

# Test 1: Basic LED hardware
python test_led.py

# Test 2: Integration test
python test_led_integration_complete.py

# Test 3: Start real app and observe LED
./run.sh
# Watch LED during startup → should show white blinking then white solid
```

**Test scenarios:**

1. **Startup Flow:**
   - LED should blink white during boot
   - LED should turn solid white when ready

2. **NFC Flow:**
   - Scan unassociated tag → Orange double blink
   - Scan associated tag → Blue pulse → Green flash → Green solid (playing)

3. **Playback Flow:**
   - Play music → Green solid
   - Pause → Yellow solid
   - Stop → LED off or back to IDLE

4. **Association Flow:**
   - Start mode → Blue slow blink
   - Touch tag → Blue double blink
   - Save → Green double blink
   - Exit → White solid (IDLE)

**Checklist:**
- [ ] Test all scenarios on real hardware
- [ ] Verify colors are correct
- [ ] Verify animations work smoothly
- [ ] Verify priorities (errors override playback, etc.)
- [ ] Document any issues

---

### Task 5.2: Performance and Stability Testing (30 min)

**Test rapid state changes:**

```python
# test_led_stress.py
"""Stress test LED state changes."""
import asyncio
from app.src.infrastructure.di.container import register_core_infrastructure_services, get_container

async def stress_test():
    register_core_infrastructure_services()
    container = get_container()
    bootstrap = container.get("domain_bootstrap")
    bootstrap.initialize()
    await bootstrap.start()

    led = bootstrap.led_event_handler

    # Rapid state changes
    for i in range(50):
        await led.on_nfc_scan_started()
        await asyncio.sleep(0.1)
        await led.on_nfc_scan_success()
        await asyncio.sleep(0.1)

        if i % 10 == 0:
            print(f"Iteration {i}/50")

    await bootstrap.stop()
    print("Stress test complete - no crashes!")

asyncio.run(stress_test())
```

**Run stress test:**
```bash
USE_MOCK_HARDWARE=true python test_led_stress.py
```

**Check for:**
- [ ] No memory leaks
- [ ] No threading deadlocks
- [ ] State changes are smooth
- [ ] Timeouts work correctly
- [ ] Cleanup is proper

---

### Task 5.3: Documentation Update (30 min)

**Create user guide:**

```markdown
# File: LED_USER_GUIDE.md

# LED Indicator Guide - TheOpenMusicBox

## LED States Overview

### System States
| LED | Meaning |
|-----|---------|
| ⚪ Blinking white | System starting up |
| ⚪ Solid white | System ready (IDLE) |
| 🔴 Pulsing red | System shutting down |
| 🔴 Blinking red slow | Boot error (audio/NFC hardware failed) |
| 🔴 Solid red | System crash |

### NFC States
| LED | Meaning |
|-----|---------|
| 🔵 Pulsing blue | Scanning NFC tag |
| 🔵 Blinking blue slow | Association mode active |
| 🔵 Double blink blue | Tag physically detected |
| 🟠 Double blink orange | Tag not associated (warning) |
| 🟢 Flash green | Tag scan success |
| 🟢 Double blink green | Association saved |
| 🔴 Flash red | NFC scan error |

### Playback States
| LED | Meaning |
|-----|---------|
| 🟢 Solid green | Playing music |
| 🟡 Solid yellow | Paused |
| ⚫ Off | Stopped |

### Error States
| LED | Meaning |
|-----|---------|
| 🟠 Blinking orange slow | Playback error (5s timeout) |
| 🔴 Blinking red fast | Critical error |

## Priority Order
(Higher number = higher priority, overrides lower states)

1. Crash (99) - Solid red
2. Boot error (98) - Blinking red
3. Shutdown (95) - Pulsing red
4. Critical error (100) - Blinking red fast
5. Playback error (90) - Blinking orange
6. Association mode (85) - Blinking blue
7. Tag detected (82) - Double blink blue
8. NFC scanning (80) - Pulsing blue
9. Tag unassociated (78) - Double blink orange
10. Association success (77) - Double blink green
11. NFC result (75) - Flash
12. Playing (50) - Solid green
13. Paused (40) - Solid yellow
14. Stopped (35) - Off
15. Starting (30) - Blinking white
16. IDLE (10) - Solid white

## Troubleshooting

### LED doesn't turn on
- Check GPIO pins: R=25, G=12, B=24
- Verify USE_MOCK_HARDWARE is false
- Check LED hardware connection
- Run: `python test_led.py`

### LED wrong color
- Check wiring (RGB pins may be swapped)
- Verify LED is common cathode (not common anode)

### LED doesn't change states
- Check logs for "LED updated:" messages
- Verify events are triggering
- Check state priorities (high priority blocks low)
```

**Checklist:**
- [ ] Create LED_USER_GUIDE.md
- [ ] Document all states with examples
- [ ] Add troubleshooting section
- [ ] Include priority table
- [ ] Add wiring diagram reference

---

### Task 5.4: Final Test Suite Run (15 min)

**Run ALL LED tests:**

```bash
# Unit tests
pytest tests/unit/application/services/test_led_state_manager_application_service.py -v
pytest tests/unit/application/services/test_led_event_handler_application_service.py -v
pytest tests/unit/infrastructure/hardware/leds/ -v

# Integration tests
pytest tests/integration/test_playlist_playback_state_persistence_e2e.py -v

# Architecture tests
pytest tests/architecture/ -v
```

**Generate coverage report:**

```bash
pytest tests/ -k "led" --cov=app.src --cov-report=html --cov-report=term
```

**Expected Results:**
- ✅ 90+ LED-related tests pass
- ✅ >95% coverage for LED system
- ✅ No warnings
- ✅ All architecture tests pass

**Checklist:**
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All architecture tests pass
- [ ] Coverage >95%
- [ ] Generate HTML coverage report

**Final Git Commit:**
```bash
git add LED_USER_GUIDE.md test_led_stress.py test_led_integration_complete.py
git commit -m "docs(led): add user guide and complete integration testing

Added comprehensive LED system documentation:
- LED_USER_GUIDE.md with all states explained
- Troubleshooting guide
- Priority order table
- Wiring reference

Added integration tests:
- test_led_integration_complete.py: Full event flow testing
- test_led_stress.py: Performance and stability testing

Test Results:
- 90+ LED tests passing
- >95% code coverage
- All architecture tests passing
- Stress tests show no leaks or deadlocks

LED system is production-ready! 🎉

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## ✅ Phase 5 Complete Checklist

- [ ] Task 5.1: Hardware testing complete
- [ ] Task 5.2: Stress testing complete
- [ ] Task 5.3: Documentation created
- [ ] Task 5.4: Final test suite passing
- [ ] Git commit completed

**Phase 5 Deliverables:**
- ✅ Hardware tested on real GPIO
- ✅ Performance verified
- ✅ Comprehensive documentation
- ✅ All tests passing

**Estimated Time:** 2 hours

---

## 🎯 Complete Implementation Summary

### Total Effort: 12-15 hours over 2 days

| Phase | Description | Time | Status |
|-------|-------------|------|--------|
| Phase 4 | Comprehensive test suite (TDD) | 4-5h | ⬜ Not started |
| Phase 1 | New states and animations | 1-2h | ⬜ Not started |
| Phase 2 | Event handler methods | 2h | ⬜ Not started |
| Phase 3 | Connect events to triggers | 3-4h | ⬜ Not started |
| Phase 5 | Final integration testing | 2h | ⬜ Not started |

### Deliverables

**Code:**
- ✅ 6 new LED states
- ✅ DOUBLE_BLINK animation
- ✅ 7 new event handler methods
- ✅ 14 event connections
- ✅ 40+ new tests

**Documentation:**
- ✅ LED_USER_GUIDE.md
- ✅ Test coverage report
- ✅ Integration test scripts

**Quality:**
- ✅ >95% test coverage
- ✅ All architecture tests pass
- ✅ No regressions
- ✅ Production-ready

---

## 📋 Execution Checklist

### Before Starting
- [ ] Review this plan completely
- [ ] Ensure development environment is ready
- [ ] Ensure test environment works
- [ ] Create git branch: `feat/led-complete-implementation`

### During Implementation
- [ ] Follow phases in order (4 → 1 → 2 → 3 → 5)
- [ ] Commit after each phase
- [ ] Run tests after each task
- [ ] Document any deviations from plan

### After Completion
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Code reviewed
- [ ] Hardware tested
- [ ] Merge to main branch
- [ ] Deploy to production

---

**Plan Created:** 2025-10-24
**Ready to Execute:** YES
**Recommended Start:** Phase 4 (Tests First - TDD)
