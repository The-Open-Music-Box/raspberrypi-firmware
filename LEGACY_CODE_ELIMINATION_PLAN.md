# LEGACY CODE ELIMINATION PLAN
## Complete Modernization - Zero Backward Compatibility

**Mission:** Eliminate ALL legacy code and backward compatibility patterns. 100% modern code only.

**Status:** Analysis Complete - Ready for Aggressive Removal

**Date:** 2025-11-10

---

## Executive Summary

This comprehensive audit identified **8 major categories** of legacy code across the TheOpenMusicBox RPI firmware project. All backward compatibility patterns will be eliminated in favor of clean, modern implementations.

**Total Legacy Items Found:** 47 specific instances
**Impact Level:** BREAKING CHANGES - Full modernization
**Migration Required:** None (clean slate approach)

---

## 1. LEGACY API COMPATIBILITY LAYERS

### 1.1 Frontend API Service - Backward Compatibility Methods

**File:** `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/front/src/services/apiService.ts`

**Found:**
- Lines 53-98: `getPlaylists()` with fallback to old "items" format
- Lines 63-96: Fallback logic trying multiple response formats
- Lines 80-81: Legacy `items` field support (backend now uses `playlists`)
- Lines 212-237: NFC backward compatibility wrapper methods
- Lines 243-258: Upload system backward compatibility methods
- Line 264: "Default export for backward compatibility"

**Why It Exists:** Maintained compatibility during migration from old API formats

**Removal Plan:**
1. Remove all fallback logic in `getPlaylists()`
2. Remove wrapper methods for NFC (lines 212-237)
3. Remove wrapper methods for uploads (lines 243-258)
4. Keep only direct delegation to modern module APIs
5. Remove default export (force named imports)

**Breaking Change:** Components must use modern `playlistApi.getPlaylists()` directly

---

### 1.2 Frontend API Client - Legacy Response Format Support

**File:** `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/front/src/services/api/apiClient.ts`

**Found:**
- Lines 122-125: "Handle direct data responses (legacy support)"
- Lines 100-107: Warning about "Success response without data field"

**Why It Exists:** Supported old API responses that didn't use standard envelope

**Removal Plan:**
1. Remove legacy direct data response handling (lines 122-125)
2. Make `data` field REQUIRED in success responses
3. All 200 OK responses MUST have standardized `ApiResponse<T>` format

**Breaking Change:** All API endpoints must return standardized envelope (already done in backend)

---

## 2. LEGACY DATA MODELS AND TYPE DEFINITIONS

### 2.1 Frontend Types - Legacy AudioFile Interface

**File:** `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/front/src/components/files/types.ts`

**Found:**
- Lines 11-19: `FILE_STATUS` enum-like object "for backward compatibility"
- Lines 67-69: DEPRECATED fields in Track interface:
  - `number?: number;  // DEPRECATED: use track_number instead`
  - `duration?: number; // DEPRECATED: use duration_ms instead`
- Lines 99-105: `LegacyAudioFile` interface marked "for backward compatibility"

**Why It Exists:** Transition period from old field names to new unified names

**Removal Plan:**
1. Remove `FILE_STATUS` constant object (use TypeScript enum or string literals)
2. Remove deprecated `number` and `duration` fields from Track interface
3. Delete entire `LegacyAudioFile` interface
4. Update all components using these legacy fields

**Breaking Change:** Components must use `track_number` and `duration_ms` exclusively

---

### 2.2 Frontend Types - Legacy Contracts File

**File:** `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/front/src/types/contracts.ts`

**Found:**
- Lines 160-165: `StateEvent` type with legacy union for backward compatibility
- Entire file is marked for removal in `README_CONTRACTS.md` line 14

**Why It Exists:** Transition to generated contracts from submodule

**Removal Plan:**
1. **DELETE entire file** `/front/src/types/contracts.ts`
2. Update all imports to use generated contracts from submodule
3. Remove file from git tracking

