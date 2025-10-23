#!/usr/bin/env bash
# portal.sh — Wi‑Fi dual‑mode (Client <-> AP Captive) installer & validator for Raspberry Pi
# Idempotent: safe to re-run. Adds diagnostics, auto-revert, and captive portal tests.
# Usage:
#   sudo bash portal.sh install     # install/repair everything
#   sudo bash portal.sh setup [s]   # start AP+captive for s seconds (default 180) with auto-revert
#   sudo bash portal.sh normal      # return to client mode
#   sudo bash portal.sh status      # show state & quick health checks
#   sudo bash portal.sh logs        # show last lines from setup log & webserver
#   sudo bash portal.sh selftest    # run local HTTP/DNS tests
#
# Notes:
# - Creates /usr/local/bin/wifi_setup.sh (controller)
# - Creates lighttpd captive pages & CGI handler /var/www/html/setup/save_wifi.sh
# - Configures hostapd, dnsmasq, lighttpd, iptables
# - Forces DHCP options (router & DNS) for clients, and DNS catch-all to 192.168.4.1
# - Adds Android/iOS/Windows captive endpoints & rewrite
# - Sets Wi‑Fi country code (default BE) and sane AP defaults
# - Writes logs to /var/log/wifi-setup.log and /var/log/lighttpd/access.log
set -euo pipefail

# ---------- Defaults (edit if needed) ----------
AP_SSID="${AP_SSID:-Setup-RPI}"
AP_PSK="${AP_PSK:-Setup1234}"
AP_NET="${AP_NET:-192.168.4.0}"
AP_IP="${AP_IP:-192.168.4.1}"
AP_CIDR="${AP_CIDR:-192.168.4.1/24}"
AP_DHCP_START="${AP_DHCP_START:-192.168.4.2}"
AP_DHCP_END="${AP_DHCP_END:-192.168.4.50}"
WIFI_COUNTRY="${WIFI_COUNTRY:-BE}"
LOG_FILE="/var/log/wifi-setup.log"
DOCROOT="/var/www/html/setup"
WPA_SUPP_CONF="/etc/wpa_supplicant/wpa_supplicant.conf"
WPA_SUPP_CLIENT="/etc/wpa_supplicant/wpa_supplicant.client.conf"
HOSTAPD_CONF="/etc/hostapd/hostapd.conf"
DNSMASQ_CONF="/etc/dnsmasq.conf"
LIGHTTPD_CONF="/etc/lighttpd/lighttpd.conf"
CAPTIVE_SNIPPET="/etc/lighttpd/conf-available/99-captive.conf"

# ---------- Helpers ----------
log(){ echo "[$(date +'%F %T')] $*" | tee -a "$LOG_FILE" >/dev/null; }
require_root(){ if [[ $EUID -ne 0 ]]; then echo "Run as root: sudo $0 $*"; exit 1; fi; }
backup_once(){
  local f="$1"
  [[ -f "$f" && ! -f "${f}.orig" ]] && cp -a "$f" "${f}.orig" || true
}

enable_mod(){
  local mod="$1"
  lighttpd-enable-mod "$mod" >/dev/null 2>&1 || true
}

