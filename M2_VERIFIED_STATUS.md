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
`organization_a`, profile created fresh at
`ml/adaptive_profiles/organization_a_profile.json`, 10/10 windows
schema_ok=True.

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
