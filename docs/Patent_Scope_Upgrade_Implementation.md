# BlackBox Sentinel — Patent-Scope Upgrade Implementation

> **Engineering planning document only.** This document does not determine patentability, novelty, inventorship, or validity. A qualified patent professional should review any formal filing or claim language.

## Purpose

The new patent-scope plan shifts the project emphasis from demonstrating an ML detector to proving a stronger **trusted hardware-security sequence** around detection, containment, communication, power loss, key invalidation, receipts, quorum, and recovery.

The existing ML model remains useful, but it must become an evidence source rather than the sole authority for destructive relay isolation.

## Scope-to-implementation matrix

| Scope feature | Current repository status | Required owner | Immediate engineering action |
|---|---|---|---|
| Independent trusted security controller | Partial simulation and ESP32/relay foundation; policy is not yet enforced independently in firmware | M1 with M2/M3 support | Define the controller state machine and move the containment policy outside the Python GUI/ML process |
| Two independent authenticated compromise signals | Previously missing from the active containment path | M1/M3 with M2 transport support | Keep known-attack and adaptive-anomaly evidence separate; require both before destructive isolation |
| Authenticated anti-replay alerts | Current prototype transport is not strong enough for the new scope | M2 with M1/M3 support | Define message envelope, identity, sequence/nonce, freshness, authentication, and rejection reasons |
| Fail-safe relay topology | Logical relay states exist; fault behavior is not fully proven | M1 with M2 support | Document safe electrical state for crash, reset, brownout, GPIO failure, and power loss |
| Hardware-backed key invalidation | Current prototype uses volatile/file zeroization only | M1 with M2/M3 support | Select secure element/TPM/protected MCU mechanism and test invalidated keys cannot decrypt |
| Dedicated hold-up power path | Missing | M1 with M2/M3 support | Add power-fail detection, energy budget, hold-up sequence, and controlled power-removal test |
| Authenticated monotonic containment receipt | Local hash-chain exists; signature/MAC, protected counter, and external witness are missing | M3 with M1/M2 support | Add event ID, signal IDs, controller decision, relay acknowledgment, counter, signature/MAC, and standalone verifier |
| ML as one input to trusted logic | Current pipeline can isolate from one result | M1/M3 with M2 support | Emit structured ML evidence and require trusted-controller corroboration |
| Authenticated multi-node quorum | Mesh skeleton exists; quorum/authentication/freshness/conflict rules are missing | M2 with M1/M3 support | Define peer enrollment, quorum threshold, deadline, conflict policy, outage behavior, and tests |
| Final M4 visibility and recovery | Basic relay/tamper/PIN/ledger display exists | M4 with M1/M2/M3 telemetry | Display controller state, separate signals, relay acknowledgment, receipt verification, quorum, key, power, and recovery status |

## M4 deliverables

M4 must not create or forge security decisions. The GUI should consume trusted telemetry and clearly distinguish **requested**, **acknowledged**, **verified**, **unknown**, **stale**, **rejected**, and **conflicting** states.

The compact 480×320 dashboard now includes a simulation-oriented view for controller state, relay acknowledgment, tamper state, key state, power state, independent signal count, receipt status, and quorum status. The implementation is a visualization and integration scaffold; it does not replace the future ESP32/security-MCU enforcement.

M4 should complete the following integration work when M1–M3 schemas are stable:

1. Display the authoritative controller state and last transition reason/time.
2. Display known-attack and adaptive-anomaly evidence as separate rows.
3. Display the containment decision as pending, approved, rejected, expired, or conflicting.
4. Display relay requested state separately from controller acknowledgment and verified physical state.
5. Display receipt ID, protected counter, receipt hash, verification result, and external-witness status.
6. Display authenticated peer identity, vote, quorum threshold, deadline, and conflict state.
7. Display key state as valid, invalidated, or unknown without exposing key material.
8. Display primary-power loss, hold-up active, containment complete, invalidation complete, and incomplete-failure states.
9. Keep recovery behind the controller’s authenticated workflow; the GUI must not bypass policy.
10. Test stale telemetry, failed authentication, controller disconnect, failed relay transition, wrong PIN, and incomplete recovery.

## Phase 2 simulation policy

Before hardware enforcement is available, the simulation should model the intended policy:

```text
known_attack evidence
        AND
adaptive_anomaly evidence
        AND
(optional configured peer quorum)
        |
        v
trusted-controller decision
        |
        v
relay isolation + receipt + alert + M4 visibility
```

The simulation must label any unavailable feature honestly. For example, when quorum or hold-up power is not implemented, the GUI should show `NOT CONFIGURED` rather than displaying fabricated votes or claiming a real power-fail sequence.

## Required cross-team contracts

| Contract | Minimum fields |
|---|---|
| Controller telemetry | state, link health, transition reason, transition time, relay requested, relay acknowledged, relay verified |
| Signal evidence | signal ID, event ID, source, signal type, timestamp, sequence/nonce, model/profile version, threshold, confidence, evidence hash, authentication status, freshness status |
| Quorum | peer ID, vote ID, vote value, peer authentication, received time, deadline, required threshold, received count, conflicts, decision |
| Containment receipt | receipt ID, event ID, monotonic counter, controller decision, signal IDs, vote IDs, relay acknowledgment, current hash, previous hash, signature/MAC status, external-witness status |
| Power and key status | primary power, hold-up state, containment completion, invalidation completion, key state, failure reason |
| Recovery | authentication result, lockout state, controller recovery state, relay restoration acknowledgment |

## Recommended implementation order

M1 and M2 should first agree on the trusted-controller boundary, relay electrical safety, authenticated command envelope, and power-fail behavior. M3 should then finalize the evidence and receipt schema, including signal independence rules. M1 and M2 can implement peer authentication and quorum behavior while M3 extends the ledger and standalone verifier. Finally, M4 connects to the stable telemetry contracts and replaces demo values with verified state.

All members should then run hardware-in-loop, replay, forged-message, single-signal, quorum, power-loss, tamper, receipt, and recovery tests. No feature should be described as a completed patent-scope capability until its assigned trust boundary and validation evidence exist.