# ---------- Install / Repair ----------
install_all(){
  require_root
  echo "== Installing & validating packages… =="
  apt-get update -y
  DEBIAN_FRONTEND=noninteractive apt-get install -y hostapd dnsmasq lighttpd iptables curl python3 iw wireless-tools
  systemctl unmask hostapd || true
  systemctl enable lighttpd || true
  mkdir -p "$(dirname "$LOG_FILE")" /var/log/lighttpd "$DOCROOT"
  chown -R www-data:www-data /var/log/lighttpd "$DOCROOT"
  chmod -R 755 "$DOCROOT"

  echo "== Setting Wi‑Fi country (${WIFI_COUNTRY}) =="
  sed -i "s/^#*country=.*/country=${WIFI_COUNTRY}/" "$WPA_SUPP_CONF" || true
  grep -q "^country=${WIFI_COUNTRY}" "$WPA_SUPP_CONF" || echo "country=${WIFI_COUNTRY}" >> "$WPA_SUPP_CONF"

  echo "== Configuring hostapd =="
  backup_once "$HOSTAPD_CONF"
  install -d -m 0755 /etc/hostapd
  cat >"$HOSTAPD_CONF" <<EOF
interface=wlan0
driver=nl80211
ssid=${AP_SSID}
hw_mode=g
channel=6
ieee80211n=1
ieee80211d=1
country_code=${WIFI_COUNTRY}
wmm_enabled=1
auth_algs=1
wpa=2
wpa_passphrase=${AP_PSK}
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
ignore_broadcast_ssid=0
EOF
  sed -i 's|^#\?DAEMON_CONF=.*|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd

  echo "== Configuring dnsmasq (DHCP/DNS captive) =="
  backup_once "$DNSMASQ_CONF"
  cat >"$DNSMASQ_CONF" <<EOF
interface=wlan0
bind-interfaces
dhcp-range=${AP_DHCP_START},${AP_DHCP_END},255.255.255.0,24h
# Force router & DNS to the portal
dhcp-option=3,${AP_IP}
dhcp-option=6,${AP_IP}
# DNS catch-all -> portal
address=/#/${AP_IP}
log-queries
log-dhcp
EOF
  systemctl enable dnsmasq || true

  echo "== Configuring lighttpd (docroot & modules) =="
  backup_once "$LIGHTTPD_CONF"
  # Ensure global docroot points to portal
  sed -i 's|^server\.document-root *=.*|server.document-root = "/var/www/html/setup"|' "$LIGHTTPD_CONF" || \
    echo 'server.document-root = "/var/www/html/setup"' >> "$LIGHTTPD_CONF"

  # Access log conf
  echo 'accesslog.filename = "/var/log/lighttpd/access.log"' > /etc/lighttpd/conf-available/10-accesslog.conf
  ln -sf ../conf-available/10-accesslog.conf /etc/lighttpd/conf-enabled/10-accesslog.conf

  # Captive extras (no duplicate docroot here)
  cat >"$CAPTIVE_SNIPPET" <<'EOF'
# Captive portal extras
# Expose .sh via bash (CGI)
cgi.assign = ( ".sh" => "/bin/bash" )

# Captive probes -> /
$HTTP["url"] =~ "^/generate_204$"         { url.redirect = ( "" => "/" ) }   # Android
$HTTP["url"] =~ "^/gen_204$"              { url.redirect = ( "" => "/" ) }   # Android alt
$HTTP["url"] =~ "^/hotspot-detect\.html$" { url.redirect = ( "" => "/" ) }   # iOS/macOS
$HTTP["url"] =~ "^/ncsi\.txt$"            { url.redirect = ( "" => "/" ) }   # Windows
$HTTP["url"] =~ "^/connecttest\.txt$"     { url.redirect = ( "" => "/" ) }   # Windows alt

# Everything else -> / (when not a real file)
url.rewrite-if-not-file = ( "^/.*" => "/" )
EOF
  ln -sf ../conf-available/99-captive.conf /etc/lighttpd/conf-enabled/99-captive.conf

  # Enable required modules
  enable_mod cgi
  enable_mod accesslog
  enable_mod rewrite
  enable_mod redirect

  echo "== Creating captive portal pages =="

  # Check if modern index.html exists in same directory as this script
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [[ -f "$SCRIPT_DIR/index.html" ]]; then
    echo "Using modern interface from $SCRIPT_DIR/index.html"
    cp "$SCRIPT_DIR/index.html" "$DOCROOT/index.html"
  else
    echo "WARN: Modern index.html not found, creating basic fallback"
    cat >"$DOCROOT/index.html" <<'EOF'
<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Configuration Wi‑Fi du Raspberry Pi</title>
<style>
 body{font-family:system-ui,Segoe UI,Roboto,Arial,sans-serif;max-width:720px;margin:40px auto;padding:0 16px}
 h1{font-size:1.6rem} .card{padding:16px;border:1px solid #ddd;border-radius:12px}
 input,button{padding:10px;margin:6px 0;width:100%;box-sizing:border-box}
 .ok{color:#0a0} .err{color:#a00}
</style></head><body>
  <h1>Configurer le Wi‑Fi</h1>
  <div class="card">
    <form action="/save_wifi.sh" method="POST">
      <label>Nom du Wi‑Fi (SSID)</label>
      <input type="text" name="ssid" placeholder="ex: Maison" required>
      <label>Mot de passe</label>
      <input type="password" name="password" placeholder="mot de passe Wi‑Fi" required>
      <button type="submit">Connecter le Raspberry Pi</button>
      <p>Après envoi, l'AP s'éteint et le Pi rejoint votre réseau.</p>
    </form>
  </div>
</body></html>
EOF
  fi

  # Captive probe files
  echo "OK" >"$DOCROOT/generate_204"
  echo "<html><head><title>Success</title></head><body>Success</body></html>" >"$DOCROOT/hotspot-detect.html"
  echo "Microsoft NCSI" >"$DOCROOT/ncsi.txt"
  echo "connect test" >"$DOCROOT/connecttest.txt"

  echo "== Creating CGI save_wifi.sh =="
  cat >"$DOCROOT/save_wifi.sh" <<'EOF'
#!/bin/bash
set -euo pipefail
echo "Content-Type: text/html"
echo ""

# read POST body
read -N "${CONTENT_LENGTH:-0}" POST_DATA || true

urldecode(){ : "${1//+/ }"; echo -e "${_//%/\\x}"; }
SSID=""; PASSWORD=""
for pair in ${POST_DATA//&/ }; do
  key="${pair%%=*}"; val="${pair#*=}"; val="$(urldecode "$val")"
  case "$key" in
    ssid) SSID="$val" ;;
    password) PASSWORD="$val" ;;
  esac
done

SETUP_LOCK_FLAG="/run/wifi_setup_lock"; sudo touch "$SETUP_LOCK_FLAG" 2>/dev/null || true

if [[ -z "$SSID" || -z "$PASSWORD" ]]; then
  echo "<h1>Erreur: SSID/mot de passe manquant</h1>"; exit 0
fi

WPA_SUPP_CONF="/etc/wpa_supplicant/wpa_supplicant.conf"
WPA_SUPP_CLIENT="/etc/wpa_supplicant/wpa_supplicant.client.conf"

sudo bash -c "cat > \"$WPA_SUPP_CLIENT\" <<WPAEOF
country=BE
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid=\"$SSID\"
    psk=\"$PASSWORD\"
}
WPAEOF
cp \"$WPA_SUPP_CLIENT\" \"$WPA_SUPP_CONF\""

echo "<html><body><h1>Connexion à '$SSID'…</h1><p>Le point d’accès va s’éteindre et le Pi va tenter de rejoindre votre réseau. Patientez ~30s.</p></body></html>"

sudo /usr/local/bin/wifi_setup.sh normal >/dev/null 2>&1 || true
EOF
  chmod +x "$DOCROOT/save_wifi.sh"

  echo "== Creating CGI scan_networks.sh =="
  # Check if modern scan_networks.sh exists in same directory as this script
  if [[ -f "$SCRIPT_DIR/scan_networks.sh" ]]; then
    echo "Using modern scan script from $SCRIPT_DIR/scan_networks.sh"
    cp "$SCRIPT_DIR/scan_networks.sh" "$DOCROOT/scan_networks.sh"
  else
    echo "WARN: Modern scan_networks.sh not found, creating basic fallback"
    cat >"$DOCROOT/scan_networks.sh" <<'SCANEOF'
#!/bin/bash
set -euo pipefail
echo "Content-Type: application/json"
echo "Access-Control-Allow-Origin: *"
echo ""
echo '[]'
SCANEOF
  fi
  chmod +x "$DOCROOT/scan_networks.sh"

  echo "== Creating controller /usr/local/bin/wifi_setup.sh =="
  cat >/usr/local/bin/wifi_setup.sh <<'EOF'
#!/bin/bash
set -euo pipefail
LOG_FILE="/var/log/wifi-setup.log"
WPA_SUPP_CONF="/etc/wpa_supplicant/wpa_supplicant.conf"
WPA_SUPP_CLIENT="/etc/wpa_supplicant/wpa_supplicant.client.conf"
AUTO_REVERT_FLAG="/run/wifi_setup_autorevert"
SETUP_LOCK_FLAG="/run/wifi_setup_lock"
AP_IP_CIDR="192.168.4.1/24"
AP_HTTP_PORT=80

log(){ echo "[$(date +'%F %T')] $*" | tee -a "$LOG_FILE" >/dev/null; }

enable_ap_mode(){
  local timeout="${1:-180}"
  log "Activation du mode Setup Wi‑Fi… (auto-revert ${timeout}s)"

  # Scan WiFi networks BEFORE switching to AP mode
  log "Scan des réseaux WiFi disponibles…"
  ip link set wlan0 up 2>/dev/null || true
  sleep 2
  if iw dev wlan0 scan 2>/dev/null > /tmp/wifi_scan_raw.txt; then
    log "Scan WiFi réussi, $(grep -c "^BSS" /tmp/wifi_scan_raw.txt || echo 0) réseaux détectés"
    # Pre-populate cache via scan script
    bash /var/www/html/setup/scan_networks.sh > /tmp/wifi_prescan.json 2>/dev/null || true
  else
    log "AVERTISSEMENT: Scan WiFi échoué, le portail affichera une liste vide"
  fi

  systemctl stop wpa_supplicant || true
  systemctl stop dhcpcd || true
  systemctl stop NetworkManager 2>/dev/null || true

  ip link set wlan0 down || true
  ip addr flush dev wlan0 || true
  ip addr add "$AP_IP_CIDR" dev wlan0
  ip link set wlan0 up

  systemctl restart dnsmasq
  systemctl restart lighttpd
  systemctl restart hostapd

  iptables -t nat -F || true
  iptables -t nat -A PREROUTING -p tcp --dport 80 -j DNAT --to-destination 192.168.4.1:$AP_HTTP_PORT
  iptables -t nat -A POSTROUTING -j MASQUERADE

  sleep 2
  if ! iw dev wlan0 info 2>/dev/null | grep -qi "type AP"; then
    log "ERREUR: wlan0 n'est pas en mode AP"; exit 1
  fi

  # Timer d’auto-revert
  if [[ "$timeout" -gt 0 ]]; then
    ( sleep "$timeout"
      if [[ ! -f "$SETUP_LOCK_FLAG" ]]; then
        log "Auto-revert: aucune conf reçue, retour au mode client."
        disable_ap_mode
      else
        log "Auto-revert annulé (conf reçue)."
      fi
      rm -f "$AUTO_REVERT_FLAG" >/dev/null 2>&1 || true
    ) & echo $! > "$AUTO_REVERT_FLAG"
  fi
  log "AP opérationnel. SSID visible: ${AP_SSID:-Setup-RPI}"
}

disable_ap_mode(){
  log "Retour au mode client Wi‑Fi…"
  systemctl stop hostapd || true
  iptables -t nat -F || true

  if [[ -f "$WPA_SUPP_CLIENT" ]]; then
    cp "$WPA_SUPP_CLIENT" "$WPA_SUPP_CONF"
    log "wpa_supplicant.conf restauré."
  else
    log "ATTENTION: $WPA_SUPP_CLIENT introuvable."
  fi

  ip addr flush dev wlan0 || true
  ip link set wlan0 up || true

  systemctl restart wpa_supplicant || true
  systemctl restart dhcpcd || true

  if [[ -f "$AUTO_REVERT_FLAG" ]]; then
    kill "$(cat "$AUTO_REVERT_FLAG")" 2>/dev/null || true
    rm -f "$AUTO_REVERT_FLAG"
    log "Timer auto-revert annulé."
  fi
  rm -f "$SETUP_LOCK_FLAG" 2>/dev/null || true
  log "Mode client rétabli."
}

status(){
  echo "---- iw dev wlan0 info ----"; iw dev wlan0 info || true
  echo "---- iwconfig ----"; iwconfig || true
  echo "---- hostapd ----"; systemctl status hostapd --no-pager -l || true
  echo "---- dnsmasq ----"; systemctl status dnsmasq --no-pager -l || true
  echo "---- lighttpd ----"; systemctl status lighttpd --no-pager -l || true
  echo "---- wpa_supplicant ----"; systemctl status wpa_supplicant --no-pager -l || true
}

usage(){ cat <<USAGE
Usage: sudo wifi_setup.sh {setup [timeout_s]|normal|status|logs}
  setup [timeout]  Lance AP + portail captif, auto-revert après N secondes (défaut 180)
  normal           Reviens en mode client
  status           Affiche l'état
  logs             Affiche les 100 dernières lignes de ${LOG_FILE}
USAGE
}

case "${1:-}" in
  setup) shift || true; enable_ap_mode "${1:-180}";;
  normal) disable_ap_mode;;
  status) status;;
  logs) tail -n 100 "$LOG_FILE" || true;;
  *) usage; exit 1;;
