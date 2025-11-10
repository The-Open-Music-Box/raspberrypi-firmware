# LEGACY CODE ELIMINATION - Quick Reference Card

**Print this and keep it handy during implementation!**

---

## Files to DELETE (Just remove them!)

```bash
# Frontend
rm front/src/types/contracts.ts
rm front/src/services/socketService.ts

# Deployment
rm sync_tmbdev.sh
rm sync_tmbdev.config

# Verify deleted
git status
```

---

## Search & Replace Patterns

### TypeScript Imports

```bash
# Find all legacy imports
grep -r "from '@/types/contracts'" front/src/
grep -r "from '@/services/socketService'" front/src/
grep -r "from '@/services/apiService'" front/src/ | grep default

# Replace in files
# Old: import { Type } from '@/types/contracts'
# New: import { Type } from '@/types'

# Old: import socketService from '@/services/socketService'
# New: import { SocketServiceFactory } from '@/services/SocketServiceFactory'

# Old: import apiService from '@/services/apiService'
# New: import { playlistApi } from '@/services/api/playlistApi'
```

### Data Field Names

```bash
# Find deprecated field usage
grep -r "track\.number" front/src/
grep -r "track\.duration[^_]" front/src/

# Replace
# Old: track.number
# New: track.track_number

# Old: track.duration
# New: track.duration_ms
```

### API Calls

```bash
# Old Pattern
await apiService.getPlaylists()
await apiService.startNfcAssociation(id)

# New Pattern
await playlistApi.getPlaylists(page, limit)
await nfcApi.startNfcAssociationScan(id, timeout)
```

---

## Contract Changes (v4.0.0)

### Track Schema

```yaml
# REMOVE from openapi.yaml
duration:
  type: integer
  deprecated: true
  description: DEPRECATED

# KEEP
duration_ms:
  type: integer
  description: Duration in milliseconds
```

### OpenAPI Version

```yaml
# Change
info:
  version: "3.3.1"

# To
info:
  version: "4.0.0"
```

---

## Code Snippets to Remove

### apiService.ts - Lines 63-96

```typescript
// DELETE THIS ENTIRE BLOCK
try {
  const result = await playlistApi.getPlaylists(...)
  return result.items
} catch (error) {
  // Fallback logic - DELETE
  try {
    const response = await apiClient.get(...)
    // Multiple format checks - DELETE
  } catch (fallbackError) {
    // More fallback - DELETE
  }
}
```

### apiClient.ts - Lines 122-125

```typescript
// DELETE THIS
if (typeof apiResponse === 'object' && !('status' in apiResponse)) {
  return apiResponse as T  // Legacy support - DELETE
}
```

### types.ts - Lines 67-69

```typescript
// DELETE THESE FIELDS
export interface Track {
  number?: number;      // DEPRECATED - DELETE
  duration?: number;    // DEPRECATED - DELETE
}
```

### types.ts - Lines 99-105

```typescript
// DELETE ENTIRE INTERFACE
export interface LegacyAudioFile extends AudioFile {
  path: string;
  uploaded: string;
  metadata?: Record<string, unknown>;
}
```

---

## Test Commands (Run frequently!)

```bash
# Frontend type checking
cd front
npm run type-check

# Frontend tests
npm run test

# Frontend build
npm run build

# Backend tests
cd ../back
pytest

# Verify test count
pytest --collect-only | grep "test session starts"
# Should see 1652+ tests

# Full integration test
cd ..
./deploy.sh --test-only
```

---

## Git Commands

```bash
# Check what's changed
git status
git diff

# Stage deletions
git rm front/src/types/contracts.ts
git rm front/src/services/socketService.ts
git rm sync_tmbdev.sh

# Commit phases
git add .
git commit -m "Phase 1: Remove frontend legacy data layer

- Deleted contracts.ts (replaced by generated types)
- Deleted socketService.ts (use SocketServiceFactory)
- Removed deprecated Track fields
- Updated all imports to modern patterns
- All tests passing

BREAKING CHANGES:
- Components must import from @/types
- Components must use SocketServiceFactory
- Components must use track_number and duration_ms"

# Before moving to next phase
git push origin dev
```

---

## Common Error Fixes

### Error: "Cannot find module '@/types/contracts'"

