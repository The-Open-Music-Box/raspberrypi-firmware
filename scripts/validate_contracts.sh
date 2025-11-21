#!/bin/bash
#
# Contract Validation CI/CD Script for TheOpenMusicBox
#
# This script runs comprehensive contract validation tests to ensure API and Socket.IO
# coherence between frontend and backend implementations.
#

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/back"
FRONTEND_DIR="$PROJECT_ROOT/front"

# Default URLs - can be overridden by environment variables
API_URL="${API_URL:-http://localhost:8000}"
SOCKETIO_URL="${SOCKETIO_URL:-http://localhost:8000}"

# Output configuration
REPORT_DIR="${REPORT_DIR:-$PROJECT_ROOT/contract-validation-reports}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKEND_REPORT="$REPORT_DIR/backend_validation_$TIMESTAMP.json"
FRONTEND_REPORT="$REPORT_DIR/frontend_validation_$TIMESTAMP.json"
COMBINED_REPORT="$REPORT_DIR/combined_validation_$TIMESTAMP.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Help function
show_help() {
    cat << EOF
Contract Validation Script for TheOpenMusicBox

USAGE:
    $0 [OPTIONS]

OPTIONS:
    -h, --help          Show this help message
    -u, --api-url URL   API base URL (default: http://localhost:8000)
    -s, --socket-url URL Socket.IO URL (default: http://localhost:8000)
    -o, --output DIR    Output directory for reports (default: ./contract-validation-reports)
    -b, --backend-only  Run only backend validation
    -f, --frontend-only Run only frontend validation
    -w, --wait-server   Wait for server to be ready before validation
    --auto-start        Automatically start the server if not running
    --keep-running      Keep server running after validation completes
    --skip-setup        Skip dependency installation and setup
    --fail-fast         Exit immediately on first failure

ENVIRONMENT VARIABLES:
    API_URL             Override default API URL
    SOCKETIO_URL        Override default Socket.IO URL
    REPORT_DIR          Override default report directory
    USE_MOCK_HARDWARE   Set to 'true' for mock hardware mode

EXAMPLES:
    # Run full validation with auto-start (recommended)
    $0 --auto-start

    # Run validation against already running server
    $0

    # Run validation against remote server
    $0 --api-url https://api.musicbox.example.com --socket-url https://api.musicbox.example.com

    # Auto-start server and keep it running after validation
    $0 --auto-start --keep-running

    # Run only backend validation with custom output
    $0 --backend-only --output ./my-reports --auto-start

EOF
}

# Parse command line arguments
BACKEND_ONLY=false
FRONTEND_ONLY=false
WAIT_SERVER=false
SKIP_SETUP=false
FAIL_FAST=false
AUTO_START_SERVER=false
KEEP_SERVER_RUNNING=false
SERVER_PID=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -u|--api-url)
            API_URL="$2"
            shift 2
            ;;
        -s|--socket-url)
            SOCKETIO_URL="$2"
            shift 2
            ;;
        -o|--output)
            REPORT_DIR="$2"
            shift 2
            ;;
        -b|--backend-only)
            BACKEND_ONLY=true
            shift
            ;;
        -f|--frontend-only)
            FRONTEND_ONLY=true
            shift
            ;;
        -w|--wait-server)
            WAIT_SERVER=true
            shift
            ;;
        --no-wait-server)
            WAIT_SERVER=false
            shift
            ;;
        --auto-start)
            AUTO_START_SERVER=true
            WAIT_SERVER=true  # Auto-enable wait if auto-starting
            shift
            ;;
        --keep-running)
            KEEP_SERVER_RUNNING=true
            shift
            ;;
        --skip-setup)
            SKIP_SETUP=true
            shift
            ;;
        --fail-fast)
            FAIL_FAST=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate arguments
if [[ "$BACKEND_ONLY" == true && "$FRONTEND_ONLY" == true ]]; then
    log_error "Cannot specify both --backend-only and --frontend-only"
    exit 1
