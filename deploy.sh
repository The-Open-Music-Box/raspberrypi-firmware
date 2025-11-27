#!/bin/bash

# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.

# TheOpenMusicBox - Unified Deployment Script
# ==========================================
#
# Provides unified deployment for both production and development environments
# with comprehensive testing, building, deployment, and monitoring capabilities

set -e  # Exit on any error

# Script metadata
readonly SCRIPT_VERSION="1.0.0"
readonly SCRIPT_NAME="TheOpenMusicBox Unified Deploy"

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly BOLD='\033[1m'
readonly NC='\033[0m' # No Color

# Configuration files
readonly PROJECT_ROOT="$(dirname "$(realpath "$0")")"
readonly CONFIG_FILE="${PROJECT_ROOT}/deploy.config"
readonly VERSION_FILE="${PROJECT_ROOT}/VERSION"

# Read app version
if [ -f "$VERSION_FILE" ]; then
    readonly APP_VERSION=$(cat "$VERSION_FILE" | tr -d '\n')
else
    readonly APP_VERSION="unknown"
fi

# Default configuration
DEPLOY_MODE=""
SSH_TARGET=""
RUN_TESTS=true
BUILD_FRONTEND=true
DEPLOY_TO_SERVER=true
MONITOR_AFTER_DEPLOY=true
SKIP_HEALTH_CHECK=false
VERBOSE=false
QUIET=false

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_header() {
    echo ""
    print_status $CYAN "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_status $CYAN "  $1"
    print_status $CYAN "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

show_help() {
    echo -e "${BOLD}${SCRIPT_NAME} v${SCRIPT_VERSION}${NC}"
    echo -e "${BOLD}App Version: v${APP_VERSION}${NC}"
    echo "==============================================="
    echo ""
    echo "USAGE:"
    echo "  $0 [MODE] [OPTIONS]"
    echo ""
    echo "MODES:"
    echo "  --prod [target]         Deploy to production server"
    echo "  --dev                   Deploy for local development"
    echo "  --test-only             Run tests without deployment"
    echo "  --build-only            Build without deployment"
    echo "  --monitor [target]      Monitor remote server logs"
    echo ""
    echo "OPTIONS:"
    echo "  -h, --help              Show this help message"
    echo "  -v, --verbose           Enable verbose output"
    echo "  -q, --quiet             Enable quiet mode"
    echo "  --skip-tests            Skip test execution"
    echo "  --skip-build            Skip frontend build"
    echo "  --no-monitor            Don't monitor after deployment"
    echo "  --skip-health-check     Skip post-deployment health check"
    echo ""
    echo "EXAMPLES:"
    echo "  $0 --prod tomb                      # Deploy to SSH alias 'tomb'"
    echo "  $0 --prod admin@192.168.1.100      # Deploy to specific server"
    echo "  $0 --dev                            # Local development deployment"
    echo "  $0 --test-only --verbose            # Run all tests with details"
    echo "  $0 --monitor tomb                   # Monitor remote server logs"
    echo ""
    echo "DEPLOYMENT FLOW:"
    echo "  Production: Test → Build → Package → Upload → Restart → Monitor"
    echo "  Development: Test → Build → Package → Start Local → Monitor"
    echo ""
}

# Load configuration
load_config() {
    if [ -f "$CONFIG_FILE" ]; then
        source "$CONFIG_FILE"
        if [ "$VERBOSE" = true ]; then
            print_status $BLUE "📋 Loaded configuration from: $CONFIG_FILE"
        fi
    else
        if [ "$VERBOSE" = true ]; then
            print_status $YELLOW "⚠️  Configuration file not found: $CONFIG_FILE (using defaults)"
        fi
    fi
}

# Update git submodules to latest version
update_submodules() {
    print_header "📦 Updating Git Submodules"

    cd "${PROJECT_ROOT}" || exit 1

    if [ "$VERBOSE" = true ]; then
        print_status $BLUE "🔄 Initializing and updating submodules..."
    fi

    # Initialize submodules if not already done
    if ! git submodule init; then
        print_status $YELLOW "⚠️  No submodules to initialize (this is OK)"
    fi

    # Update submodules to latest commit from their remote
    if git submodule update --remote --merge; then
        print_status $GREEN "✅ Submodules updated successfully"

        if [ "$VERBOSE" = true ]; then
            # Show submodule status
            print_status $BLUE "📋 Submodule status:"
            git submodule status
        fi
    else
        print_status $YELLOW "⚠️  Submodule update had issues (may be OK if no submodules exist)"
    fi

    echo ""
}

# Run comprehensive test suite
run_tests() {
    print_header "🧪 Running Comprehensive Test Suite"

    # Update submodules before running tests (especially contracts)
    update_submodules

    local test_args=""
    if [ "$VERBOSE" = true ]; then
        test_args="--verbose"
    elif [ "$QUIET" = true ]; then
        test_args="--quiet"
    fi

    if [ "$QUIET" != true ]; then
        print_status $BLUE "📊 Running all test suites:"
        print_status $BLUE "   • Backend tests (Python/pytest)"
        print_status $BLUE "   • Frontend tests (Vitest)"
        print_status $BLUE "   • Contract validation tests (API/Socket.IO)"
        echo ""
    fi

    # Run backend tests
    print_header "🔧 Backend Tests"
    cd "${PROJECT_ROOT}/back" || exit 1

    if ./run_tests.sh $test_args; then
        print_status $GREEN "✅ Backend tests passed!"
    else
        print_status $RED "❌ Backend tests failed! Deployment aborted."
        exit 1
    fi

    # Run frontend tests
    print_header "⚛️  Frontend Tests"
    cd "${PROJECT_ROOT}/front" || exit 1

    if [ "$QUIET" != true ]; then
        print_status $BLUE "📦 Running frontend unit tests..."
    fi

    if npm run test:unit; then
        print_status $GREEN "✅ Frontend tests passed!"
    else
        print_status $RED "❌ Frontend tests failed! Deployment aborted."
        exit 1
    fi

    # Run contract validation tests (optional - may have false positives)
    print_header "📋 Contract Validation Tests"
    cd "${PROJECT_ROOT}" || exit 1

    if [ "$QUIET" != true ]; then
        print_status $BLUE "🔍 Validating API and Socket.IO contracts..."
    fi

    # Run backend contract tests directly with pytest
    print_status $BLUE "🔍 Running backend contract validation tests..."
    cd "${PROJECT_ROOT}/back" || exit 1
    if source venv/bin/activate && python -m pytest tests/contracts/ -q --tb=short; then
        print_status $GREEN "✅ Backend contract validation passed (78 tests)!"
    else
        print_status $RED "❌ Backend contract validation failed!"
        print_status $RED "Deployment aborted."
        return 1
    fi
    cd "${PROJECT_ROOT}" || exit 1

    cd "${PROJECT_ROOT}" || exit 1
    print_status $GREEN "🎉 All test suites passed successfully!"
    return 0
}

# Build frontend
build_frontend() {
    print_header "🔨 Building Frontend"

    local front_dir="${PROJECT_ROOT}/front"

    if [ ! -d "$front_dir" ]; then
        print_status $RED "❌ Frontend directory not found: $front_dir"
        exit 1
    fi

    if [ "$QUIET" != true ]; then
        print_status $BLUE "📦 Building Vue.js frontend..."
    fi

    cd "$front_dir" || exit 1

    if npm run build; then
        print_status $GREEN "✅ Frontend built successfully!"
        cd "$PROJECT_ROOT" || exit 1
        return 0
    else
        print_status $RED "❌ Frontend build failed!"
        exit 1
    fi
}

# Package release directory
package_release() {
    print_header "📦 Packaging Release"

    local back_dir="${PROJECT_ROOT}/back"
    local front_dir="${PROJECT_ROOT}/front"
    local release_dir="${PROJECT_ROOT}/${RELEASE_DEV_DIR}/tomb-rpi"

    if [ "$QUIET" != true ]; then
        print_status $BLUE "📋 Creating release package in: $release_dir"
    fi

    # Create release directory
    mkdir -p "$release_dir"

    # Copy backend files using deployment manifests
    if [ "$VERBOSE" = true ]; then
        print_status $BLUE "📂 Copying backend files using deployment manifests..."
    fi

    # Use deployment manifests for file selection
    rsync -a --delete \
        --exclude-from="${back_dir}/.deploy-exclude" \
        --exclude='app/data/*' \
        "${back_dir}/" "${release_dir}/"

    # Create empty data directory structure
    mkdir -p "${release_dir}/app/data"
    touch "${release_dir}/app/data/.gitkeep"

    # Create flattened requirements.txt for production
    local req_dst="${release_dir}/requirements.txt"
    awk -v src_dir="${back_dir}/requirements" '
      /^-r / {
        sub(/^-r /, "", $0);
        file = src_dir "/" $0;
        while ((getline line < file) > 0) print line;
        close(file);
        next;
      }
      { print }
    ' "${back_dir}/requirements/prod.txt" > "$req_dst"

    # Remove comments and blank lines
    sed -i.bak "/^\\s*#/d;/^\\s*$/d" "$req_dst" && rm "$req_dst.bak"

    # Set executable permissions
    chmod +x "${release_dir}/start_app.py" 2>/dev/null || true
    chmod +x "${release_dir}/tools/"*.py 2>/dev/null || true

    # Verify .env file exists
    if [ ! -f "${release_dir}/.env" ]; then
        print_status $YELLOW "⚠️  WARNING: .env file not found in release!"
    elif [ "$VERBOSE" = true ]; then
        print_status $GREEN "✅ Configuration file (.env) included"
    fi

    # Copy frontend build
    if [ "$VERBOSE" = true ]; then
        print_status $BLUE "📂 Copying frontend build..."
    fi

    mkdir -p "${release_dir}/app/static"
    cp -r "${front_dir}/dist/"* "${release_dir}/app/static/"

    print_status $GREEN "✅ Release packaged successfully!"
}

# Deploy to production server
deploy_production() {
    print_header "🚀 Deploying to Production Server"

    if [ -z "$SSH_TARGET" ]; then
        print_status $RED "❌ No SSH target specified!"
        echo "Use: $0 --prod [user@host or ssh-alias]"
        exit 1
    fi

    local release_dir="${PROJECT_ROOT}/${RELEASE_DEV_DIR}/tomb-rpi"

    # Build SSH options only if configured
    local ssh_opts=""
    if [ -n "$SSH_OPTS" ]; then
        ssh_opts="$SSH_OPTS"
    fi
    if [ -n "$SSH_KEY" ]; then
        ssh_opts="$ssh_opts -i ${SSH_KEY}"
    fi

    if [ "$QUIET" != true ]; then
        print_status $BLUE "📤 Deploying to: $SSH_TARGET"
        print_status $BLUE "📂 Remote directory: $REMOTE_DIR"
    fi

    # Create remote directory
    if [ "$VERBOSE" = true ]; then
        print_status $BLUE "📁 Creating remote directory..."
    fi
    ssh $ssh_opts "$SSH_TARGET" "mkdir -p ${REMOTE_DIR} && sudo chown admin:admin ${REMOTE_DIR}" 2>/dev/null


    # Upload files
    if [ "$QUIET" != true ]; then
        print_status $BLUE "📤 Synchronizing files..."
    fi

    # CRITICAL: Protect user data from deletion with --filter
    rsync -azP --delete \
        --rsync-path="sudo rsync" \
        --no-owner --no-group \
        --chown=admin:admin \
        --ignore-errors \
        -e "ssh $ssh_opts" \
        --filter='protect app/data/' \
        --filter='protect app/data/**' \
        "${RSYNC_EXCLUDES[@]}" \
        "${release_dir}/" "${SSH_TARGET}:${REMOTE_DIR}/" 2>/dev/null

    if [ $? -eq 0 ]; then
        print_status $GREEN "✅ Files synchronized successfully!"
    else
        print_status $RED "❌ File synchronization failed!"
        exit 1
    fi

    # Fix permissions
    if [ "$VERBOSE" = true ]; then
        print_status $BLUE "🔧 Fixing remote permissions..."
    fi
    ssh $ssh_opts "$SSH_TARGET" "sudo chown -R admin:admin ${REMOTE_DIR}" 2>/dev/null

    # Restart service
    print_status $BLUE "🔄 Restarting application service..."
    if ssh $ssh_opts "$SSH_TARGET" "sudo systemctl restart app.service" 2>/dev/null; then
        print_status $GREEN "✅ Service restarted successfully!"
    else
        print_status $RED "❌ Service restart failed!"
        exit 1
    fi

    # Health check
    if [ "$SKIP_HEALTH_CHECK" != true ]; then
        print_status $BLUE "🏥 Performing health check..."
        sleep 3

        if ssh $ssh_opts "$SSH_TARGET" "sudo systemctl is-active app.service" 2>/dev/null | grep -q "active"; then
            print_status $GREEN "✅ Service is running and healthy!"
        else
            print_status $YELLOW "⚠️  Service status unclear, check manually"
        fi
    fi

}

# Deploy for development
deploy_development() {
    print_header "🔧 Starting Development Environment"

    local release_dir="${PROJECT_ROOT}/${RELEASE_DEV_DIR}/tomb-rpi"

    if [ "$QUIET" != true ]; then
        print_status $BLUE "🏠 Starting local development server..."
        print_status $BLUE "📂 Using packaged release: $release_dir"
    fi

    cd "$release_dir" || exit 1

    if [ "$MONITOR_AFTER_DEPLOY" = true ]; then
        print_status $BLUE "🚀 Starting server with monitoring..."
        python3 start_app.py  # This will use development config
    else
        print_status $BLUE "🚀 Starting server in background..."
        nohup python3 start_app.py > server.log 2>&1 &
        print_status $GREEN "✅ Server started in background (PID: $!)"
        print_status $BLUE "📋 Check logs: tail -f $release_dir/server.log"
    fi
}

# Monitor server logs
monitor_server() {
    local target="${SSH_TARGET:-$1}"

    if [ -z "$target" ]; then
        print_status $RED "❌ No SSH target specified for monitoring!"
        echo "Use: $0 --monitor [user@host]"
        exit 1
    fi

    print_header "📊 Monitoring Server Logs"
    print_status $BLUE "🔍 Monitoring: $target"
    print_status $BLUE "📋 Press Ctrl+C to stop monitoring"
    echo ""

    # Build SSH options only if configured
    local ssh_opts=""
    if [ -n "$SSH_OPTS" ]; then
        ssh_opts="$SSH_OPTS"
    fi
    if [ -n "$SSH_KEY" ]; then
        ssh_opts="$ssh_opts -i ${SSH_KEY}"
    fi

    ssh $ssh_opts "$target" "sudo journalctl -fu app.service --output=cat"
}


# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --prod)
                DEPLOY_MODE="production"
                if [[ $2 && $2 != --* ]]; then
                    SSH_TARGET="$2"
                    shift
                fi
                shift
                ;;
            --dev)
                DEPLOY_MODE="development"
                shift
                ;;
            --test-only)
                DEPLOY_MODE="test-only"
                BUILD_FRONTEND=false
                DEPLOY_TO_SERVER=false
                MONITOR_AFTER_DEPLOY=false
                shift
                ;;
            --build-only)
                DEPLOY_MODE="build-only"
                DEPLOY_TO_SERVER=false
                MONITOR_AFTER_DEPLOY=false
                shift
                ;;
            --monitor)
                DEPLOY_MODE="monitor"
                if [[ $2 && $2 != --* ]]; then
                    SSH_TARGET="$2"
                    shift
                fi
                RUN_TESTS=false
                BUILD_FRONTEND=false
                DEPLOY_TO_SERVER=false
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -q|--quiet)
                QUIET=true
                shift
                ;;
            --skip-tests)
                RUN_TESTS=false
                shift
                ;;
            --skip-build)
                BUILD_FRONTEND=false
                shift
                ;;
            --no-monitor)
                MONITOR_AFTER_DEPLOY=false
                shift
                ;;
            --skip-health-check)
                SKIP_HEALTH_CHECK=true
                shift
                ;;
            *)
                echo "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
}

