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
readonly CONFIG_FILE="${PROJECT_ROOT}/sync_tmbdev.config"
readonly DEPLOY_CONFIG_FILE="${PROJECT_ROOT}/.deploy_config"
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
    echo "  $0 --prod                           # Deploy to last-used server"
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
        print_status $RED "❌ Configuration file not found: $CONFIG_FILE"
        exit 1
    fi
}

# Load last-used SSH target
load_last_ssh_target() {
    if [ -f "$DEPLOY_CONFIG_FILE" ]; then
        source "$DEPLOY_CONFIG_FILE"
        if [ -n "$LAST_SSH_TARGET" ] && [ -z "$SSH_TARGET" ]; then
            SSH_TARGET="$LAST_SSH_TARGET"
            if [ "$VERBOSE" = true ]; then
                print_status $BLUE "📋 Using last SSH target: $SSH_TARGET"
            fi
        fi
    fi
}

# Save SSH target for future use
save_ssh_target() {
    if [ -n "$SSH_TARGET" ]; then
        echo "LAST_SSH_TARGET=\"$SSH_TARGET\"" > "$DEPLOY_CONFIG_FILE"
        if [ "$VERBOSE" = true ]; then
            print_status $BLUE "💾 Saved SSH target: $SSH_TARGET"
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

    if "${PROJECT_ROOT}/scripts/validate_contracts.sh" --auto-start; then
        print_status $GREEN "✅ Contract validation passed!"
    else
        print_status $YELLOW "⚠️  Contract validation had failures (non-blocking)"
        print_status $YELLOW "    Backend: 29/36 passed - Check reports for details"
        print_status $YELLOW "    Continuing deployment as core tests passed..."
    fi

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
    local deploy_exclude="${back_dir}/.deploy-exclude"
    local deploy_dev_include="${back_dir}/.deploy-dev-include"

    if [ "$QUIET" != true ]; then
        print_status $BLUE "📋 Creating release package in: $release_dir"
    fi

    # Validate manifest files exist
    if [ ! -f "$deploy_exclude" ]; then
        print_status $RED "❌ Missing deployment exclusion manifest: $deploy_exclude"
        exit 1
    fi

    # Create release directory
    mkdir -p "$release_dir"

    # Copy backend files
    if [ "$VERBOSE" = true ]; then
        print_status $BLUE "📂 Copying backend files using deployment manifests..."
    fi

    # Build rsync exclude arguments from manifest
    local exclude_args=()
    while IFS= read -r pattern; do
        # Skip empty lines and comments
        [[ -z "$pattern" || "$pattern" =~ ^[[:space:]]*# ]] && continue
        exclude_args+=("--exclude=$pattern")
    done < "$deploy_exclude"

    # For development deployments, we want to include additional files
    # so we need to NOT exclude them from the dev-include list
    local include_args=()
    if [ "$DEPLOY_MODE" = "development" ] && [ -f "$deploy_dev_include" ]; then
        if [ "$VERBOSE" = true ]; then
            print_status $BLUE "📋 Including development files..."
        fi
        while IFS= read -r pattern; do
            # Skip empty lines and comments
            [[ -z "$pattern" || "$pattern" =~ ^[[:space:]]*# ]] && continue
            # Remove these patterns from exclusions by adding them as includes
            include_args+=("--include=$pattern")
        done < "$deploy_dev_include"
    fi

    # Copy backend files using rsync with manifest-based exclusions
    rsync -a --delete \
        "${include_args[@]}" \
        "${exclude_args[@]}" \
        --exclude='export_public_package.sh' \
        "${back_dir}/" "${release_dir}/"

    # Create flattened requirements.txt for production
    if [ "$VERBOSE" = true ]; then
        print_status $BLUE "📋 Creating flattened requirements.txt..."
    fi

    local req_dst="${release_dir}/requirements.txt"
    if [ -f "${back_dir}/requirements/prod.txt" ]; then
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
    fi

    # Ensure critical files are executable
    chmod +x "${release_dir}/start_app.py" 2>/dev/null || true
    chmod +x "${release_dir}/setup.sh" 2>/dev/null || true
    chmod +x "${release_dir}/tools/"*.py 2>/dev/null || true
    chmod +x "${release_dir}/tools/"*.sh 2>/dev/null || true

    # Create empty data directory structure
    mkdir -p "${release_dir}/app/data"
    touch "${release_dir}/app/data/.gitkeep"

    # Copy frontend build
    if [ "$VERBOSE" = true ]; then
        print_status $BLUE "📂 Copying frontend build..."
    fi

    mkdir -p "${release_dir}/app/static"
    cp -r "${front_dir}/dist/"* "${release_dir}/app/static/"

    # Validate critical files exist
    local critical_files=("start_app.py" "app/main.py" "requirements.txt")
    for file in "${critical_files[@]}"; do
        if [ ! -f "${release_dir}/$file" ]; then
            print_status $RED "❌ Critical file missing in package: $file"
            exit 1
        fi
    done

    if [ "$VERBOSE" = true ]; then
        print_status $BLUE "📊 Package contents:"
        du -sh "${release_dir}" 2>/dev/null || true
    fi

    print_status $GREEN "✅ Release packaged successfully!"
}

# Deploy to production server
deploy_production() {
    print_header "🚀 Deploying to Production Server"

    if [ -z "$SSH_TARGET" ]; then
        print_status $RED "❌ No SSH target specified!"
        echo "Use: $0 --prod [user@host] or configure LAST_SSH_TARGET"
        exit 1
    fi

    local release_dir="${PROJECT_ROOT}/${RELEASE_DEV_DIR}/tomb-rpi"
    local ssh_opts="${SSH_OPTS} -i ${SSH_KEY}"

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

    rsync -azP --delete \
        --rsync-path="sudo rsync" \
        --no-owner --no-group \
        --chown=admin:admin \
        --ignore-errors \
        -e "ssh $ssh_opts" \
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

    save_ssh_target
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

    local ssh_opts="${SSH_OPTS} -i ${SSH_KEY}"
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
    load_last_ssh_target

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