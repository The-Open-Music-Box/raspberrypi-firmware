---
title: "Breaking Changes v4.0.0"
status: deprecated
category: architecture
last_reviewed: 2026-02-09
review_cycle: 12months
---

# BREAKING CHANGES - v4.0.0 Legacy Code Elimination

**Date:** 2025-11-10
**Mission:** Complete elimination of ALL legacy code and backward compatibility patterns
**Status:** IN PROGRESS

---

## Executive Summary

This document tracks the systematic removal of legacy code across the entire TheOpenMusicBox RPI firmware. We are implementing a **ZERO TOLERANCE** policy for backward compatibility - all legacy patterns will be eliminated in favor of clean, modern implementations based SOLELY on the OpenAPI contract v4.0.0.

---

## Phase 1: Contract Schema Updates (COMPLETED)

### OpenAPI Schema v4.0.0
- **Version bumped**: 3.3.1 → 4.0.0 (MAJOR)
- **Track schema cleaned**:
  - ✅ Removed: `duration` field (deprecated since v3.0.0)
  - ✅ Changed: `number` → `track_number` (more explicit naming)
  - ✅ Kept: `duration_ms` only (millisecond precision)

### Generated TypeScript Types (COMPLETED)
- ✅ Regenerated from OpenAPI v4.0.0
- ✅ Created release: `contracts/releases/4.0.0-82d5310/`
- ✅ Track type now has `track_number`, NOT `number`
- ✅ Track type has `duration_ms` only, NO `duration`

**Files:**
- `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/contracts/schemas/openapi.yaml`
- `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/contracts/generated/typescript/api-types.ts`
- `/Users/jonathanpiette/github/theopenmusicbox/rpi-firmware/contracts/releases/4.0.0-82d5310/`

---

## Phase 2: Frontend Type System Migration (IN PROGRESS)

