# Frontend Coverage Improvement Plan

**Date:** 2025-10-23
**Current Coverage:** 62.06% statements, 91.95% branches, 84.34% functions
**Target:** 80% statements, 90% branches, 90% functions

---

## 📊 Current State Analysis

### ✅ High Coverage Areas (Keep Maintaining)
| Area | Coverage | Status |
|------|----------|--------|
| `src/utils/` | 99.64% | ✅ Excellent |
| `src/services/api/` | 96.49% | ✅ Excellent |
| `src/constants/` | 98.76% | ✅ Excellent |
| `src/components/files/` | 95.99% | ✅ Excellent |
| `src/components/upload/` | 100% | ✅ Perfect |
| `src/components/youtube/` | 100% | ✅ Perfect |
| `src/stores/unifiedPlaylistStore.ts` | 98.91% | ✅ Excellent |
| `src/stores/uploadStore.ts` | 100% | ✅ Perfect |

### 🔴 Critical Gaps (0% Coverage - HIGH PRIORITY)

| File | Lines | Priority | Estimated Impact |
|------|-------|----------|------------------|
| `socketService.ts` | 992 | 🔴 **URGENT** | +7.1% total coverage |
| `nativeWebSocket.ts` | 512 | 🔴 **URGENT** | +3.7% total coverage |
| `serverStateStore.ts` | 836 (19% covered) | 🔴 **URGENT** | +4.8% total coverage |
| `router/index.ts` + `lazyRoutes.ts` | 97 | 🟡 Medium | +0.7% |
| `i18n/index.ts` + locales | 196 | 🟡 Medium | +1.4% |
| `cacheService.ts` | 307 (36% covered) | 🟡 Medium | +1.4% |
| `views/*.vue` (3 pages) | 175 | 🟠 Low | +1.3% |
| `components/*.vue` (3 components) | 204 | 🟠 Low | +1.5% |

**Total potential improvement from critical gaps: +21.9% coverage**

---

## 🎯 Improvement Strategy (Phased Approach)

### Phase 1: Critical Services (Week 1) - Target: +15% coverage

#### 1. `socketService.ts` (992 lines, 0% → 80% target)
**Impact:** +7.1% total coverage

```bash
# Create test file
touch src/tests/unit/services/socketService.comprehensive.test.ts
```

**Test areas:**
- Connection lifecycle (connect, disconnect, reconnect)
- Event emission and subscription
- Room management
- Error handling and retries
- State synchronization
- Ping/pong heartbeat

**Estimated:** 60-80 tests needed

#### 2. `nativeWebSocket.ts` (512 lines, 0% → 80% target)
**Impact:** +3.7% total coverage

```bash
# Create test file
touch src/tests/unit/services/nativeWebSocket.test.ts
```

**Test areas:**
- WebSocket connection management
- Message handling
- Binary/text frame processing
- Error scenarios
- Reconnection logic

**Estimated:** 40-50 tests needed

#### 3. `serverStateStore.ts` (836 lines, 19% → 80% target)
**Impact:** +4.8% total coverage

```bash
# Expand existing test
# Edit: src/tests/unit/stores/serverStateStore.test.ts
```

**Test areas:**
- Server state synchronization
- Operation tracking
- Conflict resolution
- State updates from WebSocket events
- Optimistic updates and rollbacks

**Estimated:** 50-70 tests needed

**Phase 1 Total Impact: +15.6% → 77.6% coverage**

---

### Phase 2: Medium Priority (Week 2) - Target: +4% coverage

#### 4. `cacheService.ts` (307 lines, 36% → 80% target)
**Impact:** +1.4% total coverage

**Test areas:**
- Cache operations (get, set, delete)
- TTL and expiration
- Cache invalidation
- Memory management

**Estimated:** 30-40 tests

#### 5. Router (`router/index.ts` + `lazyRoutes.ts`)
**Impact:** +0.7% total coverage

**Test areas:**
- Route navigation
- Guards and middleware
- Lazy loading
- Route parameters

**Estimated:** 15-20 tests

#### 6. i18n System
**Impact:** +1.4% total coverage

**Test areas:**
- Locale switching
- Translation key resolution
- Fallback behavior
- Dynamic translations

**Estimated:** 20-25 tests

**Phase 2 Total Impact: +3.5% → 81.1% coverage**

---

### Phase 3: Component Coverage (Week 3) - Target: +3% coverage

