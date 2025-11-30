#!/bin/bash
# ==============================================================================
# Test Environment Cleanup Script
# ==============================================================================
# Purpose: Clean up orphaned processes and prepare environment for testing
# Usage: ./scripts/cleanup_test_environment.sh [--verbose]
# ==============================================================================

set -e

VERBOSE=false
if [[ "$1" == "--verbose" ]]; then
    VERBOSE=true
fi

log() {
    if [[ "$VERBOSE" == true ]]; then
        echo "$@"
    fi
}

echo "🧹 Cleaning up test environment..."

# 1. Kill orphaned uvicorn test processes
log "🔍 Looking for orphaned uvicorn processes..."
if pgrep -f "uvicorn.*app.main:app_sio" > /dev/null 2>&1; then
    echo "  ⚠️  Found orphaned uvicorn processes, killing them..."
    pkill -f "uvicorn.*app.main:app_sio" || true
    sleep 2
    log "  ✅ Uvicorn processes cleaned up"
else
    log "  ✅ No orphaned uvicorn processes found"
fi

# 2. Check and clean up test ports
log "🔍 Checking test ports (5005, 8000)..."
TEST_PORTS=(5005 8000)
PORTS_CLEANED=false

for port in "${TEST_PORTS[@]}"; do
    if lsof -i ":$port" > /dev/null 2>&1; then
        echo "  ⚠️  Port $port is in use, attempting to free it..."
        # Try to find and kill the process using the port
        PID=$(lsof -t -i ":$port" 2>/dev/null || true)
        if [[ -n "$PID" ]]; then
            kill "$PID" 2>/dev/null || true
            sleep 1
            PORTS_CLEANED=true
            log "  ✅ Port $port freed"
        fi
    else
        log "  ✅ Port $port is available"
    fi
done

if [[ "$PORTS_CLEANED" == true ]]; then
    echo "  ⏳ Waiting for OS to release ports..."
    sleep 2
fi

# 3. Clean up test database locks (if any)
log "🔍 Checking for database locks..."
if [[ -f "app/data/app.db-wal" ]] || [[ -f "app/data/app.db-shm" ]]; then
    echo "  ⚠️  Found SQLite WAL files, cleaning up..."
    rm -f app/data/app.db-wal app/data/app.db-shm
    log "  ✅ Database locks cleaned up"
else
    log "  ✅ No database locks found"
fi

# 4. Clean up pytest cache if stale
log "🔍 Checking pytest cache..."
if [[ -d ".pytest_cache" ]]; then
    CACHE_AGE=$(find .pytest_cache -mtime +7 2>/dev/null | wc -l)
    if [[ $CACHE_AGE -gt 0 ]]; then
        echo "  ⚠️  Pytest cache is old, cleaning..."
        rm -rf .pytest_cache
        log "  ✅ Pytest cache cleaned"
    else
        log "  ✅ Pytest cache is fresh"
    fi
fi

# 5. Clean up coverage files
log "🔍 Cleaning up old coverage files..."
rm -f .coverage coverage.json 2>/dev/null || true
rm -rf coverage_html_report 2>/dev/null || true
log "  ✅ Coverage files cleaned"

# 6. Verify environment is clean
echo "🔍 Verifying environment is clean..."
ISSUES_FOUND=false

# Check ports again
for port in "${TEST_PORTS[@]}"; do
    if lsof -i ":$port" > /dev/null 2>&1; then
        echo "  ❌ ERROR: Port $port is still in use!"
        ISSUES_FOUND=true
    fi
done

# Check for orphaned processes
if pgrep -f "uvicorn.*app.main" > /dev/null 2>&1; then
    echo "  ❌ ERROR: Uvicorn processes still running!"
    ISSUES_FOUND=true
fi

if [[ "$ISSUES_FOUND" == true ]]; then
    echo ""
    echo "❌ Environment cleanup failed - manual intervention required"
    echo ""
    echo "Diagnostic information:"
    echo "----------------------"
    echo "Processes:"
    pgrep -af "uvicorn" || echo "  No uvicorn processes found"
    echo ""
    echo "Port usage:"
    for port in "${TEST_PORTS[@]}"; do
        echo "  Port $port:"
        lsof -i ":$port" || echo "    Not in use"
    done
    exit 1
fi

echo "✅ Test environment is clean and ready"
exit 0
