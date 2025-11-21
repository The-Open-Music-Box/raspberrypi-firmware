# Code Duplication Reduction Plan: Reaching < 1%

**Current Status:** 2.70% duplication (1,190 lines, 120 clones)
**Target:** < 1.0% duplication
**Required Reduction:** ~1.7%

---

## Overview

This plan outlines a systematic approach to reduce code duplication from 2.70% to below 1% through 6 major refactoring phases. Each phase targets specific duplication patterns with concrete actions and expected outcomes.

**Total Estimated Impact:** -1.45% to -1.85% duplication
**Expected Final Result:** 0.85% - 1.25% duplication

---

## Phase 1: Hardware Implementation Abstraction (High Priority)

**Current Duplication:** ~25 clones, ~250 lines
**Expected Reduction:** -0.5% to -0.7%
**Target Result:** 2.70% → ~2.0-2.2%

### 1.1 Audio Backend Abstraction

**Problem:** Duplication between `macos_audio_backend.py` and `wm8960_audio_backend.py`

**Action Plan:**
1. Create `base_audio_backend.py` with abstract base class
   ```python
   class BaseAudioBackend(ABC):
       @abstractmethod
       async def initialize(self) -> bool:
           """Initialize audio backend hardware"""

       @abstractmethod
       async def cleanup(self) -> None:
           """Cleanup audio backend resources"""

       @abstractmethod
       async def _configure_hardware(self) -> None:
           """Configure hardware-specific settings"""
   ```

2. Extract common patterns:
   - Initialization error handling (11 lines duplicated)
   - Resource cleanup (8 lines duplicated)
   - Status checking logic

3. Refactor both backends to inherit from base class

**Files to Modify:**
- `app/src/domain/audio/backends/implementations/base_audio_backend.py` (NEW)
- `app/src/domain/audio/backends/implementations/macos_audio_backend.py`
- `app/src/domain/audio/backends/implementations/wm8960_audio_backend.py`

**Estimated Lines Reduced:** ~40 lines

---

### 1.2 NFC Hardware Abstraction

**Problem:** Extensive duplication between `mock_nfc_hardware.py` and `pn532_nfc_hardware.py`

**Action Plan:**
1. Create `base_nfc_hardware.py` with abstract base class
   ```python
   class BaseNFCHardware(ABC):
       def __init__(self):
           self._is_initialized = False
           self._last_error: Optional[str] = None

       @abstractmethod
       async def _initialize_hardware(self) -> bool:
           """Initialize hardware-specific NFC reader"""

       @abstractmethod
       async def _read_tag_hardware(self) -> Optional[str]:
           """Read tag from hardware"""

       async def initialize(self) -> bool:
           """Common initialization logic with error handling"""
           try:
               result = await self._initialize_hardware()
               self._is_initialized = result
               return result
           except Exception as e:
               self._last_error = str(e)
               logger.error(f"NFC initialization failed: {e}")
               return False
   ```

2. Extract common patterns:
   - Import blocks (18 lines duplicated)
   - Error handling patterns (9 lines duplicated)
   - Tag reading retry logic (7 lines duplicated)
   - Status property methods

3. Refactor both implementations to inherit from base
4. Update `nfc_factory.py` to use base class types

**Files to Modify:**
- `app/src/infrastructure/hardware/nfc/base_nfc_hardware.py` (NEW)
- `app/src/infrastructure/hardware/nfc/mock_nfc_hardware.py`
- `app/src/infrastructure/hardware/nfc/pn532_nfc_hardware.py`
- `app/src/infrastructure/hardware/nfc/nfc_factory.py`

**Estimated Lines Reduced:** ~90 lines

---

### 1.3 LED Controller Abstraction

**Problem:** Duplication between `mock_led_controller.py` and `rgb_led_controller.py`

