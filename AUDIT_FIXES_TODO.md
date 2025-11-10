# Audit Fixes - Comprehensive TODO Guide

**Branch:** `audit-fixes-comprehensive`
**Based on:** Code Audit Report (2025-11-06)
**Total Issues:** 112 issues across 5 categories

---

## Progress Tracker

- [ ] **Phase 1: HIGH Priority Contract Violations** (15 issues)
- [ ] **Phase 2: HIGH Priority Code Quality** (3 issues)
- [ ] **Phase 3: Code Duplications** (22 issues)
- [ ] **Phase 4: Obsolete Code Cleanup** (22 issues)
- [ ] **Phase 5: MEDIUM Priority Code Quality** (42 issues)
- [ ] **Phase 6: Architecture Violations** (8 issues)
- [ ] **Phase 7: Testing & Verification**
- [ ] **Phase 8: Documentation Updates**

---

## Phase 1: HIGH Priority Contract Violations (15 issues)

### 1.1 Socket.IO Contract Fixes

- [ ] **Add `server_time` to connection_status event**
  - File: `back/app/src/routes/factories/websocket_handlers_state.py:48-56`
  - Fix: Add `"server_time": time.time()` to payload

- [ ] **Implement envelope format for all state events**
  - File: `back/app/src/routes/factories/websocket_handlers_state.py` (multiple locations)
  - Fix: Use StateEventCoordinator.broadcast_state_change() or create proper envelopes
  - Locations:
    - Lines 197-206 (nfc_association_state activated)
    - Lines 237-245 (nfc_association_state cancelled)
    - Lines 311-323 (nfc_association_state waiting)

- [ ] **Ensure server_seq in all NFC events**
  - File: `back/app/src/routes/factories/websocket_handlers_state.py:146,148`
  - Fix: Verify snapshot objects contain server_seq

- [ ] **Use StateEventCoordinator instead of direct emit**
  - File: `back/app/src/routes/factories/websocket_handlers_state.py` (multiple)
  - Fix: Replace direct `self.sio.emit()` with coordinator methods
  - Locations: Lines 48, 74, 97, 114, 126, 148, 166, 197, 237, 311, 347, etc.

### 1.2 API Contract Fixes

- [ ] **Fix volume endpoint response to match contract**
  - File: `back/app/src/api/endpoints/player_api_routes.py:472-482`
  - Fix: Return `{"volume": int}` instead of full PlayerState

- [ ] **Add request_id tracking to UnifiedResponseService**
  - File: `back/app/src/services/response/unified_response_service.py:55-82`
  - Fix: Add request_id parameter and populate from request headers

- [ ] **Standardize error_type usage across endpoints**
  - Files: Multiple API route files
  - Fix: Document and enforce consistent error_type patterns

---

## Phase 2: HIGH Priority Code Quality (3 issues)

### 2.1 Refactor WebSocket Handlers (421 lines → modular)

- [ ] **Create handler module structure**
  - Create: `back/app/src/routes/handlers/`
  - Create: `back/app/src/routes/handlers/__init__.py`

- [ ] **Extract ConnectionHandlers**
  - Create: `back/app/src/routes/handlers/connection_handlers.py`
  - Move: connect, disconnect handlers

- [ ] **Extract SubscriptionHandlers**
  - Create: `back/app/src/routes/handlers/subscription_handlers.py`
  - Move: join:playlists, join:playlist, leave:playlists, leave:playlist, join:nfc

- [ ] **Extract NFCHandlers**
  - Create: `back/app/src/routes/handlers/nfc_handlers.py`
  - Move: start_nfc_link, stop_nfc_link, override_nfc_tag

- [ ] **Extract SyncHandlers**
  - Create: `back/app/src/routes/handlers/sync_handlers.py`
  - Move: sync:request, client:request_current_state, client_ping, health_check

- [ ] **Update websocket_handlers_state.py to use new handlers**
  - Refactor: Compose handlers instead of implementing directly

- [ ] **Extract override_nfc_tag logic (87 lines → ~30)**
  - Create: `back/app/src/application/use_cases/nfc_override_use_case.py`
  - Extract: Business logic from handler

### 2.2 Fix Direct Private Member Access

- [ ] **Add public method to UploadController**
  - File: `back/app/src/application/controllers/upload_controller.py`
  - Add: `get_all_sessions() -> List[SessionInfo]`

