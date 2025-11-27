#!/bin/bash
echo "========================================"
echo " 🎵  The Open Music Box Setup  🎵 "
echo "========================================"

# Local setup script for Raspberry Pi deployment
# Usage: sudo ./setup.sh
# This script must be run from the root of the extracted public_release folder

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Check if the script is run with sudo
if [ "$(id -u)" -ne 0 ]; then
  echo -e "${RED}This script must be run as root. Please use sudo.${NC}"
  exit 1
fi

# Get script directory (used throughout the script)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 1. Install required apt packages
REQUIRED_APT_PACKAGES=(python3 python3-venv python3-pip ffmpeg libasound2-dev libnss-mdns git i2c-tools python3-smbus python3-libgpiod libsdl2-mixer-2.0-0 swig unzip build-essential dkms raspberrypi-kernel-headers)
echo -e "${GREEN}Installing required apt packages...${NC}"
sudo apt-get update
sudo apt-get install -y "${REQUIRED_APT_PACKAGES[@]}"

# Enable I2C interface
echo -e "${GREEN}Enabling I2C interface...${NC}"
sudo raspi-config nonint do_i2c 0
echo "I2C interface enabled"

# Install lgpio from source since it's not available in package manager
if ! ldconfig -p | grep -q liblgpio; then
  echo -e "${GREEN}Installing lgpio from source...${NC}"
  ORIGINAL_DIR=$(pwd)
  cd /tmp
  wget https://github.com/joan2937/lg/archive/master.zip
  unzip -o master.zip
  cd lg-master
  make
  sudo make install
  cd "$ORIGINAL_DIR"
else
  echo -e "${GREEN}lgpio already installed, skipping...${NC}"
fi

# Install WM8960 Audio HAT driver
echo -e "${GREEN}Installing WM8960 Audio HAT driver...${NC}"

# Use bundled driver files
WM8960_DRIVER_DIR="$SCRIPT_DIR/drivers/wm8960"
if [ ! -d "$WM8960_DRIVER_DIR" ]; then
  echo -e "${RED}WM8960 driver files not found in $WM8960_DRIVER_DIR${NC}"
  exit 1
fi

# Install kernel module via DKMS
WM8960_MOD="wm8960-soundcard"
WM8960_VER="1.0"
WM8960_SRC="/usr/src/${WM8960_MOD}-${WM8960_VER}"

# Remove old module if exists
dkms remove --force -m $WM8960_MOD -v $WM8960_VER --all 2>/dev/null || true

# Copy source and install
mkdir -p "$WM8960_SRC"
cp -a "$WM8960_DRIVER_DIR/"* "$WM8960_SRC/"
dkms add -m $WM8960_MOD -v $WM8960_VER
dkms build -m $WM8960_MOD -v $WM8960_VER
dkms install --force -m $WM8960_MOD -v $WM8960_VER

# Install device tree overlay
cp "$WM8960_DRIVER_DIR/wm8960-soundcard.dtbo" /boot/overlays/

# Configure boot parameters
CONFIG_FILE="/boot/firmware/config.txt"
if [ ! -f "$CONFIG_FILE" ]; then
  CONFIG_FILE="/boot/config.txt"
fi

# Enable I2S
if ! grep -q "^dtparam=i2s=on" "$CONFIG_FILE"; then
  sed -i 's/^#dtparam=i2s=on/dtparam=i2s=on/' "$CONFIG_FILE"
  grep -q "^dtparam=i2s=on" "$CONFIG_FILE" || echo "dtparam=i2s=on" >> "$CONFIG_FILE"
fi

# Add overlays (only if not present)
grep -q "^dtoverlay=i2s-mmap" "$CONFIG_FILE" || echo "dtoverlay=i2s-mmap" >> "$CONFIG_FILE"
grep -q "^dtoverlay=wm8960-soundcard" "$CONFIG_FILE" || echo "dtoverlay=wm8960-soundcard" >> "$CONFIG_FILE"

# Install configuration files
mkdir -p /etc/wm8960-soundcard
cp "$WM8960_DRIVER_DIR"/*.state /etc/wm8960-soundcard/ 2>/dev/null || true

# Install ALSA configuration in /etc/wm8960-soundcard/
# This file will be symlinked by the wm8960-soundcard service
cat > /etc/wm8960-soundcard/asound.conf << 'EOF'
# WM8960 Audio HAT Configuration
# Simple configuration for pygame/SDL compatibility

pcm.!default {
    type asym
    playback.pcm "plughw:wm8960soundcard"
    capture.pcm "plughw:wm8960soundcard"
}

ctl.!default {
    type hw
    card wm8960soundcard
}
EOF

# Install wm8960-soundcard service
cp "$WM8960_DRIVER_DIR/wm8960-soundcard" /usr/bin/
chmod +x /usr/bin/wm8960-soundcard
cp "$WM8960_DRIVER_DIR/wm8960-soundcard.service" /lib/systemd/system/
systemctl daemon-reload
systemctl enable wm8960-soundcard.service
systemctl restart wm8960-soundcard.service

# Add i2c-dev to /etc/modules (only this one, NOT the snd-soc modules to avoid double loading)
if ! grep -q "^i2c-dev" /etc/modules; then
  echo "i2c-dev" >> /etc/modules
fi

# Remove redundant module entries that cause driver conflicts
sed -i '/^snd-soc-wm8960$/d' /etc/modules
sed -i '/^snd-soc-wm8960-soundcard$/d' /etc/modules

echo -e "${GREEN}WM8960 Audio HAT driver installed successfully!${NC}"

# 2. Créer un environnement virtuel Python et installer les dépendances dans le venv
VENV_PATH="$SCRIPT_DIR/venv"

# Create the virtual environment in the specified path
if [ ! -d "$VENV_PATH" ]; then
  echo -e "${GREEN}Creating Python virtual environment in $VENV_PATH...${NC}"
  python3 -m venv "$VENV_PATH"
fi

source "$VENV_PATH/bin/activate"
echo -e "${GREEN}Upgrading pip in venv...${NC}"
pip install --upgrade pip
echo -e "${GREEN}Installing/Updating Python dependencies from requirements.txt into venv...${NC}"
pip install --upgrade -r "$SCRIPT_DIR/requirements.txt"
deactivate

# Fix venv ownership (script runs as root but venv should be owned by admin)
echo -e "${GREEN}Fixing venv ownership...${NC}"
chown -R admin:admin "$VENV_PATH"

# 4. Déploiement du service systemd
# Ensure app.service exists before enabling
if [ -f "$SCRIPT_DIR/app.service" ]; then
  echo -e "${GREEN}Copying app.service to /etc/systemd/system/app.service...${NC}"
  sudo cp "$SCRIPT_DIR/app.service" /etc/systemd/system/app.service
  echo -e "${GREEN}Reloading systemd...${NC}"
  sudo systemctl daemon-reload
  # Enable and restart the service (restart handles both new and existing installations)
  sudo systemctl enable app
  sudo systemctl restart app
else
  echo -e "${RED}app.service not found in $SCRIPT_DIR. Please ensure it is present.${NC}"
fi

echo -e "${GREEN}Setup complete!${NC}"
echo "→ Service installé : sudo systemctl status app"
echo "→ Configuration dans le fichier .env"
echo "→ Lancement : sudo systemctl start app"