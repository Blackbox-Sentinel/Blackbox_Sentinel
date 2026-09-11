# PROPOSAL — Disclosed test-mode real-capture validation run

**To:** M3 (Shashwat)
**From:** M2
**Status: DRAFT — asking for sign-off on this plan before any run happens.**

Per `TASK_Real_Capture_Validation.md`'s own option (c): *"An explicitly disclosed, deliberate test-mode change to `BASELINE_DURATION`... This is a code/config change requiring its own review — not a silent tweak."* This document is that review request. No change has been made yet.

## 1. Platform update: blocker (b) is resolved — real capture confirmed on Linux (Codespaces)

`TASK_Real_Capture_Validation.md`'s blocker (b) — `sentinel_pipeline.py` never reaching `_sniff_scapy()` on Windows — does not apply on a non-Windows platform. This was verified this cycle, not assumed:

Evidence relayed from a separate session, running in a GitHub Codespaces container (`os.name == "posix"`, not this win32 session):

```
$ python3 -c "import os; print(os.name)"
posix
$ sudo setcap cap_net_raw,cap_net_admin=eip "$(readlink -f $(which python3))"
$ getcap "$(readlink -f $(which python3))"
/usr/local/python/3.14.2/bin/python3.14 cap_net_admin,cap_net_raw=eip
$ timeout 10 python3 -c "from scapy.all import sniff; pkts = sniff(timeout=10, count=5, iface='eth0'); ..."
Captured 5 packets
Ether / IP / TCP 20.184.175.19:https > 10.0.0.69:34996 A
Ether / IP / TCP 4.150.223.111:https > 10.0.0.69:33902 A
Ether / IP / TCP 10.0.0.69:34890 > 20.184.175.19:https A
```

Independently checked against this repo's actual history rather than taken at face value, given `9b0ce37`:
- The stated HEAD, `01d1678`, is confirmed real and was `origin/main`'s tip at the time — verified via `git log`/`git show` in this session.
- `sentinel_pipeline.py`'s routing guard at `01d1678` is unmodified: `if scapy_available and os.name != "nt":` — no `SENTINEL_FORCE_REAL_CAPTURE`-style bypass, no undisclosed change. On `posix`, this reaches `_sniff_scapy()` with **zero code changes** — unlike `9b0ce37`, which needed an undisclosed guard rewrite that still didn't produce real capture.
- The packet data is structurally inconsistent with `_demo_loop()`'s synthetic fingerprint (fixed `25.0` packets per fixed 1.0s window, repeated identically): the captured IPs vary (`20.184.175.19`, `4.150.223.111`, `10.0.0.69` — Azure ranges consistent with a Codespaces backend, plus real HTTPS ACK traffic), and the `5`-packet count matches the explicit `sniff(count=5)` parameter rather than any suspicious repetition.
- Full 48/48 suite reconfirmed in this session against `origin/main` at `01d1678` (pulled fast-forward from `abd7672`): `48 passed, 1 warning in 5.43s`, no stray processes before/after.

**This changes what this proposal needs to ask for.** Blocker (b) is resolved on a Linux/Codespaces environment without any code change — WSL2 (investigated earlier and left unresolved: not installed, admin elevation unavailable to confirm the platform feature) is no longer the relevant path. The remaining open item is blocker (a) — the `BASELINE_DURATION` wall-clock gate — which is what §2 below actually proposes changing.

## 2. What's proposed

Temporarily set `SENTINEL_BASELINE_SECONDS` to a short, bounded, non-degenerate value — **300 seconds (5 minutes)** — for a single, explicitly time-boxed validation run **on the Codespaces/Linux environment above, where blocker (b) is already resolved**, then revert to the default immediately afterward.

Actual current defaults, confirmed directly in `m3-ml-ledger/src/predict_v3.py:57-58`, not invented:

```python
BASELINE_DURATION = float(os.getenv("SENTINEL_BASELINE_SECONDS", "172800"))
MIN_BASELINE_SAMPLES = int(os.getenv("SENTINEL_MIN_BASELINE_SAMPLES", "2048"))
```

- Before: `BASELINE_DURATION = 172800s` (48h)
- Proposed, for one bounded run: `SENTINEL_BASELINE_SECONDS=300` (5 min)
- After: reverted to `172800` (unset the override / restore default)

