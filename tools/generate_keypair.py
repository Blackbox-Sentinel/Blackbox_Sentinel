#!/usr/bin/env python3
"""Generate a new Ed25519 keypair for the Sentinel system."""
import sys
sys.path.insert(0, '/home/sentinel/Blackbox_Sentinel/m3-ml-ledger/src')

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption
import base64

# Generate new keypair
priv = Ed25519PrivateKey.generate()
priv_bytes = priv.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
pub_bytes = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)

priv_b64 = base64.urlsafe_b64encode(priv_bytes).decode().rstrip('=')
pub_b64 = base64.urlsafe_b64encode(pub_bytes).decode().rstrip('=')

print("=" * 60)
print("NEW Ed25519 KEYPAIR FOR BLACKBOX SENTINEL")
print("=" * 60)
print()
print("PRIVATE KEY (for systemd service env var):")
print(f"  SENTINEL_ED25519_KEY={priv_b64}")
print()
print("PUBLIC KEY (for ESP32 firmware):")
print(f"  Base64Url: {pub_b64}")
print()
print("Paste this into blackbox_sentinel.ino:")
print(f"// Base64Url: {pub_b64}")
print("const uint8_t TRUSTED_PUB_KEY[32] = {")
hex_vals = ", ".join(hex(b) for b in pub_bytes)
print(f"    {hex_vals}")
print("};")
print()
print("=" * 60)
print("SAVE THE PRIVATE KEY ABOVE - IT CANNOT BE RECOVERED!")
print("=" * 60)
