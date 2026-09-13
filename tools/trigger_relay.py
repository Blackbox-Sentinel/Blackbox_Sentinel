#!/usr/bin/env python3
"""
BlackBox Sentinel - Minimal Relay Trigger
Uses Ed25519ReceiptSigner directly with the SENTINEL_ED25519_KEY private key.
No ledger dependency needed.

Run on Pi:
  cd /home/sentinel/Blackbox_Sentinel
  SENTINEL_ED25519_KEY=pTzAdlRSVMXTi2PNIXM1BiONgTEHAxyea2wxPEoR-0Q python3 /tmp/trigger_relay.py
"""
import sys
import os
import serial
import time
import json
import base64

sys.path.insert(0, '/home/sentinel/Blackbox_Sentinel')
sys.path.insert(0, '/home/sentinel/Blackbox_Sentinel/m3-ml-ledger/src')

PORT = '/dev/ttyAMA5'
BAUD = 115200

print("=== BlackBox Sentinel Relay Trigger ===\n")

s = serial.Serial(PORT, BAUD, timeout=3)
time.sleep(0.5)

# 1. Confirm UART link
print("1. UART link check...")
s.write(b'PING\n')
s.flush()
time.sleep(1)
resp = s.read(s.in_waiting).decode('utf-8', errors='replace').strip()
if 'pong' not in resp:
    print(f"   ❌ No pong. Check wiring.")
    s.close()
    sys.exit(1)
print(f"   ✅ {resp[:80]}")

# 2. Build a signed receipt using SENTINEL_ED25519_KEY
print("\n2. Signing containment receipt...")

priv_key_b64 = os.environ.get("SENTINEL_ED25519_KEY")
if not priv_key_b64:
    print("   ❌ SENTINEL_ED25519_KEY not set!")
    print("   Run: SENTINEL_ED25519_KEY=pTzAdlRSVMXTi2PNIXM1BiONgTEHAxyea2wxPEoR-0Q python3 /tmp/trigger_relay.py")
    s.close()
    sys.exit(1)

try:
    from m3_security_contracts import Ed25519ReceiptSigner
    
    # Add padding if needed for urlsafe base64
    padded = priv_key_b64 + '=' * (4 - len(priv_key_b64) % 4)
    priv_bytes = base64.urlsafe_b64decode(padded)
    signer = Ed25519ReceiptSigner.from_private_bytes(priv_bytes)
    
    # Build the payload (sorted keys = canonical JSON for Ed25519)
    payload = {
        "algorithm": "ed25519",
        "controller_id": "Pi4-HW-Relay-Test",
        "decision": "CONTAIN",
        "event_hash": "ab" * 32,
        "evidence_digest": "cd" * 32,
        "incident_id": "RELAY-LIVE-TEST-001",
        "key_epoch": 1,
        "organization_id": "sentinel",
        "quorum": 1,
        "receipt_sequence": 1,
        "receipt_version": "1.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    
    # Sign it
    signature = signer.sign(payload)
    receipt = {"signature": signature, "payload": payload}
    print(f"   ✅ Signed! sig={signature[:20]}...")
    
except Exception as e:
    print(f"   ❌ Signing failed: {e}")
    s.close()
    sys.exit(1)

# 3. Send
print("\n3. Sending receipt to ESP32...")
print("   👀 WATCH OLED -> 'JSON RX' -> 'Verifying' -> '!! ISOLATED !!'")
print("   👂 LISTEN for relay CLICK!\n")

payload_bytes = (json.dumps(receipt, separators=(',', ':')) + '\n').encode('utf-8')
print(f"   Sending {len(payload_bytes)} bytes...")
s.write(payload_bytes)
s.flush()

# 4. Read response
print("\n4. ESP32 responses:")
buf = ''
end = time.time() + 8
relay_fired = False
while time.time() < end:
    if s.in_waiting:
        buf += s.read(s.in_waiting).decode('utf-8', errors='replace')
        lines = buf.split('\n')
        buf = lines[-1]
        for line in lines[:-1]:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                evt = data.get('event', '')
                if evt == 'relay_isolated':
                    print(f"   🚨 RELAY FIRED! Reason: {data.get('reason')}")
                    relay_fired = True
                elif evt == 'sig_valid':
                    print(f"   ✅ SIGNATURE VALID -> {data.get('action')}")
                elif evt == 'sig_invalid':
                    print(f"   ❌ Sig invalid ({data.get('reason')}) — key mismatch")
                elif evt == 'receipt_received':
                    print(f"   📥 ESP32 received {data.get('len')} bytes")
                elif evt == 'sms_dispatched':
                    print(f"   📱 SMS sent to {data.get('phone')}")
                elif evt == 'heartbeat':
                    iso = data.get('isolated', False)
                    print(f"   💓 heartbeat | isolated={iso} | tamper={data.get('tamper')}")
                else:
                    print(f"   {line}")
            except Exception:
                print(f"   {line}")
    time.sleep(0.05)

print()
if relay_fired:
    print("✅✅✅ RELAY SUCCESSFULLY TRIGGERED! ✅✅✅")
    print("   The physical network is now AIR-GAPPED.")
    print("   Press the PRG button on Heltec to restore.")
else:
    print("❌ Relay did not fire. Check the OLED for what happened.")

s.close()
