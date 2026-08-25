# M2 Verified Status

**Verification timestamp:** 2026-08-22 07:20:56 UTC

This document records three verification checks performed against the
`m3-v3-integration` branch, with raw, unedited command output captured
during this session.

---

## 1. Environment / branch state

Command:
```
git status && git branch --show-current && git rev-parse --abbrev-ref --symbolic-full-name @{u} && git status -sb
```

Raw output:
```
On branch m3-v3-integration
Your branch is up to date with 'origin/m3-v3-integration'.

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	ml/adaptive_profiles/
	pipeline_raw.txt

nothing added to commit but untracked files present (use "git add" to track)
---BRANCH---
m3-v3-integration
---REMOTE---
origin/m3-v3-integration
## m3-v3-integration...origin/m3-v3-integration
?? ml/adaptive_profiles/
?? pipeline_raw.txt
```

Result: clean, on `m3-v3-integration`, up to date with `origin/m3-v3-integration`.
Only untracked scratch/generated files present (`ml/adaptive_profiles/`,
`pipeline_raw.txt`) — no modified or staged files.

---

## 2. capture.py (m2-systems/src/capture.py)

Command:
```
"venv/Scripts/python.exe" m2-systems/src/capture.py
```

Raw output:
```
WARNING: No libpcap provider available ! pcap won't be used
C:\Users\suhan shetty\Projects\Blackbox_Sentinel\venv\Lib\site-packages\scapy\layers\tls\crypto\groups.py:25: CryptographyDeprecationWarning: Diffie-Hellman over finite fields (FFDH) is deprecated and support will be removed in a future release. Use a more modern key exchange algorithm.
  from cryptography.hazmat.primitives.asymmetric.dh import DHParameterNumbers
=== BlackBox Sentinel M2 — Packet Capture ===
Interface: eth0
Output: c:\Users\suhan shetty\Projects\Blackbox_Sentinel\m2-systems\src\..\..\m3-ml-ledger\data\capture_20260822_125053.pcap
Capturing 1000 packets...

Traceback (most recent call last):
  File "c:\Users\suhan shetty\Projects\Blackbox_Sentinel\m2-systems\src\capture.py", line 47, in <module>
    run_capture()
    ~~~~~~~~~~~^^
  File "c:\Users\suhan shetty\Projects\Blackbox_Sentinel\m2-systems\src\capture.py", line 36, in run_capture
    packets = sniff(
        iface=CAPTURE_INTERFACE,
        count=CAPTURE_COUNT,
        prn=packet_callback
    )
  File "C:\Users\suhan shetty\Projects\Blackbox_Sentinel\venv\Lib\site-packages\scapy\sendrecv.py", line 1438, in sniff
    sniffer._run(*args, **kwargs)
    ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
  File "C:\Users\suhan shetty\Projects\Blackbox_Sentinel\venv\Lib\site-packages\scapy\sendrecv.py", line 1283, in _run
    sniff_sockets[_RL2(iface)(type=ETH_P_ALL, iface=iface,
                  ~~~~^^^^^^^
  File "C:\Users\suhan shetty\Projects\Blackbox_Sentinel\venv\Lib\site-packages\scapy\sendrecv.py", line 1268, in <lambda>
    _RL2 = lambda i: L2socket or resolve_iface(i).l2listen()  # type: Callable[[_GlobInterfaceType], Callable[..., SuperSocket]]  # noqa: E501
                                 ~~~~~~~~~~~~~^^^
  File "C:\Users\suhan shetty\Projects\Blackbox_Sentinel\venv\Lib\site-packages\scapy\interfaces.py", line 437, in resolve_iface
    return resolve_iface(dev, retry=False)
  File "C:\Users\suhan shetty\Projects\Blackbox_Sentinel\venv\Lib\site-packages\scapy\interfaces.py", line 434, in resolve_iface
    raise ValueError("Interface '%s' not found !" % dev)
ValueError: Interface 'eth0' not found !
```

Result: fails with the expected `ValueError: Interface 'eth0' not found !`
— this is the correct/expected result on a machine with no `eth0` NIC, not
a bug.

---

## 3. Full pipeline (sentinel_pipeline.py)

Command:
```
"venv/Scripts/python.exe" sentinel_pipeline.py
```
(run for ~15 seconds, then stopped)

Raw output:
```
WARNING: No libpcap provider available ! pcap won't be used
C:\Users\suhan shetty\Projects\Blackbox_Sentinel\venv\Lib\site-packages\scapy\layers\tls\crypto\groups.py:25: CryptographyDeprecationWarning: Diffie-Hellman over finite fields (FFDH) is deprecated and support will be removed in a future release. Use a more modern key exchange algorithm.
  from cryptography.hazmat.primitives.asymmetric.dh import DHParameterNumbers
=================================================================
  🛡️  BlackBox Sentinel — Autonomous Edge Defense Node (AEDN-NODE-01)
=================================================================
[HAL] Initializing Hardware Abstraction Layer in mode: [SIM]
[HAL-SIM] [RELAY] Relay initialized in ENGAGED state (data line connected)
[HAL-SIM] [TAMPER] Monitor active (Grid continuous)
[HAL-SIM] [LED] Status LED initialized (OFF)
[HAL-SIM] [CELLULAR] SIM800L Modem: Registered to SIMULATED-2G-GSM Network (RSSI: 24/31)
[HAL-SIM] [MESH] ESP-NOW Radio: Node 'AEDN-NODE-01' listening on UDP loopback :39999
[SCORER] Loaded v3 model (45 features) — threshold: 0.55
[SCORER] Organization profile: default_organization — 130 accepted windows, ready=False
[PIPELINE] Node ID:    AEDN-NODE-01
[PIPELINE] Ledger:     C:\Users\suhan shetty\Projects\Blackbox_Sentinel\m3-ml-ledger\data\sentinel_ledger.json
[PIPELINE] Interface:  br0
[PIPELINE] HAL Mode:   SIM

[HAL-SIM] [LED] [OFF] — System Calibrating / Idle
[CALIBRATE] Learning organization default_organization for 172800s; local alerts remain disabled during warm-up
[PIPELINE] Network interface capture not active — launching synthetic traffic loop
[DEMO] Streaming simulated enterprise traffic through v3 windows...

  [CALIBRATE] 131 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 133 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 135 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 137 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 139 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 141 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 143 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 145 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 147 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 149 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 151 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 153 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 155 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 157 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 159 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 161 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 163 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 165 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 167 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 169 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 171 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 173 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 175 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 177 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 179 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 181 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 183 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 185 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 187 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 189 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 191 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 193 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 195 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 197 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 199 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 201 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 203 accepted baseline windows | local detection enabled=False
  [CALIBRATE] 205 accepted baseline windows | local detection enabled=False
```

Result: HAL initialized in SIM mode, 45-feature v3 model loaded, calibration
counted up past 200 accepted baseline windows with no exceptions, process
was stopped cleanly (no crash).

---

## Notes

This run used synthetic/demo traffic — no libpcap/Npcap installed, so real
packet capture on br0 was not exercised. Real-capture validation against the
45-feature schema remains a separate, not-yet-completed task.

capture.py and bridge.py are not currently used by sentinel_pipeline.py — it
has its own internal capture loop.

---

## 22 Aug 2026, continued

### 4. Real-capture schema validation (verify_real_capture_schema.py)

**Initial run — false positive.**

Command:
```
"venv/Scripts/python.exe" verify_real_capture_schema.py --iface "RZ616 Wi-Fi 6E 160MHz" --windows 10 --org-id organization_a
```

Raw output (excerpt — all 10 windows identical pattern):
```
[INFO] Expecting 45 features per window.
[SCORER] Loaded v3 model (45 features) — threshold: 0.55
[SCORER] Organization profile: default_organization — 189 accepted windows, ready=False
[CAPTURE] Window 1/10 on iface='RZ616 Wi-Fi 6E 160MHz' ...
  -> features=46/45 schema_ok=False scored=calibrating
...
[DONE] Report written to C:\Users\suhan shetty\Projects\Blackbox_Sentinel\m2_real_capture_schema_report.json
[SUMMARY] all_schema_ok=False empty_windows=0
```

Report excerpt (`m2_real_capture_schema_report.json`):
```json
{
  "window": 0,
  "feature_count": 46,
  "expected_count": 45,
  "missing_features": [],
  "extra_features": ["window_start_epoch"],
  "schema_ok": false
}
```

