import os
import string
import urllib.request
import sys

print("[*] Searching for Raspberry Pi SD card...")

def get_pi_drive():
    available_drives = ['%s:\\' % d for d in string.ascii_uppercase if os.path.exists('%s:\\' % d)]
    for drive in available_drives:
        if os.path.exists(os.path.join(drive, 'issue.txt')) or os.path.exists(os.path.join(drive, 'kernel.img')) or os.path.exists(os.path.join(drive, 'config.txt')):
            return drive
    return None

drive = get_pi_drive()

if not drive:
    print("[-] Could not find the Raspberry Pi SD card. Please plug it into the laptop!")
    sys.exit(1)
    
print(f"[+] Found SD card at {drive}")

# 1. Download the GoodTFT tft35a driver directly from their repo
driver_url = "https://raw.githubusercontent.com/goodtft/LCD-show/master/usr/tft35a-overlay.dtb"
target_driver_path = os.path.join(drive, "overlays", "tft35a.dtbo")

print(f"[*] Downloading tft35a driver to {target_driver_path}...")
try:
    if not os.path.exists(os.path.join(drive, "overlays")):
        os.makedirs(os.path.join(drive, "overlays"))
    urllib.request.urlretrieve(driver_url, target_driver_path)
    print("[+] Driver downloaded successfully.")
except Exception as e:
    print(f"[-] Failed to download driver: {e}")
    sys.exit(1)

# 2. Modify config.txt to load the driver
config_path = os.path.join(drive, "config.txt")
try:
    with open(config_path, "r") as f:
        config_data = f.read()
        
    if "tft35a" not in config_data:
        print("[*] Injecting driver activation into config.txt...")
        with open(config_path, "a") as f:
            f.write("\n# GoodTFT LCD-show offline injection\n")
            f.write("dtparam=spi=on\n")
            f.write("dtoverlay=tft35a:rotate=90\n")
        print("[+] config.txt patched.")
    else:
        print("[*] config.txt is already patched.")
except Exception as e:
    print(f"[-] Failed to patch config.txt: {e}")

# 3. Modify cmdline.txt to route terminal text to the screen
cmdline_path = os.path.join(drive, "cmdline.txt")
try:
    with open(cmdline_path, "r") as f:
        cmdline_data = f.read().strip()
        
    if "fbcon=map:10" not in cmdline_data:
        print("[*] Routing terminal video output to SPI screen in cmdline.txt...")
        new_cmdline = cmdline_data + " fbcon=map:10"
        with open(cmdline_path, "w") as f:
            f.write(new_cmdline)
        print("[+] cmdline.txt patched.")
    else:
        print("[*] cmdline.txt is already patched.")
except Exception as e:
    print(f"[-] Failed to patch cmdline.txt: {e}")

print("\n[+] SUCCESS! The 3.5-inch screen drivers are now permanently baked into the SD card.")
print("[+] You can safely eject the SD card, put it in the Raspberry Pi, and turn it on. No Wi-Fi required!")
