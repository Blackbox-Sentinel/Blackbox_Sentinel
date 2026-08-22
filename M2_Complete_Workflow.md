# M2 — Systems: Complete Workflow
**Updated:** 22 Aug 2026 | **Owner:** Suhan Shetty | **Module:** M2 — Systems (network capture/gateway layer)

This update merges Track A (real-capture validation, carried over from the 22 Aug session) with Track B (patent-scope hardening, new from the Manus AI report, 20 Aug 2026). Track B introduces a hard **approval gate**: no patent-scope feature gets *implemented* until M1+M2+M3 agree on architecture. Solo work on Track B is therefore **prep/draft only** — designed to walk into that meeting with something concrete, not to jump ahead of the team.

---

## Track A — Real-Capture Validation (in progress)

| # | Task | Status |
|---|---|---|
| A1 | Apply `window_start_epoch` exclusion fix in `verify_real_capture_schema.py` | 🔴 Not applied — one-line change, drafted twice already |
| A2 | Investigate `AnomalyScorer.__init__` / `ingest_feature_window()` for org-id handling | 🔴 Not started — **read-only**, do not modify `predict_v3.py` |
| A3 | Re-run real-capture validation clean (3rd time) | ⏸ Blocked on A1 + A2 |
| A4 | Fold clean result into `M2_VERIFIED_STATUS.md`, push | ⏸ Blocked on A3 |

## Track A — Priority 2 (queued, not started)

| # | Task | Status |
|---|---|---|
| A5 | 3 unit tests — capture/feature-extraction path | Not started |
| A6 | `capture.py` cross-platform fix (`eth0` hardcode → `scapy.get_if_list()` auto-detect) | Not started — held until A1–A4 close |
| A7 | 60-second demo recording | Not started |

## Track A — Lower priority / blocked

| # | Task | Status |
|---|---|---|
| A8 | Digital twin sim (`sim/run_simulation.py`, needs WSL2) | Not started, low urgency |
| A9 | `bridge.py` real ESP32 test | ⏸ **Blocked** — needs M1 hardware, not solo-actionable |

---

## Track B — Patent-Scope Hardening (new, from Manus AI report)

**Cross-team ownership relevant to M2:**

| Feature | M2 role |
|---|---|
| Authenticated anti-replay protocol | **Primary owner** |
| Authenticated multi-node quorum | **Primary owner** |
| Independent trusted controller | Supporting |
| Two compromise signals | Supporting |
| Fail-safe relay topology | Supporting |
| Hardware-backed key invalidation | Supporting |
| Hold-up power | Supporting |
| Containment receipt | Supporting |
| ML as one trusted-controller input | Supporting |
| Final M4 visibility/recovery | Supporting |

**Approval gate (verbatim from the report):** *"No missing patent-scope feature should be integrated until the team agrees on the independent controller, the two-signal policy, the relay safe state, the key-invalidation hardware, the hold-up energy path, and the quorum rules."*

### Solo-prep tasks (draft only — for the architecture meeting, not for merge)

| # | Task | Why solo-doable now |
|---|---|---|
| B1 | Draft the authenticated command envelope proposal: version, sender ID, recipient/scope, message type, sequence/nonce, timestamp, payload, auth tag | M2 is primary owner of this spec — having a draft walks the team into the decision instead of starting from zero |
| B2 | Research + shortlist crypto mechanism options (HMAC vs. ECDSA-based signing) and key-provisioning approach, for the M1+M2 discussion | Research task, no integration risk |
| B3 | Draft quorum state-machine outline: vote collection, threshold, deadline, conflict resolution, peer recovery | M2 is primary owner of quorum |
| B4 | Gap-analysis doc: map M2's *existing* telemetry/health signals (systemd status, bridge health, watchdog) against what each of the 10 features needs from M2 | Pure documentation of current state, useful reference for every subsystem in the meeting |

### Explicitly blocked (do not start)

- Any actual implementation of the authenticated transport, quorum state machine, or key provisioning — blocked by the approval gate until M1+M2+M3 agree on architecture.
- Peer enrollment / trust-root design — depends on the controller decision (Feature 1), which isn't made yet.

---

## Consolidated Solo Priority Queue (do these, in order, before group integration starts)

1. **A1** — Apply the schema fix (5 min)
2. **A2** — Investigate `AnomalyScorer` org-id mechanism, report findings
3. **A3 → A4** — Clean 3rd validation run, push updated `M2_VERIFIED_STATUS.md`
4. **A5** — 3 unit tests
5. **A6** — `capture.py` auto-detect fix
6. **A7** — 60-second demo
7. **B1** — Draft authenticated command envelope (bring to meeting)
8. **B3** — Draft quorum state-machine outline (bring to meeting)
9. **B2** — Crypto mechanism shortlist
10. **B4** — Gap-analysis doc
11. **A8** — Digital twin sim (lowest urgency)
12. Send consolidated status update to Shashwat/Prajwal — **now needs to include both** the real-capture results (A-track) **and** the patent-scope M2-ownership summary (B-track), so the architecture meeting doesn't start blind

## Still blocked, not yours to unblock solo

- **A9** — `bridge.py` real ESP32 test (needs M1 hardware)
- **All Track B implementation** (needs full team architecture agreement per the approval gate)