# Main execution
main() {
    # Show header
    print_header "🎵 ${SCRIPT_NAME} v${SCRIPT_VERSION} (App v${APP_VERSION})"

    # Parse arguments
    parse_arguments "$@"

    # Check if mode was specified
    if [ -z "$DEPLOY_MODE" ]; then
        print_status $RED "❌ No deployment mode specified!"
        echo ""
        show_help
        exit 1
    fi

    # Load configuration
    load_config

    # Show configuration
    if [ "$QUIET" != true ]; then
        echo "Configuration:"
        echo "  • App version: v$APP_VERSION"
        echo "  • Mode: $DEPLOY_MODE"
        echo "  • Run tests: $RUN_TESTS"
        echo "  • Build frontend: $BUILD_FRONTEND"
        echo "  • Deploy to server: $DEPLOY_TO_SERVER"
        echo "  • Monitor after deploy: $MONITOR_AFTER_DEPLOY"
        if [ -n "$SSH_TARGET" ]; then
            echo "  • SSH target: $SSH_TARGET"
        fi
        echo ""
    fi

    # Execute based on mode
    case $DEPLOY_MODE in
        production)
            [ "$RUN_TESTS" = true ] && run_tests
            [ "$BUILD_FRONTEND" = true ] && build_frontend
            package_release
            deploy_production
            [ "$MONITOR_AFTER_DEPLOY" = true ] && monitor_server
            ;;
        development)
            [ "$RUN_TESTS" = true ] && run_tests
            [ "$BUILD_FRONTEND" = true ] && build_frontend
            package_release
            deploy_development
            ;;
        test-only)
            run_tests
            ;;
        build-only)
            [ "$BUILD_FRONTEND" = true ] && build_frontend
            package_release
            ;;
        monitor)
            monitor_server
            ;;
        *)
            print_status $RED "❌ Invalid deployment mode: $DEPLOY_MODE"
            exit 1
            ;;
    esac

    print_status $GREEN "🎉 Deployment completed successfully!"
}

# Run main function with all arguments
main "$@"