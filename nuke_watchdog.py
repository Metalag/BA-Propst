#!/usr/bin/env python3
import subprocess


KILLSWITCH_PATH = "/home/atlantis/killswitch.sh"

def nuke_system():
    print("\nStarte Nuke")
    subprocess.run(["sudo", KILLSWITCH_PATH])

def main():
    print("ssh aktiv")

    # journalctl liest die System-Logs.
    # -u ssh: Filtert nach dem SSH-Dienst
    # -f: "Follow" – wartet live auf neue Einträge (wie tail -f)
    # -n 0: Ignoriert alte Einträge im Log, damit das Skript nicht wegen gestriger Fehler auslöst
    cmd = ["journalctl", "-u", "ssh", "-f", "-n", "0"]

    try:
        prozess = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)

        for zeile in prozess.stdout:
            if "Failed password" in zeile:
                nuke_system()
                break

    except KeyboardInterrupt:
        pass
if __name__ == "__main__":
    main()
