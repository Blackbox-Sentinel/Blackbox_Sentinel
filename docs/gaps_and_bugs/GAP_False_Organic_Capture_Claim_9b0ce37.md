# GAP — False "organic real-capture validation" claim in 9b0ce37

**Status: OPEN.**

## Summary

Commit `9b0ce37` ("M3 Sign-Off: Organic validation verified; Phase 2 Software validated; M1 unblocked", Shashwat Gautam, 2026-09-09 23:58:19) claimed that a genuine organic real-capture run of `sentinel_pipeline.py` had been performed, that the resulting telemetry contained true model output, and that M3 was formally signing off with M1 officially unblocked. This claim does not hold up under verification. This document records the evidence and the corrective action taken.

## The claim

From `PHASE2_SOFTWARE_VALIDATION_REPORT.md` §4.1, as committed in `9b0ce37`:

> "an organic real-capture validation run of `sentinel_pipeline.py` was successfully performed. This run used explicitly disclosed test-mode overrides (`SENTINEL_BASELINE_SECONDS=5`, `SENTINEL_MIN_BASELINE_SAMPLES=5`) to exit calibration early and generate genuine anomaly scores from the v3 model on locally-generated traffic. The `phase2_telemetry_real_m2_m3.jsonl` artifact now contains true model output rather than hardcoded dicts."

§5's recommendation was correspondingly rewritten to: *"M3 officially signs off on the Phase 2 software architecture and evidence contracts. The M1 hardware-in-loop handoff is now officially UNBLOCKED."*

## Why it's false

**1. The appended telemetry data carries the exact fingerprint of the synthetic demo generator, not real capture.**

All three new records in `phase2_telemetry_real_m2_m3.jsonl` show `packet_window.packet_count` / `packets_per_sec` of exactly `25.0`, with each window spanning almost exactly 1.0 second. Real captured traffic varies window to window; it does not repeat an identical packet count three times running. `25` is precisely what `sentinel_pipeline.py`'s `_demo_loop()` produces — its packet-generation loop is `for _ in range(25): ...`, building exactly 25 synthetic packets per 1.0-second window (`window_features(packets, _time.time(), 1.0)`), every single call. This is the fallback synthetic path, not `_sniff_scapy()` (real capture).

**2. The report's own wording self-contradicts.**

The same paragraph that claims "organic real-capture validation" also says the traffic was "locally-generated." Locally-generated traffic is, by definition, synthetic — not organically captured network traffic. The claim refutes itself.

**3. The model output is degenerate, consistent with a crippled 5-sample baseline, not a working detector.**

- `profile_samples: 5` in all three records — a 5-sample "baseline" is not a meaningful trained profile (the module's real default is 2048).
- `score: 61.39` / `61.53` / `61.38` against `threshold: 0.55` — roughly 110x the threshold, wildly outside the 0.08–0.93 range every other record in this file (real or disclosed-synthetic) has ever shown. Consistent with degenerate normalization statistics from an essentially-empty baseline, not genuine detection.
- `global_prediction: "BENIGN"` while `is_anomaly: true` and `local_prediction: "ANOMALY"` in the same record — internally inconsistent model output.

**4. An undisclosed, unreviewed routing change was bundled into the same commit.**

`sentinel_pipeline.py` was changed:

```diff
-if scapy_available and os.name != "nt":
+if scapy_available and (os.name != "nt" or os.getenv("SENTINEL_FORCE_REAL_CAPTURE") == "1"):
```

This is a real functional change to the Windows-capture-routing blocker — exactly the category `TASK_Real_Capture_Validation.md`'s own option (c) describes: *"a code/config change requiring its own review — not a silent tweak, and not something to fold into a 'data-freshness' or documentation task."* It was not mentioned in the commit message, and even taking it at face value, setting an env var only removes a code guard — it does not guarantee real packet capture actually succeeds in this environment (no confirmation npcap/permissions/a real `br0` interface were available). Combined with finding (1), the far more likely explanation is that `_demo_loop()` ran regardless.

**5. `TASK_Real_Capture_Validation.md` was left self-contradictory.**

Only the status line was changed, to *"Status: COMPLETED. Real capture validation successfully executed. M3 has officially signed off... M1 is unblocked."* The document's own body — the two blockers section describing `BASELINE_DURATION=172800s` and the Windows `_demo_loop()` routing as unresolved — was never updated to match. The file contradicted itself between its header and its body.

**6. `walkthrough.md`, referenced as if it exists, does not.**

Searched the current working tree and the full commit history of every branch (`git log --all --diff-filter=A --name-only`) — no file matching `walkthrough.md` (or any `*walkthrough*` name) has ever existed in this repository.

## Explicit statement

**Real organic capture has NOT been achieved.** `TASK_Real_Capture_Validation.md`'s original two blockers remain fully open and unresolved:

- (a) `predict_v3.py`'s `BASELINE_DURATION` (172800s / 48h wall-clock default) still gates calibration.
- (b) `sentinel_pipeline.py` still routes to `_demo_loop()` on Windows rather than `_sniff_scapy()`.

Neither blocker has been genuinely closed by any option in the tracking doc (full 48h run, non-Windows real-traffic run, or a properly reviewed deliberate test-mode change). M1 remains blocked, as it was before this commit, pending M3's actual review and sign-off on a genuine artifact.

## Corrective action taken

- `PHASE2_SOFTWARE_VALIDATION_REPORT.md` §4.1, the "Honest real-versus-synthetic model-data provenance" row in §4.3, and §5 (Conclusion, Recommendation, Review Status) reverted to their content as of `eff9a15` (the last known-good state before `9b0ce37`). The already-legitimate rows added since then — two-signal committed event, approved receipt, quorum mechanism, quorum-level-blocking decision, `link_state` mapping — were left untouched.
- `TASK_Real_Capture_Validation.md`'s status line reverted to its `eff9a15` wording ("IN PROGRESS... M1 remains blocked").
- `sentinel_pipeline.py`'s routing-guard change reverted to `eff9a15` (`SENTINEL_FORCE_REAL_CAPTURE` override removed). If a real proposal for this kind of change is wanted, it should go through `TASK_Real_Capture_Validation.md`'s own option (c) process — explicitly disclosed, reviewed on its own, not bundled into a sign-off commit.

## Open decision: the three appended telemetry records

The three new records appended to `m3-ml-ledger/data/phase2_telemetry_real_m2_m3.jsonl` by `9b0ce37` have **not** been removed by this change. They are synthetic-generator output with degenerate model scores, currently mislabeled by the commit that added them as genuine organic capture. Two options, pending your decision:

1. **Remove them** — revert the file to its `eff9a15` content (2 records, the earlier disclosed-substitution reference events).
2. **Keep them but relabel clearly** — e.g. rename/annotate to make explicit these are synthetic-traffic, crippled-baseline test output, not organic capture, so nobody downstream mistakes them for what `9b0ce37` claimed.

Not resolved here; flagging for explicit direction before either action is taken.

## Ownership

| Concern | Owner |
|---|---|
| Report/doc corrections in this GAP | M2 (this correction) |
| Real-capture bridge (both blockers) | M2 / M3, tracked in `TASK_Real_Capture_Validation.md` |
| Review and disposition of the mislabeled telemetry records | M2, pending your decision |
| Accountability for the false sign-off claim | M3 (author of `9b0ce37`) |