**Action Plan:**
1. Create `base_led_controller.py` with abstract base class
   ```python
   class BaseLEDController(ABC):
       def __init__(self):
           self._check_gpio_availability()

       def _check_gpio_availability(self) -> None:
           """Common GPIO availability check (8 lines duplicated)"""
           try:
               import gpiozero
               self.gpio_available = True
           except ImportError:
               self.gpio_available = False
               logger.warning("GPIO not available")

       @abstractmethod
       async def _set_hardware_color(self, color: LEDColor) -> None:
           """Set color on actual hardware"""
   ```

2. Extract common patterns:
   - GPIO availability check (8 lines duplicated)
   - Initialization validation
   - Error handling wrappers

3. Refactor both controllers to inherit from base

**Files to Modify:**
- `app/src/infrastructure/hardware/leds/base_led_controller.py` (NEW)
- `app/src/infrastructure/hardware/leds/mock_led_controller.py`
- `app/src/infrastructure/hardware/leds/rgb_led_controller.py`

**Estimated Lines Reduced:** ~30 lines

---

### 1.4 GPIO Controls Abstraction

**Problem:** Duplication between `gpio_controls_implementation.py` and `mock_controls_implementation.py`

**Action Plan:**
1. Create `base_controls_implementation.py` with abstract base class
   ```python
   class BaseControlsImplementation(ABC):
       def __init__(self):
           self._event_handlers: Dict[str, Callable] = {}
           self._is_active = False

       def register_event_handler(self, event_type: str, handler: Callable) -> None:
           """Common event handler registration (5 lines duplicated)"""
           self._event_handlers[event_type] = handler

       async def _trigger_event(self, event_type: str, data: Dict[str, Any]) -> None:
           """Common event triggering logic (13 lines duplicated)"""
           if event_type in self._event_handlers:
               handler = self._event_handlers[event_type]
               try:
                   if asyncio.iscoroutinefunction(handler):
                       await handler(data)
                   else:
                       handler(data)
               except Exception as e:
                   logger.error(f"Event handler error: {e}")
   ```

2. Extract common patterns:
   - Initialization logic (9 lines duplicated)
   - Cleanup sequences (5 lines duplicated)
   - Event handling infrastructure (13 lines duplicated)

3. Refactor both implementations to inherit from base

**Files to Modify:**
- `app/src/infrastructure/hardware/controls/base_controls_implementation.py` (NEW)
- `app/src/infrastructure/hardware/controls/gpio_controls_implementation.py`
- `app/src/infrastructure/hardware/controls/mock_controls_implementation.py`

**Estimated Lines Reduced:** ~40 lines

---

### Phase 1 Summary

**Total Files Created:** 4 base classes
**Total Files Modified:** 10 files
**Estimated Lines Reduced:** ~200 lines
**Expected Duplication Reduction:** -0.5% to -0.7%
**Result:** 2.70% → ~2.0-2.2%

---

## Phase 2: API Endpoint Consolidation (Medium Priority)

**Current Duplication:** ~35 clones, ~300 lines
**Expected Reduction:** -0.3% to -0.5%
**Target Result:** ~2.0-2.2% → ~1.5-1.7%

### 2.1 Base API Route Class

**Problem:** Repetitive service getter, error handling, and response patterns across all API route files