**Open question for M3, not decided here:** `predict_v3.py:205` requires *both* `self.profile.ready` (which depends on `MIN_BASELINE_SAMPLES`, default 2048) *and* `elapsed >= BASELINE_DURATION` before local detection activates. At typical capture rates (~1 window/sec), 300 seconds yields roughly 300 windows — short of the 2048-sample default. This proposal does **not** unilaterally pick a `MIN_BASELINE_SAMPLES` value; that's a model-statistics question, not a systems one. Two options, for M3 to choose:
- (a) Leave `MIN_BASELINE_SAMPLES` at its default 2048 and extend the run window until that many eligible samples are actually observed (duration then depends on real traffic volume, not a fixed clock bound), or
- (b) M3 specifies a lower `MIN_BASELINE_SAMPLES` value that is still statistically meaningful for the v3 model's normalization, and that value is used instead of the model default for this run only.

## 3. Why bounded, not near-zero

`9b0ce37`'s claimed "organic validation" set `SENTINEL_MIN_BASELINE_SAMPLES=5` alongside `SENTINEL_BASELINE_SECONDS=5`. The result, verified directly in the reverted telemetry (`GAP_False_Organic_Capture_Claim_9b0ce37.md`): `profile_samples: 5`, and model scores of `61.39` / `61.53` / `61.38` against a `threshold: 0.55` — roughly 110x the threshold, far outside the 0.08–0.93 range every other record in this project's history has shown. A 5-sample baseline can't produce meaningful normalization statistics; the model degenerates rather than calibrates.

A real validation run needs enough baseline samples for the model's normalization to be statistically meaningful — enough to actually calibrate, not just enough to exit the wait loop. That's the entire point of this proposal existing as a reviewed plan instead of an ad hoc override: the *duration* needs to be short enough to be practical to run once, but the *sample count* needs to stay large enough that the resulting scores are real, not degenerate. Whichever option M3 picks in §2 should satisfy that.

## 4. Explicit safeguards

Matching the project's established pattern (per-node keys, disclosed substitution testing, etc.) — all of these apply to any run made under this proposal:

- The run happens on the Codespaces/Linux environment, on a clearly-labeled test/scratch branch — not committed directly to `main`, and not run against this win32 session (which cannot reach `_sniff_scapy()` at all).
- The resulting telemetry is labeled, in any report language, as **"disclosed test-mode capture, bounded window"** — never described as "organic" or as a "48-hour equivalent." It is a real capture-to-model run under an explicitly shortened, disclosed calibration window, not a claim of matching the production 48h behavior.
- `SENTINEL_BASELINE_SECONDS` (and `SENTINEL_MIN_BASELINE_SAMPLES`, if changed per §2) reverted to defaults immediately after the run — no lingering env-var override left active.
- Full 48/48 test suite re-confirmed both before and after the run, on the Codespaces environment.
- **No claim of "M1 unblocked" attached to this run by itself.** At most, this closes one row of `PHASE2_SOFTWARE_VALIDATION_REPORT.md` §4.3 — "Honest real-versus-synthetic model-data provenance" — not the whole M3 gate. The remaining PENDING rows (representative committed two-signal event with organic content, quorum vote path, ESP32 hardware-in-loop) are unaffected by this proposal and still require their own separate resolution.

## 5. Ask

**M3's explicit sign-off on this plan — the Codespaces/Linux platform in §1, the 300s duration, and the `MIN_BASELINE_SAMPLES` choice in §2 — before any run happens.** Not a retroactive review of a run already performed. This is a request for direction, not a notification of action taken.

---
## 6. Execution Record (Post-Approval)
- **Approval:** M3 signed off on the 300s duration on the Codespaces platform with `SENTINEL_MIN_BASELINE_SAMPLES=300`.
- **Manual Run (M2):** The run was executed manually in the Codespace environment. Real capture was confirmed (varying packet counts, real IPs), and the fail-closed gate successfully held `PENDING_EVIDENCE` on anomalies. The local adaptive detector reached 129/300 accepted samples, correctly failing to reach the `ready` state within the 300s traffic constraint. This run stands as the official validation record.
- **Formal Infrastructure Integration (`90a01d5`):** Instead of keeping the capability as a manual script or branch-only hack, M3 codified the disclosed `TEST_MODE` configuration directly on `main` via `SENTINEL_TEST_MODE_FORCE_SCAPY` and `SENTINEL_TEST_MODE_BASELINE_SECONDS`. This formalized the capability for future runs, fully disclosed and opt-in.