```bash
# Fix: Update import
# Old
import { Track } from '@/types/contracts'

# New
import { Track } from '@/types'
```

### Error: "Property 'number' does not exist on type 'Track'"

```bash
# Fix: Use modern field name
# Old
const trackNum = track.number

# New
const trackNum = track.track_number
```

### Error: "Property 'duration' does not exist on type 'Track'"

```bash
# Fix: Use millisecond field
# Old
const dur = track.duration  // seconds

# New
const dur = track.duration_ms / 1000  // convert to seconds if needed
```

### Error: "Cannot find name 'socketService'"

```bash
# Fix: Use factory
# Old
import socketService from '@/services/socketService'
socketService.connect()

# New
import { SocketServiceFactory } from '@/services/SocketServiceFactory'
const socket = SocketServiceFactory.create(deps)
socket.connect()
```

### Error: "Property 'getPlaylists' does not exist"

```bash
# Fix: Use module API
# Old
await apiService.getPlaylists()

# New
import { playlistApi } from '@/services/api/playlistApi'
await playlistApi.getPlaylists(1, 50)
```

---

## Deployment Quick Commands

```bash
# Deploy to dev
./deploy.sh --dev tomb

# Check service status
ssh tomb@tmbdev.local "systemctl status tomb.service"

# View logs
ssh tomb@tmbdev.local "journalctl -u tomb.service -f"

# Deploy to production
./deploy.sh --prod tomb

# Quick health check
curl http://tmbdev.local:8000/api/system/health
```

---

## Verification Checklist (Print & Check Off)

**After Phase 1:**
- [ ] No imports from `/types/contracts`
- [ ] No imports from `/services/socketService`
- [ ] No `track.number` usage
- [ ] No `track.duration` usage
- [ ] `npm run type-check` passes
- [ ] `npm run test` passes

**After Phase 2:**
- [ ] Contract version is v4.0.0
- [ ] No `duration` field in schema
- [ ] Generated clients successful
- [ ] Backend tests pass (1652+)
- [ ] Frontend tests pass

**After Phase 3:**
- [ ] No `sync_tmbdev.sh` file
- [ ] `./deploy.sh` works
- [ ] Documentation updated

**After Phase 4:**
- [ ] No "backward compatible" in docs
- [ ] No "legacy" in docs (except plan)
- [ ] No "v2.0" references

**After Phase 5:**
- [ ] All tests passing
- [ ] Coverage targets met
- [ ] Integration tests pass

**After Phase 6:**
- [ ] Dev deployment successful
- [ ] Production deployment successful
- [ ] No errors in logs

---

## Emergency Contacts

**If something breaks:**
1. Check TypeScript errors: `npm run type-check`
2. Check test output: `npm run test`
3. Check backend logs: `journalctl -u tomb.service -f`
4. Check frontend console: Browser DevTools

**If stuck:**
1. Review `/LEGACY_CODE_ELIMINATION_PLAN.md` for details
2. Check `/LEGACY_CODE_CHECKLIST.md` for step-by-step
3. Search codebase for similar patterns

**Do NOT:**
- Re-add backward compatibility
- Restore deleted files
- Add fallback logic
- Support old contract versions

**DO:**
- Fix forward in modern code
- Add tests for issues
- Update documentation
- Ask for help if needed

---

## Success Indicators

✅ TypeScript compiles without errors
✅ All tests passing
✅ No console errors
✅ Deployment successful
✅ Services running stable
✅ No "legacy" or "deprecated" in code

---

## Key Files Reference

**Frontend:**
- `/front/src/types/contracts.ts` → DELETE
- `/front/src/services/socketService.ts` → DELETE
- `/front/src/services/apiService.ts` → MODIFY
- `/front/src/components/files/types.ts` → MODIFY

**Backend:**
- `/contracts/schemas/openapi.yaml` → MODIFY
- `/back/README.md` → UPDATE

**Deployment:**
- `/sync_tmbdev.sh` → DELETE
- `/DEPLOY_GUIDE.md` → UPDATE

**Documentation:**
- `/COMPREHENSIVE_AUDIT_FIXES_SUMMARY.md` → UPDATE
- `/front/README_CONTRACTS.md` → UPDATE

---

**Keep this card visible during implementation!**

*Generated by Claude Code - 2025-11-10*