**Action Plan:**
1. Create `base_api_routes.py` with reusable patterns
   ```python
   class BaseAPIRoutes:
       """Base class for API routes with common patterns"""

       def _get_required_service(
           self,
           request: Request,
           service_key: str,
           client_op_id: Optional[str] = None
       ) -> Tuple[Optional[Any], Optional[Response]]:
           """Get service or return error response (8 lines duplicated everywhere)"""
           try:
               service = request.app.state.container.get(service_key)
               if not service:
                   return None, UnifiedResponseService.service_unavailable(
                       service=service_key,
                       client_op_id=client_op_id
                   )
               return service, None
           except Exception as e:
               logger.error(f"Failed to get {service_key}: {e}")
               return None, UnifiedResponseService.service_unavailable(
                   service=service_key,
                   client_op_id=client_op_id
               )

       def _get_multiple_services(
           self,
           request: Request,
           service_keys: List[str],
           client_op_id: Optional[str] = None
       ) -> Tuple[Optional[Dict[str, Any]], Optional[Response]]:
           """Get multiple services or return error"""
           services = {}
           for key in service_keys:
               service, error = self._get_required_service(request, key, client_op_id)
               if error:
                   return None, error
               services[key] = service
           return services, None

       async def _execute_with_ack(
           self,
           state_manager: Optional[Any],
           client_op_id: Optional[str],
           operation: Callable,
           success_response: Callable,
           error_response: Callable
       ) -> Response:
           """Execute operation with acknowledgment pattern (13 lines duplicated)"""
           try:
               result = await operation()
               if state_manager and client_op_id:
                   await state_manager.send_acknowledgment(
                       client_op_id, True, result or {}
                   )
               return success_response(result)
           except Exception as e:
               if state_manager and client_op_id:
                   await state_manager.send_acknowledgment(
                       client_op_id, False, {"error": str(e)}
                   )
               return error_response(e)
   ```

2. Create specialized mixins for common patterns:
   - `PlaybackCommandMixin` - For player control endpoints
   - `ServiceValidationMixin` - For service existence checks
   - `StateManagementMixin` - For state manager operations

**Files to Create:**
- `app/src/api/endpoints/base_api_routes.py` (NEW)
- `app/src/api/endpoints/mixins/playback_command_mixin.py` (NEW)
- `app/src/api/endpoints/mixins/service_validation_mixin.py` (NEW)

**Estimated Lines Reduced:** ~120 lines

---

### 2.2 Refactor Playlist Upload API

**Problem:** 4 clones of 8-line service getter pattern within same file

**Action Plan:**
1. Inherit from `BaseAPIRoutes`
2. Replace all instances of duplicated service getter with `_get_required_service()`
3. Replace duplicated error handling with `_execute_with_ack()`

**Files to Modify:**
- `app/src/api/endpoints/playlist/playlist_upload_api.py`

**Lines at:** 74-82, 107-115, 190-198, 218-226

**Estimated Lines Reduced:** ~32 lines

---

### 2.3 Refactor Playlist Track API

**Problem:** 3 clones of 8-line service getter pattern

**Action Plan:**
1. Inherit from `BaseAPIRoutes`
2. Replace all instances with `_get_required_service()`

**Files to Modify:**
- `app/src/api/endpoints/playlist/playlist_track_api.py`

**Lines at:** 78-86, 132-140

**Estimated Lines Reduced:** ~24 lines

---

### 2.4 Refactor Player API Routes

**Problem:** 8 clones of error handling, service getter, and state validation patterns

**Action Plan:**
1. Inherit from `BaseAPIRoutes` and `PlaybackCommandMixin`
2. Extract common playback command pattern:
   ```python
   async def _execute_playback_command(
       self,
       request: Request,
       command: Callable,
       client_op_id: Optional[str] = None
   ) -> Response:
       """Common pattern for playback commands (13 lines duplicated 3 times)"""
       services, error = self._get_multiple_services(
           request,
           ["audio_controller", "state_manager"],
           client_op_id
       )
       if error:
           return error

       return await self._execute_with_ack(
           services["state_manager"],
           client_op_id,
           lambda: command(services["audio_controller"]),
           lambda r: UnifiedResponseService.success(data=r),
           lambda e: UnifiedResponseService.error(message=str(e))
       )
   ```

3. Replace all duplicated patterns with helper methods

**Files to Modify:**
- `app/src/api/endpoints/player_api_routes.py`

**Lines at:** 80-93, 138-151, 189-202 (error handling)
**Lines at:** 162-171, 217-226, 458-467 (service getter)
**Lines at:** 248-266, 299-317, 317-328 (state validation)

**Estimated Lines Reduced:** ~90 lines

---

### 2.5 Refactor System API Routes