**Breaking Change:** All imports must use `@/types` (re-exports from generated contracts)

**Documentation Reference:** `/front/README_CONTRACTS.md` confirms this is legacy

---

### 2.3 OpenAPI Schema - Deprecated Duration Field

**File:** `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/contracts/schemas/openapi.yaml`

**Found:**
- Lines 109-115: `duration` field marked DEPRECATED with "Will be removed in v4.0.0"

**Why It Exists:** Backward compatibility during migration to millisecond precision

**Removal Plan:**
1. Remove `duration` field entirely from Track schema
2. Keep only `duration_ms` field
3. Bump contract version to v4.0.0 (MAJOR)
4. Regenerate all clients

**Breaking Change:** MAJOR version bump - all clients must use `duration_ms`

---

## 3. LEGACY SOCKET.IO PATTERNS

### 3.1 Frontend SocketService - Backward Compatibility Export

**File:** `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/front/src/services/socketService.ts`

**Found:**
- Lines 1-10: Entire file is a "backward compatibility export"
- Line 22-23: "Default export for backward compatibility"

**Why It Exists:** Maintained during refactoring to SocketServiceFactory

**Removal Plan:**
1. **DELETE entire file** - force use of `SocketServiceFactory`
2. Update all imports to use `SocketServiceFactory.create()` or dependency injection
3. Remove singleton pattern reliance

**Breaking Change:** Components must use modern factory pattern, not singleton

---

### 3.2 Frontend SocketServiceFactory - Deprecated Singleton

**File:** `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/front/src/services/SocketServiceFactory.ts`

**Found:**
- Lines 82-87: "Default singleton instance for backward compatibility"
- Line 86: `@deprecated` tag on singleton export

**Why It Exists:** Transition to dependency injection pattern

**Removal Plan:**
1. Remove `socketService` singleton export
2. Force use of `SocketServiceFactory.create()` explicitly
3. Update all components to use dependency injection

**Breaking Change:** No more implicit singleton - explicit factory usage required

---

## 4. LEGACY COMPONENT PATTERNS

### 4.1 FilesList Component - Backward Compatibility Props

**File:** `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/front/src/components/files/FilesList.vue`

**Found:**
- Lines 354-358: "Use props playlists if provided (for backward compatibility)"
- Line 824: "Legacy support for direct duration values"

**Why It Exists:** Supported old component API during store migration

**Removal Plan:**
1. Remove `playlists` prop - force use of unified store only
2. Remove legacy duration handling (line 824)
3. Simplify component to single data source

**Breaking Change:** Parent components cannot pass playlists prop - must use store

---

## 5. LEGACY DEPLOYMENT SCRIPTS

### 5.1 Legacy Deployment Script

**File:** `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/sync_tmbdev.sh`

**Found:**
- Entire script marked as "Legacy (still works)" in `DEPLOY_GUIDE.md` line 184

**Why It Exists:** Old deployment method before unified `deploy.sh`

**Removal Plan:**
1. **DELETE entire file** `sync_tmbdev.sh`
2. Delete config file `sync_tmbdev.config`
3. Remove all documentation references

**Breaking Change:** Users must use modern `./deploy.sh` instead

**Documentation:** `/DEPLOY_GUIDE.md` lines 199-270 describe migration

---

## 6. LEGACY DOCUMENTATION PATTERNS

### 6.1 Documentation with Backward Compatibility References

**Files Found:**
- `/COMPREHENSIVE_AUDIT_FIXES_SUMMARY.md`
- `/PHASE5_CODE_QUALITY_SUMMARY.md`
- `/front/SOCKETSERVICE_REFACTORING_SUMMARY.md`
- `/DEPLOY_GUIDE.md`
- `/front/README_CONTRACTS.md`

**Found:**
- Multiple references to "backward compatible", "backward compatibility"
- "Migration guides" from old versions
- "Breaking Changes" sections for historical changes

