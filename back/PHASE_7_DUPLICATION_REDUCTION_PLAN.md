# Phase 7: Final Duplication Reduction Plan
## Target: 2.06% → <1.0% (-1.06%, ~50 clones)

### Current Status: 2.06% (94 clones)

## High-Impact Opportunities (Sorted by Impact)

### Category 1: Protocol/Interface Duplications (Highest Impact)
**Impact**: ~35% of remaining duplications (30+ clones)
**Files**: `domain/protocols/*.py`

#### 1.1 Protocol Method Signatures (144 tokens, 16 lines)
- `persistence_service_protocol.py` - 5 internal duplications
- Nearly identical abstract method definitions
- **Action**: Extract common protocol base class with shared method patterns
- **Estimated reduction**: -5 clones (-80 lines)

#### 1.2 Response Service Protocol (98 tokens, 10 lines)
- `response_service_protocol.py` - 4 internal duplications
- Duplicate method signatures for error responses
- **Action**: Consolidate into base response protocol methods
- **Estimated reduction**: -4 clones (-35 lines)

#### 1.3 Audio Backend Protocol (57 tokens, 21 lines)
- `audio_backend_protocol.py` - 1 duplication with implementations
- **Action**: Review if duplication is necessary for protocol definition
- **Estimated reduction**: -1 clone (-21 lines)

**Category 1 Total**: -10 clones, -136 lines

---

### Category 2: Repository Duplications (Second Highest Impact)
**Impact**: ~20% of remaining duplications
**Files**: `infrastructure/repositories/*.py`

#### 2.1 SQLite Playlist Repository (144 tokens, 14 lines)
- `pure_sqlite_playlist_repository.py` - 4 internal duplications
- Duplicate query execution patterns
- **Action**: Extract `_execute_query_with_tx()` helper method
- **Estimated reduction**: -4 clones (-65 lines)

#### 2.2 SQLite Database Service (81 tokens, 12 lines)
- `sqlite_database_service.py` - 3 internal duplications
- Connection retry logic duplicated
- **Action**: Extract `_execute_with_retry()` helper
- **Estimated reduction**: -3 clones (-31 lines)

**Category 2 Total**: -7 clones, -96 lines

---

### Category 3: Error Decorator Internal (Third Highest Impact)
**Impact**: ~15% of remaining duplications
**File**: `services/error/unified_error_decorator.py`

#### 3.1 Async/Sync Wrapper Duplications (98 tokens, 15 lines)
- 4 internal duplications of nearly identical async/sync wrappers
- **Action**: Create `_create_wrapper()` factory function
- **Estimated reduction**: -4 clones (-50 lines)

**Category 3 Total**: -4 clones, -50 lines

---

### Category 4: Route Handlers Initialization
**Impact**: ~10% of remaining duplications
**Files**: `routes/handlers/*.py`, `routes/factories/*.py`

#### 4.1 WebSocket Handler State (78 tokens, 12 lines)
- `connection_handlers.py`, `subscription_handlers.py` - similar init patterns
- **Action**: Extract base handler initialization class
- **Estimated reduction**: -5 clones (-40 lines)

#### 4.2 Route Factory Imports (66 tokens, 10 lines)
- All route factories have identical import patterns
- **Action**: Create `routes/common_imports.py`
- **Estimated reduction**: -5 clones (-50 lines)

**Category 4 Total**: -10 clones, -90 lines

---

### Category 5: Playlist API Initialization
**Impact**: ~8% of remaining duplications
**Files**: `api/endpoints/playlist/*.py`

#### 5.1 Constructor Duplications (87 tokens, 17 lines)
- `playlist_playback_api.py`, `playlist_track_api.py` - identical `__init__`
- **Action**: Extract common initialization to BasePlaylistAPI
- **Estimated reduction**: -4 clones (-60 lines)

**Category 5 Total**: -4 clones, -60 lines

---

### Category 6: Internal API Route Duplications
**Impact**: ~8% of remaining duplications
**Files**: Various `*_api_routes.py`

#### 6.1 NFC API Internal (63 tokens, 10 lines)
- `nfc_api_routes.py` - 2 internal error handling patterns
- **Action**: Extract to helper method
- **Estimated reduction**: -2 clones (-20 lines)

#### 6.2 Player API Internal (54 tokens, 11 lines)
- `player_api_routes.py` - broadcasting patterns
- **Action**: Already partially done, extract remaining
- **Estimated reduction**: -2 clones (-22 lines)

#### 6.3 YouTube API Internal (63 tokens, 12 lines)
- `youtube_api_routes.py` - error handling patterns
- **Action**: Extract validation helper
- **Estimated reduction**: -2 clones (-24 lines)

#### 6.4 Upload API Internal (58 tokens, 11 lines)
- `upload_api_routes.py` - session validation patterns
- **Action**: Extract session check helper
- **Estimated reduction**: -2 clones (-22 lines)

#### 6.5 System API Internal (74 tokens, 10 lines)
- `system_api_routes.py` - health check patterns
- **Action**: Extract health check helper
- **Estimated reduction**: -3 clones (-30 lines)

**Category 6 Total**: -11 clones, -118 lines

---

### Category 7: Small Optimizations
**Impact**: ~4% remaining
**Various files**: Multiple small 5-7 line duplications

#### 7.1 Progress Utils (52 tokens, 8 lines)
- Internal duplication in progress calculation
- **Action**: Extract calculation helper
- **Estimated reduction**: -1 clone (-8 lines)

#### 7.2 NFC Events (59 tokens, 5 lines)
- Event creation patterns
- **Action**: Extract event factory
- **Estimated reduction**: -1 clone (-5 lines)

**Category 7 Total**: -2 clones, -13 lines

---

## Execution Plan (Prioritized by Impact/Effort Ratio)

### Phase 7A: Quick Wins (30 minutes, -15 clones)
1. **Extract repository helpers** (Category 2) - High impact, low complexity
2. **Extract API route helpers** (Category 6) - Medium impact, low complexity
3. **Extract progress utils** (Category 7.1) - Low impact, very easy

**Target after 7A**: 2.06% → ~1.50%

### Phase 7B: Medium Effort (1 hour, -15 clones)
1. **Consolidate error decorator wrappers** (Category 3)
2. **Extract route handler base class** (Category 4.1)
3. **Create playlist API base class** (Category 5)

**Target after 7B**: 1.50% → ~1.00%

### Phase 7C: Protocol Refactoring (1-2 hours, -10 clones) [OPTIONAL]
1. **Consolidate protocol duplications** (Category 1)
   - This is complex and risky
   - May not be worth it given protocols are by design repetitive
   - **Decision**: Skip unless absolutely needed for <1.0% target

**Final Target**: ~1.00% or below

---

## Success Criteria
- ✅ Achieve <1.0% duplication (target: 0.90-0.95%)
- ✅ All tests passing (27/27)
- ✅ No breaking changes to public APIs
- ✅ Maintain code readability and maintainability

---

## Risk Assessment

### Low Risk (Safe to execute)
- Categories 2, 6, 7: Pure extraction, no architectural changes

### Medium Risk (Test carefully)
- Categories 3, 4, 5: Structural changes, but well-isolated

### High Risk (Consider skipping)
- Category 1: Protocol changes could affect contracts and type checking
  - **Recommendation**: Skip this category unless critical

---

## Estimated Results
- **Conservative**: -25 clones (-350 lines) → **1.35%**
- **Optimistic**: -35 clones (-500 lines) → **0.85%**
- **Realistic**: -30 clones (-450 lines) → **1.05%**
