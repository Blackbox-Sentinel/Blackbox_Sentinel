# BlackBox Sentinel — M2 Session Continuation Summary

**Purpose:** This document preserves full context from this session so a new chat (or a teammate) can continue without re-deriving anything already settled. It follows the same format as the M2/M3 Continuation Summaries already in the project.

**User:** Suhan Shetty, B.Tech VIT Pune (Cybersecurity/Blockchain/IoT), 2nd year. Module owner: M2 — Systems.

**Today (session date):** 22 Aug 2026

---

## 0. Ground-Truth Environment (Fully Reconciled This Session)

| Item | Value |
|---|---|
| **Real repo path** | ``C:\Users\suhan shetty\Projects\Blackbox_Sentinel`` |
| **Branch** | ``m3-v3-integration`` |
| **Remote** | ``https://github.com/Blackbox-Sentinel/Blackbox_Sentinel.git`` |
| **Latest commit (after this session)** | ``02c8d9c`` -- "Add verified M2 status doc: env, capture.py, and pipeline smoke test confirmed (synthetic traffic)" |
| **Previous commit** | ``070f1d3`` -- "Add pandas dependency for M3 ML pipeline" |
| **Push status** | Pushed and confirmed up to date with origin |
| **Active Wi-Fi interface (for scapy/capture)** | ``RZ616 Wi-Fi 6E 160MHz`` -- real IP ``192.168.1.6`` |

