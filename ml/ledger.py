import hashlib
import json
import time
import os

LEDGER_FILE = "sentinel_ledger.json"

class Ledger:
    def __init__(self, file_path=LEDGER_FILE):
        self.file_path = file_path
        self.chain = []
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                self.chain = json.load(f)
        else:
            self._create_genesis()

    def _create_genesis(self):
        genesis = {
            "index": 0,
            "timestamp": time.time(),
            "event": "GENESIS",
            "data": {},
            "previous_hash": "0" * 64,
            "hash": self._calculate_hash(0, time.time(), "GENESIS", {}, "0" * 64)
        }
        self.chain.append(genesis)
        self._save()

    def _calculate_hash(self, index, timestamp, event, data, previous_hash):
        block_string = json.dumps({
            "index": index, "timestamp": timestamp,
            "event": event, "data": data,
            "previous_hash": previous_hash
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def append_entry(self, event, data=None):
        if data is None:
            data = {}
        prev = self.chain[-1]
        idx = prev["index"] + 1
        ts = time.time()
        h = self._calculate_hash(idx, ts, event, data, prev["hash"])
        block = {
            "index": idx, "timestamp": ts, "event": event,
            "data": data, "previous_hash": prev["hash"], "hash": h
        }
        self.chain.append(block)
        self._save()
        return block

    def verify_chain(self):
        for i in range(1, len(self.chain)):
            c, p = self.chain[i], self.chain[i-1]
            if c["previous_hash"] != p["hash"]:
                return False, f"Broken at block {i}"
            if self._calculate_hash(c["index"], c["timestamp"], c["event"], c["data"], c["previous_hash"]) != c["hash"]:
                return False, f"Hash mismatch at block {i}"
        return True, "Chain valid"

    def _save(self):
        with open(self.file_path, "w") as f:
            json.dump(self.chain, f, indent=2)

    def get_all(self):
        return self.chain