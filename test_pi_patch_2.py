import paramiko
import io

patch = """import sys
with open('/home/admin/blackbox-sentinel/m4-gui-venture/src/app.py', 'r') as f:
    code = f.read()

bad_str = '''ser.write(receipt_str.encode("utf-8"))
                    ser.flush()
                    import time
                    time.sleep(0.1)'''

good_str = '''ser.write(receipt_str.encode("utf-8"))
                    ser.flush()
                    time.sleep(0.1)'''

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
    sftp.putfo(io.BytesIO(patch.encode('utf-8')), '/home/admin/patch_app2.py')
    sftp.close()
    
    stdin, stdout, stderr = client.exec_command('python3 /home/admin/patch_app2.py && echo 12345 | sudo -S systemctl restart gui.service')
    print('STDOUT:', stdout.read().decode())
    print('STDERR:', stderr.read().decode())
    client.close()
except Exception as e:
    print(e)