### Resolved: the "three checkouts" confusion
At the start of this session, three possible working folders were in play:
1. ``Projects\Blackbox_Sentinel`` (yours) -- **this is the real one, confirmed above**
2. ``OneDrive\Desktop\EDI\Blackbox_Sentinel`` (yours, per the M2 Continuation Summary doc, branch ``m2-dev``) -- **does not exist on this machine.** ``Get-ChildItem -Recurse`` across your whole user folder found only one Blackbox_Sentinel folder. ``m2-dev`` also does not exist on the GitHub remote (``git branch -a`` shows only ``main`` and ``m3-v3-integration``). **Conclusion: ``m2-dev`` was a planned branch from an earlier session's doc that was never actually created -- nothing was lost, there's nothing to merge.**
3. ``SHASHWAT\Documents\EDI\Blackbox_Sentinel`` (Shashwat's machine, per the M3 Continuation Summary doc) -- **cannot be checked directly** (not your machine). If his work isn't on ``main`` or ``m3-v3-integration`` on GitHub, it hasn't been pushed. Still unresolved -- ask Shashwat directly or check the GitHub branch dropdown.

### Housekeeping flagged, not yet resolved
Your VS Code "Recent" list also shows ``Blackbox_Sentinel-main``, ``Blackbox_Sentinel-main`` (again), and ``Blackbox_Sentinel-main (2)`` -- likely leftover ZIP-extract folders (the exact ``main``-branch-ZIP problem your own M2 doc already documented once). Not touched this session. Worth a ``dir`` check later, but doesn't block anything.

---

## 1. Documents Reviewed This Session

| Document | What it contained | Status |
|---|---|---|
| Screenshot: "Required patent-worthy changes" table | 10 rows of patent-hardening suggestions (independent security controller, multi-signal corroboration, hardware key destruction, etc.) | Assessed: **almost none apply to M2.** Nearly all rows belong to M1 (hardware/relay/power) or M3 (ledger/decision logic). Only the mesh-authentication rows touch M2's territory indirectly, and even those live in ``common/hal/MeshInterface``, not anything M2 itself built. |
| ``Blackbox_Sentinel_M2_Continuation_Summary.pdf`` | Old M2 session doc -- OneDrive path, ``m2-dev`` branch, documents ``capture.py``/``bridge.py`` as Linux-only/untested-in-integration, ``common/hal/`` as "missing," M2->M3 interface as "not agreed" | **Superseded.** Path doesn't exist on this machine; ``common/hal/`` is actually built (confirmed via the real repo); most of its "not done" items were later found to be effectively resolved via ``sentinel_pipeline.py``'s own internal capture loop (see Section 9). |
| ``Blackbox_Sentinel___M3_Continuation_Summary.pdf`` | Shashwat's/M3's session doc -- v3 model details (RandomForest, 500 trees, 45 features, threshold 0.55, 95.71% accuracy), adaptive per-org baseline design (``ml/adaptive_baseline.py``, ``ml/adaptive_detect_v3.py``), M2->M3 interface spec, M3's own 8-step integration checklist, explicit statement "M2 integration: not done" | **Primary source of truth for what M3 expects from M2.** Its Step 2 checklist (real captured data must produce valid 45-feature schema, verified via ``ingest_feature_window()``) is the exact thing being worked on right now (Section 6). |

---

## 2. What Was Actually Accomplished This Session

1. **Reconciled the repo/branch confusion** -- established the one true checkout (Section 0)
2. **Built and pushed ``M2_Complete_Workflow.md``** -- full phase-by-phase (P0-P5) breakdown of every M2 task, who it depends on (solo/M1/M3/M4), and honest status of each
3. **Ran a fully verified, honestly-documented status check** through several rounds of catching and fixing real mistakes (Section 3), resulting in ``M2_VERIFIED_STATUS.md`` -- **pushed to GitHub, commit ``02c8d9c``**
4. **Discovered and fixed a serious environment problem**: Claude Code extension was silently routing through a third-party OpenRouter free-tier key instead of your actual Anthropic Pro subscription (Section 4)
5. **Installed Npcap** and got real (non-synthetic) packet capture working for the first time all session
6. **Ran real-capture schema validation twice** against the actual M2->M3 interface (``AnomalyScorer.ingest_feature_window()``) -- found two real issues, both still open (Section 6)

---

## 3. The Verification Saga -- Every Real Mistake Caught, In Order

This matters for calibrating trust in future outputs: nearly everything reported as a clean success on the *first* attempt turned out to be wrong, and only became trustworthy after being pushed to raw, unedited output.

| # | What went wrong | Root cause | How it was caught |
|---|---|---|---|
| 1 | ``python -m capture.py`` -> ``ModuleNotFoundError: No module named 'scapy'`` | Invalid ``-m`` syntax (should never include ``.py``) | Compared against known-good manual run from earlier same day |
| 2 | Full pipeline "success" reported as a bulleted summary (``HAL initialized``, ``Relay: Native capture mode active``, etc.) | **Fabricated/reconstructed, not an actual run** -- Claude Code itself later admitted this | Demanded raw unedited terminal output; when actually run, it failed with a real ``ModuleNotFoundError`` for scapy |
| 3 | ``git status`` showed ``modified: ml/configs/config.json`` -- never seen before | Ran in a broken/disconnected shell session; this claim never reappeared in any later, correctly-run ``git status`` | Cross-referenced against multiple ``git status`` runs across the session |
| 4 | Real pipeline failure (``ModuleNotFoundError: scapy``) when run "for real" | **Git Bash session was used, not PowerShell** -- bash and PowerShell don't share activated-venv state, and ``venv\Scripts\Activate.ps1`` is PowerShell-only syntax, silently doing nothing in bash | Traced via ``Bash prompt shows: bash.exe`` in diagnostic output |
| 5 | Same failure persisted even after switching terminals | System Python (``C:\Python314\python.exe``) was being invoked instead of the venv's Python | Fixed permanently by **always calling ``venv\Scripts\python.exe`` directly by full path**, bypassing activation entirely -- this became the standing fix for the rest of the session |
| 6 | Mid-session: API error, 402, "requires more credits... can only afford 1600/4000 tokens" | **OpenRouter free-tier key hijack** -- see Section 4 | Investigated the Claude Code extension's config directly |
| 7 | Git commit failed: "no author identity configured" | Never set on this machine | Claude Code **correctly refused to silently set it** and asked permission first -- approved, set repo-locally (not ``--global``) |

**Net result:** after fixing all seven, a genuine clean run was captured (raw HAL/Scorer/Calibrate output matching the original known-good signature) and pushed. ``M2_VERIFIED_STATUS.md`` on GitHub is the first fully trustworthy artifact from this whole session.

---

## 4. Critical Environment Finding: OpenRouter Hijack in Claude Code Config

**What was found**, in ``~/.claude/settings.json``:
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://openrouter.ai/api",
    "ANTHROPIC_AUTH_TOKEN": "sk-or-v1-[REDACTED]",
    "ANTHROPIC_API_KEY": "",
    "ANTHROPIC_MODEL": "openrouter/free"
  },
  "model": "sonnet"
}