- [ ] **Update upload_api_routes to use public method**
  - File: `back/app/src/api/endpoints/upload_api_routes.py:73-75`
  - Replace: Direct `._sessions` access with `get_all_sessions()`

### 2.3 Create Error Handling Infrastructure

- [ ] **Create error handling decorators**
  - Create: `back/app/src/services/decorators/error_decorators.py`
  - Add: `@with_rate_limiting`, `@with_error_handling`, `@with_logging`

- [ ] **Create dependency injection helpers**
  - Create: `back/app/src/services/decorators/injection_decorators.py`
  - Add: `@inject_services(...)`

- [ ] **Apply decorators to player_api_routes**
  - File: `back/app/src/api/endpoints/player_api_routes.py`
  - Refactor: Remove duplicated try-catch blocks (8 locations)

- [ ] **Apply decorators to nfc_api_routes**
  - File: `back/app/src/api/endpoints/nfc_api_routes.py`
  - Refactor: Remove duplicated error handling

- [ ] **Apply decorators to upload_api_routes**
  - File: `back/app/src/api/endpoints/upload_api_routes.py`
  - Refactor: Remove duplicated error handling

---

## Phase 3: Code Duplications (22 issues)

### 3.1 Error Handling Patterns

- [x] Already covered in Phase 2.3

### 3.2 Service Getter Pattern

- [ ] **Enhance dependency injection for service getters**
  - Files: nfc_api_routes.py, player_api_routes.py
  - Fix: Use `@inject_services` decorator

### 3.3 Test Data Detection

- [ ] **Create test detection utility**
  - Create: `back/app/src/utils/test_detection.py`
  - Add: `is_test_request()`, `create_mock_response()`

- [ ] **Replace duplicated test detection in nfc_api_routes**
  - File: `back/app/src/api/endpoints/nfc_api_routes.py`
  - Lines: 102-123, 197-208, 307-326
  - Replace: With utility calls

### 3.4 Acknowledgment Sending

- [ ] **Create acknowledgment helper**
  - File: `back/app/src/utils/acknowledgment_helper.py`
  - Add: `async def send_ack_if_needed(state_manager, client_op_id, success, data)`

- [ ] **Replace 20+ duplicated acknowledgment patterns**
  - File: `back/app/src/api/endpoints/nfc_api_routes.py`
  - Replace: All conditional acknowledgment sends

### 3.5 Playlist Serialization

- [ ] **Consolidate playlist serialization**
  - Review: `unified_serialization_service.py` vs `state_serialization_application_service.py`
  - Fix: Use single source of truth

- [ ] **Remove duplicated serialization logic**
  - Identify: All playlist serialization locations
  - Consolidate: Into single service

### 3.6 Socket Event Listening Setup

- [ ] **Create centralized event subscription manager**
  - Create: `front/src/services/EventSubscriptionManager.ts`
  - Consolidate: Event listener setup patterns

### 3.7 State Event Conversion

- [ ] **Create bidirectional event type map**
  - File: `back/app/src/application/services/state_event_coordinator.py:275-301`
  - Fix: Use enum with conversion methods

### 3.8 Playlist Operations Error Handling

- [ ] **Create base service class with common error handling**
  - Create: `back/app/src/api/services/base_operations_service.py`
  - Extract: Common try-catch patterns

### 3.9 Upload Progress Calculation

- [ ] **Create progress calculation utility**
  - Create: `back/app/src/utils/progress_utils.py`
  - Add: `calculate_progress(current, total)`

### 3.10 Empty Object Defaults

- [ ] **Add type-safe wrappers or Optional types**
  - Review: All `or {}` patterns
  - Fix: Use proper type hints

---

## Phase 4: Obsolete Code Cleanup (22 issues)

### 4.1 Commented-Out Code

- [ ] **Remove obsolete comments about API Contract v2.0**
  - File: `back/app/src/routes/factories/websocket_handlers_state.py:175-177`

- [ ] **Review and simplify logging state variables**
  - File: `back/app/src/application/services/state_event_coordinator.py:63-66`

### 4.2 Dead Code

- [ ] **Remove unused get_router method**
  - File: `back/app/src/api/endpoints/web_api_routes.py:115-121`

- [ ] **Address or remove TODO comment**
  - File: `back/app/src/domain/data/models/track.py:48`

### 4.3 Unused Imports

- [ ] **Run pylint/flake8 to identify unused imports**
  - Command: `pylint back/app/src/`

