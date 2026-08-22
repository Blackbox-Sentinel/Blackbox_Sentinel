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
