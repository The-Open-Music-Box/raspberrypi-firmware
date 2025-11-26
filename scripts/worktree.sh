#!/bin/bash

# Git Worktree Management Script for TheOpenMusicBox
# Usage: ./scripts/worktree.sh [command] [options]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_NAME="rpi-firmware"
WORKTREE_BASE_DIR="$(dirname "$REPO_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_info() { echo -e "${BLUE}ℹ${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }

# Show usage
show_usage() {
    cat <<EOF
Git Worktree Management for TheOpenMusicBox

Usage: ./scripts/worktree.sh [command] [options]

Commands:
    create <issue-number> <type> <description>
        Create a new worktree for an issue
        Types: feat, fix, refactor, chore, docs, test
        Example: ./scripts/worktree.sh create 75 feat "new-audio-feature"

    list
        List all active worktrees

    switch <issue-number>
        Switch to a worktree directory (outputs path to cd to)

    remove <issue-number>
        Remove a worktree (will prompt for confirmation)

    clean
        Remove all worktrees except the main repo (with confirmation)

    status
        Show status of all worktrees

    help
        Show this help message

Examples:
    # Create a new feature worktree for issue #75
    ./scripts/worktree.sh create 75 feat "audio-enhancement"

    # List all worktrees
    ./scripts/worktree.sh list

    # Switch to worktree for issue #75 (use with cd)
    cd \$(./scripts/worktree.sh switch 75)

    # Remove worktree for issue #75
    ./scripts/worktree.sh remove 75

EOF
}

# Create a new worktree
create_worktree() {
    local issue_number=$1
    local branch_type=$2
    local description=$3

    if [[ -z "$issue_number" || -z "$branch_type" || -z "$description" ]]; then
        print_error "Missing arguments"
        echo "Usage: create <issue-number> <type> <description>"
        exit 1
    fi

    # Validate branch type
    if [[ ! "$branch_type" =~ ^(feat|fix|refactor|chore|docs|test)$ ]]; then
        print_error "Invalid branch type: $branch_type"
        echo "Valid types: feat, fix, refactor, chore, docs, test"
        exit 1
    fi

    local branch_name="${branch_type}/issue-${issue_number}-${description}"
    local worktree_name="${REPO_NAME}-wt-${issue_number}"
    local worktree_path="${WORKTREE_BASE_DIR}/${worktree_name}"

    print_info "Creating worktree for issue #${issue_number}"
    print_info "Branch: ${branch_name}"
    print_info "Path: ${worktree_path}"

    cd "$REPO_DIR"

    # Check if worktree already exists
    if [[ -d "$worktree_path" ]]; then
        print_error "Worktree already exists at: ${worktree_path}"
        exit 1
    fi

    # Check if branch already exists
    if git rev-parse --verify "$branch_name" >/dev/null 2>&1; then
        print_warning "Branch ${branch_name} already exists, checking it out"
        git worktree add "$worktree_path" "$branch_name"
    else
        print_info "Creating new branch: ${branch_name}"
        git worktree add "$worktree_path" -b "$branch_name"
    fi

    print_success "Worktree created successfully!"
    echo ""
    print_info "To start working, run:"
    echo "  cd ${worktree_path}"
    echo ""
    print_info "Or open in Claude Code:"
    echo "  claude ${worktree_path}"
}

# List all worktrees
list_worktrees() {
    cd "$REPO_DIR"
    print_info "Active worktrees:"
    echo ""
    git worktree list
}

# Switch to a worktree (output path for cd)
switch_worktree() {
    local issue_number=$1

    if [[ -z "$issue_number" ]]; then
        print_error "Missing issue number"
        echo "Usage: switch <issue-number>"
        exit 1
    fi

    local worktree_name="${REPO_NAME}-wt-${issue_number}"
    local worktree_path="${WORKTREE_BASE_DIR}/${worktree_name}"

    if [[ ! -d "$worktree_path" ]]; then
        print_error "Worktree for issue #${issue_number} not found" >&2
        exit 1
    fi

    echo "$worktree_path"
}

# Remove a worktree
remove_worktree() {
    local issue_number=$1

    if [[ -z "$issue_number" ]]; then
        print_error "Missing issue number"
        echo "Usage: remove <issue-number>"
        exit 1
    fi

    local worktree_name="${REPO_NAME}-wt-${issue_number}"
    local worktree_path="${WORKTREE_BASE_DIR}/${worktree_name}"

    if [[ ! -d "$worktree_path" ]]; then
        print_error "Worktree for issue #${issue_number} not found"
        exit 1
    fi

    cd "$REPO_DIR"

    # Check for uncommitted changes
    if ! git -C "$worktree_path" diff-index --quiet HEAD -- 2>/dev/null; then
        print_warning "Worktree has uncommitted changes!"
        git -C "$worktree_path" status --short
        echo ""
        read -p "Are you sure you want to remove it? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Cancelled"
            exit 0
        fi
    fi

    print_info "Removing worktree: ${worktree_path}"
    git worktree remove "$worktree_path"
    print_success "Worktree removed successfully"
}

# Clean all worktrees except main
clean_worktrees() {
    cd "$REPO_DIR"

    local worktrees=$(git worktree list --porcelain | grep "worktree " | awk '{print $2}' | grep -v "^${REPO_DIR}$" || true)

    if [[ -z "$worktrees" ]]; then
        print_info "No worktrees to clean"
        exit 0
    fi

    print_warning "The following worktrees will be removed:"
    echo "$worktrees"
    echo ""
    read -p "Are you sure? (y/N): " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Cancelled"
        exit 0
    fi

    while IFS= read -r worktree_path; do
        if [[ -n "$worktree_path" && "$worktree_path" != "$REPO_DIR" ]]; then
            print_info "Removing: ${worktree_path}"
            git worktree remove "$worktree_path" --force
        fi
    done <<< "$worktrees"

    print_success "All worktrees cleaned"
}

# Show status of all worktrees
show_status() {
    cd "$REPO_DIR"

    print_info "Worktree Status:"
    echo ""

    git worktree list --porcelain | while IFS= read -r line; do
        if [[ $line == worktree* ]]; then
            current_path=$(echo "$line" | awk '{print $2}')
            echo -e "${BLUE}Path:${NC} ${current_path}"
        elif [[ $line == branch* ]]; then
            current_branch=$(echo "$line" | awk '{print $2}')
            echo -e "${GREEN}Branch:${NC} ${current_branch}"

            # Show status for this worktree
            if [[ -d "$current_path" ]]; then
                cd "$current_path"
                if ! git diff-index --quiet HEAD -- 2>/dev/null; then
                    echo -e "${YELLOW}Status:${NC} Has uncommitted changes"
                else
                    echo -e "${GREEN}Status:${NC} Clean"
                fi
            fi
            echo ""
        fi
    done
}

# Main command handler
case "${1:-help}" in
    create)
        create_worktree "$2" "$3" "$4"
        ;;
    list)
        list_worktrees
        ;;
    switch)
        switch_worktree "$2"
        ;;
    remove)
        remove_worktree "$2"
        ;;
    clean)
        clean_worktrees
        ;;
    status)
        show_status
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_usage
        exit 1
        ;;
esac