**Root cause:** `verify_real_capture_schema.py` line 82 computed
`actual_keys = set(feature_row.keys()) - {"timestamp"}`, which did not
exclude the live-capture-only field `window_start_epoch` (present in
`feature_pipeline_v2.capture_live_window`'s output but not in
`model_feature_columns()`'s expected schema). Real capture was working
correctly the whole time — this was a diagnostic-script bug, not a
capture or model problem.

**Fix applied (one line, verify_real_capture_schema.py:82):**
```diff
-        actual_keys = set(feature_row.keys()) - {"timestamp"}
+        actual_keys = set(feature_row.keys()) - {"timestamp", "window_start_epoch"}
```

**Re-run after fix — clean.**

Command:
```
"venv/Scripts/python.exe" verify_real_capture_schema.py --iface "RZ616 Wi-Fi 6E 160MHz" --org-id organization_a --windows 10
```

Raw output:
```
[INFO] Expecting 45 features per window.
[SCORER] Loaded v3 model (45 features) — threshold: 0.55
[SCORER] Organization profile: default_organization — 189 accepted windows, ready=False
[CAPTURE] Window 1/10 on iface='RZ616 Wi-Fi 6E 160MHz' ...
  -> features=45/45 schema_ok=True scored=calibrating
[CAPTURE] Window 2/10 on iface='RZ616 Wi-Fi 6E 160MHz' ...
  -> features=45/45 schema_ok=True scored=calibrating
[CAPTURE] Window 3/10 on iface='RZ616 Wi-Fi 6E 160MHz' ...
  -> features=45/45 schema_ok=True scored=calibrating
[CAPTURE] Window 4/10 on iface='RZ616 Wi-Fi 6E 160MHz' ...
  -> features=45/45 schema_ok=True scored=calibrating
[CAPTURE] Window 5/10 on iface='RZ616 Wi-Fi 6E 160MHz' ...
  -> features=45/45 schema_ok=True scored=calibrating
[CAPTURE] Window 6/10 on iface='RZ616 Wi-Fi 6E 160MHz' ...
  -> features=45/45 schema_ok=True scored=calibrating
[CAPTURE] Window 7/10 on iface='RZ616 Wi-Fi 6E 160MHz' ...
  -> features=45/45 schema_ok=True scored=calibrating
[CAPTURE] Window 8/10 on iface='RZ616 Wi-Fi 6E 160MHz' ...
  -> features=45/45 schema_ok=True scored=calibrating
[CAPTURE] Window 9/10 on iface='RZ616 Wi-Fi 6E 160MHz' ...
  -> features=45/45 schema_ok=True scored=calibrating
[CAPTURE] Window 10/10 on iface='RZ616 Wi-Fi 6E 160MHz' ...
  -> features=45/45 schema_ok=True scored=calibrating

[DONE] Report written to C:\Users\suhan shetty\Projects\Blackbox_Sentinel\m2_real_capture_schema_report.json
[SUMMARY] all_schema_ok=True empty_windows=0
```

Result: **10/10 windows, features=45/45, schema_ok=True, empty_windows=0.**
Real captured traffic on a live Wi-Fi interface (`RZ616 Wi-Fi 6E 160MHz`,
192.168.1.6) produces valid 45-feature v3 windows.

---

### 5. Organization ID handling — two issues found and resolved

**Issue A: `verify_real_capture_schema.py` never passed `organization_id`
into `AnomalyScorer()`.**

Before (verify_real_capture_schema.py:63):
```python
scorer = AnomalyScorer()
```

`--org-id organization_a` was only ever stuffed into
`row_for_scorer["organization_id"]` (a per-call feature-row field), which
`AnomalyScorer.ingest_feature_window()` never reads — confirmed by reading
`m3-ml-ledger/src/predict_v3.py:160-236`, which only ever uses
`self.organization_id` (set once at construction) in its output, never
`feature_row["organization_id"]`. This produced
`"organization_id": "default_organization"` in every scorer result despite
`--org-id organization_a` being passed on the command line.

**Fix applied (one line, verify_real_capture_schema.py:63):**
```diff
-    scorer = AnomalyScorer()
+    scorer = AnomalyScorer(organization_id=org_id)
```

**Issue B (new finding): `organization_id` passed to `AnomalyScorer()` only
sets an output label — it does not control which profile file loads.**

Applying the Issue A fix alone crashed:

Command:
```
"venv/Scripts/python.exe" verify_real_capture_schema.py --iface "RZ616 Wi-Fi 6E 160MHz" --org-id organization_a --windows 10
```

Raw output:
```
[INFO] Expecting 45 features per window.
[SCORER] Loaded v3 model (45 features) — threshold: 0.55
Traceback (most recent call last):
  File "c:\Users\suhan shetty\Projects\Blackbox_Sentinel\verify_real_capture_schema.py", line 150, in <module>
    main()
  File "c:\Users\suhan shetty\Projects\Blackbox_Sentinel\verify_real_capture_schema.py", line 146, in main
    run_live(args.iface, args.windows, args.org_id)
  File "c:\Users\suhan shetty\Projects\Blackbox_Sentinel\verify_real_capture_schema.py", line 63, in run_live
    scorer = AnomalyScorer(organization_id=org_id)
  File "C:\Users\suhan shetty\Projects\Blackbox_Sentinel\m3-ml-ledger\src\predict_v3.py", line 92, in __init__
    self._load_profile()
  File "C:\Users\suhan shetty\Projects\Blackbox_Sentinel\m3-ml-ledger\src\predict_v3.py", line 114, in _load_profile
    self.profile = AdaptiveBaseline.load_or_create(
  File "C:\Users\suhan shetty\Projects\Blackbox_Sentinel\ml\adaptive_baseline.py", line 345, in load_or_create
    raise ValueError(
ValueError: Profile organization_id does not match requested organization
```

**Root cause:** `predict_v3.py:54-60` computes `PROFILE_PATH` as a
module-level constant at import time, from the `SENTINEL_ORGANIZATION_ID`
env var (default `"default_organization"`) — independent of whatever
`organization_id` is passed to `AnomalyScorer(organization_id=...)` at
construction time:
```python
ORGANIZATION_ID = os.getenv("SENTINEL_ORGANIZATION_ID", "default_organization")
PROFILE_PATH = Path(
    os.getenv(
        "SENTINEL_PROFILE_PATH",
        str(ML_ROOT / "adaptive_profiles" / f"{ORGANIZATION_ID}_profile.json"),
    )
)
```
`AdaptiveBaseline.load_or_create` (`ml/adaptive_baseline.py:330-358`) then
loads whatever profile sits at that fixed path and validates its stored
`organization_id` against the constructor argument — since `PROFILE_PATH`
resolved to `default_organization_profile.json` (env var unset) but the
constructor argument was `"organization_a"`, the two disagree and it
raises.

**Workaround used to complete validation** — set the env var before
import so `PROFILE_PATH` resolves consistently with the constructor arg:

Command:
```
$env:SENTINEL_ORGANIZATION_ID = "organization_a"
venv\Scripts\python.exe verify_real_capture_schema.py --iface "RZ616 Wi-Fi 6E 160MHz" --org-id organization_a --windows 10
```

Raw output:
```
[INFO] Expecting 45 features per window.
[SCORER] Loaded v3 model (45 features) — threshold: 0.55
[SCORER] Organization profile: organization_a — 0 accepted windows, ready=False
[CAPTURE] Window 1/10 on iface='RZ616 Wi-Fi 6E 160MHz' ...
  -> features=45/45 schema_ok=True scored=calibrating
[CAPTURE] Window 2/10 on iface='RZ616 Wi-Fi 6E 160MHz' ...
  -> features=45/45 schema_ok=True scored=calibrating
[CAPTURE] Window 3/10 on iface='RZ616 Wi-Fi 6E 160MHz' ...
  -> features=45/45 schema_ok=True scored=calibrating
[CAPTURE] Window 4/10 on iface='RZ616 Wi-Fi 6E 160MHz' ...
  -> features=45/45 schema_ok=True scored=calibrating
[CAPTURE] Window 5/10 on iface='RZ616 Wi-Fi 6E 160MHz' ...
  -> features=45/45 schema_ok=True scored=calibrating
[CAPTURE] Window 6/10 on iface='RZ616 Wi-Fi 6E 160MHz' ...
  -> features=45/45 schema_ok=True scored=calibrating
[CAPTURE] Window 7/10 on iface='RZ616 Wi-Fi 6E 160MHz' ...
  -> features=45/45 schema_ok=True scored=calibrating
[CAPTURE] Window 8/10 on iface='RZ616 Wi-Fi 6E 160MHz' ...
  -> features=45/45 schema_ok=True scored=calibrating
[CAPTURE] Window 9/10 on iface='RZ616 Wi-Fi 6E 160MHz' ...
  -> features=45/45 schema_ok=True scored=calibrating
[CAPTURE] Window 10/10 on iface='RZ616 Wi-Fi 6E 160MHz' ...
  -> features=45/45 schema_ok=True scored=calibrating

[DONE] Report written to C:\Users\suhan shetty\Projects\Blackbox_Sentinel\m2_real_capture_schema_report.json
[SUMMARY] all_schema_ok=True empty_windows=0
```

Result: clean — `organization_id` label now correctly reads
`organization_a`, 10/10 windows schema_ok=True.

**Correction (added later in this session):** this section originally
claimed the profile was "created fresh at
`ml/adaptive_profiles/organization_a_profile.json`." That was asserted
from the `[SCORER] Organization profile: organization_a — 0 accepted
windows` log line alone, without verifying the file actually existed on
disk — an inference, not a checked fact. A filesystem-wide search
performed at that point in the session confirmed **no
`organization_a_profile.json` (or `_state.json`) existed anywhere on this
machine** — `ml/adaptive_profiles/` contained only
`default_organization_profile.json`/`default_organization_state.json`.

**Why the file didn't exist yet:** `predict_v3.py:63` sets
`PROFILE_SAVE_INTERVAL = int(os.getenv("SENTINEL_PROFILE_SAVE_INTERVAL", "60"))`,
and `predict_v3.py:217-218` only calls `self.profile.save(self.profile_path)`
when `self.window_count % PROFILE_SAVE_INTERVAL == 0`. Every run up to
that point used `--windows 10`, so window count never reached a multiple
of 60 within a single run, and `verify_real_capture_schema.py`'s
`run_live()` never calls `scorer.save_profile()` at the end either — so
persistence to disk was never actually triggered. The `[SCORER]
Organization profile: ... — 0 accepted windows` line reflects a
freshly-**constructed in-memory** `AdaptiveBaseline` object each run
(`AdaptiveBaseline.load_or_create()`'s create-new-profile branch is
`return cls(...)`, with no disk write), not a persisted file.

**Update — now resolved with real evidence, not just corrected to
"unknown."** A follow-up `--windows 60` run (window count crosses the
`PROFILE_SAVE_INTERVAL` threshold) actually triggered persistence:
`organization_a_profile.json`/`organization_a_state.json` are now
confirmed created and growing across two consecutive `--windows 60` runs
(`82826 → 159892` bytes), while `default_organization_profile.json`/
`default_organization_state.json` are confirmed **byte-identical and
mtime-unchanged** across all three checkpoints in this session — proving
genuine per-organization separation, not just coexistence. Separately,
`ml/M3_INTERFACE.md`'s documented `scorer_result` contract (16 fields:
`state`, `score`, `probability_attack`, `threshold`, `is_anomaly`,
`global_prediction`, `local_prediction`, `local_detection_enabled`,
`organization_id`, `profile_ready`, `profile_samples`,
`eligible_for_learning`, `local_score`, `top_local_features`,
`feature_count`, `timestamp`) was checked field-by-field against the
actual report output — **exact match, no extras, none missing**,
confirmed stable across both the `--windows 10` and `--windows 60` runs.
Full evidence (byte counts, mtimes, before/after comparisons) is in
section 8, below.

