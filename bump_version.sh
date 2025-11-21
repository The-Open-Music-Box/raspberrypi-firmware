#!/bin/bash

# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.

# TheOpenMusicBox - Version Bump Script
# ======================================
#
# Usage:
#   ./bump_version.sh patch   # 0.4.1 → 0.4.2
#   ./bump_version.sh minor   # 0.4.1 → 0.5.0
#   ./bump_version.sh major   # 0.4.1 → 1.0.0
#   ./bump_version.sh 0.6.0   # Set specific version

set -e

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly BOLD='\033[1m'
readonly NC='\033[0m'

# Project root
readonly PROJECT_ROOT="$(dirname "$(realpath "$0")")"
readonly VERSION_FILE="${PROJECT_ROOT}/VERSION"
readonly PACKAGE_JSON="${PROJECT_ROOT}/front/package.json"
readonly CHANGELOG="${PROJECT_ROOT}/CHANGELOG.md"

print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_header() {
    echo ""
    print_status "$CYAN" "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_status "$CYAN" "  $1"
    print_status "$CYAN" "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

show_help() {
    echo -e "${BOLD}TheOpenMusicBox Version Bump${NC}"
    echo "=============================="
    echo ""
    echo "USAGE:"
    echo "  $0 [patch|minor|major|VERSION]"
    echo ""
    echo "EXAMPLES:"
    echo "  $0 patch      # 0.4.1 → 0.4.2 (bug fixes)"
    echo "  $0 minor      # 0.4.1 → 0.5.0 (new features)"
    echo "  $0 major      # 0.4.1 → 1.0.0 (breaking changes)"
    echo "  $0 0.6.0      # Set specific version"
    echo ""
    echo "WHAT IT DOES:"
    echo "  1. ✅ Checks git status (must be clean)"
    echo "  2. 📝 Updates VERSION file"
    echo "  3. 📦 Updates front/package.json"
    echo "  4. 📋 Prepares CHANGELOG.md entry"
    echo "  5. 💾 Creates git commit"
    echo "  6. 🏷️  Creates git tag"
    echo ""
}

# Read current version
get_current_version() {
    if [ ! -f "$VERSION_FILE" ]; then
        print_status "$RED" "❌ VERSION file not found!"
        exit 1
    fi
    cat "$VERSION_FILE" | tr -d '\n'
}

# Parse version into components
parse_version() {
    local version=$1
    echo "$version" | sed 's/^v//' | tr '.' ' '
}

# Calculate new version
calculate_new_version() {
    local current=$1
    local bump_type=$2

    read -r major minor patch <<< "$(parse_version "$current")"

    case $bump_type in
        major)
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        minor)
            minor=$((minor + 1))
            patch=0
            ;;
        patch)
            patch=$((patch + 1))
            ;;
        *)
            # Specific version provided
            echo "$bump_type" | sed 's/^v//'
            return
            ;;
    esac

    echo "${major}.${minor}.${patch}"
}

# Validate version format
validate_version() {
    local version=$1
    if ! [[ $version =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$ ]]; then
        print_status "$RED" "❌ Invalid version format: $version"
        print_status "$YELLOW" "Expected format: X.Y.Z or X.Y.Z-suffix"
        exit 1
    fi
}

# Check git status
check_git_status() {
    print_header "🔍 Checking Git Status"

    if [ -n "$(git status --porcelain)" ]; then
        print_status "$RED" "❌ Git working directory is not clean!"
        print_status "$YELLOW" "Please commit or stash your changes first."
        echo ""
        git status --short
        exit 1
    fi

    print_status "$GREEN" "✅ Git working directory is clean"
}

# Update VERSION file
update_version_file() {
    local new_version=$1
    echo "$new_version" > "$VERSION_FILE"
    print_status "$GREEN" "✅ Updated VERSION file"
}

# Update package.json
update_package_json() {
    local new_version=$1

    if [ ! -f "$PACKAGE_JSON" ]; then
        print_status "$YELLOW" "⚠️  package.json not found, skipping"
        return
    fi

    # Use sed to update version in package.json
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/\"version\": \"[^\"]*\"/\"version\": \"$new_version\"/" "$PACKAGE_JSON"
    else
        # Linux
        sed -i "s/\"version\": \"[^\"]*\"/\"version\": \"$new_version\"/" "$PACKAGE_JSON"
    fi

    print_status "$GREEN" "✅ Updated package.json"
}