fi

# Create report directory
mkdir -p "$REPORT_DIR"

log_info "Starting contract validation..."
log_info "API URL: $API_URL"
log_info "Socket.IO URL: $SOCKETIO_URL"
log_info "Report directory: $REPORT_DIR"

# Function to check if server is running
is_server_running() {
    curl -s --fail --connect-timeout 2 --max-time 5 "$API_URL/api/health" > /dev/null 2>&1
    return $?
}

# Function to start the server
start_server() {
    log_info "Starting backend server..."

    cd "$BACKEND_DIR"

    # Kill any existing server first
    pkill -f "uvicorn app.main:" 2>/dev/null || true
    sleep 2

    # Set environment variables
    export USE_MOCK_HARDWARE="${USE_MOCK_HARDWARE:-true}"

    # Start the server in background (using app_sio for Socket.IO support)
    if source venv/bin/activate && nohup python -m uvicorn app.main:app_sio --host 0.0.0.0 --port 8000 > /tmp/musicbox_server.log 2>&1 &
    then
        SERVER_PID=$!
        log_info "Server started with PID: $SERVER_PID"

        # Wait a bit for server to initialize
        sleep 5

        # Verify server is running
        if is_server_running; then
            log_success "Server started successfully and is responding"
            return 0
        else
            log_error "Server started but not responding to health checks"
            log_info "Server log (last 20 lines):"
            tail -20 /tmp/musicbox_server.log || true
            return 1
        fi
    else
        log_error "Failed to start server"
        return 1
    fi
}

# Function to stop the server
stop_server() {
    if [[ -n "$SERVER_PID" && "$KEEP_SERVER_RUNNING" != true ]]; then
        log_info "Stopping server (PID: $SERVER_PID)..."
        kill "$SERVER_PID" 2>/dev/null || true
        sleep 2

        # Force kill if still running
        if kill -0 "$SERVER_PID" 2>/dev/null; then
            log_warning "Server still running, force killing..."
            kill -9 "$SERVER_PID" 2>/dev/null || true
        fi

        log_success "Server stopped"
    elif [[ "$KEEP_SERVER_RUNNING" == true ]]; then
        log_info "Keeping server running as requested (PID: $SERVER_PID)"
    fi
}

# Function to wait for server to be ready
wait_for_server() {
    log_info "Waiting for server to be ready..."
    local max_attempts=60
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        if is_server_running; then
            log_success "Server is ready!"
            # Additional delay to ensure all services are fully initialized
            sleep 3
            return 0
        fi

        log_info "Attempt $attempt/$max_attempts: Server not ready, waiting..."
        sleep 3
        ((attempt++))
    done

    log_error "Server failed to become ready after $max_attempts attempts"
    return 1
}

# Function to check if required dependencies are installed
check_dependencies() {
    log_info "Checking dependencies..."

    # Check Python dependencies for backend validation
    if [[ "$FRONTEND_ONLY" != true ]]; then
        if ! command -v python3 &> /dev/null; then
            log_error "Python 3 is required for backend validation"
            return 1
        fi

        # Check if packages are available (try venv first, then global)
        cd "$BACKEND_DIR"
        local packages_available=false

        # Try with venv if it exists
        if [[ -f "venv/bin/activate" ]]; then
            if source venv/bin/activate && python3 -c "import pytest, jsonschema, requests, socketio" 2>/dev/null; then
                packages_available=true
            fi
        else
            # Try global installation
            if python3 -c "import pytest, jsonschema, requests, socketio" 2>/dev/null; then
                packages_available=true
            fi
        fi

        if [[ "$packages_available" != true ]]; then
            if [[ "$SKIP_SETUP" != true ]]; then
                log_info "Installing Python dependencies..."
                if [[ -f "venv/bin/activate" ]]; then
                    source venv/bin/activate && pip install pytest jsonschema requests python-socketio-client aiohttp
                else
                    pip install pytest jsonschema requests python-socketio-client aiohttp
                fi
                cd - > /dev/null
            else
                log_error "Required Python packages not found. Run without --skip-setup or install manually."
                cd - > /dev/null
                return 1
            fi
        fi
        cd - > /dev/null
    fi

    # Check Node.js dependencies for frontend validation
    if [[ "$BACKEND_ONLY" != true ]]; then
        if ! command -v node &> /dev/null; then
            log_error "Node.js is required for frontend validation"
            return 1
        fi

        if ! command -v npm &> /dev/null; then
            log_error "npm is required for frontend validation"
            return 1
        fi

        # Check if node_modules exists
        if [[ ! -d "$FRONTEND_DIR/node_modules" && "$SKIP_SETUP" != true ]]; then
            log_info "Installing frontend dependencies..."
            cd "$FRONTEND_DIR"
            npm install
            cd - > /dev/null
        fi
    fi

    log_success "Dependencies check completed"
}

