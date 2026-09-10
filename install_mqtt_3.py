import paramiko
import io

patch = """import sys
with open('/home/admin/blackbox-sentinel/m4-gui-venture/src/app.py', 'r') as f:
    code = f.read()

import re
# Regex to match the entire for p in [...] block
pattern = re.compile(r"for p in \['/dev/serial0'.*?except Exception:[ \t\n]*pass\n", re.DOTALL)

replacement = '''for p in ['/dev/serial0', '/dev/ttyS0', '/dev/ttyAMA0', '/dev/ttyUSB0']:
            try:
                with serial.Serial(p, 115200, timeout=1) as ser:
                    ser.write(receipt_str.encode("utf-8"))
                    ser.flush()
                    import time as pytime
                    pytime.sleep(0.1)
            except Exception:
                pass
                
        # --- MQTT BACKUP PIPELINE ---
        try:
            import paho.mqtt.publish as publish
            publish.single("sentinel/c2_attack", receipt_str, hostname="localhost")
        except Exception as e:
            pass
'''

if "sentinel/c2_attack" not in code:
    code = pattern.sub(replacement, code)
    with open('/home/admin/blackbox-sentinel/m4-gui-venture/src/app.py', 'w') as f:
        f.write(code)
    print("Patched successfully!")
else:
    print("Already patched!")
"""

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect('sentinel.local', username='admin', password='12345', timeout=5)
    
    sftp = client.open_sftp()
    sftp.putfo(io.BytesIO(patch.encode('utf-8')), '/home/admin/patch_mqtt.py')
    sftp.close()
    
    stdin, stdout, stderr = client.exec_command('python3 /home/admin/patch_mqtt.py && echo 12345 | sudo -S systemctl restart gui.service')
    print('STDOUT:', stdout.read().decode())
    print('STDERR:', stderr.read().decode())
    client.close()
except Exception as e:
    print(e)
