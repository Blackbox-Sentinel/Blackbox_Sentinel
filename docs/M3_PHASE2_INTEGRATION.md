# M3 Phase-2 Integration Handoff

## Purpose

This document defines the M3 software handoff for the joint M2–M3–M4 Phase-2 integration. The implementation preserves the authoritative 45-feature v3 scorer and treats its result as evidence rather than as direct relay authority.

The software-only path is:

```text
M2 packet window
→ shared 45-feature pipeline
→ M3 v3 scorer and organization profile
→ authenticated evidence envelope
→ independent two-signal policy
→ quorum approval when configured
→ signed containment receipt
→ simulated trusted-controller verification
→ append-only ledger
→ normalized M4 telemetry
```

Physical ESP32 enforcement, hardware-backed key storage, relay fail-safe behavior, tamper enforcement, power-fail validation, and ESP-NOW hardware validation remain M1 handoff requirements.

## M3 entry points

The scorer remains unchanged at the interface boundary:

```python
result = scorer.ingest_feature_window(feature_row)
```

`feature_row` must contain exactly the 45 numeric features defined by `ml/M3_INTERFACE.md`. Metadata such as timestamps and source files must not be included in the model vector.

The Phase-2 security path is exposed through `m3-ml-ledger/src/m3_decision_path.py`:

```python
from m3_decision_path import M3DecisionPath

path = M3DecisionPath(
    ledger=ledger,
    node_id="node-a",
    organization_id=scorer.organization_id,
    counter_path="m3-ml-ledger/data/receipt_counter.txt",
)

outcome = path.submit(
    model_result=result,
    signals=independent_signals,
    incident_id="node-a:window-1",
)
```

A model-only submission cannot approve containment. M2 or an approved peer must provide a second signal with a distinct `source_id` and `signal_type`, and both signals must be authenticated and fresh. When quorum is configured, the caller must also provide authenticated, fresh votes whose evidence digest matches the M3 decision.

## M4 normalized telemetry

`M3DecisionPath.submit()` returns a `DecisionPathResult`. Its `telemetry` member is a versioned `NormalizedTelemetry` mapping from `m3-ml-ledger/src/normalized_telemetry.py`.

| Section | Required contents |
|---|---|
| `schema_version` | Current schema version, presently `1`. |
| `event_type` | `BENIGN`, `PENDING_EVIDENCE`, `PENDING_QUORUM`, `CONTAINMENT_ACCEPTED`, or a rejection state. |
| `model` | v3 state, score, probability, threshold, global/local prediction, profile readiness, sample count, and feature count. |
| `evidence` | Evidence digest, signal count, source IDs, signal types, authentication/freshness-derived signal records, independence, and approval. |
| `quorum` | `NOT_CONFIGURED` or the quorum snapshot containing state, threshold, votes, deadline, conflicts, timeouts, and rejected votes. |
| `receipt` | Issuance, receipt sequence, signature verification, ledger binding, and algorithm. No private signing material is included. |
| `controller` | Simulated-controller status, trusted decision, receipt verification, relay state, and rejection reason. |
| `actuation` | Relay requested, relay acknowledged, and relay verified separately. `relay_verified` remains false in the software-only slice. |
| `hardware` | Explicit software-simulation mode and unknown/unvalidated physical tamper, key, and power states. |
| `recovery` | Whether recovery is required and the current recovery status. |

M4 must display these fields without inferring physical success from a request or software-controller acknowledgment. The telemetry serializer rejects secret-like fields, including private keys, HMAC keys, authentication keys, and provisioning secrets.

## M2 handoff

M2 should authenticate and freshness-check transport envelopes before passing evidence or votes to M3. The reusable contract is `AuthenticatedEnvelope` plus `ReplayProtector` in `m3-ml-ledger/src/authenticated_envelope.py`.

M2 must preserve sender identity, recipient, message type, sequence, key ID, key epoch, timestamp, payload, and authentication result. It must not alter the M3 result or remove verification fields. The M3 adapter also exposes `accept_authenticated_envelope()` for the software vertical slice and integration tests.

M2 should provide an independent signal only when it represents a genuinely distinct source and signal type. A duplicate copy of the M3 result is not independent evidence.

## M1 boundary

`SimTrustedController` is a software reference boundary. It rejects direct isolate requests and accepts containment only after receipt verification and policy approval. The pipeline does not call the relay directly from `is_anomaly` anymore.

The current telemetry deliberately reports:

```text
 enforcement_mode = software-simulation
 physical_controller_validated = false
 relay_hardware_verified = false
 relay_verified = false
```

These values must remain false until M1 supplies hardware-in-loop evidence.

## Verification

The focused Phase-2 tests are:

```text
 tests/test_m3_decision_path.py
 tests/test_postmeeting_security_flow.py
 tests/test_m3_security_contracts.py
```

They cover the approved software slice, explicit unconfigured quorum, configured quorum approval, one-signal blocking, quorum conflict, authenticated-envelope replay rejection, receipt verification, ledger integrity, and secret-free telemetry.

## Real M2-to-M3 vertical slice

The orchestrator at `integration/phase2_vertical_slice.py` now calls the M2-owned APIs directly:

```python
signal_a = m2_transport.submit_signal(...)
signal_b = m2_peer_transport.submit_signal(...)
first_vote = m2_transport.submit_vote(...)
second_vote = m2_peer_transport.submit_vote(...)
```

The two transport instances use the same HMAC-SHA256 envelope contract and maintain one sequence space per sender/key epoch across signal and vote messages. The returned `EvidenceSignal` and `QuorumVote` objects are then consumed by the M3 two-signal gate, quorum state machine, Ed25519 receipt service, simulated controller, ledger, and normalized M4 telemetry writer.

`m3-ml-ledger/data/phase2_telemetry_real_m2_m3.jsonl` is a generated software-integration artifact from this path. It is real API-level M2/M3 integration output, but it remains simulation-only at the hardware boundary.