**Problem:** 3 clones of service getter and response formatting

**Action Plan:**
1. Inherit from `BaseAPIRoutes`
2. Replace service getter pattern with `_get_required_service()`
3. Extract response formatting helper

**Files to Modify:**
- `app/src/api/endpoints/system_api_routes.py`

**Lines at:** 73-80, 365-372 (service getter)
**Lines at:** 390-400, 426-436 (response formatting)

**Estimated Lines Reduced:** ~30 lines

---

### 2.6 Further Refactor NFC API Routes

**Problem:** Additional 2 clones beyond Phase 4 improvements

**Action Plan:**
1. Ensure inheritance from `BaseAPIRoutes`
2. Replace remaining duplicated patterns

**Files to Modify:**
- `app/src/api/endpoints/nfc_api_routes.py`

**Lines at:** 197-206, 234-243, 470-479, 499-509

**Estimated Lines Reduced:** ~20 lines

---

### Phase 2 Summary

**Total Files Created:** 4 files (1 base class + 3 mixins)
**Total Files Modified:** 6 API route files
**Estimated Lines Reduced:** ~316 lines
**Expected Duplication Reduction:** -0.3% to -0.5%
**Result:** ~2.0-2.2% → ~1.5-1.7%

---

## Phase 3: Domain Service Consolidation (Medium Priority)

**Current Duplication:** ~10 clones, ~100 lines
**Expected Reduction:** -0.1% to -0.2%
**Target Result:** ~1.5-1.7% → ~1.3-1.5%

### 3.1 Base Domain Service

**Problem:** Similar validation and transformation patterns across domain services

**Action Plan:**
1. Create `base_domain_service.py` with common patterns
   ```python
   class BaseDomainService:
       """Base class for domain services with common validation patterns"""

       def _validate_required_fields(
           self,
           data: Dict[str, Any],
           required_fields: List[str]
       ) -> Optional[str]:
           """Common validation logic (8 lines duplicated in playlist_service)"""
           missing = [f for f in required_fields if f not in data or not data[f]]
           if missing:
               return f"Missing required fields: {', '.join(missing)}"
           return None

       def _transform_with_defaults(
           self,
           data: Dict[str, Any],
           defaults: Dict[str, Any]
       ) -> Dict[str, Any]:
           """Common transformation logic"""
           result = defaults.copy()
           result.update(data)
           return result

       async def _execute_with_logging(
           self,
           operation: Callable,
           operation_name: str,
           context: Dict[str, Any]
       ) -> Any:
           """Common execution pattern with logging (11 lines duplicated in track_service)"""
           logger.info(f"Starting {operation_name}", extra=context)
           try:
               result = await operation()
               logger.info(f"Completed {operation_name}", extra=context)
               return result
           except Exception as e:
               logger.error(f"Failed {operation_name}: {e}", extra=context)
               raise
   ```

**Files to Create:**
- `app/src/domain/base/base_domain_service.py` (NEW)

**Estimated Lines Reduced:** ~25 lines (from base class creation)

---

### 3.2 Refactor Track Service

**Problem:** 1 clone within same file - 11-line validation pattern duplicated

**Action Plan:**
1. Inherit from `BaseDomainService`
2. Extract validation method:
   ```python
   async def _validate_track_operation(
       self,
       playlist_id: str,
       track_data: Dict[str, Any]
   ) -> None:
       """Extracted validation pattern"""
       await self._execute_with_logging(
           lambda: self._validate_track_data(track_data),
           "validate_track",
           {"playlist_id": playlist_id}
       )
   ```

3. Replace duplicated logic at lines 231-242 and 273-284

**Files to Modify:**
- `app/src/domain/data/services/track_service.py`

**Estimated Lines Reduced:** ~15 lines

---

### 3.3 Refactor Playlist Service

**Problem:** 1 clone within same file - 8-line transformation logic duplicated

