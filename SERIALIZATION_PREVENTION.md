# Serialization Bug Prevention Guide

This document describes the prevention strategies implemented to avoid serialization bugs like issue #71.

## The Problem (Issue #71)

**Root Cause**: Duplicate serialization paths with different behaviors:
1. `UnifiedSerializationService` - Correct (includes `number` field)
2. `PurePlaylistRepositoryAdapter._track_to_dict()` - Buggy (missing `number` field)

**Impact**: Playlist "bibeo - promenons nous dans les bois" failed to display because:
- It had an NFC tag association
- NFC associations triggered WebSocket broadcasts
- WebSocket broadcasts used the broken serialization path
- Frontend expected `number` field but received only `track_number`

## Prevention Layers Implemented

### Layer 1: Automated Contract Tests ✅

**File**: `back/tests/unit/test_serialization_contracts.py`

**What it does**:
- Validates ALL serialization paths produce contract-compliant output
- Tests that `number` field is present in all track serializations
- Regression tests for issue #71 specific scenarios
- Runs automatically on every commit via CI/CD

**Coverage** (15 tests):
- `serialize_track()` includes required fields
- Field types are correct (number is int, not string)
- Property-based fields (@property) are serialized
- Playlist serialization embeds tracks correctly
- Format consistency (API vs WebSocket)
- Edge cases (minimal tracks, dict inputs, missing optionals)

**Example**:
```python
def test_track_serialization_includes_required_fields(self, sample_track):
    result = UnifiedSerializationService.serialize_track(sample_track, format="api")

    required_fields = ['id', 'number', 'track_number', 'title', 'filename', 'duration_ms']
    for field in required_fields:
        assert field in result, f"Missing required field: {field}"

    assert result['number'] == result['track_number']
```

### Layer 2: Runtime Defense-in-Depth ✅

**File**: `back/app/src/services/broadcasting/unified_broadcasting_service.py`

**What it does**:
- Validates data before broadcasting to frontend
- Auto-fixes common serialization bugs
- Logs warnings/errors for debugging
- Prevents silent failures

**Implementation**:
```python
def _validate_and_fix_contract(self, playlist_data: dict[str, Any]) -> dict[str, Any]:
    """Validate and fix contract compliance before broadcasting."""
    for idx, track in enumerate(playlist_data.get('tracks', [])):
        if 'number' not in track:
            if 'track_number' in track:
                # Auto-fix
                track['number'] = track['track_number']
                logger.warning(
                    f"CONTRACT VIOLATION FIXED: Track {idx} missing 'number' field, "
                    f"auto-fixed from 'track_number'. This indicates a serialization bug."
                )
            else:
                # Cannot fix - log error
                logger.error(
                    f"CONTRACT VIOLATION CANNOT FIX: Track {idx} missing both fields! "
                    f"Available fields: {', '.join(track.keys())}. "
                    f"This will cause frontend errors!"
                )
    return playlist_data
```

**Coverage** (11 tests):
- Auto-detection of missing fields
- Auto-fix logic
- Warning/error logging
- Batch track validation
- Non-mutating behavior
- Integration with broadcasting

### Layer 3: Frontend Fail-Loud ✅

**File**: `front/src/utils/trackFieldAccessor.ts`

**What it does**:
- Throws explicit errors on missing/invalid fields
- No silent fallbacks (`?? 0` removed)
- Comprehensive error logging
- **This is what caught the bug in production!**

**Implementation**:
```typescript
export function getTrackNumber(track: Track): number {
  if (track.number === undefined || track.number === null) {
    logger.error('CONTRACT VIOLATION: Track missing required "number" field', {
      trackId: track.id,
      availableFields: Object.keys(track),
      trackData: track
    });

    throw new Error(
      `Track missing required 'number' field. ` +
      `Available fields: ${Object.keys(track).join(', ')}. ` +
      `This indicates a backend serialization bug (see issue #71).`
    );
  }

  if (typeof track.number !== 'number') {
    throw new Error(
      `Track 'number' field has wrong type. ` +
      `Expected: number, Got: ${typeof track.number}`
    );
  }

  return track.number;
}
```

## Architectural Guidelines

### ✅ DO: Use UnifiedSerializationService

**Good**:
```python
from app.src.services.serialization.unified_serialization_service import UnifiedSerializationService

def get_playlist_by_id(self, playlist_id: str) -> dict[str, Any] | None:
    playlist = await self._repo.find_by_id(playlist_id)
    if playlist is not None:
        return self._serializer.serialize_playlist(playlist)  # ✅ Single source of truth
    return None
