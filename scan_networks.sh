#!/bin/bash
# scan_networks.sh - CGI script to scan and return available WiFi networks as JSON
set -euo pipefail

echo "Content-Type: application/json"
echo "Access-Control-Allow-Origin: *"
echo ""

SCAN_CACHE="/tmp/wifi_networks_cache.json"

# If cache exists and is less than 30 seconds old, use it
if [[ -f "$SCAN_CACHE" ]] && [[ $(($(date +%s) - $(stat -c %Y "$SCAN_CACHE" 2>/dev/null || echo 0))) -lt 30 ]]; then
  cat "$SCAN_CACHE"
  exit 0
fi

# Check if wlan0 is in AP mode (can't scan in AP mode on same interface)
if iw dev wlan0 info 2>/dev/null | grep -qi "type AP"; then
  # Return cached data or empty if no cache
  if [[ -f "$SCAN_CACHE" ]]; then
    cat "$SCAN_CACHE"
  else
    echo "[]"
  fi
  exit 0
fi

# Bring interface up if needed
ip link set wlan0 up 2>/dev/null || true
sleep 1

# Scan networks (retry once if first scan fails)
if ! iw dev wlan0 scan 2>/dev/null > /tmp/wifi_scan.txt; then
  sleep 2
  if ! iw dev wlan0 scan 2>/dev/null > /tmp/wifi_scan.txt; then
    echo "[]"
    exit 0
  fi
fi

# Parse scan results into JSON
python3 <<'PYEOF'
import re
import json

networks = []
current = {}

try:
    with open('/tmp/wifi_scan.txt', 'r') as f:
        for line in f:
            line = line.strip()

            # New BSS = new network
            if line.startswith('BSS '):
                if current.get('ssid'):
                    networks.append(current)
                current = {'bssid': line.split()[1].rstrip('('), 'secured': False}

            # SSID
            elif line.startswith('SSID: '):
                ssid = line[6:].strip()
                if ssid:  # Skip hidden networks
                    current['ssid'] = ssid

            # Signal strength
            elif 'signal:' in line.lower():
                match = re.search(r'(-?\d+\.?\d*)\s*dBm', line)
                if match:
                    dbm = float(match.group(1))
                    # Convert dBm to percentage (approximation)
                    # -30dBm = 100%, -90dBm = 0%
                    signal_pct = max(0, min(100, int((dbm + 90) * (100/60))))
                    current['signal'] = signal_pct
                    current['dbm'] = dbm

            # Frequency
            elif 'freq:' in line.lower() or 'DS Parameter set: channel' in line:
                if 'freq:' in line.lower():
                    match = re.search(r'(\d+)', line)
                    if match:
                        freq = int(match.group(1))
                        current['frequency'] = freq
                        current['band'] = '5GHz' if freq > 5000 else '2.4GHz'
                elif 'DS Parameter set: channel' in line:
                    match = re.search(r'channel (\d+)', line)
                    if match:
                        current['channel'] = int(match.group(1))

            # Security (WPA/WPA2/WPA3)
            elif 'WPA' in line or 'RSN' in line or 'Privacy' in line:
                current['secured'] = True

        # Add last network
        if current.get('ssid'):
            networks.append(current)

    # Deduplicate by SSID (keep strongest signal)
    unique_networks = {}
    for net in networks:
        ssid = net.get('ssid', '')
        if ssid:
            if ssid not in unique_networks or net.get('signal', 0) > unique_networks[ssid].get('signal', 0):
                unique_networks[ssid] = net

    # Sort by signal strength
    sorted_networks = sorted(unique_networks.values(), key=lambda x: x.get('signal', 0), reverse=True)

    # Add missing fields with defaults
    for net in sorted_networks:
        net.setdefault('signal', 0)
        net.setdefault('band', '2.4GHz')
        net.setdefault('channel', 0)
        net.setdefault('secured', True)

    result = json.dumps(sorted_networks, indent=2)

    # Save to cache
    with open('/tmp/wifi_networks_cache.json', 'w') as cache:
        cache.write(result)

    print(result)

except Exception as e:
    print(json.dumps([]))
PYEOF
