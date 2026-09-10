import os

drive = "D:\\"

wpa = """ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=IN

network={
    ssid="Prajwal"
    psk="15415404"
}
"""

try:
    with open(os.path.join(drive, 'wpa_supplicant.conf'), 'w', newline='\n') as f:
        f.write(wpa)
        
    with open(os.path.join(drive, 'ssh'), 'w') as f:
        f.write("")
        
    print("[+] Wi-Fi and SSH injected successfully into D:\\")
except Exception as e:
    print(f"[-] Error: {e}")