#### 7. View Components (`views/*.vue`)
**Impact:** +1.3% total coverage

Files:
- `AboutPage.vue`
- `HomePage.vue`
- `SettingsPage.vue`

**Test approach:** Component testing with Vue Test Utils

**Estimated:** 25-30 tests

#### 8. Missing Components
**Impact:** +1.5% total coverage

Files:
- `BottomNavigation.vue`
- `OptimizedImage.vue`
- `StatsInfo.vue`
- `TrackControls.vue`
- `ProgressBar.vue`
- `TrackInfo.vue`
- `FileActions.vue`
- `FileStatus.vue`

**Test approach:** Component testing with user interaction simulation

**Estimated:** 30-40 tests

**Phase 3 Total Impact: +2.8% → 83.9% coverage**

---

## 🚀 Quick Start Commands

### 1. Generate Current Coverage Report
```bash
npm test -- --coverage --run
```

### 2. Generate HTML Coverage Report
```bash
npm test -- --coverage --run
# Open: coverage/index.html
```

### 3. Watch Mode for TDD
```bash
npm test -- --coverage
```

### 4. Test Specific File
```bash
npm test -- src/tests/unit/services/socketService.test.ts --coverage
```

---

## 📝 Coverage Baseline Tracking

| Date | Total Coverage | Files Added | Tests Added | Notes |
|------|----------------|-------------|-------------|-------|
| 2025-10-23 | 62.06% | Baseline | 447 tests | Expanded from 1 to all files |
| | | | | |

---

## 🎯 Milestone Goals

### Short Term (2 weeks)
- [ ] **Coverage: 62% → 78%** (+16%)
- [ ] socketService.ts: 0% → 80%
- [ ] nativeWebSocket.ts: 0% → 80%
- [ ] serverStateStore.ts: 19% → 80%
- [ ] Zero files with 0% coverage in critical services

### Medium Term (1 month)
- [ ] **Coverage: 78% → 84%** (+6%)
- [ ] cacheService.ts: 36% → 80%
- [ ] Router coverage: 0% → 70%
- [ ] i18n coverage: 0% → 70%
- [ ] All stores ≥ 80%

### Long Term (2 months)
- [ ] **Coverage: 84% → 88%** (+4%)
- [ ] All view components ≥ 70%
- [ ] All shared components ≥ 80%
- [ ] Integration tests enabled
- [ ] E2E tests coverage tracked

---

## 🛠️ Testing Best Practices

### 1. Use Existing Test Patterns
Look at well-tested files for patterns:
- `src/tests/unit/stores/unifiedPlaylistStore.test.ts` (98.91%)
- `src/services/api/apiClient.ts` (90.6%)
- `src/utils/` (99.64% average)

### 2. Test Structure
```typescript
describe('ServiceName', () => {
  describe('methodName', () => {
    it('should handle success case', () => { ... })
    it('should handle error case', () => { ... })
    it('should handle edge case', () => { ... })
  })
})
```

### 3. Mock WebSocket for Testing
```typescript
import { vi } from 'vitest'

vi.mock('@/services/socketService', () => ({
  socketService: {
    connect: vi.fn(),
    emit: vi.fn(),
    on: vi.fn()
  }
}))
```

### 4. Component Testing Example
```typescript
import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import MyComponent from '@/components/MyComponent.vue'

describe('MyComponent', () => {
  it('renders correctly', () => {
    const wrapper = mount(MyComponent)
    expect(wrapper.text()).toContain('Expected text')
  })
})
```

---

## 📊 Success Metrics

- [x] Configuration updated to track all files
- [ ] Critical services (socketService, nativeWebSocket) ≥ 80%
- [ ] All stores ≥ 80%
- [ ] No files with 0% coverage in src/services/
- [ ] Overall coverage ≥ 85%
- [ ] Branch coverage maintained ≥ 90%
- [ ] Function coverage maintained ≥ 85%

---

## 🔍 Coverage Analysis Tools

### Find files below threshold
```bash
npm test -- --coverage --run 2>&1 | grep "^\s.*\s0\s*|"
```

### Coverage by directory
```bash
npm test -- --coverage --run 2>&1 | grep "src/services"
```

### Generate detailed HTML report
```bash
npm test -- --coverage --run --coverage.reporter=html
open coverage/index.html
```

---

**Next Review:** 2025-10-27
**Owner:** Development Team
**Priority:** HIGH - Critical services need coverage for production reliability