**What was confirmed correct even before this update:** the org-scoping
*logic* itself was never in question — `organization_id` read
`organization_a` correctly throughout, in both the `[SCORER]` line and
every `scorer_result`. Only the "written to disk" claim was unverified at
the time; it's now independently confirmed true.

**Flag — M3-owned interface gap (predict_v3.py / adaptive_baseline.py),
not blocking:** `AnomalyScorer(organization_id=...)` and the
`SENTINEL_ORGANIZATION_ID` env var are two independent inputs that are
expected to agree but are never validated against each other until
`AdaptiveBaseline.load_or_create` throws. There is no supported way to
select a per-org profile purely via the constructor argument — the env
var (read once, at module import) is authoritative for `PROFILE_PATH`.
This is fine for the current single-process, single-org-per-run deployment
model, but per-org profile isolation should be revisited before Week 7
integration if multi-org support at the object level (e.g. one process
scoring multiple orgs, or object-level org switching without a process
restart) is required.

**Update — Issue B: RESOLVED**, by commit
`d45a1c3abb1fa9e687d5e984b75b89383d1e4a97` ("Fix M3 organization identity
and document v3 interface", Shashwat Gautam, 22 Aug 2026 23:06:07 +0530),
touching `m3-ml-ledger/src/predict_v3.py` and adding `ml/M3_INTERFACE.md`.

**Mechanically:** the fix removes the module-level `PROFILE_PATH`/
`STATE_FILE` constants that were previously computed once at import time
from the `SENTINEL_ORGANIZATION_ID` env var, decoupled from whatever
`organization_id` got passed to `AnomalyScorer.__init__()` — that
decoupling was the root cause of Issue B. In their place,
`self.organization_id` and `self.profile_path`/`self.state_file` are now
derived together, per-instance, inside `__init__`:

```python
explicit_organization = organization_id is not None
requested_organization = organization_id or os.getenv(
    "SENTINEL_ORGANIZATION_ID", DEFAULT_ORGANIZATION
)
self.organization_id = safe_organization_name(requested_organization)
...
self.profile_path = profile_root / f"{self.organization_id}_profile.json"
```

`_load_profile()`, `_save_state()`, `save_profile()`, and the periodic
save inside `ingest_feature_window()` all switched from the old module
constants to `self.profile_path`/`self.state_file`. When `organization_id`
is passed explicitly to the constructor, it now directly determines which
profile file loads — the two values that used to be able to disagree are
structurally the same value. `AnomalyScorer(organization_id="organization_a")`
no longer crashes with `ValueError: Profile organization_id does not
match requested organization`.

**Confirmed: nothing from this session's earlier validation was broken.**
The env-var fallback still works — when `organization_id` is *not* passed
explicitly, `requested_organization` falls back to `SENTINEL_ORGANIZATION_ID`
exactly as before, and `SENTINEL_PROFILE_PATH`/`SENTINEL_V3_STATE_FILE`
overrides are still honored in that case too. The `$env:SENTINEL_ORGANIZATION_ID
= "organization_a"` workaround this session used earlier in this section
still produces the same result under the new code.

**`verify_real_capture_schema.py`'s own fix now works standalone.** Our
A2 fix (`scorer = AnomalyScorer(organization_id=org_id)`, line 63,
documented above under "Issue A") was correct all along but only
succeeded when paired with the env-var workaround, because of Issue B.
With Issue B resolved, that same line now works on its own — the
`$env:SENTINEL_ORGANIZATION_ID` workaround is no longer necessary for
`verify_real_capture_schema.py`, though it remains harmless if still set.

---

### 6. capture.py cross-platform fix (m2-systems/src/capture.py)

**Problem:** `m2-systems/src/capture.py:14` hardcoded
`CAPTURE_INTERFACE = "eth0"` — a Linux-only interface name, module-level
constant, no CLI arg, no env var. On this Windows machine it failed with
`ValueError: Interface 'eth0' not found !`, which was already documented
(section 2, above) as the correct/expected failure, not a bug to patch
around. The real fix is auto-detection.

Confirmed nothing else in the repo reads this constant before touching it:

Command:
```
grep -rn "CAPTURE_INTERFACE" .
```

Raw output:
```
m2-systems\src\capture.py:14:CAPTURE_INTERFACE = "eth0"  # Change to your network interface
m2-systems\src\capture.py:32:    print(f"Interface: {CAPTURE_INTERFACE}")
m2-systems\src\capture.py:37:        iface=CAPTURE_INTERFACE,
M2_VERIFIED_STATUS.md:67:        iface=CAPTURE_INTERFACE,
sentinel_pipeline.py:45:CAPTURE_INTERFACE = os.getenv("SENTINEL_INTERFACE", "br0")
sentinel_pipeline.py:90:            "interface": CAPTURE_INTERFACE,
sentinel_pipeline.py:96:        print(f"[PIPELINE] Interface:  {CAPTURE_INTERFACE}")
sentinel_pipeline.py:139:            f"{CAPTURE_INTERFACE}..."
sentinel_pipeline.py:144:                iface=CAPTURE_INTERFACE,
```
`sentinel_pipeline.py`'s `CAPTURE_INTERFACE` is a separate, unrelated
module-level constant (`SENTINEL_INTERFACE` env var, default `"br0"`) —
no import relationship to `capture.py`'s. `M2_VERIFIED_STATUS.md:67` is
this document's own quoted traceback text, non-executing. Safe to remove.

**Attempt 1 — auto-detect via plain `get_if_list()`, discovered broken on
Windows.**

First implementation filtered `scapy.all.get_if_list()` for non-loopback
names, auto-picking on exactly one candidate. Running it with no `--iface`:

Raw output:
```
[FATAL] Multiple candidate interfaces found — cannot auto-select confidently.
Available interfaces (pass one via --iface):
  \Device\NPF_{A2130613-5A3A-4667-99B0-0D6A313025B8}
  \Device\NPF_{EDABC4FE-0193-46F2-96CC-AC8F940F3639}
  \Device\NPF_{BB0E457F-ADE2-432F-96E5-042FEEB61ECD}
  \Device\NPF_{9015EF72-8B07-4C72-AD8D-0BD1830C96FD}
  \Device\NPF_{BE306130-9D05-4E95-ADF0-970E299178AE}
  \Device\NPF_{EEB984AB-8070-4B5C-8C9F-C776E17B7B4C}
  \Device\NPF_{703F8E8F-1D06-4320-BA10-9CF774B70B5F}
  \Device\NPF_Loopback

[exited with code 1]
```

**Root cause:** on Windows, plain `get_if_list()` returns raw NPF device
GUIDs (`\Device\NPF_{...}`), not human-friendly names like
`"RZ616 Wi-Fi 6E 160MHz"`. 7 real devices remain after loopback filtering,
so the "exactly one candidate" auto-pick logic can never fire from this
data — always ambiguous.

**Investigation: `get_windows_if_list()` field structure.**

Command:
```
"venv/Scripts/python.exe" -m pip show scapy
```
Raw output:
```
Name: scapy
Version: 2.7.0
Summary: Scapy: interactive packet manipulation tool
Home-page: https://scapy.net
Author: Philippe BIONDI, Gabriel POTTER
Author-email:
License: GPL-2.0-only
Location: C:\Users\suhan shetty\Projects\Blackbox_Sentinel\venv\Lib\site-packages
Requires:
Required-by:
```

Command:
```
"venv/Scripts/python.exe" -c "
from scapy.arch.windows import get_windows_if_list
ifaces = get_windows_if_list()
print(f'TYPE: {type(ifaces)}')
print(f'COUNT: {len(ifaces)}')
for i, iface in enumerate(ifaces):
    print(f'--- interface {i} ---')
    print(f'  raw dict: {iface}')
    print(f'  keys: {sorted(iface.keys())}')
"
```
Raw output: `TYPE: <class 'list'>`, `COUNT: 50`. Every entry shares the
same keys: `['description', 'guid', 'index', 'ips', 'ipv4_metric',
'ipv6_metric', 'mac', 'name', 'nameservers', 'type']`. Full raw dump:
```
--- interface 0 ---
  raw dict: {'name': 'Ethernet', 'index': 6, 'description': 'VirtualBox Host-Only Ethernet Adapter', 'guid': '{703F8E8F-1D06-4320-BA10-9CF774B70B5F}', 'mac': '0a:00:27:00:00:06', 'type': 6, 'ipv4_metric': 25, 'ipv6_metric': 25, 'ips': ['fe80::653a:dd29:bc9:fea8', '192.168.56.1'], 'nameservers': ['fec0:0:0:ffff::1', 'fec0:0:0:ffff::2', 'fec0:0:0:ffff::3']}
--- interface 1 ---
  raw dict: {'name': 'Local Area Connection* 1', 'index': 18, 'description': 'Microsoft Wi-Fi Direct Virtual Adapter', 'guid': '{EEB984AB-8070-4B5C-8C9F-C776E17B7B4C}', 'mac': 'ae:f2:3c:54:db:85', 'type': 71, 'ipv4_metric': 25, 'ipv6_metric': 25, 'ips': ['fe80::739a:b3f8:bde2:a485', '169.254.108.237'], 'nameservers': ['fec0:0:0:ffff::1', 'fec0:0:0:ffff::2', 'fec0:0:0:ffff::3']}
--- interface 2 ---
  raw dict: {'name': 'Local Area Connection* 2', 'index': 14, 'description': 'Microsoft Wi-Fi Direct Virtual Adapter #2', 'guid': '{BE306130-9D05-4E95-ADF0-970E299178AE}', 'mac': 'ae:f2:3c:54:cb:95', 'type': 71, 'ipv4_metric': 25, 'ipv6_metric': 25, 'ips': ['fe80::ad87:9651:98cc:7ba1', '169.254.49.65'], 'nameservers': ['fec0:0:0:ffff::1', 'fec0:0:0:ffff::2', 'fec0:0:0:ffff::3']}
--- interface 3 ---
  raw dict: {'name': 'Wi-Fi', 'index': 8, 'description': 'RZ616 Wi-Fi 6E 160MHz', 'guid': '{9015EF72-8B07-4C72-AD8D-0BD1830C96FD}', 'mac': 'ac:f2:3c:54:fb:a5', 'type': 71, 'ipv4_metric': 30, 'ipv6_metric': 30, 'ips': ['fe80::8bb8:60e1:3529:5e96', '10.25.27.26'], 'nameservers': ['10.10.10.1']}
--- interface 4 ---
  raw dict: {'name': 'Loopback Pseudo-Interface 1', 'index': 1, 'description': 'Software Loopback Interface 1', 'guid': '{5E0E10DA-85BF-11EF-9FD1-806E6F6E6963}', 'mac': '', 'type': 24, 'ipv4_metric': 75, 'ipv6_metric': 75, 'ips': ['::1', '127.0.0.1'], 'nameservers': ['fec0:0:0:ffff::1', 'fec0:0:0:ffff::2', 'fec0:0:0:ffff::3']}
--- interface 5 ---
  raw dict: {'name': 'Ethernet-WFP Native MAC Layer LightWeight Filter-0000', 'index': 19, 'description': 'VirtualBox Host-Only Ethernet Adapter-WFP Native MAC Layer LightWeight Filter-0000', 'guid': '{8913572C-9D96-11F1-A059-806E6F6E6963}', 'mac': '0a:00:27:00:00:06', 'type': 6, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 6 ---
  raw dict: {'name': 'Local Area Connection* 9-Npcap Packet Driver (NPCAP)-0000', 'index': 25, 'description': 'WAN Miniport (IPv6)-Npcap Packet Driver (NPCAP)-0000', 'guid': '{89137228-9D96-11F1-A059-8ABE5E49A5E1}', 'mac': '', 'type': 6, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 7 ---
  raw dict: {'name': 'Ethernet-WFP 802.3 MAC Layer LightWeight Filter-0000', 'index': 21, 'description': 'VirtualBox Host-Only Ethernet Adapter-WFP 802.3 MAC Layer LightWeight Filter-0000', 'guid': '{8913572E-9D96-11F1-A059-806E6F6E6963}', 'mac': '0a:00:27:00:00:06', 'type': 6, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 8 ---
  raw dict: {'name': 'Local Area Connection* 8-WFP Native MAC Layer LightWeight Filter-0000', 'index': 38, 'description': 'WAN Miniport (IP)-WFP Native MAC Layer LightWeight Filter-0000', 'guid': '{89135A6A-9D96-11F1-A059-8ABE5E49A5E1}', 'mac': '', 'type': 6, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 9 ---
  raw dict: {'name': 'Local Area Connection* 8-QoS Packet Scheduler-0000', 'index': 39, 'description': 'WAN Miniport (IP)-QoS Packet Scheduler-0000', 'guid': '{89135A6B-9D96-11F1-A059-8ABE5E49A5E1}', 'mac': '', 'type': 6, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 10 ---
  raw dict: {'name': 'Local Area Connection* 9-WFP Native MAC Layer LightWeight Filter-0000', 'index': 40, 'description': 'WAN Miniport (IPv6)-WFP Native MAC Layer LightWeight Filter-0000', 'guid': '{89135A6C-9D96-11F1-A059-8ABE5E49A5E1}', 'mac': '', 'type': 6, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 11 ---
  raw dict: {'name': 'Local Area Connection* 9-QoS Packet Scheduler-0000', 'index': 41, 'description': 'WAN Miniport (IPv6)-QoS Packet Scheduler-0000', 'guid': '{89135A6D-9D96-11F1-A059-8ABE5E49A5E1}', 'mac': '', 'type': 6, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 12 ---
  raw dict: {'name': 'Local Area Connection* 10-WFP Native MAC Layer LightWeight Filter-0000', 'index': 42, 'description': 'WAN Miniport (Network Monitor)-WFP Native MAC Layer LightWeight Filter-0000', 'guid': '{89135A6E-9D96-11F1-A059-8ABE5E49A5E1}', 'mac': '', 'type': 6, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 13 ---
  raw dict: {'name': 'Local Area Connection* 10-QoS Packet Scheduler-0000', 'index': 43, 'description': 'WAN Miniport (Network Monitor)-QoS Packet Scheduler-0000', 'guid': '{89135A6F-9D96-11F1-A059-8ABE5E49A5E1}', 'mac': '', 'type': 6, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 14 ---
  raw dict: {'name': 'Ethernet-QoS Packet Scheduler-0000', 'index': 44, 'description': 'VirtualBox Host-Only Ethernet Adapter-QoS Packet Scheduler-0000', 'guid': '{8913721C-9D96-11F1-A059-8ABE5E49A5E1}', 'mac': '0a:00:27:00:00:06', 'type': 6, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 15 ---
  raw dict: {'name': 'Local Area Connection* 8-Npcap Packet Driver (NPCAP)-0000', 'index': 35, 'description': 'WAN Miniport (IP)-Npcap Packet Driver (NPCAP)-0000', 'guid': '{89137225-9D96-11F1-A059-8ABE5E49A5E1}', 'mac': '', 'type': 6, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 16 ---
  raw dict: {'name': 'Local Area Connection* 10-Npcap Packet Driver (NPCAP)-0000', 'index': 46, 'description': 'WAN Miniport (Network Monitor)-Npcap Packet Driver (NPCAP)-0000', 'guid': '{89137224-9D96-11F1-A059-8ABE5E49A5E1}', 'mac': '', 'type': 6, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 17 ---
  raw dict: {'name': 'Ethernet-Npcap Packet Driver (NPCAP)-0000', 'index': 49, 'description': 'VirtualBox Host-Only Ethernet Adapter-Npcap Packet Driver (NPCAP)-0000', 'guid': '{8913721B-9D96-11F1-A059-8ABE5E49A5E1}', 'mac': '0a:00:27:00:00:06', 'type': 6, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 18 ---
  raw dict: {'name': 'Bluetooth Network Connection', 'index': 11, 'description': 'Bluetooth Device (Personal Area Network)', 'guid': '{99A78D0C-15FA-46BE-A977-D0563FA5AE06}', 'mac': 'ac:f2:3c:54:fb:a6', 'type': 6, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 19 ---
  raw dict: {'name': 'Ethernet (Kernel Debugger)', 'index': 15, 'description': 'Microsoft Kernel Debug Network Adapter', 'guid': '{C4FE71E4-ECCC-4E10-88A8-D9B3B83D18A8}', 'mac': '', 'type': 6, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 20 ---
  raw dict: {'name': 'Local Area Connection* 8', 'index': 13, 'description': 'WAN Miniport (IP)', 'guid': '{BB0E457F-ADE2-432F-96E5-042FEEB61ECD}', 'mac': '', 'type': 6, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 21 ---
  raw dict: {'name': 'Local Area Connection* 9', 'index': 17, 'description': 'WAN Miniport (IPv6)', 'guid': '{EDABC4FE-0193-46F2-96CC-AC8F940F3639}', 'mac': '', 'type': 6, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 22 ---
  raw dict: {'name': 'Local Area Connection* 10', 'index': 12, 'description': 'WAN Miniport (Network Monitor)', 'guid': '{A2130613-5A3A-4667-99B0-0D6A313025B8}', 'mac': '', 'type': 6, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 23 ---
  raw dict: {'name': 'Local Area Connection* 7', 'index': 5, 'description': 'WAN Miniport (PPPOE)', 'guid': '{380B97AD-82AE-4586-A109-2EDFFD74E802}', 'mac': '', 'type': 23, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 24 ---
  raw dict: {'name': 'Wi-Fi-WFP Native MAC Layer LightWeight Filter-0000', 'index': 22, 'description': 'RZ616 Wi-Fi 6E 160MHz-WFP Native MAC Layer LightWeight Filter-0000', 'guid': '{89135786-9D96-11F1-A059-ACF23C54FBA5}', 'mac': 'ac:f2:3c:54:fb:a5', 'type': 71, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 25 ---
  raw dict: {'name': 'Wi-Fi-Virtual WiFi Filter Driver-0000', 'index': 23, 'description': 'RZ616 Wi-Fi 6E 160MHz-Virtual WiFi Filter Driver-0000', 'guid': '{2B0C3D72-33F8-11F0-9FD8-A04DD371893E}', 'mac': 'ac:f2:3c:54:fb:a5', 'type': 71, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 26 ---
  raw dict: {'name': 'Wi-Fi-Native WiFi Filter Driver-0000', 'index': 24, 'description': 'RZ616 Wi-Fi 6E 160MHz-Native WiFi Filter Driver-0000', 'guid': '{2B0C3D73-33F8-11F0-9FD8-A04DD371893E}', 'mac': 'ac:f2:3c:54:fb:a5', 'type': 71, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 27 ---
  raw dict: {'name': 'Local Area Connection* 1-Npcap Packet Driver (NPCAP)-0000', 'index': 20, 'description': 'Microsoft Wi-Fi Direct Virtual Adapter-Npcap Packet Driver (NPCAP)-0000', 'guid': '{89137229-9D96-11F1-A059-8ABE5E49A5E1}', 'mac': 'ae:f2:3c:54:db:85', 'type': 71, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 28 ---
  raw dict: {'name': 'Wi-Fi-VirtualBox NDIS Light-Weight Filter-0000', 'index': 26, 'description': 'RZ616 Wi-Fi 6E 160MHz-VirtualBox NDIS Light-Weight Filter-0000', 'guid': '{D820D5BE-909F-11F1-A04D-9F44496C522B}', 'mac': 'ac:f2:3c:54:fb:a5', 'type': 71, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 29 ---
  raw dict: {'name': 'Wi-Fi-WFP 802.3 MAC Layer LightWeight Filter-0000', 'index': 27, 'description': 'RZ616 Wi-Fi 6E 160MHz-WFP 802.3 MAC Layer LightWeight Filter-0000', 'guid': '{89135789-9D96-11F1-A059-ACF23C54FBA5}', 'mac': 'ac:f2:3c:54:fb:a5', 'type': 71, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 30 ---
  raw dict: {'name': 'Local Area Connection* 1-WFP Native MAC Layer LightWeight Filter-0000', 'index': 28, 'description': 'Microsoft Wi-Fi Direct Virtual Adapter-WFP Native MAC Layer LightWeight Filter-0000', 'guid': '{8913581D-9D96-11F1-A059-ACF23C54FBA5}', 'mac': 'ae:f2:3c:54:db:85', 'type': 71, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 31 ---
  raw dict: {'name': 'Local Area Connection* 1-Native WiFi Filter Driver-0000', 'index': 29, 'description': 'Microsoft Wi-Fi Direct Virtual Adapter-Native WiFi Filter Driver-0000', 'guid': '{2B0C3D80-33F8-11F0-9FD8-A04DD371893E}', 'mac': 'ae:f2:3c:54:db:85', 'type': 71, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 32 ---
  raw dict: {'name': 'Local Area Connection* 2-Npcap Packet Driver (NPCAP)-0000', 'index': 30, 'description': 'Microsoft Wi-Fi Direct Virtual Adapter #2-Npcap Packet Driver (NPCAP)-0000', 'guid': '{89137226-9D96-11F1-A059-8ABE5E49A5E1}', 'mac': 'ae:f2:3c:54:cb:95', 'type': 71, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 33 ---
  raw dict: {'name': 'Local Area Connection* 1-VirtualBox NDIS Light-Weight Filter-0000', 'index': 31, 'description': 'Microsoft Wi-Fi Direct Virtual Adapter-VirtualBox NDIS Light-Weight Filter-0000', 'guid': '{D820D5C3-909F-11F1-A04D-9F44496C522B}', 'mac': 'ae:f2:3c:54:db:85', 'type': 71, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 34 ---
  raw dict: {'name': 'Local Area Connection* 1-WFP 802.3 MAC Layer LightWeight Filter-0000', 'index': 32, 'description': 'Microsoft Wi-Fi Direct Virtual Adapter-WFP 802.3 MAC Layer LightWeight Filter-0000', 'guid': '{8913583E-9D96-11F1-A059-ACF23C54FBA5}', 'mac': 'ae:f2:3c:54:db:85', 'type': 71, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 35 ---
  raw dict: {'name': 'Local Area Connection* 2-WFP Native MAC Layer LightWeight Filter-0000', 'index': 33, 'description': 'Microsoft Wi-Fi Direct Virtual Adapter #2-WFP Native MAC Layer LightWeight Filter-0000', 'guid': '{891359F5-9D96-11F1-A059-8ABE5E49A5E1}', 'mac': 'ae:f2:3c:54:cb:95', 'type': 71, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 36 ---
  raw dict: {'name': 'Local Area Connection* 2-Native WiFi Filter Driver-0000', 'index': 34, 'description': 'Microsoft Wi-Fi Direct Virtual Adapter #2-Native WiFi Filter Driver-0000', 'guid': '{2B0C3E0A-33F8-11F0-9FD8-A04DD371893E}', 'mac': 'ae:f2:3c:54:cb:95', 'type': 71, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 37 ---
  raw dict: {'name': 'Wi-Fi-Npcap Packet Driver (NPCAP)-0000', 'index': 47, 'description': 'RZ616 Wi-Fi 6E 160MHz-Npcap Packet Driver (NPCAP)-0000', 'guid': '{89137222-9D96-11F1-A059-8ABE5E49A5E1}', 'mac': 'ac:f2:3c:54:fb:a5', 'type': 71, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 38 ---
  raw dict: {'name': 'Local Area Connection* 2-VirtualBox NDIS Light-Weight Filter-0000', 'index': 36, 'description': 'Microsoft Wi-Fi Direct Virtual Adapter #2-VirtualBox NDIS Light-Weight Filter-0000', 'guid': '{D820D5C1-909F-11F1-A04D-9F44496C522B}', 'mac': 'ae:f2:3c:54:cb:95', 'type': 71, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 39 ---
  raw dict: {'name': 'Local Area Connection* 2-WFP 802.3 MAC Layer LightWeight Filter-0000', 'index': 37, 'description': 'Microsoft Wi-Fi Direct Virtual Adapter #2-WFP 802.3 MAC Layer LightWeight Filter-0000', 'guid': '{891359F7-9D96-11F1-A059-8ABE5E49A5E1}', 'mac': 'ae:f2:3c:54:cb:95', 'type': 71, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 40 ---
  raw dict: {'name': 'Wi-Fi-QoS Packet Scheduler-0000', 'index': 45, 'description': 'RZ616 Wi-Fi 6E 160MHz-QoS Packet Scheduler-0000', 'guid': '{89137223-9D96-11F1-A059-8ABE5E49A5E1}', 'mac': 'ac:f2:3c:54:fb:a5', 'type': 71, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 41 ---
  raw dict: {'name': 'Local Area Connection* 2-QoS Packet Scheduler-0000', 'index': 48, 'description': 'Microsoft Wi-Fi Direct Virtual Adapter #2-QoS Packet Scheduler-0000', 'guid': '{89137227-9D96-11F1-A059-8ABE5E49A5E1}', 'mac': 'ae:f2:3c:54:cb:95', 'type': 71, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 42 ---
  raw dict: {'name': 'Local Area Connection* 1-QoS Packet Scheduler-0000', 'index': 50, 'description': 'Microsoft Wi-Fi Direct Virtual Adapter-QoS Packet Scheduler-0000', 'guid': '{8913722A-9D96-11F1-A059-8ABE5E49A5E1}', 'mac': 'ae:f2:3c:54:db:85', 'type': 71, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 43 ---
  raw dict: {'name': 'Teredo Tunneling Pseudo-Interface', 'index': 9, 'description': 'Microsoft Teredo Tunneling Adapter', 'guid': '{93123211-9629-4E04-82F0-EA2E4F221468}', 'mac': '', 'type': 131, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 44 ---
  raw dict: {'name': 'Microsoft IP-HTTPS Platform Interface', 'index': 4, 'description': 'Microsoft IP-HTTPS Platform Adapter', 'guid': '{2EE2C70C-A092-4D88-A654-98C8D7645CD5}', 'mac': '', 'type': 131, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 45 ---
  raw dict: {'name': '6to4 Adapter', 'index': 2, 'description': 'Microsoft 6to4 Adapter', 'guid': '{07374750-E68B-490E-9330-9FD785CD71B6}', 'mac': '', 'type': 131, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 46 ---
  raw dict: {'name': 'Local Area Connection* 3', 'index': 10, 'description': 'WAN Miniport (SSTP)', 'guid': '{99012715-F6C4-4D10-AAF3-63C6241C4AC9}', 'mac': '', 'type': 131, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 47 ---
  raw dict: {'name': 'Local Area Connection* 4', 'index': 16, 'description': 'WAN Miniport (IKEv2)', 'guid': '{D58393CC-1220-4511-8407-5AC16B26762C}', 'mac': '', 'type': 131, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 48 ---
  raw dict: {'name': 'Local Area Connection* 5', 'index': 7, 'description': 'WAN Miniport (L2TP)', 'guid': '{8622FEFB-6354-4348-A126-1BEA0BE4F0F4}', 'mac': '', 'type': 131, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
--- interface 49 ---
  raw dict: {'name': 'Local Area Connection* 6', 'index': 3, 'description': 'WAN Miniport (PPTP)', 'guid': '{1D13E7AC-CF7B-4F81-BFB6-F2A384CF35DA}', 'mac': '', 'type': 131, 'ipv4_metric': 0, 'ipv6_metric': 0, 'ips': [], 'nameservers': []}
```

**Key finding — `description` matches, `name` does not.** Every earlier
`verify_real_capture_schema.py` run passed `--iface "RZ616 Wi-Fi 6E
160MHz"` and worked. That string matches interface 3's **`description`**
field (`'RZ616 Wi-Fi 6E 160MHz'`), not its `name` field (`'Wi-Fi'`). Also
flagged: interfaces 24, 25, 26, 28, 29, 37, 40 all have `description`
values starting with `"RZ616 Wi-Fi 6E 160MHz-..."` too (WFP filters, QoS
scheduler, Virtual WiFi Filter Driver, etc. layered on the same physical
adapter) — a naive substring match on `description` would hit multiple
entries, not just interface 3. The fix uses exact `description` equality
via a filtered candidate list, not substring matching, to avoid this.

**Cross-platform import safety, checked via source (not tested on a
non-Windows machine — none available here).** `scapy/arch/windows/__init__.py`
does `import winreg` unconditionally at module level (confirmed at line 18
of that file). `winreg` is Windows-only in the Python standard library —
importing `scapy.arch.windows` (required for `get_windows_if_list`) would
raise `ModuleNotFoundError` (an `ImportError` subclass) on Linux/macOS,
at import time, before the function is ever called. The fix imports
`get_windows_if_list` lazily inside a Windows-only code path, guarded by
`scapy.consts.WINDOWS` (confirmed importable cross-platform — no `winreg`
dependency in `scapy/consts.py`), never at module top level.

**Fix applied** — `resolve_interface()` split into
`_resolve_interface_windows()` (uses `get_windows_if_list()`, filters on
non-empty `ips`, `type != 24`, no `"loopback"` in `description`, at least
one IP not link-local/APIPA, matches on `description`) and
`_resolve_interface_posix()` (unchanged `get_if_list()` + name-loopback
filtering, since real friendly names are returned natively there).
`CAPTURE_INTERFACE` constant removed entirely; `--iface` bypasses
auto-detection completely when passed.

**Verified path A — explicit `--iface` override, unaffected by
auto-detect.**

Command:
```
"venv/Scripts/python.exe" m2-systems/src/capture.py --iface eth0
```
Raw output (excerpt):
```
=== BlackBox Sentinel M2 — Packet Capture ===
Interface: eth0
Output: c:\Users\suhan shetty\Projects\Blackbox_Sentinel\m2-systems\src\..\..\m3-ml-ledger\data\capture_20260822_154327.pcap
Capturing 1000 packets...

Traceback (most recent call last):
  ...
  File "C:\Users\suhan shetty\Projects\Blackbox_Sentinel\venv\Lib\site-packages\scapy\interfaces.py", line 434, in resolve_iface
    raise ValueError("Interface '%s' not found !" % dev)
ValueError: Interface 'eth0' not found !
```
Confirms `--iface` reaches Scapy's `sniff()` unmodified — no silent
correction of a bad explicit value.

Command:
```
"venv/Scripts/python.exe" m2-systems/src/capture.py --iface "RZ616 Wi-Fi 6E 160MHz"
```
Raw output (header + first lines, real live traffic — ran to completion
in ~5s, full 1000-packet capture, no Ctrl+C needed):
```
=== BlackBox Sentinel M2 — Packet Capture ===
Interface: RZ616 Wi-Fi 6E 160MHz
Output: c:\Users\suhan shetty\Projects\Blackbox_Sentinel\m2-systems\src\..\..\m3-ml-ledger\data\capture_20260822_155611.pcap
Capturing 1000 packets...

[CAPTURE] Ether / IP / UDP / mDNS Qry b'_googlecast._tcp.local.'
[CAPTURE] Ether / IPv6 / UDP / mDNS Qry b'_googlecast._tcp.local.'
[CAPTURE] Ether / IP / UDP / mDNS Qry b'_googlecast._tcp.local.'
[CAPTURE] Ether / IPv6 / UDP / mDNS Qry b'_googlecast._tcp.local.'
[CAPTURE] Ether / ARP who has 10.25.31.194 says 10.25.20.98 / Padding
```
No `[AUTO-DETECT]` line (correct — bypassed when `--iface` is passed).

**Verified path B — auto-detect, ambiguous-candidate branch.**

Command:
```
"venv/Scripts/python.exe" m2-systems/src/capture.py
```
Raw output:
```
[FATAL] Multiple candidate interfaces found — cannot auto-select confidently.
Available interfaces (pass one via --iface):
  VirtualBox Host-Only Ethernet Adapter
  Microsoft Wi-Fi Direct Virtual Adapter
  Microsoft Wi-Fi Direct Virtual Adapter #2
  RZ616 Wi-Fi 6E 160MHz
  Software Loopback Interface 1
  ... (49 total, full list printed)
```
Confirms the zero-or-multiple branch works and correctly prints
`description` values, not raw dicts or GUIDs.

**Known limitation — explicitly unverified: the exactly-one-candidate
auto-pick success path.** On this machine, `VirtualBox Host-Only Ethernet
Adapter` (interface 0, IP `192.168.56.1`, non-link-local) and
`RZ616 Wi-Fi 6E 160MHz` (interface 3, IP `10.25.27.26`) both pass the
candidate filter, so `resolve_interface()` always lands in the
zero-or-multiple branch on this hardware — it has never actually reached
the `if len(candidates) == 1: ... return selected` line in this session.
That branch is logically simple and symmetric with the POSIX path (which
*has* been exercised in earlier sections of this document via
`verify_real_capture_schema.py`), but it has zero live execution evidence
here. Verifying it would require either a machine without a VM host-only
adapter holding a real IP, or temporarily disabling that adapter on this
one — neither was done in this session. This is the documented, intended
behavior per the fix's design (a VM adapter with a real IP is
indistinguishable from a second physical NIC using ip-presence data
alone), not a defect — but the single-candidate code path itself remains
unexercised.

