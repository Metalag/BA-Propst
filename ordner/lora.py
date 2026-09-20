#!/usr/bin/env python3
import meshtastic
import meshtastic.serial_interface
from pubsub import pub
import os
import glob
import time
import shutil
import random
import subprocess


TARGET_NODE = "!49b6d470"  # (Lapi-D)
LOKALE_ID = "!49b61d3c"    # Pi ID
OUTBOX_DIR = "/home/atlantis/ordner/outbox/psk"
MAX_CHUNK_SIZE = 170
PAUSE_ZWISCHEN_CHUNKS = 90
TIMEOUT_SEKUNDEN = 300
KILLSWITCH_PATH = "/home/atlantis/killswitch.sh"

aktuelle_datei_name = ""
aktuelle_session_id = ""
aktuelle_datei_gesendet_um = 0

def notfall_loeschung():
    print("\n ABBRUCH empfangen, starte kill switch")
    subprocess.run(["sudo", KILLSWITCH_PATH])

def on_receive(packet, interface):
    global aktuelle_datei_name, aktuelle_session_id, aktuelle_datei_gesendet_um
    
    from_id = packet.get('fromId', 'Unbekannt')
    if from_id == LOKALE_ID:
        return

    decoded = packet.get('decoded', {})
    if decoded.get('portnum') == 'TEXT_MESSAGE_APP':
        befehl = decoded.get('text', '').strip()
        
        if befehl == "ABBRUCH":
            notfall_loeschung()
            
        elif befehl.startswith("ACK:"):
            empfangenes_ack = befehl.split(":", 1)[1]
            print(f"\n Laptop bestätigt Session: {empfangenes_ack}")
            
            if empfangenes_ack == aktuelle_session_id:
                dateipfad = os.path.join(OUTBOX_DIR, aktuelle_datei_name)
                if os.path.exists(dateipfad):
                    # Löschen nach erfolgreichem Versand
                    os.remove(dateipfad)
                    print(f" Datei '{aktuelle_datei_name}' erfolgreich gelöscht.")
                
                #  zurücksetzen für die nächste Datei
                aktuelle_datei_name = ""
                aktuelle_session_id = ""
                aktuelle_datei_gesendet_um = 0

def sende_outbox(interface):
    global aktuelle_datei_name, aktuelle_session_id, aktuelle_datei_gesendet_um
    
    if aktuelle_session_id != "":
        vergangene_zeit = time.time() - aktuelle_datei_gesendet_um
        if vergangene_zeit < TIMEOUT_SEKUNDEN:
            return
        else:
            print(f"\n Kein ACK für Session {aktuelle_session_id}. Starte Wiederholung...")
            aktuelle_session_id = ""
            aktuelle_datei_name = ""

    suchmuster_hc = glob.glob(os.path.join(OUTBOX_DIR, "*.hc22000"))
    suchmuster_txt = glob.glob(os.path.join(OUTBOX_DIR, "*.txt"))
    dateien = suchmuster_hc + suchmuster_txt
    
    if not dateien:
        return
        
    zieldatei = dateien[0]
    aktuelle_datei_name = os.path.basename(zieldatei)
    aktuelle_session_id = str(random.randint(1000, 9999))
    
    with open(zieldatei, "r") as f:
        payload = f.read().strip()
        
    chunks = [payload[i:i + MAX_CHUNK_SIZE] for i in range(0, len(payload), MAX_CHUNK_SIZE)]
    total_chunks = len(chunks)
    
    print(f"\n {aktuelle_datei_name} | Session-ID: {aktuelle_session_id} | {total_chunks} Pakete")

    for idx, chunk in enumerate(chunks):
        chunk_nr = idx + 1
        formatted_packet = f"seq {aktuelle_session_id}:{chunk_nr}/{total_chunks}:{chunk}"
        
        print(f" Sende Paket {chunk_nr}/{total_chunks} ({len(formatted_packet)} Bytes)...")
        interface.sendText(formatted_packet, destinationId=TARGET_NODE, wantAck=False)
        
        if idx < len(chunks) - 1:
            time.sleep(PAUSE_ZWISCHEN_CHUNKS)
            
    time.sleep(15)
    
    aktuelle_datei_gesendet_um = time.time()
    print(f" Senden abgeschlossen. Lausche auf ACK für Session {aktuelle_session_id}...")

def main():
    print("LoRa gestartet")
    try:
        interface = meshtastic.serial_interface.SerialInterface()
        time.sleep(5)
    except Exception as e:
        print(f"[!] Fehler: {e}")
        return

    pub.subscribe(on_receive, "meshtastic.receive")
    print("Empfänger aktiv.")

    try:
        while True:
            sende_outbox(interface)
            time.sleep(5)
    except KeyboardInterrupt:
        interface.close()

if __name__ == "__main__":
    main()
