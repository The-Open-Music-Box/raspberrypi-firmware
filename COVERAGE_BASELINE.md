# Test Coverage Baseline Report

**Date:** 2025-10-23 (Updated)
**Version:** rpi-firmware backend
**Total Tests:** 1589 passed, 2 skipped
**Execution Time:** 44.30s

---

## 📊 Overall Coverage Summary

| Metric | Coverage | Lines | Change |
|--------|----------|-------|--------|
| **TOTAL** | **63.45%** | 8806/13879 | +0.84% / +116 lines |

### ✅ Significant Improvement
- **Previous baseline (2025-10-20):** ~35% (partial report)
- **Current baseline (2025-10-23):** **62.61%**
- **Improvement:** +27.61 percentage points

---

## 🏗️ Coverage by Layer

| Layer | Coverage | Lines | Status | Target |
|-------|----------|-------|--------|--------|
| **Domain Layer** | **81.34%** | 2825/3473 | ✅ Excellent | 85% |
| **Application Layer** | **75.47%** | 1871/2479 | 🟡 Good | 75% |
| **API Layer** | **63.61%** | 1040/1635 | 🟡 Fair | 80% |
| **Infrastructure** | **45.55%** | 917/2013 | 🔴 Needs Work | 70% |
| **Services (other)** | **34.37%** | 629/1830 | 🔴 Critical | 70% |

---

## 🎯 TODO Plan Target Files - Progress Report

### Originally Identified Low Coverage Files (from 2025-10-20)

| File | Old | Current | Change | Status |
|------|-----|---------|--------|--------|
| `playlist_broadcasting_service.py` | 33% | **95.0%** | +62% | ✅ **COMPLETED** |
| `playlist_operations_service.py` | 22% | **76.8%** | +55% | 🟡 Near target (80%) |
| `player_operations_service.py` | 41% | **69.6%** | +29% | 🟡 Good progress |
| `player_broadcasting_service.py` | 53% | **64.7%** | +12% | 🟡 Needs work |

**Analysis:** Significant improvement across all target files. `playlist_broadcasting_service.py` now exceeds target coverage!

---

## 🔴 CRITICAL: Files with 0% Coverage

### High Priority (Core Services - 0% Coverage)

| File | Statements | Missing | Priority |
|------|------------|---------|----------|
| `services/chunked_upload_service.py` | 97 | 97 | 🔴 **URGENT** |
| `services/file_path_resolver.py` | 63 | 63 | 🔴 **URGENT** |
| `services/filesystem_sync_service.py` | 164 | 164 | 🔴 **URGENT** |
| `services/upload_service.py` | 56 | 56 | 🔴 **URGENT** |
| `services/mdns_service.py` | 51 | 51 | 🟡 Medium |

**Total uncovered lines in 0% files:** 431 statements

---

## 🟡 Files with Low Coverage (<40%)

| File | Coverage | Statements | Missing | Priority |
|------|----------|------------|---------|----------|
| `audio_application_service.py` | 14.6% | 82 | 70 | 🔴 High |
| `track_progress_service.py` | 14.7% | 259 | 221 | 🔴 High |
| `web_api_routes.py` | 19.6% | 46 | 37 | 🟡 Medium |
| `unified_broadcasting_service.py` | 21.4% | 103 | 81 | 🔴 High |
| `youtube_application_service.py` | 21.7% | 60 | 47 | 🟡 Medium |
| `upload_api_routes.py` | 24.2% | 99 | 75 | 🔴 High |
| `upload_application_service.py` | 24.3% | 107 | 81 | 🔴 High |
| `state_manager_lifecycle_application_service.py` | 28.0% | 93 | 67 | 🟡 Medium |
| `unified_validation_service.py` | 28.6% | 203 | 145 | 🔴 High |
| `operation_tracker.py` | 28.8% | 73 | 52 | 🟡 Medium |
| `playlist_nfc_api.py` | 32.3% | 62 | 42 | 🟡 Medium |
| `nfc_api_routes.py` | 38.2% | 207 | 128 | 🔴 High |
| `playlist_playback_api.py` | 39.2% | 74 | 45 | 🟡 Medium |

**Total uncovered lines in <40% files:** 1284 statements

---

## 📈 Next Actions - PRIORITIZED

### 🔴 URGENT (Week 1)

1. **Add tests for 0% coverage services** (431 lines)
   - [ ] `chunked_upload_service.py` (97 lines)
   - [ ] `filesystem_sync_service.py` (164 lines)
   - [ ] `file_path_resolver.py` (63 lines)
   - [ ] `upload_service.py` (56 lines)
   - [ ] `mdns_service.py` (51 lines)

