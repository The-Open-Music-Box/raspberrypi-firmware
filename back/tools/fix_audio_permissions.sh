#!/bin/bash

# Audio Permission Diagnostic and Fix Script for The Open Music Box
# This script diagnoses and fixes audio permission issues on Raspberry Pi

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "Audio Permission Diagnostic & Fix Script"
echo "========================================="
echo ""

# Function to print colored output
print_status() {
    if [ "$1" = "OK" ]; then
        echo -e "${GREEN}[OK]${NC} $2"
    elif [ "$1" = "ERROR" ]; then
        echo -e "${RED}[ERROR]${NC} $2"
    elif [ "$1" = "WARNING" ]; then
        echo -e "${YELLOW}[WARNING]${NC} $2"
    else
        echo -e "${YELLOW}[INFO]${NC} $2"
    fi
}

# 1. Check current user
CURRENT_USER=$(whoami)
print_status "INFO" "Running as user: $CURRENT_USER"

# 2. Check if user is in audio group
if groups $CURRENT_USER | grep -q '\baudio\b'; then
    print_status "OK" "User $CURRENT_USER is in audio group"
else
    print_status "ERROR" "User $CURRENT_USER is NOT in audio group"
    if [ "$CURRENT_USER" != "root" ]; then
        print_status "INFO" "Fixing: Adding $CURRENT_USER to audio group..."
        sudo usermod -a -G audio $CURRENT_USER
        print_status "OK" "Added to audio group (logout/login required for changes to take effect)"
    fi
fi

# 3. Check audio device permissions
print_status "INFO" "Checking audio device permissions..."
if [ -d /dev/snd ]; then
    AUDIO_PERMS=$(ls -l /dev/snd/pcm* 2>/dev/null | head -1)
    if echo "$AUDIO_PERMS" | grep -q "root audio"; then
        print_status "OK" "Audio devices have correct ownership (root:audio)"
    else
        print_status "WARNING" "Audio devices may have incorrect ownership"
    fi
else
    print_status "ERROR" "/dev/snd directory not found"
fi

# 4. Check if tomb application is running as root
print_status "INFO" "Checking tomb application process..."
TOMB_PID=$(pgrep -f "start_app.py" || true)

if [ -n "$TOMB_PID" ]; then
    TOMB_USER=$(ps -o user= -p $TOMB_PID | tr -d ' ')
    print_status "INFO" "Tomb application (PID: $TOMB_PID) is running as: $TOMB_USER"
    
    if [ "$TOMB_USER" = "root" ]; then
        print_status "ERROR" "Tomb application is running as ROOT - this causes audio permission issues!"
        NEEDS_FIX=true
    else
        print_status "OK" "Tomb application is running as user: $TOMB_USER"
        NEEDS_FIX=false
    fi
else
    print_status "WARNING" "Tomb application is not running"
    NEEDS_FIX=false
fi