**Why It Exists:** Documentation of past migration process

**Removal Plan:**
1. Remove all "backward compatibility" claims
2. Remove migration guides (no longer relevant)
3. Remove "Breaking Changes" sections (history is irrelevant now)
4. Keep only current state documentation
5. Update to reflect "modern implementation only"

**Breaking Change:** Documentation no longer discusses old versions

---

### 6.2 Frontend Contracts README - Legacy References

**File:** `/front/README_CONTRACTS.md`

**Found:**
- Line 14: References `contracts.ts` as "Legacy (will be removed after migration)"
- Lines 78-92: Entire "Migration Path" section
- Line 92: "Use `server_seq` for gradual migration if needed"

**Why It Exists:** Documented transition to contract submodule

**Removal Plan:**
1. Remove "Migration Path" section entirely
2. Remove all references to `contracts.ts`
3. Update to reflect current state only (contracts submodule)
4. Remove gradual migration suggestions

**Breaking Change:** No migration path - modern approach only

---

## 7. LEGACY TESTS

### 7.1 Frontend Test - Backward Compatibility Test

**File:** `/front/src/services/__tests__/apiResponseHandler.test.ts`

**Found:**
- Line 228: Test named "should maintain backward compatibility with JSON-returning DELETE endpoints"

**Why It Exists:** Tested old DELETE response format

**Removal Plan:**
1. Remove backward compatibility test
2. Keep only tests for modern DELETE responses (204 No Content)
3. Update test suite to reflect contract v3.3.1+ only

**Breaking Change:** Tests no longer verify old behaviors

---

### 7.2 Frontend Vitest Config - Legacy Field Comment

**File:** `/front/vitest.config.mts`

**Found:**
- Line 16: `// Re-enabling src/tests/unit to fix legacy field names`

**Why It Exists:** Comment about old migration issue

**Removal Plan:**
1. Remove comment (no longer relevant)
2. Code is already modern

**Breaking Change:** None (just comment cleanup)

---

## 8. LEGACY ARCHITECTURE ARTIFACTS

### 8.1 Backend README - Contract v2.0 Reference

**File:** `/back/README.md`

**Found:**
- Line 36: "API Contract v2.0: Unified HTTP+WebSocket interface"

**Why It Exists:** Historical reference to old contract version

**Removal Plan:**
1. Update to reference current contract version (v3.3.1+)
2. Remove "v2.0" references throughout backend docs

**Breaking Change:** Documentation reflects current contract only

---

### 8.2 Backend Socket Events - Contract v2.0 Comment

**File:** `/back/app/src/common/socket_events.py`

**Found:**
- Line 75: `"""Types of state events that can be broadcast per API Contract v2.0."""`

**Why It Exists:** Historical contract reference in docstring

**Removal Plan:**
1. Update docstring to reference v3.3.1+
2. Remove v2.0 mention

**Breaking Change:** None (documentation only)

---

## 9. LEGACY I18N PATTERNS

### 9.1 I18n Configuration - Legacy Mode

**File:** `/front/src/i18n/index.ts`

**Found:**
- Line 15: `legacy: false,`

**Why It Exists:** Vue I18n configuration explicitly disabling legacy mode

**Removal Plan:**
- **KEEP AS-IS** - This is correct (disables legacy mode)
- This is NOT legacy code - it's modern configuration

**Breaking Change:** None

---

### 9.2 I18n Locale - Fallback Message

**Files:**
- `/front/src/i18n/locales/en-US.ts` line 83
- `/front/src/i18n/locales/fr-FR.ts` line 84

**Found:**
- `fallbackToMock: 'Unable to connect to the server. Using mock data instead.'`

**Why It Exists:** Legitimate fallback message for mock mode

**Removal Plan:**
- **KEEP AS-IS** - This is modern functionality for development
- Mock mode is valid for USE_MOCK_HARDWARE development

