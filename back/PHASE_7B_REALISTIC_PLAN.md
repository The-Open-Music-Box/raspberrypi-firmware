# Phase 7B: Realistic Duplication Reduction Plan
## Target: 1.96% → ~1.2% (Focus on High-Value Improvements Only)

### Analysis Results: 90 Remaining Clones

**✅ WORTH FIXING: 72 clones (80%)** - Genuine improvements
**⚠️ SKIP: 18 clones (20%)** - Low value / architectural necessities

---

## ⚠️ SKIP THESE - Low Value (18 clones)

### 1. Protocol Definitions (13 clones) - **BY DESIGN**
**Why Skip**: Protocols/interfaces are intentionally repetitive. They define contracts.
- `response_service_protocol.py` - Method signatures across protocol and implementation
- `persistence_service_protocol.py` - Abstract method definitions
- `audio_backend_protocol.py` - Interface contracts
- **Verdict**: These duplications are **architectural necessities**

### 2. Import Statements (3 clones) - **NECESSARY**
**Why Skip**: Standard imports required by multiple files
- GPIO/LED controller imports
- State manager imports
- **Verdict**: Cannot be reduced without harming clarity

### 3. Micro-Duplications <7 lines (2 clones) - **TOO SMALL**
**Why Skip**: Extracting would create more code than it saves
- NFC event creation (6 lines)
- Audio factory initialization (6 lines)
- **Verdict**: Abstraction overhead > benefit

---

## ✅ WORTH FIXING - High Value (72 clones)

### Category A: Internal Duplications (44 clones) 🎯 **HIGHEST PRIORITY**
**Why Fix**: Same-file duplications are always code smells

#### A1. Audio Backend Internal (3 clones - 30 lines)
**File**: `macos_audio_backend.py`
- Lines 263-271 vs 129-137 (9 lines) - Duplicate error handling
- **Action**: Extract `_handle_playback_error()` method
- **Impact**: -2 clones, improved maintainability

#### A2. NFC Hardware Adapter Internal (1 clone - 6 lines)
**File**: `nfc_hardware_adapter.py`
- Lines 152-157 vs 30-35 (6 lines) - Duplicate timeout logic
- **Action**: Extract `_create_timeout_context()` method
- **Impact**: -1 clone

#### A3. Playlist API Internal (11 clones - 110 lines)
**Files**: `playlist_nfc_api.py`, `youtube_api_routes.py`, `upload_api_routes.py`, `system_api_routes.py`, `player_api_routes.py`
- Multiple internal error handling patterns
- **Action**: Extract route-specific helpers for each file
- **Impact**: -11 clones, cleaner APIs

#### A4. Error Decorator Internal (4 clones - 50 lines)
**File**: `unified_error_decorator.py`
- Async/sync wrapper duplications
- **Action**: Extract wrapper factory function
- **Impact**: -4 clones, simpler decorator logic

#### A5. Repository/Database Internal (10 clones - 100 lines)
**Files**: `pure_sqlite_playlist_repository.py`, `sqlite_database_service.py`
- Query execution patterns
- Connection management
- **Action**: Extract query helpers
- **Impact**: -10 clones

#### A6. WebSocket Handlers Internal (8 clones - 85 lines)
**Files**: `nfc_handlers.py`, `websocket_handlers_state.py`
- Event emission patterns
- State update patterns
- **Action**: Extract handler base methods
- **Impact**: -8 clones

#### A7. Domain Services Internal (7 clones - 74 lines)
**Files**: `playback_state_manager.py`, `track_reordering_service.py`
- State validation patterns
- **Action**: Extract validation helpers
- **Impact**: -7 clones

**Category A Total**: -44 clones (-455 lines)

---

### Category B: API Init Patterns (16 clones) 🎯 **HIGH PRIORITY**
**Why Fix**: Constructors with identical patterns across related classes

#### B1. Playlist API Constructors (4 clones - 32 lines)
**Files**: `playlist_track_api.py`, `playlist_playback_api.py`, `playlist_upload_api.py`, `playlist_nfc_api.py`
- Identical `__init__` with service injection
- **Action**: Create `BasePlaylistAPI` with common initialization
- **Impact**: -4 clones, single source of truth

