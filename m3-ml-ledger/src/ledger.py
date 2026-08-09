"""
BlackBox Sentinel — M3 ML: Hash-Chained Ledger
Tamper-proof logging system using SHA-256 hash chains.

Author: M3 ML Engineer
Branch: m3-dev
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Optional


class HashChainLedger:
    """
    Append-only, tamper-proof log using SHA-256 hash chaining.
    Each entry contains a hash of the previous entry, making
    any modification to historical records detectable.
    """
    
    def __init__(self, ledger_path: str = "ledger.json"):
        self.ledger_path = ledger_path
        self.chain: list[dict] = []
        
        if os.path.exists(ledger_path):
            self._load()
    
    def _compute_hash(self, data: str) -> str:
        """Compute SHA-256 hash of input string."""
        return hashlib.sha256(data.encode("utf-8")).hexdigest()
    
    def _get_previous_hash(self) -> str:
        """Get hash of the last entry, or genesis hash."""
        if not self.chain:
            return self._compute_hash("GENESIS_BLOCK_BLACKBOX_SENTINEL")
        return self.chain[-1]["hash"]
    
    def add_entry(self, event_type: str, data: dict, anomaly_score: Optional[float] = None):
        """
        Add a new entry to the hash chain.
        
        Args:
            event_type: Type of event (e.g., "anomaly", "capture", "alert")
            data: Event data dictionary
            anomaly_score: ML model anomaly score (-1 = anomaly, 1 = normal)
        """
        entry = {
            "index": len(self.chain),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "previous_hash": self._get_previous_hash(),
            "event_type": event_type,
            "data": data,
            "anomaly_score": anomaly_score,
        }
        
        # Hash the entry content (excluding the hash field itself)
        entry_string = json.dumps(entry, sort_keys=True)
        entry["hash"] = self._compute_hash(entry_string)
        
        self.chain.append(entry)
        self._save()
        
        return entry
    
    def verify_chain(self) -> tuple[bool, Optional[int]]:
        """
        Verify the integrity of the entire hash chain.
        
        Returns:
            (is_valid, broken_index) — True if chain is intact,
            or False with the index where tampering was detected.
        """
        for i, entry in enumerate(self.chain):
            # Verify previous hash link
            if i == 0:
                expected_prev = self._compute_hash("GENESIS_BLOCK_BLACKBOX_SENTINEL")
            else:
                expected_prev = self.chain[i - 1]["hash"]
            
            if entry["previous_hash"] != expected_prev:
                return False, i
            
            # Verify entry's own hash
            stored_hash = entry["hash"]
            entry_copy = {k: v for k, v in entry.items() if k != "hash"}
            entry_string = json.dumps(entry_copy, sort_keys=True)
            computed_hash = self._compute_hash(entry_string)
            
            if stored_hash != computed_hash:
                return False, i
        
        return True, None
    
    def get_entries(self, event_type: Optional[str] = None, limit: int = 50) -> list[dict]:
        """Retrieve recent entries, optionally filtered by event type."""
        entries = self.chain
        if event_type:
            entries = [e for e in entries if e["event_type"] == event_type]
        return entries[-limit:]
    
    def _save(self):
        """Persist chain to disk."""
        with open(self.ledger_path, "w") as f:
            json.dump(self.chain, f, indent=2)
    
    def _load(self):
        """Load chain from disk."""
        with open(self.ledger_path, "r") as f:
            self.chain = json.load(f)


# ─── Demo Usage ───────────────────────────────────────────────
if __name__ == "__main__":
    ledger = HashChainLedger("demo_ledger.json")
    
    # Add sample entries
    ledger.add_entry("capture", {"packets": 1000, "interface": "eth0"})
    ledger.add_entry("anomaly", {"src_ip": "192.168.1.105", "dst_port": 4444}, anomaly_score=-0.85)
    ledger.add_entry("alert", {"method": "SMS", "recipient": "+91XXXXXXXXXX"})
    
    # Verify integrity
    is_valid, broken_at = ledger.verify_chain()
    print(f"Chain valid: {is_valid}")
    
    # Display entries
    for entry in ledger.get_entries():
        print(f"  [{entry['index']}] {entry['event_type']} — {entry['hash'][:16]}...")
    
    # Cleanup demo file
    os.remove("demo_ledger.json")
    print("\n[DEMO] Complete!")
