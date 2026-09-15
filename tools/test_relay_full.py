#!/usr/bin/env python3
"""
BlackBox Sentinel - Full Stack Relay Test
Sends a signed Ed25519 containment receipt to the ESP32 over UART5 (/dev/ttyAMA5)
and verifies it triggers the relay (watch Heltec OLED for '!! ISOLATED !!')

Run on Pi: python3 /tmp/test_relay_full.py
"""
import sys
import json
import time
import os

# Make sure we can import the HAL
sys.path.insert(0, '/home/sentinel/Blackbox_Sentinel')

print("=== BlackBox Sentinel Full Relay Test ===\n")

# Step 1: Open UART5 directly
print("1. Testing direct UART5 send to ESP32...")
try:
    import serial
    ser = serial.Serial('/dev/ttyAMA5', 115200, timeout=2)
    print(f"   ✅ /dev/ttyAMA5 opened OK")
except Exception as e:
    print(f"   ❌ Cannot open /dev/ttyAMA5: {e}")
    sys.exit(1)

# Step 2: Try to use the ContainmentReceiptService to generate a real signed receipt
print("\n2. Generating Ed25519-signed containment receipt...")
receipt = None
try:
    from m1_hardware.src.relay_controller import RelayController  # legacy import test
except Exception:
    pass

try:
    sys.path.insert(0, '/home/sentinel/Blackbox_Sentinel/m3-ml-ledger/src')
    from m3_security_contracts import ContainmentReceiptService, Ed25519ReceiptSigner, SoftwareMonotonicCounter, EvidenceDecision
    from ledger import HashChainLedger
    import base64

    priv_key_b64 = os.environ.get("SENTINEL_ED25519_KEY")
    if priv_key_b64:
        signer = Ed25519ReceiptSigner.from_private_bytes(base64.urlsafe_b64decode(priv_key_b64))
    else:
        signer = Ed25519ReceiptSigner()
        
    counter = SoftwareMonotonicCounter("/tmp/test_counter.txt")
    ledger = HashChainLedger("/tmp/test_ledger.json")
    svc = ContainmentReceiptService(ledger, counter, signer, "Pi4-HW-Test")
    
    decision = EvidenceDecision(
        incident_id="TEST-RELAY-001",
        approved=True,
        reason="Manual test trigger",
        accepted_signals=(),
        evidence_digest="00" * 32
    )

    receipt = svc.issue(
        decision=decision,
        organization_id="sentinel",
        key_epoch=1,
        quorum={"state": "APPROVED", "peers": []}
    )
    print(f"   ✅ Receipt generated (sig={receipt.get('signature', '')[:16]}...)")
except Exception as e:
    print(f"   ⚠️  ContainmentReceiptService not available ({e})")
    print("   Using minimal test receipt (ESP32 will reject sig but OLED shows activity)...")
    receipt = {
        "signature": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        "payload": {
            "algorithm": "ed25519",
            "controller_id": "pi4-test",
            "decision": "CONTAIN",
            "event_hash": "deadbeef" * 8,
            "evidence_digest": "00" * 32,
            "incident_id": "TEST-001",
            "key_epoch": 1,
            "organization_id": "sentinel",
            "quorum": {"state": "APPROVED", "peers": []},
            "receipt_sequence": 1,
            "receipt_version": 1,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    }

# Step 3: Send the receipt
print("\n3. Sending receipt to ESP32 over UART5...")
print("   👀 WATCH THE HELTEC OLED — it should show 'JSON RX' then 'Verifying...'")
print("      If signature is valid: '!! ISOLATED !!'")
print("      If signature is invalid: 'REJECTED SIG'")
print("      Either response confirms the UART5 wire is working!\n")

payload = json.dumps(receipt, separators=(',', ':')) + "\n"
print(f"   Sending {len(payload)} bytes...")
ser.write(payload.encode('utf-8'))
ser.flush()
print("   ✅ Sent!\n")

# Step 4: Wait a moment and check if OLED would have changed
print("4. Waiting 3 seconds for ESP32 to process...")
time.sleep(3)
print("   Did the OLED change from 'SYSTEM ARMED / Monitoring...'?")
print("   - If YES -> UART5 link is working! ✅")
print("   - If NO  -> TX/RX wires may still be swapped, check wiring")

ser.close()
print("\n=== Test complete ===")
