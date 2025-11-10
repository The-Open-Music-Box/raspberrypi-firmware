# LEGACY CODE ELIMINATION - Execution Checklist

**Use this checklist to track progress during implementation.**

---

## Phase 1: Frontend Data Layer (2 days) ⚠️ BREAKING

### Files to DELETE
- [ ] Delete `/front/src/types/contracts.ts` (326 lines)
- [ ] Delete `/front/src/services/socketService.ts` (24 lines)
- [ ] Verify files removed from git tracking

### Files to MODIFY - Types
- [ ] `/front/src/components/files/types.ts`
  - [ ] Remove lines 67-69 (deprecated Track.number and Track.duration)
  - [ ] Remove lines 99-105 (LegacyAudioFile interface)
  - [ ] Convert FILE_STATUS to enum or string literals
  - [ ] Run `npm run type-check`

### Files to MODIFY - API Service
- [ ] `/front/src/services/apiService.ts`
  - [ ] Remove fallback logic in getPlaylists() (lines 63-96)
  - [ ] Remove NFC wrapper methods (lines 212-237)
  - [ ] Remove upload wrapper methods (lines 243-258)
  - [ ] Remove default export (line 264)
  - [ ] Keep only direct delegation to modules
  - [ ] Run `npm run type-check`

### Files to MODIFY - API Client
- [ ] `/front/src/services/api/apiClient.ts`
  - [ ] Remove legacy response handler (lines 122-125)
  - [ ] Remove optional data field warning (lines 100-107)
  - [ ] Make data field REQUIRED in success responses
  - [ ] Run `npm run type-check`

### Files to MODIFY - Socket Factory
- [ ] `/front/src/services/SocketServiceFactory.ts`
  - [ ] Remove singleton export (lines 82-87)
  - [ ] Remove @deprecated tag
  - [ ] Force explicit factory usage
  - [ ] Run `npm run type-check`

### Files to MODIFY - Components
- [ ] `/front/src/components/files/FilesList.vue`
  - [ ] Remove playlists prop (lines 354-358)
  - [ ] Remove legacy duration handling (line 824)
  - [ ] Use unified store exclusively
  - [ ] Run `npm run type-check`

### Update All Component Imports
- [ ] Search for imports from `/types/contracts` → change to `@/types`
- [ ] Search for imports of `socketService` → change to `SocketServiceFactory`
- [ ] Search for `apiService.getPlaylists()` → change to `playlistApi.getPlaylists()`
- [ ] Search for `Track.number` → change to `Track.track_number`
- [ ] Search for `Track.duration` → change to `Track.duration_ms`

### Testing
- [ ] Run `npm run test` (all frontend tests)
- [ ] Run `npm run type-check`
- [ ] Fix any TypeScript errors
- [ ] Verify build: `npm run build`

---

## Phase 2: Contract Schema (1 day) ⚠️ BREAKING

### Contract Updates
- [ ] `/contracts/schemas/openapi.yaml`
  - [ ] Remove `duration` field (lines 109-115)
  - [ ] Keep only `duration_ms`
  - [ ] Update version to v4.0.0
  - [ ] Update CHANGELOG.md with breaking changes

### Generate Clients
- [ ] Run `cd contracts && npm run generate`
- [ ] Verify TypeScript generation successful
- [ ] Verify Python generation successful
- [ ] Verify C++ generation successful

### Create Release
- [ ] Create release directory: `contracts/releases/4.0.0-<commit>/`
- [ ] Copy generated clients to release
- [ ] Tag with `v4.0.0`
- [ ] Push tag to remote

### Update Submodules
- [ ] Update contracts submodule in rpi-firmware: `git submodule update --remote`
- [ ] Update contracts submodule in flutter-app (if applicable)
- [ ] Update contracts submodule in esp32-firmware (if applicable)

### Backend Verification
- [ ] Verify backend doesn't produce `duration` field
- [ ] Search backend for `duration` field generation
- [ ] Run backend tests: `cd back && pytest`
- [ ] Verify 1652+ tests pass

### Frontend Verification
- [ ] Run `npm run type-check`
- [ ] Fix any contract-related errors
- [ ] Run `npm run test`
- [ ] Verify all tests pass

---

## Phase 3: Deployment Scripts (0.5 days) ⚠️ BREAKING

### Files to DELETE
- [ ] Delete `/sync_tmbdev.sh`
- [ ] Delete `/sync_tmbdev.config` (if exists)
- [ ] Verify files removed from git tracking

### Documentation Updates
- [ ] `/DEPLOY_GUIDE.md`
  - [ ] Remove line 184 (legacy script reference)
  - [ ] Remove lines 199-212 (migration section)
  - [ ] Remove line 270 (backward compatibility note)
  - [ ] Update to show `./deploy.sh` as ONLY method

### Verification
- [ ] Test deployment to dev: `./deploy.sh --dev tomb`
- [ ] Verify deployment successful
- [ ] Verify no references to `sync_tmbdev.sh` remain

---

## Phase 4: Documentation (1 day)

### Major Documentation Files
- [ ] `/COMPREHENSIVE_AUDIT_FIXES_SUMMARY.md`
  - [ ] Remove "Backward Compatibility Analysis" (lines 706-789)
  - [ ] Remove all "backward compatible" claims
  - [ ] Update to "Modern Implementation Only"

