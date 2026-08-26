# Phase-2 Controller Contract

**Status:** Working canonical contract for the Phase-2 software integration slice.

**Decision:** Use **HMAC-SHA256 for transport authentication** and **Ed25519 for signed containment receipts**.

## Contract split

HMAC-SHA256 authenticates transport messages. It proves that an envelope was created by a party holding the configured shared secret and that the envelope fields were not modified in transit. It covers the sender, recipient, message type, sequence, timestamp, payload, key ID, and key epoch. M2 binds this contract to serial/ESP-NOW or simulation transport. M3 consumes the verified event. M1 must later validate the same semantics in firmware.

Ed25519 signs the containment receipt created after M3 policy approval. The receipt signer holds the private signing key, while verifiers use the public key. This allows the receipt to be verified without distributing the private signing secret to M2, M4, dashboard clients, or audit readers. M3 owns the software receipt contract and ledger binding. M1 later verifies and enforces the receipt at the trusted physical controller boundary.

These mechanisms are complementary:

```text
M2 transport → HMAC-SHA256 authenticated envelope
M3 evidence → independent two-signal gate
M3 policy → quorum approval when configured
M3 receipt → Ed25519 signed containment receipt
M1 controller → receipt verification and physical enforcement
M4 dashboard → normalized telemetry display
```

## Ownership

| Responsibility | Owner | Supporting role |
|---|---|---|
| Packet capture and wire transport | M2 | M3 defines consumed envelope fields |
| Envelope MAC, freshness, and replay semantics | M3 contract | M2 implements transport binding; M1 validates firmware behavior |
| 45-feature v3 scorer and organization profile | M3 | M2 supplies windows |
| Two-signal independence policy | M3 | M2 supplies an independent authenticated signal |
| Quorum state and vote semantics | M3 contract | M2 transports votes |
| Ed25519 containment receipt and ledger binding | M3 | M1 verifies/enforces; M4 displays |
| Normalized telemetry and dashboard visibility | M4 consumes | M3 publishes; M2/M1 provide events |
| Physical relay, tamper, key storage, and power enforcement | M1 | All software members provide validated contracts |

## Required M3 behavior

M3 must preserve the 45-feature `M3_INTERFACE.md` output. A model result is evidence and is never relay authority by itself. M3 must require two authenticated, fresh, independent signals with distinct source IDs and signal types. If quorum is configured, M3 must require an approved quorum state before issuing a receipt. M3 must verify the Ed25519 receipt independently from HMAC transport authentication, bind accepted and rejected outcomes to the append-only ledger, and publish normalized telemetry without secrets.

An explicitly unconfigured quorum is represented as `NOT_CONFIGURED` in telemetry. The independent two-signal gate remains required. The software controller may accept a signed receipt in this mode for the software slice, but telemetry must continue to identify the controller and actuation as software simulation rather than hardware enforcement.

## Treatment of the alternate HMAC controller

The HMAC receipt/controller implementation under `security/trusted_controller.py` is retained temporarily as a legacy or compatibility simulator. It is not a second live security authority. M4 must migrate its live dashboard path to the canonical M3 telemetry and controller contract. After migration is verified, the team may remove or keep the legacy adapter explicitly for historical/demo compatibility.

## Open implementation questions

The working contract does not claim that production key management is complete. The team must still define the shared-secret provisioning and rotation procedure for HMAC, the Ed25519 public-key distribution and revocation procedure, the exact ESP32 target and crypto library configuration, and the hardware-in-loop acceptance criteria. These are M1/architecture-handoff items and must not be represented as completed by the Python simulation.

## Shared API handoff

The canonical identifiers are defined in `m3-ml-ledger/src/m3_contract.py`. M2 should authenticate transport envelopes and pass them to the M3 adapter as `(envelope, key)` pairs. M3 verifies the HMAC, freshness, and sequence before decoding the payload:

```python
outcome = m3_path.submit_authenticated(
    model_result=model_result,
    evidence_envelopes=[
        (m3_envelope, m2_transport_key),
        (independent_envelope, peer_transport_key),
    ],
    quorum_envelopes=authenticated_vote_envelopes,
    incident_id=incident_id,
)
telemetry = outcome.telemetry
```

M2 evidence payloads must include `signal_id`, `signal_type`, `decision`, and optional `confidence` and `details`. The authenticated envelope sender becomes the authoritative signal source ID; a source ID copied inside the payload is not trusted for independence evaluation. Quorum payloads must include `incident_id`, `decision`, and `evidence_digest`.

M4 should consume `outcome.telemetry` or the pipeline accessor `get_latest_telemetry()`. It must not reconstruct security state from raw model fields, fabricate votes, or treat `relay_requested` or `relay_acknowledged` as physical relay verification. The canonical telemetry schema is version `1`.

## Freeze status

This document is the M3 working freeze for the Phase-2 software slice. The remaining team discussion concerns production provisioning, key rotation, public-key distribution, exact ESP32 target, and hardware acceptance—not the Python integration API. Any future contract change must update this document, `m3_contract.py`, the M3 adapter, and the focused tests together.
