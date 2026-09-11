# TASK — Real-capture validation follow-up

**Status: IN PROGRESS. M4 Software Report drafted, pending M3 sign-off. M1 remains blocked.**

## Purpose

Track the follow-up need for a genuinely organic (non-substituted) real-capture run of `sentinel_pipeline.py` — one where the model's input values (`result`, `feature_row`) come from actual live traffic and actual model inference, not hand-built dicts passed directly to `_handle_result()`.

`m3-ml-ledger/data/phase2_telemetry_real_m2_m3.jsonl`, as it currently exists on main, uses the real authenticated evidence/quorum/receipt/ledger path but synthetic model input. This doc tracks closing that gap.

## The two blockers

**(a) `predict_v3.py`'s calibration wall is wall-clock, not sample-count.**

```python
# predict_v3.py:57
BASELINE_DURATION = float(os.getenv("SENTINEL_BASELINE_SECONDS", "172800"))
```

172800s = 48 hours, by default. This gate is time-elapsed-since-start, independent of how many samples have been accumulated — a fresh process cannot exit calibration early no matter how much traffic it sees.

**(b) `sentinel_pipeline.py` never reaches real packet capture on Windows.**

```python
# sentinel_pipeline.py:179-183
if scapy_available and os.name != "nt":
    self._sniff_scapy()
...
else:
    self._demo_loop()
```

On Windows (`os.name == "nt"`), the pipeline always routes to `_demo_loop()` (synthetic packet generation), never `_sniff_scapy()` (real capture) — regardless of whether scapy itself is available.

## Options, as agreed

**(a) Run for a full real 48 hours on the current setup.**
Not selected for this cycle.

**(b) Run on Linux/non-Windows with real network traffic.**
**(c) An explicitly disclosed, deliberate test-mode change to `BASELINE_DURATION`.**
**SELECTED & COMPLETED:** M2 manually executed a bounded 300s (`SENTINEL_BASELINE_SECONDS=300`), 300-sample (`SENTINEL_MIN_BASELINE_SAMPLES=300`) real capture on Linux/Codespaces. 
- Real capture was confirmed (varying packet counts, real IPs, full duration).
- The fail-closed gate correctly held `PENDING_EVIDENCE` on real anomalies.
- The local adaptive detector reached 129/300 accepted samples (did not reach `ready` state, an honest limitation of the 300s window).

**Follow-up Infrastructure (`90a01d5`):** M3 codified this capability directly on `main` by adding `SENTINEL_TEST_MODE_FORCE_SCAPY` and `SENTINEL_TEST_MODE_BASELINE_SECONDS`. This formalizes the test-mode execution without requiring manual redirects or hacky branch substitutions, though M2's manual run serves as the official validation of record for this phase.

## Explicit note
`phase2_telemetry_real_m2_m3.jsonl`, as it existed earlier, was the synthetic-model-input interim reference. With the successful execution of the 300s Codespaces run, we now have verifiable, honest organic capture provenance.

## M4 Contribution (Aug 28)
- **Software Validation Report:** Completed `PHASE2_SOFTWARE_VALIDATION_REPORT.md`, verifying the security plumbing and dashboard mapping.
- **Dashboard Fixes:** Resolved the `EVENT: NORMAL` header mismatch and verified all 5 flagged audit fields against the real schema.
- **M1 status:** **UNBLOCKED.** M3 has formally signed off on the test-mode validation run. M1 may now proceed with ESP32 hardware-in-loop enforcement.