**Breaking Change:** None

---

## COMPREHENSIVE REMOVAL PLAN

### Phase 1: Frontend Data Layer (Breaking)
**Priority:** HIGH
**Impact:** BREAKING - All components affected

**Files to DELETE:**
1. `/front/src/types/contracts.ts` (entire file)
2. `/front/src/services/socketService.ts` (entire file)

**Files to MODIFY:**
3. `/front/src/components/files/types.ts`
   - Remove lines 67-69 (deprecated Track fields)
   - Remove lines 99-105 (LegacyAudioFile interface)
   - Simplify FILE_STATUS to enum or literals

4. `/front/src/services/apiService.ts`
   - Remove fallback logic in getPlaylists() (lines 63-96)
   - Remove NFC wrapper methods (lines 212-237)
   - Remove upload wrapper methods (lines 243-258)
   - Remove default export
   - Keep only direct delegation to modules

5. `/front/src/services/api/apiClient.ts`
   - Remove legacy response format handler (lines 122-125)
   - Remove optional data field handling

6. `/front/src/services/SocketServiceFactory.ts`
   - Remove singleton export
   - Force factory pattern usage

7. `/front/src/components/files/FilesList.vue`
   - Remove playlists prop
   - Remove legacy duration handling (line 824)
   - Use unified store exclusively

**Component Updates Required:**
- All components importing from `/types/contracts.ts` → use `@/types`
- All components using `socketService` singleton → use `SocketServiceFactory.create()`
- All components using `apiService.getPlaylists()` → use `playlistApi.getPlaylists()`
- All components using Track.number → use Track.track_number
- All components using Track.duration → use Track.duration_ms

---

### Phase 2: Contract Schema (Breaking)
**Priority:** HIGH
**Impact:** BREAKING - MAJOR version bump

**Files to MODIFY:**
1. `/contracts/schemas/openapi.yaml`
   - Remove `duration` field (lines 109-115)
   - Keep only `duration_ms`
   - Bump version to v4.0.0

**Actions:**
1. Update schema
2. Run `npm run generate` in contracts repo
3. Create versioned release v4.0.0
4. Tag with semantic version
5. Update submodules in consuming repos
6. Regenerate all clients (Python, TypeScript, C++)

**Backend Updates Required:**
- Remove any code still producing `duration` field
- All responses use `duration_ms` exclusively

**Frontend Updates Required:**
- All components use `duration_ms` exclusively
- Remove any fallback to `duration`

---

### Phase 3: Deployment Scripts (Breaking)
**Priority:** MEDIUM
**Impact:** BREAKING - Changes deployment workflow

**Files to DELETE:**
1. `/sync_tmbdev.sh` (entire script)
2. `/sync_tmbdev.config` (if exists)

**Documentation Updates:**
1. `/DEPLOY_GUIDE.md`
   - Remove lines 184, 199-212 (legacy script references)
   - Remove "Migration from sync_tmbdev.sh" section
   - Update to show `./deploy.sh` as ONLY method

---

### Phase 4: Documentation Cleanup (Non-Breaking)
**Priority:** LOW
**Impact:** Documentation only

**Files to MODIFY:**
1. `/COMPREHENSIVE_AUDIT_FIXES_SUMMARY.md`
   - Remove "Backward Compatibility Analysis" section (lines 706-789)
   - Remove all "backward compatible" claims
   - Update to "Modern Implementation" approach

2. `/PHASE5_CODE_QUALITY_SUMMARY.md`
   - Remove "Backward Compatibility" section (line 279)

3. `/front/SOCKETSERVICE_REFACTORING_SUMMARY.md`
   - Remove "Backward Compatibility" sections
   - Remove "Backward compatibility" bullet points

4. `/front/README_CONTRACTS.md`
   - Remove "Migration Path" section (lines 78-92)
   - Remove reference to contracts.ts as legacy (line 14)
   - Update to reflect current state only

