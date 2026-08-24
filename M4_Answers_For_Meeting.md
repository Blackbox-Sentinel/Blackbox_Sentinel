# M4 Answers for the B1–B4 Architecture Meeting

> **Status:** M4 engineering response for discussion. B1, B2, and B3 are drafts, not finalized implementation specifications. The GUI must not present any draft decision as a completed security capability.

## 1. M4 responsibility in one sentence

M4 is the **operator-visibility and recovery interface**. It displays evidence and controller-reported state; it must not make the destructive isolation decision, forge peer votes, export key material, or bypass the trusted controller.

## 2. What the current GUI shows

The current Tkinter application in `m4-gui-venture/src/app.py` displays or simulates:

| Area | Current behavior |
|---|---|
| Processing state | Calibration, armed monitoring, anomaly/lockdown state, packet count, anomaly count, uptime |
| Relay | Local simulated `ENGAGED` or `ISOLATED` state after the Python path calls the HAL |
| Tamper | Enclosure-secure or casing-breached state; tamper triggers simulated key-file zeroization and relay isolation |
| Ledger | Local SHA-256 ledger block count and recent event/hash log |
| GSM | Simulated registration and mock SMS notification status |
| Operator recovery | On-screen PIN keypad; incorrect PIN is rejected and correct PIN can restore the simulated relay |
| Attack testing | Buttons for C2/exfiltration and SYN-flood injection |

The `m4-gui-venture/hw_simulator_server.py` backend exposes simulation state for relay, tamper, LED, cellular, mesh, ledger, packet, and anomaly behavior. These are useful demonstration hooks, but they are not yet proof of B1 authentication, B3 quorum, protected receipt verification, hardware-backed key invalidation, or hold-up power completion.

## 3. What the current GUI does not yet prove

The current GUI mostly reads local Python variables and simulated HAL results. It does not yet receive a final authenticated controller telemetry contract from M1/M2/M3. In particular, it does not yet prove that:

1. A message was authenticated by the controller rather than merely received by the host.
2. A message is fresh and not replayed or out of order.
3. Two signals came from independent trust paths.
4. A peer vote is from an authenticated, distinct node.
5. The relay state was physically acknowledged by trusted hardware.
6. A containment receipt has a protected monotonic counter or external witness.
7. Keys were invalidated by secure hardware.
8. A hold-up power sequence completed before energy was exhausted.

These are system-integration gaps, not reasons for M4 to modify M3’s detector or M1’s firmware independently.

## 4. M4 mapping to the real B1–B4 documents

### B1 — Authenticated envelope

B1 proposes a common envelope with `version`, `sender_id`, `recipient/scope`, `message_type`, `sequence/nonce`, `timestamp`, `payload`, and `auth_tag`. B1 explicitly marks the proposal as draft and leaves the exact encoding, time representation, key provisioning, and authentication mechanism open.

M4 should display the following safe, non-secret fields:

| B1 field or result | M4 display |
|---|---|
| `sender_id` | Source identity, for example `controller-01` or `peer-02` |
| `message_type` | Telemetry, containment decision, quorum vote, recovery, or power event |
| `sequence/nonce` | Sequence number or nonce summary; never expose secret key material |
| `timestamp` | Event time and local freshness age |
| `auth_tag` result | `AUTH VERIFIED`, `AUTH FAILED`, or `NOT VERIFIED`; never display the tag as a secret credential |
| Freshness result | `FRESH`, `STALE`, `REPLAYED`, or `OUT OF ORDER` |
| Rejection reason | Clear reason such as `AUTH_FAILED`, `STALE`, or `REPLAYED` |

M4 should not label a received alert as trusted merely because it arrived through serial, UDP, or ESP-NOW.

### B2 — Crypto shortlist

B2 leans toward HMAC-SHA256 because it is simpler and likely cheaper for the candidate ESP32 targets, but it also records an important counterargument for ECDSA: per-node key isolation. B2 says the actual chip family, crypto toolchain, key provisioning, rotation, and compromise model are not yet finalized.

Therefore M4 should show:

```text
AUTH METHOD: PENDING TEAM DECISION
KEY STATE: VALID / INVALIDATED / UNKNOWN
PROVISIONING: NOT DISPLAYED
```

After M1–M3 approve a method, M4 may display the selected profile name and verification result. M4 must never display HMAC keys, private keys, provisioning secrets, or exportable credentials.

### B3 — Quorum state machine

B3 proposes that each incident have an `incident_id`, and that peers cast `CONFIRM`, `DENY`, or `ABSTAIN` votes referencing that incident. It leaves leader-based versus decentralized tallying, peer count, threshold, deadline, conflict behavior, fail-open versus fail-closed behavior, and peer recovery for the architecture meeting.

