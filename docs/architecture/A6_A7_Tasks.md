# A6 + A7 — Task Brief
**22 Aug 2026 | M2 — Systems | Suhan Shetty**

Two Priority-2 solo tasks, sequenced: A6 is a code fix, A7 is a recording that should showcase the result of A6 (and everything closed in A1–A5) working live.

---

## A6 — `capture.py` Cross-Platform Fix

**Problem:** `capture.py` hardcodes the Linux interface name `eth0`. On Windows this fails with `ValueError: Interface 'eth0' not found !` — this is documented as the **correct, expected failure**, not a bug to patch around. The actual fix is auto-detection.

### Step 1 — Investigate first (read-only)

```
Read-only. Show me the raw code of capture.py — the full file if it's under ~150 lines, otherwise just the section where "eth0" appears plus the surrounding function.

Also show me: where does `iface` come from elsewhere in this file? Is it a CLI arg, a hardcoded constant, an environment variable? And is this file actually invoked anywhere in the real pipeline (sentinel_pipeline.py), or is it standalone/unused, per what M2_VERIFIED_STATUS.md already documented?
```

### Step 2 — Propose the fix, don't write it yet

```
Based on what you just read, propose a fix using scapy.get_if_list() for auto-detection, with this priority order:
1. If an --iface CLI arg is explicitly passed, use it (don't override user intent)
2. Otherwise, auto-detect: list available interfaces via scapy.get_if_list(), and pick a sensible active default (skip loopback) — or list them and exit with a clear message if none can be auto-selected confidently
3. Never hardcode a single interface name for any OS

Tell me the proposed logic before writing any code.
```

### Step 3 — Apply and verify

```
Apply the fix. Show me the full diff before running anything.
```

Once approved:

```
Run capture.py with no --iface argument, to confirm auto-detection actually picks up a real Windows interface (should find "RZ616 Wi-Fi 6E 160MHz" or similar) instead of failing on eth0.

Show me the complete raw output, unedited.
```

**Done when:** auto-detection works with no `--iface` passed, and passing `--iface` explicitly still overrides it. Then commit:

```
git add capture.py
git commit -m "Make capture.py cross-platform: auto-detect interface via scapy.get_if_list() instead of hardcoded eth0"
git push
```

---

## A7 — 60-Second Demo Recording

**Goal:** show the real, working M2 capture → feature-extraction → scoring path live — not a slide, not a mockup. Everything below is already verified working (A1–A5), so this is a recording task, not a debugging task.

### Suggested script (60 sec)

| Time | What's on screen | What you say / show |
|---|---|---|
| 0:00–0:08 | Terminal, repo open, clean prompt | "This is BlackBox Sentinel's M2 module — live network capture feeding the ML pipeline." |
| 0:08–0:15 | Type + run the command | `venv\Scripts\python.exe verify_real_capture_schema.py --iface "RZ616 Wi-Fi 6E 160MHz" --org-id organization_a --windows 10` |
| 0:15–0:45 | Live output scrolling | Let 3–4 windows print live (`[CAPTURE] Window X/10 ... features=45/45 schema_ok=True`) — this is real traffic, not synthetic |
| 0:45–0:55 | Final summary line | `[SUMMARY] all_schema_ok=True empty_windows=0` — point at it explicitly |
| 0:55–1:00 | Cut / close | Optional: quick flash of `M2_VERIFIED_STATUS.md` in the editor as proof this is documented, not a one-off |

### Pre-recording checklist

- [ ] Close unrelated terminal tabs/windows (avoid showing stray sessions, per the earlier "unexplained commit" moment — keep it to one clean terminal)
- [ ] Increase terminal font size for recording legibility
- [ ] Do a silent rehearsal run first so you know the real timing (10 windows may take longer or shorter than 30 sec depending on live traffic — adjust `--windows` count if needed to fit 60 sec)
- [ ] Confirm Wi-Fi interface name hasn't changed since last session (`RZ616 Wi-Fi 6E 160MHz`)
- [ ] Set `$env:SENTINEL_ORGANIZATION_ID = 'organization_a'` in the recording terminal BEFORE hitting record — running the command without it crashes in ~6.6s with a ValueError (organization_id/profile mismatch), documented in M2_VERIFIED_STATUS.md section 5.
- [ ] Have `M2_VERIFIED_STATUS.md` open in a background tab if you want the optional closing shot

### Rehearsal instruction to give Claude Code first

```
$env:SENTINEL_ORGANIZATION_ID = "organization_a"
venv\Scripts\python.exe verify_real_capture_schema.py --iface "RZ616 Wi-Fi 6E 160MHz" --org-id organization_a --windows 10

Show me raw output and tell me roughly how long the full run took, so I can time the recording.
```

**Done when:** you have a screen recording, real terminal output, no editing needed to look legitimate — since it already is.

**Status: ✅ Done.** Recording completed, ~63.5s total. Actual script
execution time was ~17-18s (matching the earlier rehearsal timing) — the
rest of the clip is setup/typing/pause padding around the command, not the
operation itself running long. This run also showed `empty_windows=2` (vs.
0 in every earlier run this session) — this is normal live Wi-Fi traffic
variance (a capture window catching zero packets in its 1-second slot),
not a regression; `all_schema_ok=True` was unaffected.
