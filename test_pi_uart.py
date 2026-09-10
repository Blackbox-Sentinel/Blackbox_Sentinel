import paramiko
import io

code = """
import serial
import json
import base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
import time

try:
    priv_bytes = base64.urlsafe_b64decode("MXiKDM2sa-TwEaJHHiQKBGvt9LzHR7jmX8oZQx4x7Bo=")
    priv_key = Ed25519PrivateKey.from_private_bytes(priv_bytes)
    pub_bytes = priv_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    
    payload = {
        "algorithm": "Ed25519",
        "controller_id": "sim-controller",
        "decision": "CONTAIN",
        "incident_id": f"AEDN-NODE-01:{int(time.time())}",
        "receipt_sequence": 1,
        "receipt_version": 1
    }
    
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    sig = priv_key.sign(canonical_json)
    sig_b64 = base64.urlsafe_b64encode(sig).decode("ascii").rstrip("=")
    pub_b64 = base64.urlsafe_b64encode(pub_bytes).decode("ascii").rstrip("=")
    
    receipt = {"payload": payload, "signature": sig_b64, "public_key": pub_b64}
    receipt_str = json.dumps(receipt) + "\\n"
    print("Generated receipt:")
    print(receipt_str)
    
    success = False
    for p in ['/dev/serial0', '/dev/ttyS0', '/dev/ttyAMA0', '/dev/ttyUSB0']:
        try:
            with serial.Serial(p, 115200, timeout=1) as ser:
                ser.write(receipt_str.encode("utf-8"))
                print(f"Successfully wrote to {p}")
                success = True
        except Exception as e:
            pass
    if not success:
        print("Failed to write to ANY port!")
except Exception as e:
    import traceback
    traceback.print_exc()
"""

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect('sentinel.local', username='admin', password='12345', timeout=5)
    
    sftp = client.open_sftp()
    sftp.putfo(io.BytesIO(code.encode('utf-8')), '/home/admin/test_uart.py')
    sftp.close()
    
    stdin, stdout, stderr = client.exec_command("python3 /home/admin/test_uart.py")
    print("STDOUT:", stdout.read().decode())
    print("STDERR:", stderr.read().decode())
    client.close()
except Exception as e:
    print(e)