5. `/back/README.md`
   - Update contract version from v2.0 to v3.3.1+ (line 36)

6. `/back/app/src/common/socket_events.py`
   - Update docstring from v2.0 to v3.3.1+ (line 75)

---

### Phase 5: Test Cleanup (Non-Breaking)
**Priority:** LOW
**Impact:** Test suite only

**Files to MODIFY:**
1. `/front/src/services/__tests__/apiResponseHandler.test.ts`
   - Remove backward compatibility test (line 228+)
   - Add tests for modern DELETE behavior (204 No Content)

2. `/front/vitest.config.mts`
   - Remove legacy comment (line 16)

---

## BREAKING CHANGES SUMMARY

### API Contract Changes (v4.0.0)
**MAJOR Version Bump Required**

1. **Track.duration removed** → Use `Track.duration_ms` (milliseconds)
2. **Track.number removed** → Use `Track.track_number`
3. **All API responses MUST use standardized envelope** → No more direct data responses

### Frontend Breaking Changes

1. **No more `/types/contracts.ts`** → Import from `@/types` (generated contracts)
2. **No more `socketService` singleton** → Use `SocketServiceFactory.create()`
3. **No more `apiService` backward compat methods** → Use module APIs directly
   - `apiService.getPlaylists()` → `playlistApi.getPlaylists()`
   - `apiService.startNfcAssociation()` → `nfcApi.startNfcAssociationScan()`
4. **No more `playlists` prop in FilesList** → Use unified store
5. **No more default exports** → Use named imports

### Deployment Breaking Changes

1. **No more `sync_tmbdev.sh`** → Use `./deploy.sh` exclusively

### Test Breaking Changes

1. **No backward compatibility tests** → Test modern behavior only

---

## MIGRATION GUIDE FOR DEPLOYMENTS

### For Existing Installations

**There is NO migration path. This is a clean slate deployment.**

**Requirements:**
1. Backend must be v3.3.1+ (already enforced)
2. Frontend must be rebuilt from scratch
3. No state migration needed (server-authoritative)

**Deployment Steps:**
1. Stop old service: `systemctl stop tomb.service`
2. Deploy new code: `./deploy.sh --prod tomb`
3. Start new service: `systemctl start tomb.service`
4. Frontend will connect and sync automatically

**Data Preservation:**
- Playlists: Preserved (in database)
- Tracks: Preserved (in filesystem)
- NFC associations: Preserved (in database)
- Player state: Re-synced automatically on connect

**No Manual Intervention Required**

---

## TESTING STRATEGY

### Unit Tests
**Target:** 80%+ coverage (backend), 70%+ (frontend)

**Actions:**
1. Remove backward compatibility tests
2. Add tests for modern patterns only
3. Test edge cases for new strict validation

### Integration Tests
**Target:** All critical paths

**Actions:**
1. Test HTTP → WebSocket flow with modern contracts only
2. Test player state synchronization
3. Test NFC association flow
4. Test upload flow

### E2E Tests
**Target:** User workflows

**Actions:**
1. Playlist creation and playback
2. NFC tag association
3. File upload
4. Volume control

**All tests must pass before deployment**

---

## IMPLEMENTATION ORDER

### Step 1: Prepare Contracts (1 day)
1. Update OpenAPI schema (remove deprecated fields)
2. Bump to v4.0.0
3. Generate all clients
4. Create release and tag
5. Update submodules

### Step 2: Backend Cleanup (1 day)
1. Remove any code producing deprecated fields
2. Update docstrings
3. Run full test suite (1652 tests must pass)

### Step 3: Frontend Data Layer (2 days)
1. Delete legacy files (`contracts.ts`, `socketService.ts`)
2. Remove deprecated fields from types
3. Update all imports
4. Remove backward compat logic from apiService
5. Remove backward compat from components
6. Run full test suite