```

### ❌ DON'T: Create custom serialization methods

**Bad**:
```python
def _track_to_dict(self, track: Track) -> dict[str, Any]:
    """Custom serialization - BAD! Creates duplicate logic."""
    return {
        'id': track.id,
        'track_number': track.track_number,
        # Missing 'number' field - BUG!
        'title': track.title,
        # ... manual field mapping
    }
```

**Why it's bad**:
- Duplicate logic diverges over time
- Easy to miss required fields
- No guarantee of contract compliance
- Creates maintenance burden

### Best Practices

1. **Single Source of Truth**
   - ALL API serialization MUST use `UnifiedSerializationService`
   - Delete or deprecate custom `_to_dict()` methods
   - Update all adapters to delegate to centralized service

2. **Contract Testing**
   - Add automated tests for ALL serialization paths
   - Test required fields are present
   - Test field types are correct
   - Run tests on every commit

3. **Property Documentation**
   - Document which `@property` fields are required in API responses
   - Add comments explaining serialization requirements
   - Link to issue #71 for context

4. **Defense in Depth**
   - Multiple detection layers (build + runtime + frontend)
   - Fail-loud instead of silent fallbacks
   - Comprehensive logging for debugging

## Code Review Checklist

When reviewing code that touches serialization:

- [ ] Does it use `UnifiedSerializationService`?
- [ ] If custom serialization, does it include ALL required fields?
- [ ] Are there contract tests covering this code path?
- [ ] Is there a WebSocket broadcast that uses this data?
- [ ] Does the TypeScript consumer handle missing fields properly?
- [ ] Are `@property` fields documented if they must be serialized?

## Monitoring in Production

### Logging Patterns

**Contract violations auto-fixed**:
```
WARNING: CONTRACT VIOLATION FIXED: Track 0 (ID: abc123) missing 'number' field,
auto-fixed from 'track_number'=1. This indicates a serialization bug (see issue #71).
```

**Contract violations cannot fix**:
```
ERROR: CONTRACT VIOLATION CANNOT FIX: Track 0 (ID: abc123) missing both
'number' and 'track_number' fields! Available fields: id, title, filename.
This will cause frontend errors!
```

### What to do if you see these logs

1. **Auto-fixed violations**:
   - Find the code path that produced the bad data
   - Check if it uses `UnifiedSerializationService`
   - If not, refactor to use it
   - Add regression test

2. **Unfixable violations**:
   - CRITICAL: Bad data reached broadcasting layer
   - Investigate which repository/adapter produced it
   - Fix immediately - frontend will crash
   - Add regression test

## Automated Analysis Tools (Future)

### Recommended: Custom Linter

Create pylint/ruff rule to detect dangerous patterns:

```python
# Detect manual dict construction from domain models
def check_manual_serialization(node):
    """Warn about manual dict construction from domain models."""
    if is_dict_literal(node) and has_model_attribute_access(node):
        report_warning(
            "Manual dict construction detected. Use UnifiedSerializationService instead."
        )
```

### Recommended: Static Type Checking

Use TypedDict for return types:

```python
from typing import TypedDict

class TrackDict(TypedDict):
    id: str
    number: int  # Type checker enforces this
    track_number: int
    title: str
    # ... other fields

def serialize_track(track: Track) -> TrackDict:
    # Type checker ensures all required fields present
    return {
        'id': track.id,
        'number': track.track_number,
        'track_number': track.track_number,
        'title': track.title,
        # ...
    }
```

## Summary

**What we fixed**:
- ✅ Eliminated duplicate serialization paths (architectural fix)
- ✅ Added 26 automated tests (15 contract + 11 validation)
- ✅ Implemented runtime validation with auto-fix
- ✅ Frontend fail-loud validation (already existed)

**Result**:
- Multiple detection layers prevent bugs from reaching production
- Auto-recovery from serialization bugs
- Clear diagnostic logs for debugging
- Comprehensive test coverage prevents regression

**Lesson**: Duplicate code paths doing "similar" things inevitably diverge. Consolidate to a single source of truth to prevent this entire class of bugs.

## References

- Issue #71: https://github.com/The-Open-Music-Box/raspberrypi-firmware/issues/71
- PR #80: https://github.com/The-Open-Music-Box/raspberrypi-firmware/pull/80
- Commit (consolidation): `2f74e5c58`
- Commit (prevention): `75249486`
