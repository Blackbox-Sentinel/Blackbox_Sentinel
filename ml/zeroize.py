import os
import time
from ledger import Ledger

SECRETS = {
    "API_KEY": "sk-live-abc123",
    "DB_PASSWORD": "supersecret",
    "SESSION_TOKEN": "token_xyz789",
    "ENCRYPTION_KEY": "aes256-key-here"
}

class Zeroizer:
    def __init__(self):
        self.ledger = Ledger()
        self.store = SECRETS.copy()
        self._original = SECRETS.copy()

    def zeroize_all(self, reason="ATTACK_DETECTED"):
        for key in self.store:
            length = len(self.store[key])
            self.store[key] = os.urandom(length).hex()[:length]
            print(f"[ZEROIZE] {key} overwritten")
        self.ledger.append_entry("ZEROIZATION", {
            "reason": reason, "timestamp": time.time(),
            "secrets_zeroized": list(SECRETS.keys())
        })
        print(f"[ZEROIZE] Logged. Reason: {reason}")

    def is_zeroized(self):
        return any(self.store[k] != self._original[k] for k in self._original)