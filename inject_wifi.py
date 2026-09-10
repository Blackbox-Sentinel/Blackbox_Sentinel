import os
import string

def get_pi_drive():
    available_drives = ['%s:\\' % d for d in string.ascii_uppercase if os.path.exists('%s:\\' % d)]
    for drive in available_drives:
        if os.path.exists(os.path.join(drive, 'issue.txt')) or os.path.exists(os.path.join(drive, 'kernel.img')):
            return drive
    return None

drive = get_pi_drive()

if not drive:
    print("[-] Could not find the Raspberry Pi SD card. Is it plugged in?")
else:
    print(f"[*] Found Raspberry Pi SD card at {drive}")
    
    # 1. Enable SSH
    with open(os.path.join(drive, 'ssh'), 'w') as f:
        f.write("")
        
    # 2. Force Wi-Fi Configuration
    wpa = """ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=IN

network={
    ssid="Prajwal"
    psk="15415404"
}
"""
    with open(os.path.join(drive, 'wpa_supplicant.conf'), 'w', newline='\n') as f:
        f.write(wpa)
        
    print("[+] Successfully injected Wi-Fi and SSH configurations directly into the SD card!")
