# TheOpenMusicBox - Unified Deployment Guide

## 🚀 Quick Start

The new `deploy.sh` script replaces the old `sync_tmbdev.sh` workflow with a unified deployment system that handles both production and development environments.

### Basic Usage

```bash
# Production deployment (to last-used server)
./deploy.sh --prod

# Production deployment (to specific server)
./deploy.sh --prod admin@192.168.1.100

# Local development deployment
./deploy.sh --dev

# Run tests only
./deploy.sh --test-only

# Monitor remote server
./deploy.sh --monitor tomb
```

## 📋 Available Modes

| Mode | Description | Tests | Build | Deploy | Monitor |
|------|-------------|-------|-------|--------|---------|
| `--prod [target]` | Production deployment | ✅ | ✅ | 🌐 Remote | ✅ |
| `--dev` | Development deployment | ✅ | ✅ | 🏠 Local | ✅ |
| `--test-only` | Run tests without deployment | ✅ | ❌ | ❌ | ❌ |
| `--build-only` | Build without deployment | ❌ | ✅ | ❌ | ❌ |
| `--monitor [target]` | Monitor server logs | ❌ | ❌ | ❌ | ✅ |

## 🔧 Options

```bash
-h, --help              # Show help message
-v, --verbose           # Enable verbose output
-q, --quiet             # Enable quiet mode
--skip-tests            # Skip test execution
--skip-build            # Skip frontend build
--no-monitor            # Don't monitor after deployment
--skip-health-check     # Skip post-deployment health check
```

## 🧪 Enhanced Testing

The test system now runs **all 78+ test files** instead of just 13:

### Test Coverage
- ✅ **Main Business Logic Tests** (`back/tests/`) - 45+ files
- ✅ **App Unit Tests** (`back/app/tests/unit/`) - 20+ files
- ✅ **App Route Tests** (`back/app/tests/routes/`) - 5+ files
- ✅ **App Integration Tests** (`back/app/tests/integration/`) - 3+ files
- ✅ **Hardware Tests** (`back/tools/test_*.py`) - 5+ files

### Test Modes
```bash
# Comprehensive test suite (all 78+ tests)
./deploy.sh --test-only

# Quick business logic validation (13 critical tests)
cd back && ./run_tests.sh --business-logic

# Verbose test output
./deploy.sh --test-only --verbose

# Quiet test output (CI/CD friendly)
./deploy.sh --test-only --quiet
```

## 🚀 Production Deployment Flow

```
1. 🧪 Run Comprehensive Tests (78+ tests)
2. 🔨 Build Frontend (Vue.js compilation)
3. 📦 Package Release (backend + frontend)
4. 📤 Upload to Server (rsync over SSH)
5. 🔄 Restart Service (systemctl restart app.service)
6. 🏥 Health Check (verify service status)
7. 📊 Monitor Logs (journalctl -fu app.service)
```

## 🏠 Development Deployment Flow

```
1. 🧪 Run Comprehensive Tests (78+ tests)
2. 🔨 Build Frontend (Vue.js compilation)
3. 📦 Package Release (backend + frontend)
4. 🚀 Start Local Server (using start_dev.py)
5. 📊 Monitor Local Logs
```

## 📡 SSH Target Management

The script automatically manages SSH targets:

```bash
# First time - specify target
./deploy.sh --prod admin@myserver.com

# Subsequent deployments - uses last target
./deploy.sh --prod

# Override saved target
./deploy.sh --prod admin@newserver.com
```

SSH configuration is stored in:
- **SSH Settings**: `sync_tmbdev.config`
- **Last Target**: `.deploy_config` (auto-created)


## 📊 Monitoring

Real-time log monitoring:

```bash
# Monitor remote server
./deploy.sh --monitor tomb

# Monitor specific server
./deploy.sh --monitor admin@192.168.1.100

# Automatic monitoring after deployment
./deploy.sh --prod  # automatically monitors after deploy
./deploy.sh --prod --no-monitor  # skip monitoring
```

## ⚡ Examples

### Complete Production Deployment
```bash
# Full production deployment with monitoring
./deploy.sh --prod tomb

# Production deployment without monitoring
./deploy.sh --prod tomb --no-monitor

# Verbose production deployment
./deploy.sh --prod tomb --verbose
```

### Development Workflow
```bash
# Start development environment
./deploy.sh --dev

# Development with verbose output
./deploy.sh --dev --verbose

# Quick test before development
./deploy.sh --test-only && ./deploy.sh --dev --skip-tests
```

### Testing & Validation
```bash
# Run all tests
./deploy.sh --test-only

# Quick business logic tests
cd back && ./run_tests.sh --business-logic --quiet

# Verbose test output for debugging
./deploy.sh --test-only --verbose
```

### Build & Package Only
```bash
# Build frontend and package release
./deploy.sh --build-only

# Build with verbose output
./deploy.sh --build-only --verbose
```

## 📁 File Structure

```
tomb-rpi/
├── deploy.sh                    # ⭐ New unified deployment script
├── sync_tmbdev.sh              # 🔶 Legacy (still works)
├── sync_tmbdev.config          # SSH configuration
├── .deploy_config              # Auto-generated last SSH target
├── back/
│   ├── start_app.py            # Production server starter
│   ├── start_dev.py            # Development server starter
│   └── run_tests.sh            # Enhanced test runner (78+ tests)
└── release_dev/                # Generated deployment package
    └── tomb-rpi/
        ├── app/                # Backend + static frontend
        ├── requirements.txt    # Flattened dependencies
        ├── .env               # Configuration file
        └── start_app.py       # Server starter
```

## 🔧 Migration from sync_tmbdev.sh

The old workflow still works, but the new `deploy.sh` provides:

| Feature | sync_tmbdev.sh | deploy.sh |
|---------|----------------|-----------|
| Test Coverage | ❌ None | ✅ 78+ tests |
| SSH Management | ⚠️ Manual | ✅ Automatic |
| Server Restart | ❌ Manual | ✅ Automatic |
| Health Checks | ❌ None | ✅ Automatic |
| Log Monitoring | ❌ Manual | ✅ Automatic |
| Dev Environment | ❌ None | ✅ Integrated |

### Simple Migration
```bash
# Old way
./sync_tmbdev.sh
ssh tomb
sudo systemctl restart app.service
sudo journalctl -fu app.service

# New way
./deploy.sh --prod tomb
```

## 🛠️ Troubleshooting

### Tests Failing
```bash
# See detailed test failures
./deploy.sh --test-only --verbose

# Run only critical business logic tests
cd back && ./run_tests.sh --business-logic

# Skip tests temporarily (not recommended)
./deploy.sh --prod --skip-tests
```

### SSH Issues
```bash
# Verify SSH configuration
cat sync_tmbdev.config

# Test SSH connection manually
ssh -i ~/.ssh/musicbox_key tomb

# Override SSH target
./deploy.sh --prod admin@new-server.com
```

### Deployment Failures
```bash
# Build only to check for issues
./deploy.sh --build-only --verbose

# Monitor server status
./deploy.sh --monitor tomb
```

### Frontend Build Issues
```bash
# Check Node.js/npm setup
cd front && npm install

# Skip frontend build temporarily
./deploy.sh --prod --skip-build
```

---

**🎉 The unified deployment system provides a complete, automated workflow for both development and production environments while maintaining backward compatibility with existing scripts.**