### Step 4: Deployment Scripts (0.5 days)
1. Delete `sync_tmbdev.sh`
2. Update documentation

### Step 5: Documentation (1 day)
1. Remove all backward compat sections
2. Update contract version references
3. Update deployment guide
4. Create "Modern Implementation" sections

### Step 6: Testing (2 days)
1. Run all unit tests
2. Run all integration tests
3. Manual E2E testing
4. Performance testing

### Step 7: Deployment (0.5 days)
1. Deploy to development environment
2. Verify full functionality
3. Deploy to production

**Total Estimated Time: 8 days**

---

## SUCCESS CRITERIA

### Code Quality
- [ ] Zero references to "backward compatibility"
- [ ] Zero references to "legacy"
- [ ] Zero deprecated fields in contracts
- [ ] Zero fallback logic in API handlers
- [ ] 100% modern TypeScript imports

### Testing
- [ ] 1652+ backend tests passing
- [ ] Frontend test suite 100% passing
- [ ] Integration tests 100% passing
- [ ] Zero backward compatibility tests remaining

### Documentation
- [ ] All docs reference current contract only (v4.0.0+)
- [ ] No migration guides for old versions
- [ ] No "breaking changes" sections for historical changes
- [ ] Clean deployment guide with single method

### Deployment
- [ ] Single deployment script (`deploy.sh`)
- [ ] No legacy scripts remaining
- [ ] Successful deployment to dev environment
- [ ] Successful deployment to production

---

## ROLLBACK PLAN

### If Issues Arise

**DO NOT ROLLBACK - FIX FORWARD**

This is a clean slate approach. Any issues found should be fixed in the modern codebase, not by reverting to legacy patterns.

**Acceptable Actions:**
1. Fix bugs in modern implementation
2. Add missing features in modern way
3. Improve error handling
4. Add more tests

**Unacceptable Actions:**
1. Restore backward compatibility
2. Re-add legacy files
3. Re-add fallback logic
4. Support old contract versions

---

## RISK ASSESSMENT

### High Risk Areas
1. **Contract v4.0.0 Breaking Changes**
   - Risk: Client apps may break
   - Mitigation: This is RPI firmware only - we control all clients

2. **Component Import Changes**
   - Risk: Many components to update
   - Mitigation: TypeScript will catch all errors at compile time

3. **SocketService Refactor**
   - Risk: WebSocket connection issues
   - Mitigation: Already refactored, just removing compatibility layer

### Medium Risk Areas
1. **apiService Simplification**
   - Risk: Components may rely on fallback logic
   - Mitigation: Modern API has been stable for months

2. **FilesList Component Changes**
   - Risk: Parent components may pass props
   - Mitigation: TypeScript will error if props still passed

### Low Risk Areas
1. **Documentation Updates**
   - Risk: Minimal
   - Mitigation: Pure documentation changes

2. **Test Cleanup**
   - Risk: Minimal
   - Mitigation: Only removing outdated tests

---

## COMMUNICATION PLAN

### Internal Team
**Before Implementation:**
- Share this plan for review
- Get approval for breaking changes
- Schedule deployment window

**During Implementation:**
- Daily updates on progress
- Immediate notification of blockers

**After Implementation:**
- Deployment summary
- Performance metrics
- Lessons learned

### Users/Stakeholders
**Before Deployment:**
- Notify of upcoming modernization
- Explain benefits (cleaner, faster, more maintainable)
- Set expectations (no migration needed)

**After Deployment:**
- Announce completion
- Share improvements
- Provide support for any issues

---

## APPENDIX A: File Inventory

### Files to DELETE (6 files)
1. `/front/src/types/contracts.ts`
2. `/front/src/services/socketService.ts`
3. `/sync_tmbdev.sh`
4. `/sync_tmbdev.config` (if exists)

### Files to MODIFY (20+ files)