- [ ] **Remove all unused imports**
  - Automated: Use tool or manual cleanup

### 4.4 Redundant Type Checks

- [ ] **Add type hints to eliminate runtime checks**
  - File: `back/app/src/api/endpoints/upload_api_routes.py:76`
  - Fix: Use mypy for compile-time safety

### 4.5 Old Validation Patterns

- [ ] **Review test detection logic necessity**
  - File: `back/app/src/api/endpoints/nfc_api_routes.py:102-123`
  - Simplify: If tests updated

---

## Phase 5: MEDIUM Priority Code Quality (42 issues)

### 5.1 Missing Type Hints

- [ ] **Add type hints to websocket_handlers_state.py**
  - File: `back/app/src/routes/factories/websocket_handlers_state.py`
  - Add: Parameter and return type hints

- [ ] **Add type hints to all API routes**
  - Files: All files in `back/app/src/api/endpoints/`

- [ ] **Add type hints to all service files**
  - Files: All files in `back/app/src/api/services/`

- [ ] **Ensure build_current_player_state returns consistent type**
  - File: `back/app/src/routes/factories/websocket_handlers_state.py:389-398`
  - Fix: Always return PlayerStateModel

### 5.2 Hard-Coded Values

- [ ] **Move magic numbers to configuration**
  - Create: `front/src/config/intervals.ts`
  - Move: PLAYER_STATE_CHECK_INTERVAL and other intervals

- [ ] **Create room name constants**
  - Create: `back/app/src/constants/socket_rooms.py`
  - Add: `SocketRooms` class with static methods

- [ ] **Replace all magic strings with constants**
  - Files: websocket_handlers_state.py, state_event_coordinator.py
  - Replace: "playlists", "playlist:{id}", etc.

### 5.3 Complex Conditional Logic

- [ ] **Extract nested conditionals to methods**
  - File: `back/app/src/routes/factories/websocket_handlers_state.py:298-308`
  - Create: `_process_tag_override()`, `_emit_waiting_state()`

### 5.4 Missing Error Context

- [ ] **Add context to all error logs**
  - Pattern: Add `extra={}` dict with client_op_id, request_id, etc.
  - Files: All API endpoints and handlers

### 5.5 Lack of Defensive Programming

- [ ] **Fix silent mock object creation**
  - File: `back/app/src/application/services/state_event_coordinator.py:292-301`
  - Fix: Raise exception for unknown event types

### 5.6 Inconsistent Logging Levels

- [ ] **Create logging level guidelines**
  - Create: `LOGGING_GUIDELINES.md`

- [ ] **Review and standardize logging calls**
  - Files: All files with logger usage

### 5.7 Missing Docstrings

- [ ] **Add comprehensive docstrings to all handlers**
  - Example: handle_join_playlist needs Args, Raises, Side Effects
  - Files: All handler files

- [ ] **Add docstrings to all service methods**
  - Files: All service files

- [ ] **Add docstrings to all use cases**
  - Files: All use case files

### 5.8 Inconsistent Naming

- [ ] **Create case conversion utilities**
  - Create: `front/src/utils/caseConverter.ts`
  - Add: `toFrontendCase()`, `toBackendCase()`

- [ ] **Standardize event naming**
  - Decision: Use colon separator for all events
  - Update: `nfc_status` → `nfc:status`

---

## Phase 6: Architecture Violations (8 issues)

### 6.1 Layer Boundary Violations

- [ ] **Inject NFCApplicationService into WebSocketStateHandlers**
  - File: `back/app/src/routes/factories/websocket_handlers_state.py:269-275`
  - Fix: Add nfc_service to constructor parameters

- [ ] **Remove getattr() access to application internals**
  - Replace: All `getattr(self.app, ...)` with proper DI

### 6.2 Route Layer Knowledge

- [ ] **Use service interfaces instead of internal access**
  - File: `back/app/src/api/endpoints/upload_api_routes.py:72-75`
  - Fix: Already covered in Phase 2.2

### 6.3 Direct Imports in Functions

- [ ] **Inject playback_coordinator and player_state_service**
  - File: `back/app/src/routes/factories/websocket_handlers_state.py:376-377`
  - Fix: Add to constructor instead of importing in function

### 6.4 Service Responsibility Violations