#### B2. Route Factory Imports (7 clones - 70 lines)
**Files**: `*_routes.py` factories
- Standard import patterns
- **Action**: Create `routes/common_imports.py` or accept as necessary
- **Decision**: SKIP - These are standard imports
- **Impact**: 0 clones (accept as architectural necessity)

#### B3. Handler Initialization (5 clones - 50 lines)
**Files**: `connection_handlers.py`, `subscription_handlers.py`, `nfc_handlers.py`
- WebSocket handler setup patterns
- **Action**: Extract `BaseWebSocketHandler` class
- **Impact**: -5 clones

**Category B Total**: -9 clones (-82 lines)
*Note: Reduced from 16 because 7 are actually necessary imports*

---

### Category C: Error Patterns (10 clones) 🎯 **MEDIUM PRIORITY**
**Why Fix**: Genuine error handling that should be unified

#### C1. Audio Backend Error Handling (2 clones - 25 lines)
**Files**: `macos_audio_backend.py`, `wm8960_audio_backend.py`
- Hardware initialization error patterns
- **Action**: Extract to `BaseAudioBackend._handle_init_error()`
- **Impact**: -2 clones

#### C2. NFC Hardware Error Handling (1 clone - 13 lines)
**Files**: `mock_nfc_hardware.py`, `pn532_nfc_hardware.py`
- Import/initialization error patterns
- **Action**: Extract to `BaseNFCHardware` (if doesn't exist)
- **Impact**: -1 clone

#### C3. API Route Error Patterns (7 clones - 70 lines)
**Files**: Various `*_api.py` files
- Service unavailable responses
- Validation error responses
- **Action**: Already handled by BaseAPIRoutes or low-value
- **Decision**: Review individually
- **Impact**: -4 clones (skip 3 as too diverse)

**Category C Total**: -7 clones (-108 lines)

---

### Category D: Repository Patterns (2 clones) 🎯 **LOW PRIORITY**
**Why Fix**: Query patterns can be standardized

#### D1. Repository Adapter Queries (2 clones - 20 lines)
**Files**: `pure_playlist_repository_adapter.py`, `playlist_service.py`
- Similar query execution patterns
- **Action**: Extract to adapter base method
- **Impact**: -2 clones

**Category D Total**: -2 clones (-20 lines)

---

## EXECUTION PRIORITY

### Phase 7B-1: Internal Duplications (30 min)
**Target**: A1, A2, A3 (15 clones)
- Quick wins within single files
- No architecture changes
- **Result**: 1.96% → ~1.75%

### Phase 7B-2: API Initialization (45 min)
**Target**: B1, B3 (9 clones)
- Create base classes
- Refactor constructors
- **Result**: 1.75% → ~1.55%

### Phase 7B-3: Error Patterns (30 min)
**Target**: C1, C2, C3 (7 clones)
- Extract error handlers
- Unify patterns
- **Result**: 1.55% → ~1.40%

### Phase 7B-4: Remaining High-Value (45 min)
**Target**: A4-A7, D1 (remaining internal + repository)
- Complex refactorings
- **Result**: 1.40% → ~1.20%

---

## REALISTIC TARGET

**Optimistic**: 1.15% (16 clones) - All high-value fixed
**Realistic**: 1.25% (20 clones) - Most high-value fixed
**Conservative**: 1.40% (25 clones) - Core improvements only

**Recommended Target**: **1.20-1.30%** (18-22 clones)

---

## SUCCESS CRITERIA

✅ Fix all same-file duplications (Category A)
✅ Consolidate API initialization patterns (Category B1, B3)
✅ Extract common error handlers (Category C1, C2)
✅ No artificial abstractions
✅ Maintain or improve readability
✅ All tests passing

⚠️ Accept as architectural necessities:
- Protocol definitions (13 clones)
- Standard imports (3 clones)
- Micro-duplications (2 clones)

---

## ESTIMATED EFFORT

- **Phase 7B-1**: 30 min (quick wins)
- **Phase 7B-2**: 45 min (base classes)
- **Phase 7B-3**: 30 min (error handlers)
- **Phase 7B-4**: 45 min (complex)

**Total**: ~2.5 hours to reach 1.20-1.30%

---

## QUALITY GATES

Before merging each change:
1. All tests must pass
2. Code must be more readable than before
3. No increase in complexity
4. Clear benefit over status quo

If any gate fails → skip that refactoring
