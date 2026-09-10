import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('sentinel.local', username='admin', password='12345', timeout=5)

# Test 1: Check if serial port can be opened and written to
test_script = '''
import serial
import json
import base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

# Build the same signed receipt
priv_bytes = base64.urlsafe_b64decode("MXiKDM2sa-TwEaJHHiQKBGvt9LzHR7jmX8oZQx4x7Bo=")
priv_key = Ed25519PrivateKey.from_private_bytes(priv_bytes)

payload = {"decision": "CONTAIN"}
payload_bytes = json.dumps(payload, separators=(",",":")).encode("utf-8")
sig = priv_key.sign(payload_bytes)
sig_b64 = base64.urlsafe_b64encode(sig).decode("utf-8")

receipt = {"payload": payload, "signature": sig_b64}
receipt_str = json.dumps(receipt) + chr(10)

print("Receipt length:", len(receipt_str))
print("Receipt:", receipt_str.strip())

# Try each serial port
for port in ["/dev/serial0", "/dev/ttyS0", "/dev/ttyAMA0"]:
    try:
        s = serial.Serial(port, 115200, timeout=1)
        written = s.write(receipt_str.encode("utf-8"))
        s.flush()
        import time
        time.sleep(0.1)
        s.close()
        print(f"SUCCESS: {port} - wrote {written} bytes")
    except Exception as e:
        print(f"FAILED: {port} - {e}")
'''

stdin, stdout, stderr = client.exec_command(f"python3 -c '{test_script}'")
print("STDOUT:", stdout.read().decode('utf-8', errors='replace'))
print("STDERR:", stderr.read().decode('utf-8', errors='replace'))

client.close()
