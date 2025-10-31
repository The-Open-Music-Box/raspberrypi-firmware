#!/bin/bash

# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.

# TheOpenMusicBox - Public Package Export Script
# ===============================================
#
# Exports the backend package for public distribution using deployment manifests
# This script is called by build_public_release.sh

set -e

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# Directories
readonly SCRIPT_DIR="$(dirname "$(realpath "$0")")"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly BACK_DIR="$SCRIPT_DIR"
readonly PUBLIC_RELEASE_DIR="${PROJECT_ROOT}/public_release/tomb-rpi"

# Manifest files
readonly DEPLOY_EXCLUDE="${BACK_DIR}/.deploy-exclude"
readonly DEPLOY_INCLUDE="${BACK_DIR}/.deploy-include"

print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Validate manifest files exist
validate_manifests() {
    if [ ! -f "$DEPLOY_EXCLUDE" ]; then
        print_status "$RED" "❌ Missing deployment exclusion manifest: $DEPLOY_EXCLUDE"
        exit 1
    fi

    if [ ! -f "$DEPLOY_INCLUDE" ]; then
        print_status "$RED" "❌ Missing deployment inclusion manifest: $DEPLOY_INCLUDE"
        exit 1
    fi
}

# Export backend package
export_package() {
    print_status "$BLUE" "📦 Exporting backend package for public release..."

    # Create release directory
    mkdir -p "$PUBLIC_RELEASE_DIR"

    # Build rsync exclude arguments from manifest
    local exclude_args=()
    while IFS= read -r pattern; do
        # Skip empty lines and comments
        [[ -z "$pattern" || "$pattern" =~ ^[[:space:]]*# ]] && continue
        exclude_args+=("--exclude=$pattern")
    done < "$DEPLOY_EXCLUDE"

    # Copy backend files using rsync with exclusions
    print_status "$BLUE" "📂 Copying backend files..."
    rsync -a --delete \
        "${exclude_args[@]}" \
        "$BACK_DIR/" "$PUBLIC_RELEASE_DIR/" \
        --exclude='export_public_package.sh'

    # Create flattened requirements.txt for production
    print_status "$BLUE" "📋 Creating flattened requirements.txt..."
    local req_dst="$PUBLIC_RELEASE_DIR/requirements.txt"

    if [ -f "$BACK_DIR/requirements/prod.txt" ]; then
        awk -v src_dir="$BACK_DIR/requirements" '
          /^-r / {
            sub(/^-r /, "", $0);
            file = src_dir "/" $0;
            while ((getline line < file) > 0) print line;
            close(file);
            next;
          }
          { print }
        ' "$BACK_DIR/requirements/prod.txt" > "$req_dst"

        # Remove comments and blank lines
        sed -i.bak "/^\s*#/d;/^\s*$/d" "$req_dst" && rm "$req_dst.bak"
    else
        print_status "$YELLOW" "⚠️  Warning: requirements/prod.txt not found, copying requirements.txt"
        cp "$BACK_DIR/requirements.txt" "$req_dst" 2>/dev/null || true
    fi

    # Ensure critical files are executable
    chmod +x "$PUBLIC_RELEASE_DIR/start_app.py" 2>/dev/null || true
    chmod +x "$PUBLIC_RELEASE_DIR/setup.sh" 2>/dev/null || true
    chmod +x "$PUBLIC_RELEASE_DIR/tools/"*.py 2>/dev/null || true
    chmod +x "$PUBLIC_RELEASE_DIR/tools/"*.sh 2>/dev/null || true

    # Create empty data directory structure
    mkdir -p "$PUBLIC_RELEASE_DIR/app/data"
    touch "$PUBLIC_RELEASE_DIR/app/data/.gitkeep"

    # Validate critical files exist
    local critical_files=("start_app.py" "app/main.py" "requirements.txt")
    for file in "${critical_files[@]}"; do
        if [ ! -f "$PUBLIC_RELEASE_DIR/$file" ]; then
            print_status "$RED" "❌ Critical file missing in export: $file"
            exit 1
        fi
    done

    print_status "$GREEN" "✅ Backend package exported successfully!"
    print_status "$BLUE" "📍 Export location: $PUBLIC_RELEASE_DIR"
}

# Main execution
main() {
    print_status "$BLUE" "🚀 Starting public package export..."

    validate_manifests
    export_package

    print_status "$GREEN" "🎉 Export complete!"
}

main "$@"
