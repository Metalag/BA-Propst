#!/usr/bin/env python3
import subprocess
from gpiozero import Button
from signal import pause

KILLSWITCH_PATH = "/home/atlantis/killswitch.sh"
GPIO_PIN = 21

def nuke_system():
    print("\n Draht gerissen")
    subprocess.run(["sudo", KILLSWITCH_PATH])

def main():
    print(f"gpio aktiv")

    # pull_up=True aktiviert den internen Widerstand des Pi.
    # Solange der Draht zu GND verbunden ist, gilt der "Knopf" als gedrückt (pressed).
    draht = Button(GPIO_PIN, pull_up=True)

    if draht.is_pressed:
        print("Draht erkannt")
    else:
        print("Draht offen")

    draht.when_released = nuke_system

    try:
        pause()
    except KeyboardInterrupt:
        pass
if __name__ == "__main__":
    main()