- [ ] **Remove logging from UnifiedResponseService**
  - File: `back/app/src/services/response/unified_response_service.py:127-130`
  - Fix: Let error handling middleware handle logging

- [ ] **Extract throttling from StateEventCoordinator**
  - File: `back/app/src/application/services/state_event_coordinator.py:154-160`
  - Create: `back/app/src/services/throttle/throttle_service.py`

### 6.5 Tight Coupling

- [ ] **Use DI container instead of getattr**
  - File: `back/app/src/routes/factories/websocket_handlers_state.py` (multiple)
  - Fix: Inject all dependencies via constructor

### 6.6 State Management Inconsistency

- [ ] **Consolidate frontend state management**
  - Review: Pinia stores, DOM events, socket listeners
  - Decision: Choose single pattern
  - Refactor: Consolidate to chosen pattern

---

## Phase 7: Testing & Verification

### 7.1 Backend Tests

- [ ] **Run all backend unit tests**
  - Command: `cd back && python3 -m pytest tests/unit/ -v`

- [ ] **Run all backend integration tests**
  - Command: `cd back && python3 -m pytest tests/integration/ -v`

- [ ] **Run contract validation tests**
  - Command: `cd back && python3 -m pytest tests/contracts/ -v`

- [ ] **Run architecture tests**
  - Command: `cd back && python3 -m pytest tests/architecture/ -v`

### 7.2 Frontend Tests

- [ ] **Run all frontend unit tests**
  - Command: `cd front && npm run test:unit`

- [ ] **Run frontend integration tests**
  - Command: `cd front && npm run test:integration`

### 7.3 End-to-End Tests

- [ ] **Run E2E tests**
  - Command: `cd front && npm run test:e2e`

### 7.4 Code Quality Checks

- [ ] **Run pylint on backend**
  - Command: `cd back && pylint app/src/`

- [ ] **Run mypy for type checking**
  - Command: `cd back && mypy app/src/`

- [ ] **Run flake8 for style**
  - Command: `cd back && flake8 app/src/`

- [ ] **Run ESLint on frontend**
  - Command: `cd front && npm run lint`

### 7.5 Coverage Analysis

- [ ] **Check backend test coverage**
  - Command: `cd back && python3 -m pytest --cov=app/src --cov-report=html`
  - Target: > 80% coverage

- [ ] **Check frontend test coverage**
  - Command: `cd front && npm run test:coverage`
  - Target: > 80% coverage

---

## Phase 8: Documentation Updates

### 8.1 Code Documentation

- [ ] **Update README with refactoring details**
  - File: `README.md`

- [ ] **Create logging guidelines document**
  - Create: `documentation/LOGGING_GUIDELINES.md`

- [ ] **Create error handling documentation**
  - Create: `documentation/ERROR_HANDLING.md`

### 8.2 Architecture Decision Records

- [ ] **Create ADR for WebSocket handler refactoring**
  - Create: `documentation/adr/001-websocket-handler-modularization.md`

- [ ] **Create ADR for error handling pattern**
  - Create: `documentation/adr/002-error-handling-decorators.md`

- [ ] **Create ADR for dependency injection improvements**
  - Create: `documentation/adr/003-dependency-injection-enhancements.md`

### 8.3 Contract Updates

- [ ] **Verify contract compliance**
  - Run: Contract validation tests

- [ ] **Update contract version if needed**
  - Review: If any breaking changes made

---

## Final Checklist

- [ ] All 112 issues addressed
- [ ] All tests passing (unit, integration, E2E)
- [ ] Code coverage > 80%
- [ ] No pylint/mypy/flake8 errors
- [ ] Documentation updated
- [ ] ADRs created for major decisions
- [ ] Contract compliance verified
- [ ] Git commit with detailed message
- [ ] Ready for code review

---

## Estimated Timeline

- **Phase 1 (Contract Violations):** 4-6 hours
- **Phase 2 (Code Quality HIGH):** 6-8 hours
- **Phase 3 (Duplications):** 4-5 hours
- **Phase 4 (Obsolete Code):** 2-3 hours
- **Phase 5 (Code Quality MED):** 6-8 hours
- **Phase 6 (Architecture):** 4-5 hours
- **Phase 7 (Testing):** 3-4 hours
- **Phase 8 (Documentation):** 2-3 hours

**Total Estimated Time:** 31-42 hours of focused work

---

**Status:** Ready to begin Phase 1
**Next Action:** Start with HIGH priority contract violations