esac
EOF
  chmod +x /usr/local/bin/wifi_setup.sh

  echo "== Validating lighttpd configuration =="
  if ! lighttpd -tt -f "$LIGHTTPD_CONF"; then
    echo "Lighttpd config test failed. Please check $LIGHTTPD_CONF and snippets."; exit 1
  fi
  systemctl restart lighttpd

  echo "== Local HTTP self-test =="
  set +e
  curl -sI http://127.0.0.1/ | head -n1
  set -e
  echo "== Install/repair complete ✅ =="
  echo "Try: sudo wifi_setup.sh setup 180"
}

# ---------- Local tests ----------
selftest(){
  echo "== Self-test: HTTP + lighttpd modules =="
  lighttpd -tt -f "$LIGHTTPD_CONF" || exit 1
  curl -sI http://127.0.0.1/ | head -n1 || true
  echo "== Self-test: dnsmasq config =="
  grep -E 'dhcp-range|dhcp-option|address=/#/' "$DNSMASQ_CONF" || true
}

status_wrap(){ /usr/local/bin/wifi_setup.sh status; }

logs_wrap(){
  echo "---- wifi-setup.log ----"; tail -n 100 "$LOG_FILE" || true
  echo "---- lighttpd access.log ----"; tail -n 80 /var/log/lighttpd/access.log || true
  echo "---- lighttpd error.log ----"; tail -n 80 /var/log/lighttpd/error.log || true
}

# ---------- Entrypoint ----------
cmd="${1:-install}"
case "$cmd" in
  install) install_all ;;
  setup) shift || true; /usr/local/bin/wifi_setup.sh setup "${1:-180}" ;;
  normal) /usr/local/bin/wifi_setup.sh normal ;;
  status) status_wrap ;;
  logs) logs_wrap ;;
  selftest) selftest ;;
  *) echo "Usage: sudo bash portal.sh {install|setup [s]|normal|status|logs|selftest}" ; exit 1 ;;
esac
