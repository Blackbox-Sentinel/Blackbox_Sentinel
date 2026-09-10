import paramiko
import io

patch = """import sys
with open('/home/admin/blackbox-sentinel/m4-gui-venture/src/app.py', 'r') as f:
    code = f.read()

bad_str = '''ser.write(receipt_str.encode("utf-8"))
                    ser.flush()
                    time.sleep(0.1)'''

good_str = '''ser.write(receipt_str.encode("utf-8"))
                    ser.flush()
                    time.sleep(0.1)
                except Exception as e:
                    self.logger.error(f"UART send failed: {e}")
                    
                # NEW MQTT PUBLISH
                try:
                    import paho.mqtt.publish as publish
                    publish.single("sentinel/c2_attack", receipt_str, hostname="localhost")
                    self.logger.info("Forwarded Anomaly Receipt via MQTT")
                except Exception as e:
                    self.logger.error(f"Failed to forward via MQTT: {e}")
                
                # Dummy block to balance the try-except if needed
                try:'''

if bad_str in code:
    code = code.replace(bad_str, good_str)
    with open('/home/admin/blackbox-sentinel/m4-gui-venture/src/app.py', 'w') as f:
        f.write(code)
    print("Patched successfully!")
else:
    print("Bad string not found!")
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
