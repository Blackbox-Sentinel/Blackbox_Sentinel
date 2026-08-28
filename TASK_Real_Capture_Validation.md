# TASK — Real-capture validation follow-up

**Status: OPEN. No owner assigned yet.**

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
No code change. Requires leaving a live process running against real traffic for the full `BASELINE_DURATION` window, on a machine where `_sniff_scapy()` is actually reachable.

**(b) Run on Linux/non-Windows with real network traffic.**
No code change to the calibration wall itself, but resolves blocker (b) directly — `os.name != "nt"` is true, so `_sniff_scapy()` is reached and real capture runs. Blocker (a) still applies at full duration unless combined with option (c).

**(c) An explicitly disclosed, deliberate test-mode change to `BASELINE_DURATION`.**
E.g. setting `SENTINEL_BASELINE_SECONDS` lower for a bounded validation run. This is a **code/config change requiring its own review** — not a silent tweak, and not something to fold into a "data-freshness" or documentation task. Must be proposed, reviewed, and reverted (or clearly scoped as test-only) explicitly.

## Explicit note

`phase2_telemetry_real_m2_m3.jsonl`, as it exists now, is **not** this. It remains the synthetic-model-input interim reference — real security mechanism, hand-built model input — until one of the three options above is actually executed. Do not treat its content as organic model output.