# Prepare CHANGELOG entry
prepare_changelog() {
    local new_version=$1
    local date=$(date +%Y-%m-%d)

    if [ ! -f "$CHANGELOG" ]; then
        print_status "$YELLOW" "⚠️  CHANGELOG.md not found, creating template"
        cat > "$CHANGELOG" <<EOF
# Changelog

All notable changes to TheOpenMusicBox will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- (Add new features here)

### Changed
- (Add changes to existing functionality here)

### Fixed
- (Add bug fixes here)

## [$new_version] - $date

### Added
- Version management system with bump_version.sh script

EOF
    else
        # Add new version entry after [Unreleased]
        local temp_file=$(mktemp)
        awk -v version="$new_version" -v date="$date" '
            /^## \[Unreleased\]/ {
                print $0
                print ""
                print "### Added"
                print "- (Add new features here)"
                print ""
                print "### Changed"
                print "- (Add changes to existing functionality here)"
                print ""
                print "### Fixed"
                print "- (Add bug fixes here)"
                print ""
                print "## [" version "] - " date
                print ""
                print "### Changed"
                print "- Version bump to " version
                print ""
                next
            }
            { print }
        ' "$CHANGELOG" > "$temp_file"
        mv "$temp_file" "$CHANGELOG"
    fi

    print_status "$GREEN" "✅ Prepared CHANGELOG.md"
    print_status "$YELLOW" "📝 Please edit CHANGELOG.md to add release notes before committing!"
}

# Create git commit and tag
create_git_commit() {
    local new_version=$1

    print_header "💾 Creating Git Commit"

    git add "$VERSION_FILE" "$PACKAGE_JSON" 2>/dev/null || true

    if [ -f "$CHANGELOG" ]; then
        git add "$CHANGELOG"
    fi

    git commit -m "chore(release): bump version to v$new_version

Updated version across:
- VERSION file
- front/package.json
- CHANGELOG.md

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

    print_status "$GREEN" "✅ Created commit"
}

# Create git tag
create_git_tag() {
    local new_version=$1

    print_header "🏷️  Creating Git Tag"

    git tag -a "v$new_version" -m "Release v$new_version

See CHANGELOG.md for details."

    print_status "$GREEN" "✅ Created tag v$new_version"
}

# Main function
main() {
    if [ $# -eq 0 ] || [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
        show_help
        exit 0
    fi

    local bump_type=$1

    print_header "🎵 TheOpenMusicBox Version Bump"

    # Get current version
    local current_version=$(get_current_version)
    print_status "$BLUE" "📌 Current version: v$current_version"

    # Calculate new version
    local new_version=$(calculate_new_version "$current_version" "$bump_type")
    validate_version "$new_version"

    print_status "$GREEN" "🚀 New version: v$new_version"
    echo ""

    # Confirm with user
    read -p "Continue with version bump? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "$YELLOW" "❌ Version bump cancelled"
        exit 0
    fi

    # Check git status
    check_git_status

    # Update files
    print_header "📝 Updating Version Files"
    update_version_file "$new_version"
    update_package_json "$new_version"
    prepare_changelog "$new_version"

    # Create commit and tag
    create_git_commit "$new_version"
    create_git_tag "$new_version"

    # Success message
    print_header "🎉 Version Bump Complete!"
    print_status "$GREEN" "✅ Version bumped from v$current_version → v$new_version"
    echo ""
    print_status "$CYAN" "Next steps:"
    print_status "$BLUE" "  1. Review the changes: git show"
    print_status "$BLUE" "  2. Edit CHANGELOG.md to add detailed release notes"
    print_status "$BLUE" "  3. Amend the commit if needed: git commit --amend"
    print_status "$BLUE" "  4. Push changes: git push origin feat/version-management"
    print_status "$BLUE" "  5. Push tag: git push origin v$new_version"
    echo ""
}

main "$@"
