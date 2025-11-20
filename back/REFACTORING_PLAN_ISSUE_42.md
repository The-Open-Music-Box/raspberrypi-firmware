# Issue 42 - Code Duplication Refactoring Plan

## Executive Summary

**Initial Analysis Date:** 2025-11-20
**Current Duplication:** 3.42% (1,505 lines across 140 clones)
**Target:** < 0.5% duplication
**Estimated Effort:** 3-5 sessions
**Priority:** High (technical debt reduction)

## Current State

### Duplication Metrics (jscpd analysis)
- **Files analyzed:** 248
- **Total lines:** 44,061
- **Clones found:** 140 (significantly higher than initially reported 30)
- **Duplicated lines:** 1,505 (3.42%)
- **Duplicated tokens:** 9,943 (3.92%)

### Top Duplication Areas

| Area | Clones | Estimated Lines | Priority | Complexity |
|------|--------|----------------|----------|------------|
| Bootstrap files | 5 | ~155 | HIGH | Medium |
| LED Controllers | 11 | ~120 | HIGH | Low-Medium |
| Data Models | 6 | ~95 | HIGH | Low |
| NFC Hardware | 6 | ~85 | MEDIUM | Medium |
| Upload/NFC Entities | 2 | ~50 | MEDIUM | Low |
| Audio Backends | 2 | ~40 | LOW | Medium |
| API Routes | 20+ | ~300 | MEDIUM | Low |
| Various Services | 30+ | ~200 | LOW | Low |

---

## Phase 1: Bootstrap Files Refactoring (~155 lines)

### Problem
`application/bootstrap.py` and `domain/bootstrap.py` have significant duplication:
- 5 large clone blocks (68, 26, 24, 21, 16 lines)
- Both classes named `DomainBootstrap` (confusing)
- Application version extends domain version with LED/controls management

### Solution: Inheritance Pattern

#### Step 1: Verify Current Architecture
```bash
# Check imports and dependencies
grep -r "DomainBootstrap" app/src --include="*.py"
grep -r "from.*bootstrap import" app/src --include="*.py"
```

#### Step 2: Rename Application Bootstrap Class
**File:** `app/src/application/bootstrap.py`

```python
# Change class name
class ApplicationBootstrap(DomainBootstrap):  # Inherit from domain
    """Application-level bootstrap with hardware management."""

    def __init__(self, led_manager=None, led_event_handler=None,
                 physical_controls_manager=None):
        super().__init__()  # Call parent constructor
        # Application-specific initialization
        self._led_manager = led_manager
        self._led_event_handler = led_event_handler
        self._physical_controls_manager = physical_controls_manager
```

#### Step 3: Extract Retry Logic Helper
**New File:** `app/src/application/utils/hardware_retry.py`

```python
"""Hardware initialization retry helper."""
import asyncio
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

async def retry_hardware_init(
    name: str,
    init_func: Callable,
    max_retries: int = 3,
    retry_delay: float = 2.0,
    critical: bool = False
) -> bool:
    """Generic hardware initialization with retry logic.

    Args:
        name: Hardware component name for logging
        init_func: Async function to call for initialization
        max_retries: Maximum retry attempts
        retry_delay: Delay between retries in seconds
        critical: If True, raise exception on failure

    Returns:
        True if successful, False if non-critical failure

    Raises:
        Exception: If critical=True and all retries fail
    """
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Initializing {name} (attempt {attempt}/{max_retries})...")
            result = await init_func()
            logger.info(f"✅ {name} initialized successfully")
            return True
        except Exception as e:
            if attempt < max_retries:
                logger.warning(f"⚠️ {name} attempt {attempt} failed: {e}")
                logger.info(f"🔄 Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            else:
                msg = f"❌ {name} failed after {max_retries} attempts: {e}"
                if critical:
                    logger.error(msg, exc_info=True)
                    raise
                else:
                    logger.warning(msg)
                    logger.warning(f"⚠️ Continuing without {name} (non-critical)")
                    return False
    return False
```