**Action Plan:**
1. Inherit from `BaseDomainService`
2. Use `_transform_with_defaults()` and `_validate_required_fields()`
3. Replace duplicated logic at lines 94-102 and 263-271

**Files to Modify:**
- `app/src/domain/data/services/playlist_service.py`

**Estimated Lines Reduced:** ~12 lines

---

### Phase 3 Summary

**Total Files Created:** 1 base class
**Total Files Modified:** 2 service files
**Estimated Lines Reduced:** ~52 lines
**Expected Duplication Reduction:** -0.1% to -0.2%
**Result:** ~1.5-1.7% → ~1.3-1.5%

---

## Phase 4: Entity Session Management (Low Priority)

**Current Duplication:** ~5 clones, ~50 lines
**Expected Reduction:** -0.1% to -0.15%
**Target Result:** ~1.3-1.5% → ~1.2-1.35%

### 4.1 Base Session Entity

**Problem:** Similar session state management between `association_session.py` and `upload_session.py`

**Action Plan:**
1. Create `base_session_entity.py` with common session patterns
   ```python
   class BaseSessionEntity(ABC):
       """Base class for session entities"""

       def __init__(self, session_id: str, timeout_seconds: int = 300):
           self.session_id = session_id
           self.created_at = datetime.now()
           self.timeout_seconds = timeout_seconds
           self._state = SessionState.ACTIVE
           self._metadata: Dict[str, Any] = {}

       def is_expired(self) -> bool:
           """Common expiration check (12 lines duplicated)"""
           if self._state == SessionState.COMPLETED:
               return False
           age = (datetime.now() - self.created_at).total_seconds()
           return age > self.timeout_seconds

       def validate_state(self, required_state: SessionState) -> None:
           """Common state validation (10 lines duplicated)"""
           if self._state != required_state:
               raise InvalidStateError(
                   f"Session {self.session_id} is in state {self._state}, "
                   f"expected {required_state}"
               )
           if self.is_expired():
               raise SessionExpiredError(
                   f"Session {self.session_id} has expired"
               )

       @abstractmethod
       def get_progress(self) -> float:
           """Get session progress percentage"""
   ```

**Files to Create:**
- `app/src/domain/base/base_session_entity.py` (NEW)
- `app/src/domain/base/session_state.py` (NEW - enum for states)

**Estimated Lines Reduced:** ~20 lines

---

### 4.2 Refactor Association Session

**Action Plan:**
1. Inherit from `BaseSessionEntity`
2. Use `is_expired()` method (lines 56-68)
3. Use `validate_state()` method (lines 129-139)

**Files to Modify:**
- `app/src/domain/nfc/entities/association_session.py`

**Estimated Lines Reduced:** ~18 lines

---

### 4.3 Refactor Upload Session

**Action Plan:**
1. Inherit from `BaseSessionEntity`
2. Use `is_expired()` method (lines 80-87)
3. Use `validate_state()` method (lines 166-176)

**Files to Modify:**
- `app/src/domain/upload/entities/upload_session.py`

**Estimated Lines Reduced:** ~16 lines

---

### Phase 4 Summary

**Total Files Created:** 2 files (1 base class + 1 enum)
**Total Files Modified:** 2 entity files
**Estimated Lines Reduced:** ~54 lines
**Expected Duplication Reduction:** -0.1% to -0.15%
**Result:** ~1.3-1.5% → ~1.2-1.35%

---

## Phase 5: Utility & Helper Consolidation (Low Priority)

**Current Duplication:** ~10 clones, ~80 lines
**Expected Reduction:** -0.05% to -0.1%
**Target Result:** ~1.2-1.35% → ~1.15-1.25%

### 5.1 Refactor Test Detection Utilities

**Problem:** 15-line detection logic duplicated within same file

**Action Plan:**
1. Extract parameterized helper:
   ```python
   def _detect_environment(
       self,
       check_functions: List[Callable[[], bool]],
       env_type: str
   ) -> bool:
       """Parameterized environment detection"""
       for check_func in check_functions:
           if check_func():
               logger.debug(f"Detected {env_type} environment")
               return True
       return False
   ```

