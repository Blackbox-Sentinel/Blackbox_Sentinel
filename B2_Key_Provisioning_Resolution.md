# B2 Key Provisioning Resolution

**Status:** Resolved for the Phase-2 software contract.

## Decision

BlackBox Sentinel uses **per-node HMAC transport keys** for authenticated evidence signals and quorum votes. The key identity maps to `sender_id`; one compromised node key must not authenticate messages as another node.

The design uses one write-once 32-byte master key per sender under the gitignored `m3-ml-ledger/data/keys/<sender_id>.key` path. The transport derives the active epoch key as:

```text
signing_key = HMAC-SHA256(master_key, decimal(key_epoch))
```

A single node master key therefore supports future key epochs without redistributing a new key for every rotation. `key_epoch` remains part of the authenticated envelope and the replay identity.

## Ownership

| Concern | Owner |
|---|---|
| Transport key loading, per-node derivation, and signal/vote submission | M2 |
| Verification-side sender/epoch lookup, accepted message types, and security tests | M3 |
| Telemetry display and honest hardware-state presentation | M4 |
| Secure provisioning and hardware-in-loop validation on ESP32 | M1 |

## Required invariants

Signals and votes from the same sender and key epoch share one monotonic sequence space because `ReplayProtector` keys replay state by `(sender_id, key_epoch)`. Verification must resolve the claimed sender's provisioned key and derive the claimed epoch key; it must not trust an arbitrary caller-supplied key when per-node verification is enabled. Key material must never appear in telemetry or committed files.

The canonical M2 evidence message type is `EVIDENCE_SIGNAL`; M3 accepts it together with the existing evidence types. The transport and verifier must remain aligned on this vocabulary.

## Scope and limitation

This is a software reference design. The files and derived keys are not yet hardware-backed. M1 must validate secure provisioning, storage, rotation, zeroization, and ESP32 enforcement before the project claims hardware-grade node identity or relay enforcement.
