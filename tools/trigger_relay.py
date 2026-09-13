#!/usr/bin/env python3
"""
BlackBox Sentinel - Definitive Relay Trigger Test
Uses the EXACT same signing chain as app_web.py to generate a real Ed25519 receipt.
This WILL trigger the physical relay if the ESP32 has the matching public key.

Run on Pi:
  cd /home/sentinel/Blackbox_Sentinel
  python3 /tmp/trigger_relay.py
"""
import sys
import os
import serial
import time
import json
import base64

# Mirror app_web.py path setup
PROJECT_ROOT = '/home/sentinel/Blackbox_Sentinel'
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'm3-ml-ledger', 'src'))

PORT = '/dev/ttyAMA5'
BAUD = 115200

print("=== BlackBox Sentinel Relay Trigger (Real Ed25519) ===\n")

s = serial.Serial(PORT, BAUD, timeout=3)
time.sleep(0.5)

# 1. Confirm UART link
print("1. UART5 link check...")
s.write(b'PING\n')
s.flush()
time.sleep(1)
resp = s.read(s.in_waiting).decode('utf-8', errors='replace').strip()
if 'pong' not in resp:
    print(f"   ❌ No pong: {resp!r}")
    s.close()
    sys.exit(1)
print(f"   ✅ {resp[:80]}")

# 2. Build signing stack exactly like app_web.py
print("\n2. Building signing stack (mirrors app_web.py)...")
try:
    from m3_security_contracts import (
        ContainmentReceiptService, Ed25519ReceiptSigner,
        SoftwareMonotonicCounter, EvidenceSignal
    )
    from m3_ledger import HashChainLedger
    
    # Same counter path as app_web.py
    counter_path = os.path.join(PROJECT_ROOT, 'm3-ml-ledger', 'data', 'receipt_counter.txt')
    os.makedirs(os.path.dirname(counter_path), exist_ok=True)
    
    # Same signer logic as app_web.py
    priv_key_b64 = os.environ.get("SENTINEL_ED25519_KEY")
    if priv_key_b64:
        signer = Ed25519ReceiptSigner.from_private_bytes(base64.urlsafe_b64decode(priv_key_b64))
        print("   Using SENTINEL_ED25519_KEY from environment")
    else:
        signer = Ed25519ReceiptSigner()
        print("   Using freshly generated key (ESP32 public key won't match -> REJECTED SIG expected)")
        print("   To trigger relay for real, set SENTINEL_ED25519_KEY to the matching private key")

    ledger_path = os.path.join(PROJECT_ROOT, 'm3-ml-ledger', 'data', 'relay_test_ledger.json')
    ledger = HashChainLedger(ledger_path)
    counter = SoftwareMonotonicCounter(counter_path)
    receipt_svc = ContainmentReceiptService(ledger, counter, signer, "Pi4-HW-Relay-Test")
    
    signal = EvidenceSignal(
        signal_type="manual_relay_trigger",
        threat_score=-0.999,
        source="trigger_relay_script",
        raw_packet={"manual": True, "test": True}
    )
    receipt = receipt_svc.issue(signal, decision="CONTAIN")
    sig_preview = receipt.get('signature', '')[:20]
    print(f"   ✅ Receipt signed (sig={sig_preview}...)")

except Exception as e:
    print(f"   ⚠️  Signing stack failed: {e}")
    print("   Using correctly-sized fake sig (64 bytes = will show REJECTED SIG on OLED)")
    fake_sig = base64.urlsafe_b64encode(b'\xDE\xAD' * 32).decode('ascii').rstrip('=')
    receipt = {
        "signature": fake_sig,
        "payload": {
            "algorithm": "ed25519",
            "controller_id": "pi4-test",
            "decision": "CONTAIN",
            "event_hash": "ab" * 32,
            "evidence_digest": "cd" * 32,
            "incident_id": "RELAY-TEST-001",
            "key_epoch": 1,
            "organization_id": "sentinel",
            "quorum": 1,
            "receipt_sequence": 1,
            "receipt_version": "1.0",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    }

# 3. Send
print("\n3. Sending to ESP32...")
print("   👀 WATCH OLED: JSON RX -> Verifying -> result")
print("   👂 LISTEN for relay CLICK (if key matches)\n")

payload_bytes = (json.dumps(receipt, separators=(',', ':')) + '\n').encode('utf-8')
print(f"   {len(payload_bytes)} bytes -> /dev/ttyAMA5")
s.write(payload_bytes)
s.flush()

# 4. Read responses
print("\n4. ESP32 responses:")
buf = ''
end = time.time() + 8
while time.time() < end:
    if s.in_waiting:
        buf += s.read(s.in_waiting).decode('utf-8', errors='replace')
        lines = buf.split('\n')
        buf = lines[-1]
        for line in lines[:-1]:
            line = line.strip()
            if line:
                data = {}
                try:
                    data = json.loads(line)
                except Exception:
                    pass
                evt = data.get('event', '')
                if evt == 'relay_isolated':
                    print(f"   🚨 RELAY TRIGGERED: {line}")
                elif evt == 'sig_invalid':
                    print(f"   ❌ Sig rejected ({data.get('reason','?')}) — key mismatch, check SENTINEL_ED25519_KEY")
                elif evt == 'sig_valid':
                    print(f"   ✅ Signature VALID -> {data.get('action','?')}")
                elif evt == 'receipt_received':
                    print(f"   📥 ESP32 received {data.get('len','?')} bytes")
                else:
                    print(f"   {line}")
    time.sleep(0.05)

print("\n=== Done ===")
print()
print("KEY TAKEAWAY:")
print("  If 'sig_invalid' -> run: sudo systemctl show sentinel | grep SENTINEL_ED25519_KEY")
print("  Or check /etc/systemd/system/sentinel.service for the private key env var")
s.close()