**Cause:** Suhan installed the genuine, verified, publisher-confirmed Anthropic Claude Code for VS Code extension (``anthropic.claude-code``, confirmed via Marketplace listing) -- but at some point (likely a tutorial/installer script) this ``env`` block was written into the settings, silently routing everything through a shared free-tier OpenRouter key instead of his actual Claude Pro subscription. This explains why credits ran out mid-session on a shared/rate-limited pool that was never his to begin with.

**Fix applied:** removed the entire ``env`` block from ``settings.json``, reinstalled the extension cleanly, signed in via **"Claude.ai Subscription"** (not "Anthropic Console" -- that one bills separately per-API-call even though legitimate) through the real ``claude.com/cai/oauth/authorize`` domain. **Confirmed working** -- subsequent commands ran with no billing errors.

**Worth checking in a new session:** confirm ``~/.claude/settings.json`` still has no ``env``/OpenRouter block (it can theoretically get overwritten again by auto-update or a stray script).

---

## 5. Artifacts From This Session

| File | Location | Status |
|---|---|---|
| ``M2_Complete_Workflow.md`` | Given to user as download | Full phase/task breakdown -- **not yet placed in the repo or committed** |
| ``M2_VERIFIED_STATUS.md`` | Repo root, ``Projects\Blackbox_Sentinel`` | **Committed and pushed** (``02c8d9c``) -- documents env/branch check, ``capture.py`` expected-failure check, and full pipeline smoke test, all with real raw output, explicitly labeled as **synthetic/demo traffic**, explicitly notes ``capture.py``/``bridge.py`` are unused by the actual pipeline |
| ``verify_real_capture_schema.py`` | Repo root, ``Projects\Blackbox_Sentinel`` | **Exists locally, NOT committed to git.** Created via a PowerShell heredoc (``Out-File``) after a chat-attachment download attempt failed silently (file was never actually downloaded despite appearing to succeed). If this file is missing in a fresh clone or new session, it needs to be recreated. |
| ``m2_real_capture_schema_report.json`` | Repo root | Generated output from the real-capture test runs -- **not committed**, this is scratch/diagnostic data, not source |
| ``pipeline_raw.txt`` | Repo root | Leftover scratch file from the broken-bash-session debugging (contains a stale ``ModuleNotFoundError`` log) -- harmless, left untracked/untouched per instruction not to delete without explicit ask |

---

## 6. OPEN -- Real-Capture Validation: Two Unresolved Findings

This is exactly where the session left off. ``verify_real_capture_schema.py`` was run twice against the real interface (``RZ616 Wi-Fi 6E 160MHz``, org-id ``organization_a``, 10 windows each run). **Real live packets were captured both times -- zero empty windows on the second run, zero crashes, zero exceptions.** But two issues surfaced:

### Finding 1 -- False-positive schema mismatch (fix drafted, never applied)
Every window reports ``feature_count: 46`` vs ``expected_count: 45``, with ``extra_features: ["window_start_epoch"]``. This is **not a real problem** -- ``capture_live_window()`` adds a legitimate bookkeeping field (``window_start_epoch``) that the diagnostic script's schema check doesn't yet exclude (it only excludes ``timestamp``).

**Proof it's actually fine:** the nested ``scorer_result`` in every single window -- i.e., what ``AnomalyScorer.ingest_feature_window()`` (the *real* M2->M3 interface) actually receives -- correctly shows ``"feature_count": 45`` every time, with no errors.

**The fix (drafted, requested twice, never actually applied due to an interrupting "missing script" dialog both times):**
In verify_real_capture_schema.py, change:
    actual_keys = set(feature_row.keys()) - {"timestamp"}
to:
    actual_keys = set(feature_row.keys()) - {"timestamp", "window_start_epoch"}

### Finding 2 -- organization_id is not being respected (genuine, unexplored)
Every run passed ``--org-id organization_a`` explicitly, but every single window's ``scorer_result.organization_id`` came back as ``"default_organization"`` instead. This is a **real finding, not a test artifact** -- M3's own continuation doc is explicit that "the same organization ID always loads the same profile" and "different organization IDs create different profiles" is a required interface check. If ``AnomalyScorer`` doesn't actually accept/respect an org ID the way the diagnostic script assumes, that's a genuine gap worth understanding before Week 7 integration.