2. Replace duplicated logic at lines 19-47 and 190-205

**Files to Modify:**
- `app/src/utils/test_detection.py`

**Estimated Lines Reduced:** ~18 lines

---

### 5.2 Refactor Progress Utils

**Problem:** 8-line progress calculation duplicated within same file

**Action Plan:**
1. Extract parameterized helper:
   ```python
   def _calculate_progress_percentage(
       self,
       completed: int,
       total: int,
       precision: int = 1
   ) -> float:
       """Common progress calculation"""
       if total == 0:
           return 0.0
       percentage = (completed / total) * 100
       return round(percentage, precision)
   ```

2. Replace duplicated logic at lines 85-93 and 197-205

**Files to Modify:**
- `app/src/utils/progress_utils.py`

**Estimated Lines Reduced:** ~10 lines

---

### 5.3 Infrastructure Adapter Error Handling

**Problem:** 5-line error handling duplicated in `nfc_hardware_adapter.py`

**Action Plan:**
1. Extract error handling wrapper:
   ```python
   def _wrap_hardware_call(
       self,
       operation: Callable,
       operation_name: str
   ) -> Any:
       """Common hardware error handling"""
       try:
           return operation()
       except Exception as e:
           logger.error(f"{operation_name} failed: {e}")
           self._last_error = str(e)
           return None
   ```

2. Replace duplicated logic at lines 30-35 and 152-157

**Files to Modify:**
- `app/src/infrastructure/nfc/adapters/nfc_hardware_adapter.py`

**Estimated Lines Reduced:** ~6 lines

---

### Phase 5 Summary

**Total Files Created:** 0
**Total Files Modified:** 3 utility files
**Estimated Lines Reduced:** ~34 lines
**Expected Duplication Reduction:** -0.05% to -0.1%
**Result:** ~1.2-1.35% → ~1.15-1.25%

---

## Phase 6: NFC & Domain Event Patterns (Low Priority)

**Current Duplication:** ~5 clones, ~40 lines
**Expected Reduction:** -0.05% to -0.1%
**Target Result:** ~1.15-1.25% → ~1.1-1.15% or **< 1.0%**

### 6.1 Event Publishing Pattern

**Problem:** 5-line event publishing pattern duplicated between `nfc_events.py` and `nfc_event_publisher.py`

**Action Plan:**
1. Extract to base event publisher:
   ```python
   class BaseEventPublisher:
       """Base class for event publishing"""

       async def _publish_event(
           self,
           event_type: str,
           event_data: Dict[str, Any],
           handlers: List[Callable]
       ) -> None:
           """Common event publishing pattern (5 lines duplicated)"""
           for handler in handlers:
               try:
                   await handler(event_type, event_data)
               except Exception as e:
                   logger.error(f"Event handler failed: {e}")
   ```

2. Refactor both files to use base class

**Files to Create:**
- `app/src/domain/base/base_event_publisher.py` (NEW)

**Files to Modify:**
- `app/src/domain/nfc/events/nfc_events.py`
- `app/src/domain/nfc/services/nfc_event_publisher.py`

**Estimated Lines Reduced:** ~8 lines

---

### 6.2 Final Aggressive Pass

**Action Plan:**
After completing Phases 1-6, run jscpd again and identify any remaining quick wins:

1. **Look for micro-duplications** (3-4 lines that can be extracted)
2. **Inline documentation patterns** that can be templated
3. **Common lambda expressions** that can be named functions
4. **Repetitive type hints** that can use type aliases

**Expected Additional Reduction:** -0.05% to -0.1%

---

### Phase 6 Summary

**Total Files Created:** 1 base class
**Total Files Modified:** 2+ files
**Estimated Lines Reduced:** ~45+ lines
**Expected Duplication Reduction:** -0.1% to -0.2%
**Final Result:** **~0.95-1.15% duplication** (TARGET ACHIEVED ✅)