#### Step 4: Refactor ApplicationBootstrap Methods
Replace the three `_initialize_*_with_retry` methods with calls to the helper:

```python
async def start(self):
    """Start all domain services with hardware retry logic."""
    if not self._is_initialized:
        raise RuntimeError("ApplicationBootstrap not initialized")

    # Initialize LED system
    if self._led_manager and self._led_event_handler:
        await retry_hardware_init(
            "LED system",
            self._initialize_led,
            critical=False
        )

    # Start audio domain (critical)
    if audio_domain_container.is_initialized:
        await retry_hardware_init(
            "Audio domain",
            audio_domain_container.start,
            critical=True
        )

    # Initialize physical controls
    if self._physical_controls_manager:
        await retry_hardware_init(
            "Physical controls",
            self._physical_controls_manager.initialize,
            critical=False
        )

    # Set system ready state
    if self._led_event_handler:
        await self._led_event_handler.on_system_ready()

    logger.info("🚀 Application services started")
```

#### Step 5: Update Imports Throughout Codebase
```bash
# Find all references
grep -r "from.*application.bootstrap import DomainBootstrap" app/src
grep -r "DomainBootstrap()" app/src

# Update to:
# from app.src.application.bootstrap import ApplicationBootstrap
# ApplicationBootstrap(led_manager=..., ...)
```

**Files likely needing updates:**
- `app/src/infrastructure/di/container.py`
- `app/src/core/application.py`
- Any dependency injection configuration

#### Step 6: Testing
```bash
# Run tests
python -m pytest app/tests/ -v

# Verify no import errors
python -c "from app.src.application.bootstrap import ApplicationBootstrap"
python -c "from app.src.domain.bootstrap import DomainBootstrap"
```

### Expected Outcomes
- ✅ Remove ~155 lines of duplication
- ✅ Clear class naming (ApplicationBootstrap vs DomainBootstrap)
- ✅ Reusable retry logic helper
- ✅ Proper inheritance hierarchy (domain → application)
- ✅ Duplication reduction: 3.42% → ~2.9%

---

## Phase 2: LED Controller Refactoring (~120 lines)

### Problem
`infrastructure/hardware/leds/rgb_led_controller.py` has 11 internal clones

### Analysis Needed
1. Read `rgb_led_controller.py` to identify patterns
2. Check if clones are:
   - Similar color/animation patterns
   - Repeated state management logic
   - Duplicated hardware initialization

### Solution Approach
1. **Extract method pattern** for repeated code blocks
2. **Template method pattern** for similar animation sequences
3. **Configuration-driven** color/animation definitions

### Implementation (to be detailed after analysis)
```bash
# Analyze clones
jscpd app/src/infrastructure/hardware/leds/rgb_led_controller.py \
  --min-lines 5 --min-tokens 50 --format "python" --output ./led-analysis
```

---

## Phase 3: Data Models Refactoring (~95 lines)

### Problem
`common/data_models.py` has 6 internal clones

### Likely Issues
- Similar Pydantic model definitions
- Repeated field validation patterns
- Duplicated serialization logic

### Solution Approach
1. **Base model inheritance** for common fields
2. **Mixins** for shared functionality
3. **Field factory functions** for common field patterns

### Example Pattern
```python
class BaseModel(pydantic.BaseModel):
    """Base model with common fields."""
    id: str
    created_at: datetime
    updated_at: datetime

class PlaylistModel(BaseModel):
    """Playlist-specific fields."""
    name: str
    tracks: list[TrackModel]

class TrackModel(BaseModel):
    """Track-specific fields."""
    title: str
    duration: float
```

---

## Phase 4: NFC Hardware Refactoring (~85 lines)

### Problem
6 clones between mock and real NFC implementations