# 5. Check which processes are using audio devices
print_status "INFO" "Checking audio device usage..."
AUDIO_USERS=$(lsof /dev/snd/* 2>/dev/null | grep -v COMMAND || true)
if [ -n "$AUDIO_USERS" ]; then
    print_status "WARNING" "Following processes are using audio devices:"
    echo "$AUDIO_USERS" | while read line; do
        echo "  $line"
    done
else
    print_status "OK" "No processes currently using audio devices"
fi

# 6. Check for stale IPC semaphores
print_status "INFO" "Checking for audio IPC semaphores..."
IPC_COUNT=$(ipcs -s 2>/dev/null | grep -c "0x" || echo "0")
if [ "$IPC_COUNT" -gt "0" ]; then
    print_status "WARNING" "Found $IPC_COUNT IPC semaphores that might cause issues"
else
    print_status "OK" "No problematic IPC semaphores found"
fi

# 7. Test aplay
print_status "INFO" "Testing aplay command..."
if [ -f /usr/share/sounds/alsa/Front_Center.wav ]; then
    if timeout 2 aplay -l &>/dev/null; then
        print_status "OK" "aplay can list audio devices"
    else
        print_status "ERROR" "aplay cannot access audio devices"
    fi
else
    print_status "WARNING" "Test sound file not found"
fi

echo ""
echo "========================================="
echo "APPLYING FIXES"
echo "========================================="
echo ""

# Apply fixes if needed
if [ "$NEEDS_FIX" = true ]; then
    print_status "INFO" "Fixing tomb application running as root..."
    
    # Check if systemd service exists
    if systemctl list-units --full -all | grep -q "tomb.service"; then
        print_status "INFO" "Found tomb systemd service"
        
        # Stop the service
        print_status "INFO" "Stopping tomb service..."
        sudo systemctl stop tomb
        
        # Check if service file needs updating
        SERVICE_FILE="/etc/systemd/system/tomb.service"
        if [ -f "$SERVICE_FILE" ]; then
            if ! grep -q "^User=" "$SERVICE_FILE"; then
                print_status "INFO" "Updating systemd service to run as admin user..."
                
                # Backup original
                sudo cp "$SERVICE_FILE" "${SERVICE_FILE}.backup"
                
                # Add User and Group directives after [Service] section
                sudo sed -i '/\[Service\]/a User=admin\nGroup=audio' "$SERVICE_FILE"
                
                print_status "OK" "Service file updated"
            else
                print_status "INFO" "Service file already has User configuration"
            fi
            
            # Reload systemd and restart
            print_status "INFO" "Reloading systemd and restarting service..."
            sudo systemctl daemon-reload
            sudo systemctl start tomb
            print_status "OK" "Tomb service restarted"
        fi
    else
        print_status "INFO" "No systemd service found, killing process directly..."
        
        # Kill the root process
        sudo pkill -f "start_app.py" || true
        sleep 2
        
        # Restart as admin user
        print_status "INFO" "Restarting tomb application as admin user..."
        if [ -d "/home/admin/tomb" ]; then
            su - admin -c "cd /home/admin/tomb && nohup ./venv/bin/python start_app.py > /tmp/tomb.log 2>&1 &"
            print_status "OK" "Tomb application restarted as admin user"
        else
            print_status "ERROR" "Tomb directory not found at /home/admin/tomb"
        fi
    fi
    
    # Clean up IPC semaphores if needed
    if [ "$IPC_COUNT" -gt "0" ]; then
        print_status "INFO" "Cleaning up IPC semaphores..."
        ipcs -s | grep "0x" | awk '{print $2}' | while read sem; do
            sudo ipcrm -s $sem 2>/dev/null || true
        done
        print_status "OK" "IPC semaphores cleaned"
    fi
fi

echo ""
echo "========================================="
echo "FINAL CHECK"
echo "========================================="
echo ""

# Final verification
sleep 3
print_status "INFO" "Performing final verification..."

# Check if tomb is running correctly
TOMB_PID=$(pgrep -f "start_app.py" || true)
if [ -n "$TOMB_PID" ]; then
    TOMB_USER=$(ps -o user= -p $TOMB_PID | tr -d ' ')
    if [ "$TOMB_USER" != "root" ]; then
        print_status "OK" "Tomb application is now running as: $TOMB_USER"
    else
        print_status "ERROR" "Tomb application is still running as root - manual intervention needed"
    fi
fi

# Test aplay again
if timeout 2 aplay -l &>/dev/null; then
    print_status "OK" "Audio system is accessible"
    
    # Try to play test sound if not root
    if [ "$CURRENT_USER" != "root" ] && [ -f /usr/share/sounds/alsa/Front_Center.wav ]; then
        print_status "INFO" "Attempting to play test sound..."
        if timeout 2 aplay /usr/share/sounds/alsa/Front_Center.wav &>/dev/null; then
            print_status "OK" "Audio playback successful!"
        else
            print_status "WARNING" "Could not play test sound (device might be busy)"
        fi
    fi
else
    print_status "ERROR" "Audio system still not accessible"
fi

echo ""
echo "========================================="
echo "Script completed!"
echo ""
echo "If issues persist:"
echo "1. Logout and login again (if user was added to audio group)"
echo "2. Reboot the system: sudo reboot"
echo "3. Check the tomb application logs: journalctl -u tomb -n 50"
echo "========================================="