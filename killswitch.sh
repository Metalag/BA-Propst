#!/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

echo "Vernichtung gestartet"


pkill -f lora.py
pkill -f recon_weiche.py

sudo umount /home/atlantis/ordner
sudo cryptsetup close holla_decrypted

sudo cryptsetup erase /home/atlantis/Holla
sudo rm -f /home/atlantis/Holla

sudo rm -f /home/atlantis/*.py

sudo poweroff -f