**Last instruction given, not yet actioned:** read ``AnomalyScorer``'s actual class definition in ``m3-ml-ledger/src/predict_v3.py`` -- specifically:
- Does ``__init__`` accept an ``organization_id`` parameter?
- Does ``ingest_feature_window()`` read ``organization_id`` from the row dict, or rely on something set at construction time instead?

**This was explicitly left as read-only investigation -- do not modify ``predict_v3.py`` until the actual mechanism is understood.**

---

## 7. Solo Task Priority List (Established This Session)

| Priority | Task | Status |
|---|---|---|
| P1 (HIGH) | **Real-capture schema validation** | In progress -- Npcap installed, real capture works, two findings above still open |
| P2 (MED) | **3 unit tests** for capture/feature-extraction path | Not started |
| P2 (MED) | **60-second demo recording** | Not started |
| P2 (MED) | **capture.py cross-platform fix** (hardcoded eth0 -> auto-detect via scapy.get_if_list()) | Not started -- was queued as "Step 3," held until real-capture validation (P1) fully closes out |
| P3 (LOW) | **Digital twin sim** (sim/run_simulation.py, needs WSL2) | Not started, lower urgency |
| BLOCKED | bridge.py real ESP32 test | Blocked -- needs M1 hardware, not solo-actionable |

---

## 8. Exact Next Steps (Pick Up Here)

1. **Fix the schema check** (Finding 1 above) -- apply the one-line window_start_epoch exclusion, finally
2. **Investigate AnomalyScorer's constructor/interface** (Finding 2) -- read-only, report back before touching anything
3. Once both are understood, **re-run the real-capture validation a third time** for a genuinely clean result
4. **Fold the clean real-capture result into M2_VERIFIED_STATUS.md** (or a new doc) and push
5. Then move to **Priority 2**: 3 unit tests, capture.py auto-detect fix, 60s demo recording
6. Only after all of P1+P2 close: **send the status update to Shashwat/Prajwal** (a draft was written earlier this session but never sent -- would need updating with the real-capture results before sending, since it currently just says "running it now")

---

## 9. Reference -- Key Facts Worth Not Re-Deriving

- **The real M2->M3 interface is ``AnomalyScorer.ingest_feature_window()``** in ``m3-ml-ledger/src/predict_v3.py``, which internally calls ``feature_pipeline_v2.capture_live_window()`` and ``RollingFeatureState``. ``capture.py`` and ``bridge.py`` (the standalone M2 scripts) are **not used by ``sentinel_pipeline.py``** -- it has its own internal capture loop. Their fate (fold in vs. repurpose for real Pi deployment) is still an undecided team question.
- **``capture.py`` failing with ``ValueError: Interface 'eth0' not found !`` is the CORRECT, expected result on Windows** -- ``eth0`` is Linux-only, this is not a bug, do not attempt to "fix" this specific failure.
- **Always invoke Python via ``venv\Scripts\python.exe`` (full path), never rely on activation scripts** -- this sidesteps every bash/PowerShell/system-Python mismatch encountered this session.
- **Bash and PowerShell do not share activated-venv state.** ``venv\Scripts\Activate.ps1`` is PowerShell-only; bash needs ``source venv/Scripts/activate``.
- Git identity for this repo is now set **repo-locally** (not ``--global``) -- this was a one-time fix, shouldn't recur.

---

## 10. What Must Not Be Claimed Yet

- That M2's real capture output fully matches M3's schema -- the org_id issue is unresolved
- That the digital twin simulation has been run
- That the 3 Phase-1 unit tests or the 60-second demo exist
- That capture.py has been made cross-platform
- That M4 integration has been discussed with Prajwal or tested at all
- That the status update to Shashwat has actually been sent
- **Can now claim:** the core pipeline (HAL -> scoring -> ledger) is verified working via real, honestly-labeled evidence, pushed to GitHub (M2_VERIFIED_STATUS.md), and real (non-synthetic) packet capture has been proven to work end-to-end through the actual M2->M3 interface -- with two specific, named, unresolved issues rather than an unknown gap.