# Function to run backend validation
run_backend_validation() {
    log_info "Running backend contract validation..."

    cd "$BACKEND_DIR"

    # Set environment variables for mock hardware if needed
    export USE_MOCK_HARDWARE="${USE_MOCK_HARDWARE:-true}"

    # Activate virtual environment if it exists, then run the Python contract validator
    if [[ -f "venv/bin/activate" ]]; then
        source venv/bin/activate
    fi

    if python3 tests/contracts/contract_validator.py \
        --api-url "$API_URL" \
        --socketio-url "$SOCKETIO_URL" \
        --output "$BACKEND_REPORT"; then
        log_success "Backend validation completed successfully"
        cd - > /dev/null
        return 0
    else
        log_error "Backend validation failed"
        cd - > /dev/null
        if [[ "$FAIL_FAST" == true ]]; then
            exit 1
        fi
        return 1
    fi
}

# Function to run frontend validation
run_frontend_validation() {
    log_info "Running frontend contract validation..."

    cd "$FRONTEND_DIR"

    # Run frontend contract validation using vitest
    log_info "Running frontend contract tests with vitest..."

    # Set environment variables for the test
    export VITE_API_URL="$API_URL"
    export VITE_SOCKET_URL="$SOCKETIO_URL"

    # Run the contract tests and save results
    if npm run test:contracts -- --reporter=json --outputFile="$FRONTEND_REPORT"; then
        log_success "Frontend validation completed successfully"
        cd - > /dev/null
        return 0
    else
        log_error "Frontend validation failed"
        cd - > /dev/null
        if [[ "$FAIL_FAST" == true ]]; then
            exit 1
        fi
        return 1
    fi
}

# Function to combine reports
combine_reports() {
    log_info "Combining validation reports..."

    local combined_report_content=""

    # Create combined report structure
    cat > "$COMBINED_REPORT" << EOF
{
  "validation_timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "configuration": {
    "api_url": "$API_URL",
    "socketio_url": "$SOCKETIO_URL",
    "backend_only": $BACKEND_ONLY,
    "frontend_only": $FRONTEND_ONLY
  },
  "backend_validation": null,
  "frontend_validation": null,
  "overall_summary": {
    "total_tests": 0,
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "errors": 0,
    "success_rate": 0
  }
}
EOF

    # Merge backend report if exists
    if [[ -f "$BACKEND_REPORT" && "$FRONTEND_ONLY" != true ]]; then
        log_info "Including backend validation results"
        # Use jq if available, otherwise basic approach
        if command -v jq &> /dev/null; then
            local temp_file=$(mktemp)
            jq --slurpfile backend "$BACKEND_REPORT" '.backend_validation = $backend[0]' "$COMBINED_REPORT" > "$temp_file"
            mv "$temp_file" "$COMBINED_REPORT"
        fi
    fi

    # Merge frontend report if exists
    if [[ -f "$FRONTEND_REPORT" && "$BACKEND_ONLY" != true ]]; then
        log_info "Including frontend validation results"
        if command -v jq &> /dev/null; then
            local temp_file=$(mktemp)
            jq --slurpfile frontend "$FRONTEND_REPORT" '.frontend_validation = $frontend[0]' "$COMBINED_REPORT" > "$temp_file"
            mv "$temp_file" "$COMBINED_REPORT"
        fi
    fi

    log_success "Combined report created: $COMBINED_REPORT"
}

