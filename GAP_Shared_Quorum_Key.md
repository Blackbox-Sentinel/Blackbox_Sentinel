# GAP — Shared quorum key

**Status: CLOSED for the Phase-2 software path.** M2’s per-node key provisioning is implemented on `origin/main` at commit `1931cc3`, and the M3 follow-up updates the vertical slice to use that auto-derived path.

## Resolved problem

Previously, the node-a and node-b `M2EvidenceTransport` instances received the same module-level `TRANSPORT_KEY`. That authenticated signals and quorum votes, but anyone holding the shared key could forge either sender identity. The same gap applied to both evidence signals and quorum votes, not only votes.

## Implemented design

Each sender now has a write-once 32-byte master key at the gitignored path:

```text
m3-ml-ledger/data/keys/<sender_id>.key
```

The transport derives the active epoch key as:

```text
HMAC-SHA256(master_key, decimal(key_epoch))
```

`integration/phase2_vertical_slice.py` no longer passes an explicit shared key to the node-a/node-b M2 transports. Each transport uses its own `sender_id` and key directory. The local M2-to-M4 JSONL wrapper retains a separate simulation key; that key is not used for node-a/node-b evidence or quorum authentication.

## Required invariants

Signals and votes from the same sender and key epoch share one monotonic sequence space because `ReplayProtector` keys replay state by `(sender_id, key_epoch)`. M3 verification resolves the sender’s provisioned master key and derives the envelope epoch key; verification does not trust an arbitrary caller-supplied key when `keys_dir` is configured.

The canonical evidence message type is `EVIDENCE_SIGNAL`, and M3 accepts it. Key material must not appear in telemetry or committed files.

## Ownership

| Concern | Owner |
|---|---|
| Per-node transport key loading, derivation, and signal/vote submission | M2 |
| Sender/epoch verification, message-type contract, and security tests | M3 |
| Telemetry presentation | M4 |
| Secure provisioning, storage, zeroization, and hardware validation | M1 |

## Remaining limitation

This closes the shared-key gap in the software reference implementation. It does not prove hardware-secure key provisioning or physical relay enforcement. M1 must validate ESP32 key installation, secure storage, rotation, zeroization, transport behavior, and fail-safe relay operation.

See `B2_Key_Provisioning_Resolution.md` for the full decision record.