- [ ] `/PHASE5_CODE_QUALITY_SUMMARY.md`
  - [ ] Remove "Backward Compatibility" section (line 279)

- [ ] `/front/SOCKETSERVICE_REFACTORING_SUMMARY.md`
  - [ ] Remove "Backward Compatibility" sections
  - [ ] Remove backward compat bullet points (lines 15, 30, 131, 157, 170, etc.)

- [ ] `/front/README_CONTRACTS.md`
  - [ ] Remove line 14 (contracts.ts legacy reference)
  - [ ] Remove "Migration Path" section (lines 78-92)
  - [ ] Update to reflect current state only

### Backend Documentation
- [ ] `/back/README.md`
  - [ ] Update line 36: "v2.0" → "v4.0.0"

- [ ] `/back/app/src/common/socket_events.py`
  - [ ] Update line 75 docstring: "v2.0" → "v4.0.0"

### Search and Replace
- [ ] Search entire codebase for "backward compatible"
- [ ] Search entire codebase for "legacy" (exclude this plan!)
- [ ] Search entire codebase for "deprecated"
- [ ] Search entire codebase for "v2.0" in documentation
- [ ] Search entire codebase for "migration" (exclude this plan!)

---

## Phase 5: Testing (2 days)

### Remove Legacy Tests
- [ ] `/front/src/services/__tests__/apiResponseHandler.test.ts`
  - [ ] Remove line 228+ (backward compatibility test)
  - [ ] Add modern DELETE 204 tests

- [ ] `/front/vitest.config.mts`
  - [ ] Remove line 16 comment (legacy field names)

### Backend Tests
- [ ] Run full backend test suite: `cd back && pytest`
- [ ] Verify 1652+ tests pass
- [ ] Check coverage: target 80%+
- [ ] Fix any failing tests

### Frontend Tests
- [ ] Run frontend test suite: `npm run test`
- [ ] Check coverage: target 70%+
- [ ] Fix any failing tests
- [ ] Add tests for new modern patterns

### Integration Tests
- [ ] Test HTTP → WebSocket flow
- [ ] Test player state synchronization
- [ ] Test NFC association flow
- [ ] Test file upload flow
- [ ] Test playlist operations

### Manual E2E Testing
- [ ] Playlist creation
- [ ] Track upload
- [ ] Playback controls
- [ ] Volume control
- [ ] NFC tag association
- [ ] WebSocket reconnection
- [ ] Error handling

---

## Phase 6: Deployment (0.5 days)

### Pre-Deployment Checks
- [ ] All tests passing (backend + frontend)
- [ ] TypeScript build successful
- [ ] No console errors in dev mode
- [ ] Documentation updated
- [ ] CHANGELOG.md updated

### Development Deployment
- [ ] Deploy to dev environment: `./deploy.sh --dev tomb`
- [ ] Verify service starts: `systemctl status tomb.service`
- [ ] Check logs: `journalctl -u tomb.service -f`
- [ ] Test full user workflow
- [ ] Monitor for errors (30 minutes)

### Production Deployment
- [ ] Backup current production (if needed)
- [ ] Deploy to production: `./deploy.sh --prod tomb`
- [ ] Verify service starts: `systemctl status tomb.service`
- [ ] Check logs: `journalctl -u tomb.service -f`
- [ ] Test basic functionality
- [ ] Monitor for errors (1 hour)

### Post-Deployment Verification
- [ ] All services healthy
- [ ] WebSocket connections stable
- [ ] Player controls working
- [ ] NFC scanning working
- [ ] File uploads working
- [ ] No errors in logs

---

## Final Verification

### Code Quality Checks
- [ ] Zero references to "backward compatibility"
- [ ] Zero references to "legacy" (except this plan)
- [ ] Zero deprecated fields in contracts
- [ ] Zero fallback logic in API handlers
- [ ] 100% modern TypeScript imports

### Testing Metrics
- [ ] Backend: 1652+ tests passing
- [ ] Frontend: 100% test suite passing
- [ ] Integration: All critical paths tested
- [ ] E2E: All user workflows tested

### Documentation Metrics
- [ ] All docs reference v4.0.0+
- [ ] No migration guides for old versions
- [ ] No backward compat sections
- [ ] Clean deployment guide

### Deployment Metrics
- [ ] Single deployment script only
- [ ] No legacy scripts
- [ ] Dev deployment successful
- [ ] Production deployment successful

---

## Success Criteria

✅ **All checklist items completed**
✅ **All tests passing**
✅ **Zero legacy code remaining**
✅ **Production deployment successful**
✅ **No errors in 24-hour monitoring**

---

## Rollback Plan

**DO NOT ROLLBACK - FIX FORWARD**

If issues found:
1. Debug and fix in modern codebase
2. Add tests for the issue
3. Deploy fix
4. Do NOT re-add legacy patterns

---

## Notes Section

Use this space to track issues, blockers, or decisions during implementation:

```
Date: _____
Issue: _____
Resolution: _____

Date: _____
Issue: _____
Resolution: _____
```

---

## Sign-Off

- [ ] Code reviewed by: __________
- [ ] Tests verified by: __________
- [ ] Documentation reviewed by: __________
- [ ] Deployment approved by: __________
- [ ] Production verified by: __________

**Implementation Start Date:** __________
**Implementation End Date:** __________
**Total Duration:** __________ days

---

*Generated by Claude Code - 2025-11-10*
*Use this checklist to track your modernization progress*