---

### 7. Digital twin simulation (m2-systems/sim/run_simulation.py)

**Investigation first: does this actually need WSL2?**

The A-track planning docs (`M2_Complete_Workflow.md`, task A8;
`M2_Session_Continuation_Summary.md`, priority P3) both note this sim as
"needs WSL2." Checked before running:

- `run_simulation.py`'s full import block (lines 1-39) uses only
  `os`/`sys`/`time`/`shutil` plus internal modules (`hal`, `predict`,
  `ledger`, `traffic_generator`) — no raw sockets, no Linux-specific
  networking APIs, no driver imports. It even has an explicit Windows
  compatibility shim (`sys.stdout.reconfigure` guarded on
  `sys.platform == "win32"`).
- `m2-systems/README.md:55-58`, the module's own documented quickstart,
  lists `python m2-systems/sim/run_simulation.py` under "Run Digital Twin
  Simulation (No Hardware Needed)" with no WSL2/Linux caveat.
- The genuinely Linux-only pieces in the same directory are
  `setup_veth_lab.sh` (uses `ip netns`, veth pairs — real Linux kernel
  primitives with no Windows equivalent) and `docker-compose.yml` /
  `Dockerfile.sim` (a separate, more elaborate multi-container testbed).
  Neither is imported or invoked by `run_simulation.py` itself.