# Function to print final summary
print_final_summary() {
    log_info "=== Contract Validation Summary ==="

    local overall_success=true

    # Analyze backend results
    if [[ -f "$BACKEND_REPORT" && "$FRONTEND_ONLY" != true ]]; then
        if command -v jq &> /dev/null; then
            local backend_failed=$(jq -r '.summary.failed // 0' "$BACKEND_REPORT")
            local backend_errors=$(jq -r '.summary.errors // 0' "$BACKEND_REPORT")
            local backend_passed=$(jq -r '.summary.passed // 0' "$BACKEND_REPORT")
            local backend_total=$(jq -r '.summary.total_tests // 0' "$BACKEND_REPORT")

            log_info "Backend validation: $backend_passed/$backend_total passed"

            if [[ $backend_failed -gt 0 || $backend_errors -gt 0 ]]; then
                overall_success=false
            fi
        fi
    fi

    # Analyze frontend results
    if [[ -f "$FRONTEND_REPORT" && "$BACKEND_ONLY" != true ]]; then
        if command -v jq &> /dev/null; then
            local frontend_failed=$(jq -r '.summary.failed // 0' "$FRONTEND_REPORT")
            local frontend_errors=$(jq -r '.summary.errors // 0' "$FRONTEND_REPORT")
            local frontend_passed=$(jq -r '.summary.passed // 0' "$FRONTEND_REPORT")
            local frontend_total=$(jq -r '.summary.totalTests // 0' "$FRONTEND_REPORT")

            log_info "Frontend validation: $frontend_passed/$frontend_total passed"

            if [[ $frontend_failed -gt 0 || $frontend_errors -gt 0 ]]; then
                overall_success=false
            fi
        fi
    fi

    # Print final result
    if [[ "$overall_success" == true ]]; then
        log_success "🎉 All contract validations passed!"
        log_success "Reports available in: $REPORT_DIR"
        return 0
    else
        log_error "❌ Contract validation failures detected"
        log_error "Check detailed reports in: $REPORT_DIR"
        return 1
    fi
}

# Main execution
main() {
    # Set up cleanup trap
    trap 'stop_server' EXIT

    # Server management logic
    if [[ "$AUTO_START_SERVER" == true ]]; then
        if is_server_running; then
            log_info "Server is already running"
        else
            if ! start_server; then
                log_error "Failed to start server automatically"
                exit 1
            fi
        fi
    else
        # Traditional behavior: wait for server if requested
        if [[ "$WAIT_SERVER" != false ]]; then
            if ! wait_for_server; then
                if [[ "$AUTO_START_SERVER" != true ]]; then
                    log_error "Server not available. Try using --auto-start to start server automatically"
                fi
                exit 1
            fi
        fi
    fi

    # Check dependencies
    if ! check_dependencies; then
        exit 1
    fi

    local validation_success=true

    # Run backend validation
    if [[ "$FRONTEND_ONLY" != true ]]; then
        if ! run_backend_validation; then
            validation_success=false
        fi
    fi

    # Run frontend validation
    if [[ "$BACKEND_ONLY" != true ]]; then
        if ! run_frontend_validation; then
            validation_success=false
        fi
    fi

    # Combine reports
    combine_reports

    # Print final summary
    if ! print_final_summary; then
        validation_success=false
    fi

    # Exit with appropriate code
    if [[ "$validation_success" == true ]]; then
        exit 0
    else
        exit 1
    fi
}

# Run main function
main "$@"