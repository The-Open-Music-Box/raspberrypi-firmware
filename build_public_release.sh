#!/bin/bash

readonly GREEN="\033[0;32m"
readonly RED="\033[0;31m"
readonly YELLOW="\033[0;33m"
readonly BLUE="\033[0;34m"
readonly CYAN="\033[0;36m"
readonly BOLD="\033[1m"
readonly NC="\033[0m"

show_header() {
    echo -e "${GREEN}
    ========================================
    🎵  The Open Music Box Public Release  🎵
    ========================================
    ${NC}"
    echo -e "${CYAN}${BOLD}Build Public Release Package${NC}"
    echo ""
}

show_header

# ----------------- CONFIG -----------------
echo -e "${BOLD}${BLUE}🚀 Building public release package${NC}"

# Project directories
readonly PROJECT_ROOT="$(dirname "$(realpath "$0")")"

# Load configuration
CONFIG_FILE="${PROJECT_ROOT}/deploy.config"
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}❌ Configuration file not found: $CONFIG_FILE${NC}"
    exit 1
fi

source "$CONFIG_FILE"

readonly BACK_DIR="${PROJECT_ROOT}/back"
readonly FRONT_DIR="${PROJECT_ROOT}/front"
readonly PUBLIC_RELEASE_DIR="${PROJECT_ROOT}/public_release/tomb-rpi"
readonly DATA_DIR="${BACK_DIR}/app/data"

# ----------------- SCRIPT -----------------

# Step 1: Create public release directory
echo -e "${BLUE}📦 Creating public release directory...${NC}"
mkdir -p "${PUBLIC_RELEASE_DIR}"

# Step 2: Export backend package
echo -e "${BLUE}📦 Exporting backend package...${NC}"
"${BACK_DIR}/export_public_package.sh"
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Error exporting backend package.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Backend package exported successfully.${NC}"

# Step 2b: Create empty data directory structure but exclude content
echo -e "${BLUE}📂 Setting up empty data directory structure...${NC}"
mkdir -p "${PUBLIC_RELEASE_DIR}/app/data"
touch "${PUBLIC_RELEASE_DIR}/app/data/.gitkeep"
echo -e "${GREEN}✅ Empty data directory structure created.${NC}"

# Step 3: Build frontend
echo -e "${BLUE}🔨 Building frontend...${NC}"
# Save current directory
CURRENT_DIR=$(pwd)
cd "${FRONT_DIR}" || { echo -e "${RED}❌ Could not navigate to front directory.${NC}"; exit 1; }
npm run build
BUILD_EXIT=$?
# Return to original directory
cd "$CURRENT_DIR" || true
if [ $BUILD_EXIT -ne 0 ]; then
    echo -e "${RED}❌ Error building frontend.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Frontend built successfully.${NC}"

# Step 4: Copy frontend build to public release
echo -e "${BLUE}📋 Copying frontend build to public release...${NC}"
mkdir -p "${PUBLIC_RELEASE_DIR}/app/static"
cp -r "${FRONT_DIR}/dist/"* "${PUBLIC_RELEASE_DIR}/app/static/"
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Error copying frontend build.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Frontend copied to public release.${NC}"

# Step 5: Create release archive
echo -e "${BLUE}📦 Creating release archive...${NC}"
RELEASE_DATE=$(date +"%Y%m%d")
RELEASE_ARCHIVE="${PROJECT_ROOT}/tomb-rpi-release-${RELEASE_DATE}.tar.gz"

# Create archive from the public_release directory
tar -czf "${RELEASE_ARCHIVE}" -C "${PROJECT_ROOT}/public_release" "tomb-rpi"
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Error creating release archive.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Release archive created: ${RELEASE_ARCHIVE}${NC}"

# Step 6: Display release info
echo -e "${BLUE}📝 Release information:${NC}"
echo -e "  - Date: $(date)"
echo -e "  - Archive: ${RELEASE_ARCHIVE}"
echo -e "  - Size: $(du -h "${RELEASE_ARCHIVE}" | cut -f1)"

echo -e "${GREEN}🎉 Public release build complete!${NC}"