Command:
```
"venv/Scripts/python.exe" m2-systems/sim/run_simulation.py
```

Confirmed WSL2 is not installed on this machine:
```
wsl --status
```
Raw output:
```
The Windows Subsystem for Linux is not installed. You can install by running 'wsl.exe --install'.
For more information please visit https://aka.ms/wslinstall
```
(exit code 50)

**Full raw output of the run** (ran on native Windows Python, no WSL2,
to a clean completion — this is a scripted six-phase demo, not a
continuous process, so it stopped on its own):

```
======================================================================
   🛡️  BLACKBOX SENTINEL — DIGITAL TWIN SIMULATION OS (v2.1)  🛡️
======================================================================
[SECURITY] Volatile RAM Keystore mounted. Master keys provisioned in c:\Users\suhan shetty\Projects\Blackbox_Sentinel\scratch_keys_vault
[HAL] Initializing Hardware Abstraction Layer in mode: [SIM]
[HAL-SIM] [RELAY] Relay initialized in ENGAGED state (data line connected)
[HAL-SIM] [TAMPER] Monitor active (Grid continuous)
[HAL-SIM] [LED] Status LED initialized (OFF)
[HAL-SIM] [CELLULAR] SIM800L Modem: Registered to SIMULATED-2G-GSM Network (RSSI: 24/31)
[HAL-SIM] [MESH] ESP-NOW Radio: Node 'AEDN-RACK-01' listening on UDP loopback :39999
[SCORER] Loaded existing model — state: ARMED
[NODE] Initialized Node: AEDN-RACK-01
[NODE] Forensic Ledger: c:\Users\suhan shetty\Projects\Blackbox_Sentinel\m3-ml-ledger\data\sim_sentinel_ledger.json

----------------------------------------------------------------------
▶️  PHASE 1: 48-HOUR BASELINE CALIBRATION CYCLE (Fast Simulation Window)
----------------------------------------------------------------------
[CALIBRATE] Started — collecting baseline for 1800s
[HAL-SIM] [LED] [OFF] — System Calibrating / Idle
[CALIBRATE] Ingesting 120 baseline normal enterprise traffic samples...
[CALIBRATE] Training on 121 baseline samples...
[CALIBRATE] Complete — state: ARMED
[HAL-SIM] [LED] [SOLID GREEN] — System Armed & Monitoring

[PIPELINE] ✅ AI Model trained. System is ARMED and actively defending.

----------------------------------------------------------------------
▶️  PHASE 2: NORMAL TRAFFIC MONITORING
----------------------------------------------------------------------
  [INSPECT] Pkt #121: Port 443 (677B) -> Score: 0.1124 [STATUS: NORMAL]
  [INSPECT] Pkt #122: Port 443 (769B) -> Score: 0.1315 [STATUS: NORMAL]
  [INSPECT] Pkt #123: Port 80 (482B) -> Score: 0.1380 [STATUS: NORMAL]
  [INSPECT] Pkt #124: Port 80 (147B) -> Score: 0.0865 [STATUS: NORMAL]
  [INSPECT] Pkt #125: Port 443 (372B) -> Score: -0.0077 [STATUS: NORMAL]
  [INSPECT] Pkt #126: Port 80 (432B) -> Score: 0.1332 [STATUS: NORMAL]
  [INSPECT] Pkt #127: Port 22 (267B) -> Score: -0.0179 [STATUS: NORMAL]
  [INSPECT] Pkt #128: Port 80 (587B) -> Score: 0.0881 [STATUS: NORMAL]
  [INSPECT] Pkt #129: Port 80 (563B) -> Score: 0.0318 [STATUS: NORMAL]
  [INSPECT] Pkt #130: Port 53 (153B) -> Score: -0.0784 [STATUS: NORMAL]

----------------------------------------------------------------------
▶️  PHASE 3: ADVERSARIAL ATTACK INJECTION & AUTONOMOUS CONTAINMENT
----------------------------------------------------------------------
⚡ [ATTACK INJECTED] Rogue C2 Data Exfiltration: 14709.361758006693 Bytes on Port 4444

🚨 [ANOMALY DETECTED] Reconstruction Error Delta Spike! Score: -0.0579
[HAL-SIM] [RELAY FIRED] Mechanical data line is now CUT / ISOLATED
[BUS-INTERRUPT] Mechanical Data Line State Changed -> ISOLATED
[HAL-SIM] [LED] [RAPID FLASHING RED (0.2s)] — System in ALERT / LOCKDOWN
📋 [FORENSIC LEDGER] Block #2 committed -> SHA-256: 7701a0c03d3652cc405c56cfa9900ffb75a6a30731b790b8e989280ebf2a0bd6

[HAL-SIM] [CELLULAR OOB SMS SENT] Destination: +919876543210
  Message: "SECURITY ALERT: Node AEDN-RACK-01 detected DATA_EXFILTRATION. Line isolated. SHA256: 7701a0c03d36"
[HAL-SIM] [ESP-NOW MESH BROADCAST] Gossiping threat profile to peer rack nodes...
  Payload: {'threat_type': 'DATA_EXFILTRATION', 'attacker_port': 4444, 'victim_port': 4444, 'isolation_time': 1787419298.990763}

----------------------------------------------------------------------
▶️  PHASE 4: TOUCHSCREEN TACTICAL PIN OVERRIDE (Patent Claim 1)
----------------------------------------------------------------------
[TOUCH-GUI] On-site administrator entering physical PIN: '1234' on 800x480 screen...
[OVERRIDE] PIN accepted — state: ARMED
[HAL-SIM] [RELAY ENGAGED] Mechanical data line is now RESTORED
[BUS-INTERRUPT] Mechanical Data Line State Changed -> ENGAGED
[HAL-SIM] [LED] [SOLID GREEN] — System Armed & Monitoring
✅ [OVERRIDE] Data line mechanically RESTORED. Node returned to ARMED.

----------------------------------------------------------------------
▶️  PHASE 5: ANTI-TAMPER PHYSICAL HOUSING BREACH (Patent Claim 2)
----------------------------------------------------------------------
[PHYSICAL] Simulating malicious casing breach / lid removal...

[HAL-SIM] [TAMPER ALERT] Enclosure breach detected! Triggering zeroization...

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
🚨 [TAMPER INTERRUPT] ENCLOSURE TAMPER GRID SEVERED!
🔥 [ZEROIZATION] EXECUTING VOLATILE RAM CRYPTOGRAPHIC KEY PURGE...
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
✅ [ZEROIZATION] Cryptographic keys wiped and RAM zeroed out.
[HAL-SIM] [RELAY FIRED] Mechanical data line is now CUT / ISOLATED
[BUS-INTERRUPT] Mechanical Data Line State Changed -> ISOLATED
[HAL-SIM] [LED] [RAPID FLASHING RED (0.05s)] — System in ALERT / LOCKDOWN

[HAL-SIM] [CELLULAR OOB SMS SENT] Destination: +919876543210
  Message: "CRITICAL ALERT: Node AEDN-RACK-01 enclosure breached! Keys zeroized, data line severed."

----------------------------------------------------------------------
▶️  PHASE 6: CRYPTOGRAPHIC FORENSIC AUDIT
----------------------------------------------------------------------
🔐 [AUDIT] Forensic Ledger Chain Integrity: ✅ 100% VALID (UNALTERED)
📊 [SUMMARY] Total Packets: 131 | Anomalies: 1 | Total Ledger Blocks: 5
======================================================================
   🏆  BLACKBOX SENTINEL DIGITAL TWIN VALIDATION SUITE: PASSED  🏆
======================================================================

[exited with code 0]
```

