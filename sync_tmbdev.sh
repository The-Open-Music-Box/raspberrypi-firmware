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
    🎵  The Open Music Box Sync  🎵
    ========================================
    ${NC}"
    echo -e "${CYAN}${BOLD}Sync Local Files to tmbdev (Raspberry Pi)${NC}"
    echo -e "${YELLOW}📋 Includes .env configuration deployment${NC}"
    echo ""
}

show_header

# ----------------- CONFIG -----------------
echo -e "${BOLD}${BLUE}🚀 Secure synchronization to Raspberry Pi${NC}"

# Project directories
readonly PROJECT_ROOT="$(dirname "$(realpath "$0")")"

# Load configuration
CONFIG_FILE="${PROJECT_ROOT}/sync_tmbdev.config"
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}❌ Configuration file not found: $CONFIG_FILE${NC}"
    exit 1
fi

source "$CONFIG_FILE"

# Allow SSH_DEST override from command line
if [ ! -z "$1" ]; then
    SSH_DEST="$1"
fi
readonly BACK_DIR="${PROJECT_ROOT}/back"
readonly FRONT_DIR="${PROJECT_ROOT}/front"
readonly RELEASE_DEV_DIR="${PROJECT_ROOT}/${RELEASE_DEV_DIR}/tomb-rpi"

# SSH options with key path from config
readonly SSH_FULL_OPTS="${SSH_OPTS} -i ${SSH_KEY}"


# ----------------- SCRIPT -----------------

# Step 1: Create release_dev directory
echo -e "${BLUE}📦 Creating release_dev directory...${NC}"
mkdir -p "${RELEASE_DEV_DIR}"

# Step 2: Prepare backend files
echo -e "${BLUE}📦 Preparing backend files...${NC}"
# Copy app directory
rsync -av --delete \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='logs' \
    --exclude='app.db' \
    "${BACK_DIR}/app/" "${RELEASE_DEV_DIR}/app/"

# Create flattened requirements.txt
REQ_DST="${RELEASE_DEV_DIR}/requirements.txt"
awk -v src_dir="${BACK_DIR}/requirements" '
  /^-r / {
    sub(/^-r /, "", $0);
    file = src_dir "/" $0;
    while ((getline line < file) > 0) print line;
    close(file);
    next;
  }
  { print }
' "${BACK_DIR}/requirements/prod.txt" > "$REQ_DST"

# Remove comments and blank lines
sed -i.bak "/^\s*#/d;/^\s*$/d" "$REQ_DST" && rm "$REQ_DST.bak"

# Copy additional files
[ -f "${BACK_DIR}/README.md" ] && cp "${BACK_DIR}/README.md" "${RELEASE_DEV_DIR}/"
[ -f "${BACK_DIR}/app.service" ] && cp "${BACK_DIR}/app.service" "${RELEASE_DEV_DIR}/"
[ -f "${BACK_DIR}/LICENSE" ] && cp "${BACK_DIR}/LICENSE" "${RELEASE_DEV_DIR}/"
[ -f "${BACK_DIR}/setup.sh" ] && cp "${BACK_DIR}/setup.sh" "${RELEASE_DEV_DIR}/"
[ -f "${BACK_DIR}/start_app.py" ] && cp "${BACK_DIR}/start_app.py" "${RELEASE_DEV_DIR}/" && chmod +x "${RELEASE_DEV_DIR}/start_app.py"

# Copy tools directory
echo -e "${CYAN}🔧 Copying tools directory...${NC}"
if [ -d "${BACK_DIR}/tools" ]; then
    cp -r "${BACK_DIR}/tools" "${RELEASE_DEV_DIR}/"
    chmod +x "${RELEASE_DEV_DIR}/tools/"*.py 2>/dev/null || true
    echo -e "${GREEN}✅ Tools directory copied successfully.${NC}"
else
    echo -e "${YELLOW}⚠️  Tools directory not found at: ${BACK_DIR}/tools${NC}"
fi

# Copy configuration file (.env) - CRITICAL for production
echo -e "${CYAN}📋 Copying configuration file (.env)...${NC}"
if [ -f "${BACK_DIR}/.env" ]; then
    cp "${BACK_DIR}/.env" "${RELEASE_DEV_DIR}/.env"
    echo -e "${GREEN}✅ Configuration file (.env) copied successfully.${NC}"
else
    echo -e "${RED}❌ WARNING: .env file not found! Application will not start without it.${NC}"
    echo -e "${YELLOW}⚠️️  Please ensure .env file exists at: ${BACK_DIR}/.env${NC}"
fi

echo -e "${GREEN}✅ Backend files prepared successfully.${NC}"

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

# Step 4: Copy frontend build to release_dev
echo -e "${BLUE}📋 Copying frontend build to release_dev...${NC}"
mkdir -p "${RELEASE_DEV_DIR}/app/static"
cp -r "${FRONT_DIR}/dist/"* "${RELEASE_DEV_DIR}/app/static/"
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Error copying frontend build.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Frontend copied to release_dev.${NC}"

# Step 5: Upload to server
echo -e "${BLUE}🗂️  Creating remote directory if needed...${NC}"
ssh ${SSH_FULL_OPTS} "${SSH_DEST}" "mkdir -p ${REMOTE_DIR} && sudo chown admin:admin ${REMOTE_DIR}" 2>/dev/null

echo -e "${BLUE}📤 Synchronizing files with rsync...${NC}"

rsync -avzP --delete \
    --rsync-path="sudo rsync" \
    --no-owner --no-group \
    --chown=admin:admin \
    --ignore-errors \
    -e "ssh ${SSH_FULL_OPTS}" \
    "${RSYNC_EXCLUDES[@]}" \
    "${RELEASE_DEV_DIR}/" "${SSH_DEST}:${REMOTE_DIR}/" 2>/dev/null

RSYNC_EXIT=$?
if [ "$RSYNC_EXIT" -eq 0 ]; then
    echo -e "${GREEN}✅ Synchronization completed without errors.${NC}"
else
    echo -e "${RED}❌ Error during synchronization (code $RSYNC_EXIT).${NC}"
    exit $RSYNC_EXIT
fi

echo -e "${BLUE}🔧 Fixing permissions on the remote directory...${NC}"
ssh ${SSH_FULL_OPTS} "${SSH_DEST}" "sudo chown -R admin:admin ${REMOTE_DIR}" 2>/dev/null

# Validate .env file was deployed
echo -e "${BLUE}🔍 Validating configuration deployment...${NC}"
ENV_CHECK=$(ssh ${SSH_FULL_OPTS} "${SSH_DEST}" "[ -f ${REMOTE_DIR}/.env ] && echo 'found' || echo 'missing'" 2>/dev/null)
if [ "$ENV_CHECK" = "found" ]; then
    echo -e "${GREEN}✅ Configuration file (.env) successfully deployed to server.${NC}"
else
    echo -e "${RED}❌ WARNING: Configuration file (.env) missing on server!${NC}"
    echo -e "${YELLOW}⚠️️  Application may fail to start. Check deployment manually.${NC}"
fi

echo -e "${GREEN}🎉 All done! Files are in ${REMOTE_DIR} on the RPi.${NC}"
