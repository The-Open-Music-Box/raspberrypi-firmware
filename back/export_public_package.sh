#!/bin/bash
# TheOpenMusicBox - Export Public Package Script
# Exports backend files for public release using deployment manifests

set -e

readonly SCRIPT_DIR="$(dirname "$(realpath "$0")")"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly PUBLIC_RELEASE_DIR="${PROJECT_ROOT}/public_release/tomb-rpi"

# Color codes
readonly GREEN="\033[0;32m"
readonly BLUE="\033[0;34m"
readonly RED="\033[0;31m"
readonly NC="\033[0m"

echo -e "${BLUE}📦 Exporting backend package for public release...${NC}"

# Create public release directory
mkdir -p "${PUBLIC_RELEASE_DIR}"

# Use rsync with manifest files to copy backend
echo -e "${BLUE}📋 Using deployment manifests for file selection...${NC}"

rsync -a \
    --exclude-from="${SCRIPT_DIR}/.deploy-exclude" \
    --exclude='app/data/*' \
    "${SCRIPT_DIR}/" "${PUBLIC_RELEASE_DIR}/"

# Create empty data directory structure
mkdir -p "${PUBLIC_RELEASE_DIR}/app/data"
touch "${PUBLIC_RELEASE_DIR}/app/data/.gitkeep"

# Create flattened requirements.txt for production
echo -e "${BLUE}📝 Creating flattened requirements.txt...${NC}"
req_dst="${PUBLIC_RELEASE_DIR}/requirements.txt"
awk -v src_dir="${SCRIPT_DIR}/requirements" '
  /^-r / {
    sub(/^-r /, "", $0);
    file = src_dir "/" $0;
    while ((getline line < file) > 0) print line;
    close(file);
    next;
  }
  { print }
' "${SCRIPT_DIR}/requirements/prod.txt" > "$req_dst"

# Remove comments and blank lines
sed -i.bak "/^\\s*#/d;/^\\s*$/d" "$req_dst" && rm "$req_dst.bak"

echo -e "${GREEN}✅ Backend package exported successfully to ${PUBLIC_RELEASE_DIR}${NC}"
