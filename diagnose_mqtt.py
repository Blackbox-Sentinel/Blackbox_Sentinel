import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('sentinel.local', username='admin', password='12345', timeout=5)

# 1. Check if the pipeline worker thread is alive or crashed
print("=== CHECKING FOR CRASHES ===")
stdin, stdout, stderr = client.exec_command('echo 12345 | sudo -S journalctl -u gui.service --since "2 minutes ago" --no-pager 2>&1')
out = stdout.read().decode('utf-8', errors='replace')
print(out if out.strip() else "(no recent journal entries)")

# 2. Check mqtt debug log for new entries
print("\n=== MQTT DEBUG LOG ===")
stdin, stdout, stderr = client.exec_command('cat /home/admin/mqtt_debug.log')
print(stdout.read().decode('utf-8', errors='replace'))

# 3. Manually send a signed MQTT message and see if ESP32 gets it
print("\n=== SENDING MANUAL MQTT TEST ===")
test_cmd = """python3 -c "
import json, base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
import paho.mqtt.publish as publish

priv_bytes = base64.urlsafe_b64decode('MXiKDM2sa-TwEaJHHiQKBGvt9LzHR7jmX8oZQx4x7Bo=')
priv_key = Ed25519PrivateKey.from_private_bytes(priv_bytes)

payload = {'decision': 'CONTAIN'}
payload_bytes = json.dumps(payload, separators=(',',':')).encode('utf-8')
sig = priv_key.sign(payload_bytes)
sig_b64 = base64.urlsafe_b64encode(sig).decode('utf-8')

receipt = {'payload': payload, 'signature': sig_b64}
msg = json.dumps(receipt)
print('Sending:', msg)
print('Payload length:', len(msg))
publish.single('sentinel/c2_attack', msg, hostname='localhost')
print('MQTT publish done!')
"
"""
stdin, stdout, stderr = client.exec_command(test_cmd)
print("STDOUT:", stdout.read().decode('utf-8', errors='replace'))
print("STDERR:", stderr.read().decode('utf-8', errors='replace'))

client.close()