**Result: all six phases completed — calibration, normal-traffic
monitoring, attack injection + autonomous containment, PIN override
recovery, tamper/zeroization, and forensic audit — ending in
`DIGITAL TWIN VALIDATION SUITE: PASSED`, exit code 0.**

**Correction to prior planning docs:** the "needs WSL2" note in
`M2_Complete_Workflow.md` (task A8) and `M2_Session_Continuation_Summary.md`
(priority P3) does not hold for `run_simulation.py` itself, confirmed by
this run — WSL2 is not installed on this machine and the script completed
cleanly on native Windows Python. That assumption traces back to the
separate veth-lab/Docker testbed (`setup_veth_lab.sh`,
`docker-compose.yml`) sitting in the same directory, which genuinely does
need Linux networking primitives — not to `run_simulation.py`, which
doesn't invoke either of them. Both planning docs are being corrected to
reflect this (see their own diffs).

**Worth a follow-up question for M3, not asserted as a bug:** in Phase 2,
several `NORMAL`-status packets scored negative (`-0.0077`, `-0.0179`,
`-0.0784`), and the packet that triggered `[ANOMALY DETECTED]` in Phase 3
also scored negative (`-0.0579`) — numerically less extreme than at least
one of the `NORMAL` scores in Phase 2 (`-0.0784`). This may be entirely
correct depending on the scoring convention this model uses (e.g. a
reconstruction-error-delta metric where the anomaly decision isn't a
simple "is the score below/above a fixed line" comparison, or where sign
alone isn't meaningful and some other combined signal drove the
detection) — nothing here is asserted as a defect. Flagging it as a
question for M3 on the exact threshold/scoring convention in this sim's
model, since the score-to-decision relationship isn't obvious from this
output alone and wasn't investigated further in this session.