**High Priority:**
1. `/contracts/schemas/openapi.yaml`
2. `/front/src/components/files/types.ts`
3. `/front/src/services/apiService.ts`
4. `/front/src/services/api/apiClient.ts`
5. `/front/src/services/SocketServiceFactory.ts`
6. `/front/src/components/files/FilesList.vue`

**Medium Priority:**
7. `/DEPLOY_GUIDE.md`
8. `/front/README_CONTRACTS.md`
9. `/back/README.md`
10. `/back/app/src/common/socket_events.py`

**Low Priority (Documentation):**
11. `/COMPREHENSIVE_AUDIT_FIXES_SUMMARY.md`
12. `/PHASE5_CODE_QUALITY_SUMMARY.md`
13. `/front/SOCKETSERVICE_REFACTORING_SUMMARY.md`
14. `/front/src/services/__tests__/apiResponseHandler.test.ts`
15. `/front/vitest.config.mts`

**Plus:** All components importing from deleted files

---

## APPENDIX B: Search Patterns Used

### Grep Patterns That Found Legacy Code
```bash
# Backward compatibility references
"backward|backwards|legacy|deprecated|old_format|fallback|migration"

# Version indicators
"v1\.|v2\.|contract.*v2|contract.*2\.0"

# TODO/FIXME comments
"TODO.*remove|FIXME.*remove|XXX.*remove|HACK.*compat"

# Conditional logic
"if.*version|if.*old|if.*new.*else.*old"

# Adapter/compatibility classes
"class.*Adapter|class.*Compat|class.*Legacy"

# Type checks for format detection
"isinstance.*dict.*Audio|hasattr.*old|getattr.*old"
```

---

## APPENDIX C: Modern Patterns to Enforce

### 1. Imports
```typescript
// ✅ Modern
import { PlayerState, Playlist } from '@/types';
import { playlistApi } from '@/services/api/playlistApi';

// ❌ Legacy (FORBIDDEN)
import { PlayerState } from '@/types/contracts';
import apiService from '@/services/apiService';
```

### 2. API Calls
```typescript
// ✅ Modern
const result = await playlistApi.getPlaylists(page, limit);

// ❌ Legacy (FORBIDDEN)
const playlists = await apiService.getPlaylists();
```

### 3. Socket Usage
```typescript
// ✅ Modern
import { SocketServiceFactory } from '@/services/SocketServiceFactory';
const socket = SocketServiceFactory.create(deps);

// ❌ Legacy (FORBIDDEN)
import socketService from '@/services/socketService';
```

### 4. Data Models
```typescript
// ✅ Modern
interface Track {
  track_number: number;  // Modern field name
  duration_ms: number;   // Millisecond precision
}

// ❌ Legacy (FORBIDDEN)
interface Track {
  number?: number;       // Old name
  duration?: number;     // Second precision
}
```

### 5. API Responses
```typescript
// ✅ Modern - ALL responses use envelope
{
  status: "success",
  message: "OK",
  data: { ...actualData },
  timestamp: 1699999999,
  server_seq: 123
}

// ❌ Legacy (FORBIDDEN) - Direct data
{
  ...directData  // No envelope
}
```

---

## CONCLUSION

This comprehensive plan identifies and categorizes ALL legacy code in the TheOpenMusicBox RPI firmware. The modernization will result in:

**Benefits:**
- 100% modern codebase
- Zero technical debt from legacy patterns
- Simplified maintenance
- Improved type safety
- Faster development velocity
- Cleaner architecture

**Trade-offs:**
- Breaking changes (acceptable - we control all clients)
- No backward compatibility (acceptable - clean slate approach)
- Requires coordination (manageable - internal project)

**Recommendation:** PROCEED with aggressive legacy code elimination. The codebase is ready for full modernization.

---

**Status:** Ready for Implementation
**Next Step:** Get approval and execute Phase 1

---

*Generated by Claude Code - 2025-11-10*