2. **Complete TODO plan files to 80%+**
   - [ ] `player_operations_service.py`: 69.6% → 80% (11 more lines)
   - [ ] `player_broadcasting_service.py`: 64.7% → 80% (24 more lines)
   - [ ] `playlist_operations_service.py`: 76.8% → 80% (4 more lines)

**Estimated impact:** +5-7% total coverage

### 🟡 HIGH PRIORITY (Week 2)

3. **Improve low coverage critical files (<25%)**
   - [ ] `audio_application_service.py`: 14.6% → 70% (46 lines)
   - [ ] `track_progress_service.py`: 14.7% → 70% (143 lines)
   - [ ] `unified_broadcasting_service.py`: 21.4% → 70% (50 lines)
   - [ ] `upload_api_routes.py`: 24.2% → 70% (45 lines)
   - [ ] `upload_application_service.py`: 24.3% → 70% (49 lines)

**Estimated impact:** +3-4% total coverage

### 🟢 MEDIUM PRIORITY (Weeks 3-4)

4. **Improve infrastructure coverage (45.55% → 70%)**
   - Identify and test infrastructure components
   - Focus on repositories and adapters

5. **Improve services coverage (34.37% → 70%)**
   - Complete testing of broadcasting services
   - Add notification service tests
   - Test validation services

**Estimated impact:** +8-10% total coverage

---

## 🎯 Coverage Goals

### Short Term (2 weeks)
- [ ] **Total Coverage:** 62.61% → **75%** (+12.39%)
- [ ] **API Layer:** 63.61% → **80%** (+16.39%)
- [ ] **Services:** 34.37% → **50%** (+15.63%)
- [ ] **Zero 0% coverage files**

### Medium Term (1 month)
- [ ] **Total Coverage:** 75% → **80%** (+5%)
- [ ] **Infrastructure:** 45.55% → **70%** (+24.45%)
- [ ] **All layers ≥ 70%**

### Long Term (2 months)
- [ ] **Total Coverage:** 80% → **85%**
- [ ] **Domain Layer:** 81.34% → **90%**
- [ ] **Application Layer:** 75.47% → **85%**
- [ ] **All layers ≥ 75%**

---

## 📝 Test Execution Commands

```bash
# Generate complete coverage report
USE_MOCK_HARDWARE=true coverage run --source=app/src -m pytest tests/ -v --tb=no -q

# Generate reports (HTML, JSON, Terminal)
coverage html --omit="*/tests/*,*/venv/*,*/__pycache__/*,*/event_monitor.py"
coverage json --omit="*/tests/*,*/venv/*,*/__pycache__/*,*/event_monitor.py"
coverage report --omit="*/tests/*,*/venv/*,*/__pycache__/*,*/event_monitor.py"

# View HTML report
open coverage_html_report/index.html
```

---

## 🔍 Analysis Tools

### Find files with specific coverage range

```bash
# Files with 0% coverage
python3 -c "
import json
data = json.load(open('coverage.json'))
for file, info in data['files'].items():
    if '/tests/' not in file and '/venv/' not in file:
        pct = info['summary']['percent_covered']
        if pct == 0 and info['summary']['num_statements'] > 20:
            print(f'{file}: {info[\"summary\"][\"num_statements\"]} statements')
"

# Files with <50% coverage
python3 -c "
import json
data = json.load(open('coverage.json'))
for file, info in data['files'].items():
    if '/tests/' not in file and '/venv/' not in file:
        pct = info['summary']['percent_covered']
        if 0 < pct < 50 and info['summary']['num_statements'] > 20:
            print(f'{file}: {pct:.1f}%')
"
```

---

## 📊 Coverage Trend

| Date | Total Coverage | Change | Tests | Notes |
|------|----------------|--------|-------|-------|
| 2025-10-01 | ~35% | - | 1288 | Partial report (4 files only) |
| 2025-10-20 | ~35% | 0% | 1288 | Full report documented |
| **2025-10-23** | **62.61%** | **+27.61%** | **1565** | ✅ **Complete baseline established** |

---

## ✅ Success Criteria

- [x] Generate complete coverage report
- [x] Identify files with 0% coverage
- [x] Establish baseline metrics
- [x] Document coverage by layer
- [ ] Achieve 75% total coverage (in progress)
- [ ] Zero files with 0% coverage
- [ ] All layers ≥ 70%

---

**Report Generated:** 2025-10-23
**Next Review:** 2025-10-27
**Coverage Tool:** coverage.py v7.6.12
**HTML Report:** `coverage_html_report/index.html`
**JSON Report:** `coverage.json`