---

### 8. M3 handoff review — Shashwat's fix, step 4: CLOSED

Following Shashwat's commit `d45a1c3` (section 5 update, above), his
handoff message asked M2 to review four specific things without changing
the model. All four are now evidenced, not just asserted:

**1. `organization_id` correct** — `organization_a`, matching `--org-id
organization_a`, confirmed in both the `[SCORER]` startup line and every
`scorer_result.organization_id` in the report, across both runs in this
section.

**2. `feature_count` = 45** — `45/45` in every window, both the
`--windows 10` and `--windows 60` runs, `all_schema_ok=true` in both
reports.

**3. `M3_INTERFACE.md` exact field match** — all 16 fields documented in
section 6 of `ml/M3_INTERFACE.md` (`state`, `score`, `probability_attack`,
`threshold`, `is_anomaly`, `global_prediction`, `local_prediction`,
`local_detection_enabled`, `organization_id`, `profile_ready`,
`profile_samples`, `eligible_for_learning`, `local_score`,
`top_local_features`, `feature_count`, `timestamp`) are present in
`scorer_result` with correct types, no extras, none missing — confirmed
stable across two independent runs (`--windows 10` and `--windows 60`),
not a one-off match.

**4. Adaptive profile genuinely separated per organization** — proven
with mtime evidence, not just asserted:

- `organization_a_profile.json`/`organization_a_state.json` confirmed
  created (didn't exist before the `--windows 60` run — a filesystem-wide
  search prior to that run found zero `organization_a` files anywhere)
  and confirmed growing across two consecutive `--windows 60` runs:
  `82826 → 159892` bytes, `mtime` advancing from
  `2026-08-23 00:02:14.435362200` — accumulated `profile_samples` climbed
  from `0` to `61` across the runs, consistent with real persistence, not
  a fresh object each time.
- `default_organization_profile.json`/`default_organization_state.json`
  confirmed **byte-identical and mtime-unchanged** across all three
  checkpoints in this session (`2026-08-22 23:52:16.976591400` /
  `...979129400`, unchanged before the first `organization_a` write,
  after it, and after the second) — writing to one organization's profile
  did not touch the other's, at all, twice in a row.

**Step 4: CLOSED.**

---

### 9. M2-1 wire-format mismatch (B1) — RESOLVED

`B1_Authenticated_Envelope_Draft.md` (§1d) flagged that
`common/hal/drivers_real.py`'s `RealMesh.broadcast_threat()` wrote
`MESH_BROADCAST:{threat_payload}\n` — Python's `str(dict)` repr — while
`m1-hardware/src/esp32_coprocessor.ino`'s `processHostCommand()` parser
(`:109-134`) only recognizes `ISOLATE`/`CUT`, `ENGAGE`/`RESTORE`, `ARM`,
`DISARM`, `PING`, and a colon-delimited `GOSSIP:<type>:<score>:<port>`
command. `MESH_BROADCAST:` matched none of those — the message would
have been silently dropped by the firmware's parser on real hardware,
every time.

**Fix applied** in `common/hal/drivers_real.py`: `broadcast_threat()` now
builds `GOSSIP:{threat_type}:{score}:{port}\n`, matching the firmware
parser's `cmd.indexOf(':', ...)` / `substring()` field extraction at
`.ino:123-130` exactly. Because the three real callers of
`broadcast_threat()` don't agree on payload key names
(`sentinel_pipeline.py:270-276` uses `threat_score`/no port at all;
`m2-systems/sim/run_simulation.py:220-225` uses `threat_type`/`victim_port`/no
score; `m4-gui-venture/hw_simulator_server.py:378` uses `threat`/`score`),
a small `_first_present()` helper picks fields by alias with explicit
`is not None` checks (not `or`-chaining, which would incorrectly skip a
legitimate `score=0.0` or `port=0`), falling back to `"UNKNOWN"`/`0.0`/`0`
when a caller omits a field entirely. Extraction, casting, and the write
all happen inside one `try/except`, so a malformed payload (e.g. a
non-numeric score) returns `False` instead of raising. `threat_type` is
sanitized (`:`, `\n`, `\r` stripped) since the firmware's parser has no
escaping of its own and an embedded `\n` would truncate
`Serial.readStringUntil('\n')` mid-message.

Confirmed still true, explicitly out of scope for this fix: `RealRelay`
still drives Pi GPIO 17 directly rather than issuing `ISOLATE`/`ENGAGE`
over the ESP32 serial link (B4's relay-bypass finding), and
`RealMesh.register_peer_callback()` still has no read loop consuming the
firmware's outgoing JSON lines (B3's dead-code finding). Also confirmed
via `.ino:96-105`: the `GOSSIP:` format needs no sender/node-ID field —
`origin_node` is hardcoded to `"AEDN-RACK-01"` firmware-side and
`timestamp` is computed from `millis()`, neither taken from serial input
— though that hardcoded literal is itself a separate M1-owned gap for any
multi-node deployment, not touched here.

**Verification (mock serial, no ESP32 hardware attached — see caveat
below):**

```
--- sentinel_pipeline.py:270-276 shape (no threat_type/port keys at all) ---
raw bytes written: b'GOSSIP:UNKNOWN:-0.088:0\n'
firmware-side parse -> threat='UNKNOWN' score=-0.088 port=0

--- score=0.0 explicit, must NOT be skipped for a later non-zero key ---
raw bytes written: b'GOSSIP:ZERO_SCORE_TEST:0.0:80\n'
firmware-side parse -> threat='ZERO_SCORE_TEST' score=0.0 port=80

--- malformed score (non-numeric string) must be caught, not crash ---
broadcast_threat() returned: False
(nothing written)

--- threat_type containing ':' '\n' '\r' must be sanitized ---
raw bytes written: b'GOSSIP:EVIL_INJECT_DISARM_TYPE:-0.5:1337\n'

--- very small magnitude score -> Python default float str is scientific ---
raw bytes written: b'GOSSIP:SCI_NOTATION_SMALL:1.234e-08:443\n'
firmware-side parse -> threat='SCI_NOTATION_SMALL' score=1.234e-08 port=443
```

Full run covered all three real caller shapes, both falsy-zero cases
(`score=0.0`, `port=0`), the malformed-payload case, colon/`\n`/`\r`
injection sanitization, and three scientific-notation magnitudes
(`1.234e-08`, `6.7e+16`, `-1.234e-08`) — all ten produced the expected
`GOSSIP:` line and re-parsed correctly via a line-by-line Python
transcription of the firmware's own colon-split parsing logic. Full repo
test suite: `17/17 passed`.

**Caveat, stated plainly:** no physical ESP32 or Arduino toolchain is
available in this environment (per B2 §1a/1b, this repo doesn't even pin
a board or core version), so the firmware side of this was never
compiled or executed — only a faithful Python re-implementation of its
parsing arithmetic. Whether `String::toFloat()` (documented as wrapping
`atof()`/`strtod()` in the Arduino core) accepts scientific notation is
stated here as documented C-standard-library behavior, not as something
verified against this project's actual firmware build. Hardware-in-loop
testing of this fix is still outstanding.
