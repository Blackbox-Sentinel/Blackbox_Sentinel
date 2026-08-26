# M3 Controller-Contract Position for Phase 2

## Plain-language distinction

**HMAC-SHA256 transport authentication** answers: “Did this message arrive from a sender that knows the shared secret, and was it changed in transit?” It is a symmetric message-authentication code. The sender and verifier use the same secret. It belongs in the authenticated transport envelope used by M2 and M3, with the eventual wire-level enforcement validated by M1.

**Ed25519 signed receipts** answer: “Can this containment receipt be independently verified as issued by the authorized controller or receipt signer?” Ed25519 uses a private signing key and a public verification key. The private key signs; verifiers only need the public key. This is the M3 receipt/evidence layer in the current M3 software path, with final controller-side enforcement owned by M1.

These mechanisms solve different problems and are not automatically competitors. The proposed composition is:

```text
M2 transport envelope: HMAC-SHA256 authentication
M3 evidence/policy: two-signal gate plus quorum
M3 containment receipt: Ed25519 signature
M1 trusted controller: verify receipt and enforce hardware policy
M4 dashboard: display normalized verification state
```

## Ownership matrix

| Contract or responsibility | Primary owner | Supporting owner | Current repository location |
|---|---|---|---|
| Packet capture and transport binding | M2 | M3 defines consumed fields | `m2-systems/src/`, `m3-ml-ledger/src/authenticated_envelope.py` |
| HMAC-SHA256 envelope fields, MAC verification, freshness, and replay semantics | M3 contract; M2 transport implementation | M1 firmware validation | `m3-ml-ledger/src/authenticated_envelope.py` |
| 45-feature scoring and organization profile | M3 | M2 supplies feature windows | `ml/feature_pipeline_v2.py`, `m3-ml-ledger/src/predict_v3.py` |
| Independent two-signal policy | M3 | M2 supplies an independent signal | `m3-ml-ledger/src/m3_security_contracts.py` |
| Quorum state and vote semantics | M3 contract | M2 transports votes; M1 later enforces boundary | `m3-ml-ledger/src/quorum_state.py` |
| Signed containment receipt | M3 software contract | M1 verifies/enforces; M4 displays | `m3-ml-ledger/src/m3_security_contracts.py` |
| Dashboard and recovery visibility | M4 | M3 publishes normalized telemetry | `gui/`, `m4-gui-venture/` |
| Physical relay, tamper, key storage, and power enforcement | M1 | M2/M3/M4 provide software contracts and events | `m1-hardware/`, HAL |

## M3 working contract

M3 has selected **HMAC-SHA256 for transport authentication and Ed25519 for signed containment receipts** as the working Phase-2 contract, so M3 implementation can proceed without waiting on the two parallel controller paths.

This contract keeps the fast symmetric MAC at the message-transport boundary, where M2 needs to authenticate frequent serial or ESP-NOW messages. It keeps receipt verification independently verifiable without distributing a receipt-signing secret to every dashboard, peer, or audit reader. It also preserves the M3 implementation in `m3_security_contracts.py` and `m3_decision_path.py`.

This is the working software contract for Phase 2. The team must still confirm the exact key-provisioning, key-rotation, public-key distribution, controller identity, and target-ESP32 assumptions before hardware enforcement is claimed.

## Treatment of the parallel HMAC controller

The HMAC receipt/controller implementation under `security/trusted_controller.py` should not be deleted immediately. It should be labelled as a **legacy or alternate simulator path** while the asynchronous architecture discussion is recorded. The working Phase-2 path is the M3 contract defined above. The team must either migrate the alternate implementation to the canonical contract or explicitly retain it as a non-production compatibility/demo adapter. Both implementations must not remain silently active as competing live security authorities.

## M3 work status and next action

M3’s safe pre-decision work is complete: the v3 scorer remains unchanged, the security contracts are isolated and tested, the M3 decision path is available, the M4 normalized telemetry shape is documented, and direct model-to-relay authority has been removed from the updated pipeline path.

M3 should not implement M2-2 or M2-3 against an unapproved controller contract. Immediately after the team decision, M3 will:

1. freeze the selected receipt/controller contract and record the decision;
2. reconcile the losing or alternate implementation explicitly;
3. update M3 and M4 integration adapters and tests;
4. run the joint packet-window-to-dashboard software vertical slice; and
5. leave physical enforcement claims pending M1 hardware-in-loop validation.