### Solution: Interface + Base Class
```python
# Base class with common logic
class BaseNFCHardware(NFCHardwareProtocol):
    """Base implementation with common patterns."""

    def __init__(self):
        self._tag_cache = {}
        self._is_initialized = False

    async def _validate_tag(self, tag_id: str) -> bool:
        """Common validation logic."""
        # Shared implementation
        pass

# Implementations extend base
class MockNFCHardware(BaseNFCHardware):
    """Mock for testing."""
    pass

class PN532NFCHardware(BaseNFCHardware):
    """Real hardware."""
    pass
```

---

## Phase 5: Remaining Areas (Lower Priority)

### API Routes (~300 lines across 20+ clones)
- Extract common response patterns
- Create route decorator for repeated logic
- Standardize error handling

### Service Layer (~200 lines across 30+ clones)
- Extract common service patterns
- Create base service class
- Standardize operation patterns

### Audio Backends (~40 lines)
- Extract common audio operations
- Base class for platform-specific backends

---

## Implementation Sequence (Recommended)

### Session 1: Bootstrap + Retry Helper (Completed Analysis)
- [ ] Create `hardware_retry.py` helper
- [ ] Refactor ApplicationBootstrap to use inheritance
- [ ] Update all imports
- [ ] Run tests
- **Expected reduction:** 3.42% → ~2.9%

### Session 2: LED Controllers
- [ ] Analyze duplication patterns in detail
- [ ] Extract common methods
- [ ] Apply template method pattern
- [ ] Run tests
- **Expected reduction:** ~2.9% → ~2.5%

### Session 3: Data Models + NFC
- [ ] Create base models with inheritance
- [ ] Refactor NFC implementations
- [ ] Run tests
- **Expected reduction:** ~2.5% → ~1.8%

### Session 4: API Routes + Services
- [ ] Extract common patterns
- [ ] Apply decorator/base class patterns
- [ ] Run tests
- **Expected reduction:** ~1.8% → ~1.0%

### Session 5: Final Cleanup + Verification
- [ ] Address remaining small clones
- [ ] Run full jscpd analysis
- [ ] Verify < 0.5% target (or document why remaining duplication is acceptable)
- [ ] Update documentation

---

## Testing Strategy

### After Each Phase
```bash
# 1. Run unit tests
python -m pytest app/tests/ -v

# 2. Run duplication analysis
npx jscpd app/src --pattern "**/*.py" --min-lines 5 --min-tokens 50

# 3. Check for regressions
ruff check app/src --statistics

# 4. Verify imports
python -m py_compile app/src/**/*.py
```

### Integration Testing
- Verify application starts correctly
- Test hardware initialization paths
- Verify LED/controls functionality
- Check audio playback

---

## Success Criteria

- [ ] Duplication rate < 0.5% (target) or < 1.5% (acceptable)
- [ ] All tests passing (27 passed, 4 skipped minimum)
- [ ] No new linting errors introduced
- [ ] Clear architectural improvements documented
- [ ] Performance maintained or improved

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Breaking existing functionality | HIGH | Comprehensive testing after each phase |
| Circular dependencies | MEDIUM | Careful layer separation (domain → application) |
| Performance regression | LOW | Profile before/after if concerned |
| Over-abstraction | MEDIUM | Keep patterns simple, practical |

---

## Notes for Implementation

### Important Reminders
1. **ALWAYS run tests after each change**
2. **Commit after each successful phase** (don't batch)
3. **Update this document** as patterns emerge
4. **Document architectural decisions** in code comments
5. **Keep PRs focused** (one phase per PR recommended)

### Code Review Checklist
- [ ] Duplication reduced without over-abstraction
- [ ] Tests pass
- [ ] No circular dependencies introduced
- [ ] Clear naming and documentation
- [ ] SOLID principles maintained
- [ ] Performance acceptable

---

## Current Status

**Phase:** Analysis Complete
**Last Updated:** 2025-11-20
**Next Action:** Session 1 - Bootstrap refactoring
**Assigned:** Ready for implementation

---

## References

- **Issue #42:** https://github.com/The-Open-Music-Box/raspberrypi-firmware/issues/42
- **jscpd Report:** `./jscpd-report/` (generated 2025-11-20)
- **Related Issues:** #41 (linting - completed)
