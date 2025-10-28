#!/bin/bash

# TheOpenMusicBox - Hardware-Ready Startup Script
# =================================================
# Ensures hardware is ready before starting the application
# Particularly important for first boot after power-on

set -e

# Configuration
readonly MAX_WAIT_TIME=30  # Maximum seconds to wait for hardware
readonly CHECK_INTERVAL=2  # Seconds between checks
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PYTHON_BIN="${SCRIPT_DIR}/venv/bin/python"
readonly START_APP="${SCRIPT_DIR}/start_app.py"

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if I2C devices are ready
check_i2c_ready() {
    if [ -e /dev/i2c-1 ]; then
        return 0
    fi
    return 1
}

# Check if GPIO is accessible
check_gpio_ready() {
    if [ -d /sys/class/gpio ]; then
        return 0
    fi
    return 1
}

# Check if audio devices are ready
check_audio_ready() {
    if aplay -l &>/dev/null || [ -e /dev/snd/pcmC0D0p ]; then
        return 0
    fi
    return 1
}

# Wait for hardware to be ready
wait_for_hardware() {
    log_info "Checking hardware readiness..."

    local elapsed=0
    local i2c_ready=false
    local gpio_ready=false
    local audio_ready=false

    while [ $elapsed -lt $MAX_WAIT_TIME ]; do
        # Check I2C
        if [ "$i2c_ready" = false ] && check_i2c_ready; then
            log_success "I2C bus ready (/dev/i2c-1)"
            i2c_ready=true
        fi

        # Check GPIO
        if [ "$gpio_ready" = false ] && check_gpio_ready; then
            log_success "GPIO ready (/sys/class/gpio)"
            gpio_ready=true
        fi

        # Check Audio
        if [ "$audio_ready" = false ] && check_audio_ready; then
            log_success "Audio devices ready"
            audio_ready=true
        fi

        # All critical hardware ready?
        if [ "$i2c_ready" = true ] && [ "$gpio_ready" = true ]; then
            log_success "All critical hardware ready!"
            if [ "$audio_ready" = false ]; then
                log_warning "Audio not detected, but continuing (may use mock backend)"
            fi
            return 0
        fi

        # Wait and increment
        sleep $CHECK_INTERVAL
        elapsed=$((elapsed + CHECK_INTERVAL))

        if [ $((elapsed % 10)) -eq 0 ]; then
            log_info "Still waiting for hardware... (${elapsed}s elapsed)"
        fi
    done

    # Timeout - log warnings but continue anyway
    log_warning "Hardware check timeout after ${MAX_WAIT_TIME}s"
    log_warning "I2C ready: $i2c_ready, GPIO ready: $gpio_ready, Audio ready: $audio_ready"
    log_warning "Continuing anyway - application will retry hardware initialization"

    return 0
}

# Check if running as correct user
check_user() {
    local current_user=$(whoami)
    if [ "$current_user" != "admin" ] && [ "$current_user" != "pi" ]; then
        log_warning "Running as user: $current_user (expected: admin or pi)"
    fi
}

# Check if running from correct directory
check_directory() {
    if [ ! -f "$START_APP" ]; then
        log_error "start_app.py not found at: $START_APP"
        log_error "Working directory: $(pwd)"
        exit 1
    fi

    if [ ! -x "$PYTHON_BIN" ]; then
        log_error "Python not found at: $PYTHON_BIN"
        log_error "Have you created the virtual environment?"
        exit 1
    fi
}

# Main execution
main() {
    log_info "TheOpenMusicBox - Hardware-Ready Startup"
    log_info "========================================"

    # Pre-flight checks
    check_user
    check_directory

    # Wait for hardware
    wait_for_hardware

    # Small additional delay for good measure
    log_info "Starting application in 2 seconds..."
    sleep 2

    # Start the application
    log_success "Launching TheOpenMusicBox application..."
    exec "$PYTHON_BIN" "$START_APP"
}

# Run main
main "$@"
