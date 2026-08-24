import hashlib
import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEDGER_FILE = os.path.join(BASE_DIR, "ledger.json")

def calculate_hash(index, timestamp, event, previous_hash):
    data = f"{index}{timestamp}{event}{previous_hash}"
    return hashlib.sha256(data.encode()).hexdigest()


def create_entry(index, event, previous_hash):

    timestamp = datetime.now().isoformat()

    current_hash = calculate_hash(
        index,
        timestamp,
        event,
        previous_hash
    )

    entry = {
        "index": index,
        "timestamp": timestamp,
        "event": event,
        "previous_hash": previous_hash,
        "hash": current_hash
    }

    return entry

def append_entry(event):

    # If ledger.json doesn't exist, create it
    if not os.path.exists(LEDGER_FILE):
        with open(LEDGER_FILE, "w") as file:
            json.dump([], file)

    # Read existing ledger
    with open(LEDGER_FILE, "r") as file:
        ledger = json.load(file)

    # Determine index and previous hash
    if len(ledger) == 0:
        index = 1
        previous_hash = "0"
    else:
        last_entry = ledger[-1]
        index = last_entry["index"] + 1
        previous_hash = last_entry["hash"]

    # Create new block
    new_entry = create_entry(index, event, previous_hash)

    # Append block
    ledger.append(new_entry)

    # Save ledger
    with open(LEDGER_FILE, "w") as file:
        json.dump(ledger, file, indent=4)

    print(f"Entry #{index} added.")


def verify_chain():

    if not os.path.exists(LEDGER_FILE):
        print("Ledger file not found.")
        return False

    with open(LEDGER_FILE, "r") as file:
        ledger = json.load(file)

    if len(ledger) == 0:
        print("Ledger is empty.")
        return True

    for i in range(1, len(ledger)):

        current = ledger[i]
        previous = ledger[i - 1]

        expected_hash = calculate_hash(
            current["index"],
            current["timestamp"],
            current["event"],
            current["previous_hash"]
        )

        if current["hash"] != expected_hash:
            print(f"Block {current['index']} has been modified.")
            return False

        if current["previous_hash"] != previous["hash"]:
            print(f"Broken chain at block {current['index']}.")
            return False

    print("Ledger verified successfully.")
    return True

if __name__ == "__main__":
    print("Ledger module loaded.")
    verify_chain()