The M4 quorum view should display:

| Quorum item | Required display |
|---|---|
| Incident | Incident ID and originating node |
| Membership | Known peer IDs and link/availability state |
| Votes | Each peer’s `CONFIRM`, `DENY`, or `ABSTAIN` vote plus authentication status |
| Threshold | Required count or ratio, once approved |
| Deadline | Remaining time or expired state |
| Conflicts | Conflicting votes and unresolved status |
| Decision | `PENDING`, `APPROVED`, `REJECTED`, `EXPIRED`, or `CONFLICTING` |
| Recovery | Catch-up, recovery required, recovered, or locked |

The current repository does not have a working quorum implementation. Until B3 is approved and implemented, M4 must show `QUORUM: NOT CONFIGURED` rather than fabricated votes.

### B4 — Gap analysis and final visibility

B4 identifies final GUI visibility and recovery as an M4-owned feature, with M1, M2, and M3 supporting it. B4’s concern that M4 coverage is thin is valid when the review considers only systemd supervision; service supervision proves that a process restarts, not that the GUI displays the correct security state.

M4’s response is to make the final dashboard visibly cover the following independent state categories:

```text
CONTROLLER: ARMED / ALERT_PENDING / ISOLATED / TAMPERED / RECOVERY
LINK: HEALTHY / STALE / DISCONNECTED
SIGNAL A: type, source, confidence, auth, freshness
SIGNAL B: type, source, confidence, auth, freshness
RELAY: requested / acknowledged / physically verified / failed
TAMPER: secure / breached
KEY: valid / invalidated / unknown
POWER: primary / hold-up active / containment complete / incomplete
RECEIPT: ID, counter, verification, external witness
QUORUM: votes, threshold, deadline, conflicts, decision
RECOVERY: locked / authentication failed / recovery required / restored
```

## 5. Proposed 3.5-inch touchscreen layout

The 480×320 touchscreen should prioritize state clarity over detailed logs. The top row should show the controller state and link health. The middle rows should show relay, tamper, key, power, independent-signal, receipt, and quorum summaries. The bottom row should contain only large touch controls for `ATTACK TEST`, `TAMPER TEST`, `AUDIT RECEIPT`, and `PIN RECOVERY`.

Detailed evidence, including full payloads and event history, should be available through a scrollable audit view or exported report. The touchscreen must never provide a control that directly sends `ISOLATE`, `DISARM`, or `RESTORE` around the authenticated controller workflow.

## 6. Required M4 validation scenarios

M4 should test the display and recovery behavior against normalized integration events, whether those events arrive through a JSON Lines stream, local API, or in-process queue:

1. Normal traffic: controller is `ARMED`, relay is connected, link is fresh, and no alert is shown.
2. One signal only: the GUI shows `ALERT_PENDING`; the relay remains connected.
3. Two independent valid signals: the GUI shows the separate evidence and the final controller decision.
4. Invalid authentication: the GUI shows `AUTH FAILED` and does not show a confirmed trusted alert.
5. Stale or replayed message: the GUI shows the rejection reason and keeps the prior trusted state.
6. Quorum pending or conflicting: the GUI shows the threshold, votes, deadline, and unresolved decision.
7. Relay transition failure: requested, acknowledged, and verified physical state are visibly different.
8. Tamper or key invalidation: the GUI shows the event, invalidated/unknown key state, and locked recovery state.
9. Power-fail sequence: the GUI distinguishes hold-up active, containment complete, invalidation complete, and incomplete failure.
10. Recovery: wrong authentication leaves the controller locked; successful authenticated recovery displays the controller acknowledgment before showing restoration.

## 7. Questions to bring to the meeting

M4 needs the following decisions or contracts from the other members:

- From M1: authoritative controller states, relay acknowledgment fields, tamper/key/power telemetry, and the approved recovery workflow.
- From M2: B1 envelope encoding, authentication and freshness result fields, peer identity, link health, and quorum event transport.
- From M3: structured ML evidence fields, incident IDs, receipt schema, verification result, model/profile versions, and audit export format.
- From the repository owner: whether M4 should commit this file before or after the M3 branch is merged into `main`.

## 8. Conclusion

M4’s immediate task is documentation and visibility, not implementation of B1–B4 cryptography or quorum logic. The correct deliverable is this `M4_Answers_For_Meeting.md` file on the `m3-v3-integration` branch. After the file is reviewed, M4 should commit and push it to that branch. The designated repository owner remains responsible for merging the branch into `main` without force-pushing.
