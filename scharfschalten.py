import os
import time


os.system("nohup python3 /home/atlantis/gpio_watchdog.py > /home/atlantis/gpio_watchdog3.log 2>&1 &")
os.system("nohup python3 /home/atlantis/nuke_watchdog.py > /home/atlantis/nuke_watchdog3.log 2>&1 &")
os.system("nohup python3 -u /home/atlantis/ordner/lora.py > /home/atlantis/ordner/lora3.log 2>&1 &")
time.sleep(3)
os.system("nohup python3 -u /home/atlantis/ordner/recon_weiche.py > /home/atlantis/ordner/recon_weiche3.log 2>&1 &")