---

## Execution Strategy

### Recommended Order

Execute phases in order for maximum impact and minimal risk:

1. **Phase 1** (Hardware Abstraction) - Highest impact, isolated changes
2. **Phase 2** (API Consolidation) - Medium impact, touches many files but standard patterns
3. **Phase 3** (Domain Services) - Low risk, good for code quality
4. **Phase 4** (Entity Sessions) - Low risk, domain-focused
5. **Phase 5** (Utilities) - Quick wins, easy to verify
6. **Phase 6** (Events & Final Pass) - Final push to cross the 1% threshold

### Verification Between Phases

After each phase:
1. Run `npx jscpd app/src --min-lines 5 --min-tokens 50`
2. Run full test suite: `python -m pytest`
3. Create a commit with descriptive message
4. Document actual vs expected reduction

### Commit Strategy

- **One commit per sub-phase** (e.g., "Phase 1.1: Create base audio backend")
- **Verification commit after each phase** (e.g., "Phase 1: Verify 2.70% → 2.15%")
- **Total expected commits:** ~20-25 commits

---

## Risk Mitigation

### Type Safety
- Maintain strict typing throughout (no `Any` types)
- Use `TypeVar` for generic base classes
- Ensure proper `TYPE_CHECKING` imports

### Testing
- Run full test suite after each sub-phase
- Add tests for new base classes
- Verify no test regressions

### Backwards Compatibility
- Keep public interfaces unchanged
- Use inheritance to maintain behavior
- Document breaking changes if any

---

## Success Metrics

### Primary Goal
- **Code Duplication: < 1.0%** ✅

### Secondary Goals
- **All tests passing** (maintain 27 passed, 4 skipped)
- **No `Any` types introduced**
- **Type coverage maintained or improved**
- **No performance regressions**

### Documentation
- Update architecture docs with new base classes
- Document inheritance hierarchies
- Add examples of proper usage patterns

---

## Estimated Timeline

**Assuming focused work:**

- **Phase 1:** 3-4 hours (4 base classes, careful refactoring)
- **Phase 2:** 3-4 hours (6 files, many touchpoints)
- **Phase 3:** 1-2 hours (straightforward extraction)
- **Phase 4:** 1-2 hours (isolated entity changes)
- **Phase 5:** 1 hour (simple utility refactoring)
- **Phase 6:** 1-2 hours (final cleanup)

**Total: 10-15 hours of development time**

---

## Post-Completion

After reaching < 1% duplication:

1. **Create comprehensive PR** with all commits
2. **Update CODE_DUPLICATION_REPORT.md** with final results
3. **Add jscpd to CI/CD** with 1.5% threshold
4. **Document architecture improvements** in ADRs
5. **Close Issue #42** with success metrics

---

## Summary Table

| Phase | Description | Est. Reduction | Target Result | Commits |
|-------|-------------|----------------|---------------|---------|
| **Start** | Current state | - | 2.70% | - |
| **1** | Hardware Abstraction | -0.5% to -0.7% | ~2.0-2.2% | 4-5 |
| **2** | API Consolidation | -0.3% to -0.5% | ~1.5-1.7% | 6-8 |
| **3** | Domain Services | -0.1% to -0.2% | ~1.3-1.5% | 2-3 |
| **4** | Entity Sessions | -0.1% to -0.15% | ~1.2-1.35% | 2-3 |
| **5** | Utilities | -0.05% to -0.1% | ~1.15-1.25% | 3-4 |
| **6** | Events & Final | -0.1% to -0.2% | **< 1.0%** ✅ | 2-3 |
| **TOTAL** | All phases | **-1.15% to -1.85%** | **0.85-1.15%** | **19-26** |

---

**Plan Created:** 2025-11-21
**Target Completion:** TBD
**Current Duplication:** 2.70%
**Target Duplication:** < 1.0%
**Status:** READY TO EXECUTE ✅