### Current State Analysis
The legacy `contracts.ts` file contained EXTRA FIELDS not present in the OpenAPI schema:
- `Track.id` - Not in OpenAPI (backend doesn't send it)
- `Track.play_count` - Not in OpenAPI (backend doesn't send it)
- `Track.server_seq` - Not in OpenAPI (backend doesn't send it)
- `Playlist.type` - Not in OpenAPI (frontend-only discriminator)
- `Playlist.last_played` - Not in OpenAPI (backend doesn't send it)

**Conclusion:** The legacy contracts.ts was MANUALLY EXTENDED with fields that the actual API doesn't provide. This is exactly the kind of drift that contract-driven development prevents.

### Migration Strategy
1. ✅ Created `/front/src/types/index.ts` as central export point
2. ✅ Updated all imports from `/types/contracts` → `/types`
3. 🔄 NEXT: Delete `/front/src/types/contracts.ts` entirely
4. 🔄 NEXT: Fix TypeScript errors by aligning code with ACTUAL API contract
5. 🔄 NEXT: Remove any code that depends on non-existent fields

### Files to DELETE
- `/front/src/types/contracts.ts` (326 lines) - **PENDING DELETION**
- `/front/src/services/socketService.ts` (24 lines) - **PENDING DELETION**

### Files Already Updated
✅ All API service files now import from `@/types`:
- `/front/src/services/SocketService.class.ts`
- `/front/src/services/nativeWebSocket.ts`
- `/front/src/services/api/youtubeApi.ts`
- `/front/src/services/api/playlistApi.ts`
- `/front/src/services/api/nfcApi.ts`
- `/front/src/services/api/systemApi.ts`
- `/front/src/services/api/uploadApi.ts`
- `/front/src/services/api/apiClient.ts`
- `/front/src/services/api/playerApi.ts`

---

## Phase 3: Backward Compatibility Code Removal (PENDING)

### apiService.ts - Legacy Patterns to Remove
- Lines 63-96: `getPlaylists()` fallback logic (tries multiple response formats)
- Lines 212-237: NFC wrapper methods
- Lines 243-258: Upload wrapper methods
- Line 264: Default export "for backward compatibility"

### apiClient.ts - Legacy Response Handling
- Lines 122-125: Direct data response handler (legacy support)
- Lines 100-107: Optional data field warning

### SocketServiceFactory.ts - Singleton Pattern
- Lines 82-87: Singleton export (deprecated)
- Force explicit factory usage everywhere

### FilesList.vue - Backward Compatibility Props
- Lines 354-358: `playlists` prop (for backward compatibility)
- Line 824: Legacy duration handling

---

## Phase 4: Component Updates (PENDING)

### Components Using socketService (Must Update to SocketServiceFactory)
- `/front/src/main.ts`
- `/front/src/views/SettingsPage.vue`
- `/front/src/components/files/NfcAssociateDialog.vue`
- `/front/src/components/files/FilesList.vue`
- `/front/src/components/youtube/YoutubeIntegration.vue`
- `/front/src/components/upload/SimpleUploader.vue`
- `/front/src/stores/unifiedPlaylistStore.ts`
- `/front/src/stores/serverStateStore.ts`
- `/front/src/tests/integration/api-store/socket-store-integration.test.ts`
- `/front/src/tests/integration/api-store/player-store-integration.test.ts`

**Change Required:**
```typescript
// OLD (FORBIDDEN):
import socketService from '@/services/socketService'

// NEW (REQUIRED):
import { SocketServiceFactory } from '@/services/SocketServiceFactory'
const socket = SocketServiceFactory.create(deps)
```

---

## Phase 5: Legacy Deployment Scripts (PENDING)

### Files to DELETE
- `/sync_tmbdev.sh` (200+ lines) - **PENDING DELETION**
- `/sync_tmbdev.config` (if exists) - **PENDING DELETION**

### Documentation to UPDATE
- `/DEPLOY_GUIDE.md` - Remove lines 184, 199-212, 270

---

## Phase 6: Documentation Cleanup (PENDING)

### Files with "Backward Compatibility" References
- `/COMPREHENSIVE_AUDIT_FIXES_SUMMARY.md` (lines 706-789)
- `/PHASE5_CODE_QUALITY_SUMMARY.md` (line 279)
- `/front/SOCKETSERVICE_REFACTORING_SUMMARY.md` (multiple locations)
- `/front/README_CONTRACTS.md` (lines 14, 78-92)
- `/back/README.md` (line 36: "v2.0" → "v4.0.0")
- `/back/app/src/common/socket_events.py` (line 75: "v2.0" → "v4.0.0")

**Action:** Remove ALL mentions of:
- "backward compatible"
- "backward compatibility"
- "legacy" (except in THIS file)
- "migration path"
- Contract v2.0 / v3.x references

---

## Phase 7: Test Cleanup (PENDING)

### Tests to REMOVE
- `/front/src/services/__tests__/apiResponseHandler.test.ts` (line 228: backward compat test)
- Any tests for old data formats
- Any tests for legacy API responses

### Comment Cleanup
- `/front/vitest.config.mts` (line 16: legacy field names comment)

---

## Expected Results After Completion

### Code Quality
✅ Zero references to "backward compatibility"
✅ Zero references to "legacy"
✅ Zero deprecated fields in contracts
✅ Zero fallback logic in API handlers
✅ 100% modern TypeScript imports
✅ Single code path only (no branches for old vs new)

### Performance Improvements
- Smaller bundle size (removed ~1000+ lines of legacy code)
- Faster type checking (simpler type system)
- No runtime fallback checks (direct code paths)

### Maintenance Benefits
- Contract as single source of truth
- No confusion about which field names to use
- Clear error messages (no silent fallbacks)
- Easier onboarding for new developers

---

## Breaking Changes for Deployments

### IMPORTANT: No Migration Path
This is a **CLEAN SLATE** deployment. There is NO gradual migration or backward compatibility.

### Requirements
1. Backend MUST be at contract v4.0.0
2. Frontend MUST be rebuilt from scratch
3. ALL clients must update simultaneously
4. No state migration needed (server-authoritative)

### Deployment Steps
```bash
# 1. Stop old service
systemctl stop tomb.service

# 2. Deploy new code
./deploy.sh --prod tomb

# 3. Start new service
systemctl start tomb.service

# 4. Frontend connects and syncs automatically
```

### Data Preservation
- ✅ Playlists: Preserved (in database)
- ✅ Tracks: Preserved (in filesystem)
- ✅ NFC associations: Preserved (in database)
- ✅ Player state: Re-synced automatically on connect

---

## Testing Requirements

### Before Merging to main
- [ ] Frontend build succeeds without errors
- [ ] Backend 1652+ tests pass
- [ ] Frontend test suite 100% passing
- [ ] Integration tests pass
- [ ] Manual E2E testing completed

### Manual Testing Checklist
- [ ] Playlist creation
- [ ] Track upload
- [ ] Playback controls (play/pause/next/prev)
- [ ] Volume control
- [ ] NFC tag association
- [ ] WebSocket reconnection
- [ ] Error handling

---

## Rollback Plan

**DO NOT ROLLBACK - FIX FORWARD**

If issues arise after deployment:
1. ✅ Debug and fix in modern codebase
2. ✅ Add tests for the issue
3. ✅ Deploy fix
4. ❌ Do NOT re-add legacy patterns
5. ❌ Do NOT restore deleted files
6. ❌ Do NOT add fallback logic

---

## Progress Tracking

### Completed
- ✅ OpenAPI schema updated to v4.0.0
- ✅ TypeScript types regenerated
- ✅ Created v4.0.0 release
- ✅ Created `/front/src/types/index.ts`
- ✅ Updated all imports from `/types/contracts` → `/types`
- ✅ Verified frontend build succeeds

### In Progress
- 🔄 Deleting legacy contracts.ts and socketService.ts
- 🔄 Fixing TypeScript errors from removed fields
- 🔄 Updating components to use SocketServiceFactory

### Pending
- ⏳ Remove backward compatibility from apiService.ts
- ⏳ Remove backward compatibility from apiClient.ts
- ⏳ Update all socketService imports
- ⏳ Delete sync_tmbdev.sh
- ⏳ Clean up documentation
- ⏳ Remove legacy tests
- ⏳ Run full test suite
- ⏳ Manual E2E testing
- ⏳ Production deployment

---

## Key Decisions Made

### Decision 1: Trust OpenAPI Schema as Source of Truth
**Rationale:** The legacy contracts.ts had fields that don't exist in the OpenAPI schema. This represents drift that must be eliminated. We will align code with the ACTUAL API contract, not wishful thinking.

**Impact:** Some code may reference fields that don't exist. These references will be REMOVED, not accommodated.

### Decision 2: No Gradual Migration
**Rationale:** Gradual migrations leave technical debt and maintain complexity. A clean slate ensures no legacy patterns survive.

**Impact:** Breaking changes require coordinated deployment, but result in cleaner codebase.

### Decision 3: Zero Tolerance for Backward Compatibility
**Rationale:** Every line of backward compatibility code is technical debt that slows development and confuses developers.

**Impact:** Aggressive deletion, but clearer future development.

---

## Contact

**For Questions or Issues:**
- Review this document
- Check `/LEGACY_CODE_ELIMINATION_PLAN.md` for detailed analysis
- Check `/LEGACY_CODE_CHECKLIST.md` for step-by-step guide
- DO NOT re-add legacy patterns

---

*Generated during Legacy Code Elimination - 2025-11-10*
