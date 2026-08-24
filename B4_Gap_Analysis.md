# B4 — M2 Gap Analysis Against Patent-Scope Ownership (DRAFT)

**Status: DRAFT FOR DISCUSSION ONLY.** Same framing as
[`B1_Authenticated_Envelope_Draft.md`](B1_Authenticated_Envelope_Draft.md),
[`B2_Crypto_Shortlist.md`](B2_Crypto_Shortlist.md), and
[`B3_Quorum_StateMachine_Draft.md`](B3_Quorum_StateMachine_Draft.md): not
an implementation plan, blocked by the same approval gate. This is pure
documentation of current state, meant as a reference for the architecture
meeting.

**Note on sourcing, and a deviation from "no new investigation":** the
ownership table below was pasted directly by you from the patent-scope
PDF's "Cross-team ownership summary" section — I have not read that PDF
myself and cannot independently verify it beyond what you provided, so it's
reproduced verbatim, not re-derived. Separately: while locating that table
I found `M2_Complete_Workflow.md` already exists in the repo and explicitly
defines this exact task ("map M2's *existing* telemetry/health signals —
systemd status, bridge health, watchdog — against what each of the 10
features needs"). Answering that required reading `m2-systems/os/`
(systemd unit files, provisioning/hardening scripts) and a handful of
other files — `m1-hardware/src/relay_controller.py`,
`m3-ml-ledger/src/ledger.py`, `ml/zeroize.py`, and
`sentinel_pipeline.py`'s tamper handler — none of which B1, B2, B3, or
M2_VERIFIED_STATUS.md had touched. I read those rather than guess at "what
M2 has today" from memory alone. Flagging this rather than silently going
beyond the four files named, since you were explicit that no new
investigation was expected.

---

## Ownership table (as provided, from the patent-scope PDF)

| Feature | Primary owner | Supporting owners |
|---|---|---|
| Independent trusted controller | M1 | M2, M3 |
| Two authenticated compromise signals | M1 | M2, M3 |
| Authenticated anti-replay protocol | M2 | M1, M3 |
| Fail-safe relay topology | M1 | M2 |
| Hardware-backed key invalidation | M1 | M2, M3 |
| Hold-up power | M1 | M2, M3 |
| Authenticated containment receipt | M3 | M1, M2, M4 |
| ML as one trusted-controller input | M1 | M2, M3 |
| Multi-node quorum | M2 | M1, M3, M4 |
| Final GUI visibility and recovery | M4 | M1, M2, M3 |

M2 has a role — primary or supporting — in all 10 rows, so all 10 are
included below.

---

## Gap-analysis table

| # | Feature | M2 role | What M2 has today | What's missing |
|---|---|---|---|---|
| 1 | Independent trusted controller | Supporting | ESP32 co-processor firmware implements an independent serial command interface (`ISOLATE`/`ENGAGE`/`ARM`/`DISARM`/`PING`) and its own relay/tamper GPIO logic, physically separate from the Pi (`m1-hardware/src/esp32_coprocessor.ino`). `sentinel-core.service` runs the pipeline under systemd supervision (`Restart=always`). | Confirmed via repo-wide grep: **no Python code anywhere ever sends those serial commands to the ESP32.** The relay is instead driven directly via Raspberry Pi GPIO 17 by two separate, redundant Python implementations (`common/hal/drivers_real.py:25-54`'s `RealRelay`, and `m1-hardware/src/relay_controller.py:28-71`'s `RelayController`) — both bypass the ESP32 entirely. The one component architecturally positioned to be an "independent" controller is currently unreachable from the real control path; a compromised Pi can toggle the relay without the ESP32 ever being consulted. See 1a below. |
| 2 | Two authenticated compromise signals | Supporting | Two structurally independent trigger paths already exist and each can unilaterally isolate/zeroize: the ML anomaly score (`self.scorer`, M3) and the physical tamper interrupt (`self.hal.tamper` → `_handle_tamper()`, `sentinel_pipeline.py:296-330`). | Neither signal is *authenticated*. B1 established every transport is unauthenticated; the tamper signal is a raw GPIO pin read (trustworthy only as far as the physical wiring is), and the ML signal is a local computation with no attestation. "Two signals" exists functionally; "authenticated" does not exist at all. |
| 3 | Authenticated anti-replay protocol | **Primary** | The transports this protocol would run over are real and working: serial (Pi↔ESP32), ESP-NOW mesh broadcast, and simulated UDP loopback — all confirmed functional this session (`capture.py`, `verify_real_capture_schema.py`, and the sim mesh broadcast in `sentinel_pipeline.py`). | Everything B1 found: no version field, no sequence/nonce, no auth tag on any transport; `encrypt = false` explicitly set on the ESP-NOW peer (`esp32_coprocessor.ino:177`). Replay is trivially possible — nothing tracks or rejects a repeated message. This is a from-scratch build; B1 is the draft for it. |
| 4 | Fail-safe relay topology | Supporting | Relay state is explicitly tracked (`ENGAGED`/`ISOLATED`) with `isolate()`/`engage()` methods in both relay implementations (`drivers_real.py`, `relay_controller.py`). | Genuinely unknown from code alone, not guessed: whether the physical relay module is wired normally-open or normally-closed. The GPIO logic (`active_high=True, initial_value=False`) only tells us the relay is *actively driven* to ISOLATED — what state it falls back to on Pi power loss or GPIO float depends on the physical relay module's wiring, which isn't visible in source. See 4a. |
| 5 | Hardware-backed key invalidation | Supporting | Real, working software zeroization exists in multiple places: `sentinel_pipeline.py:296-330` overwrites key files with null bytes, unlinks them, then `rmtree`s the directory; `ml/zeroize.py`'s `Zeroizer` class; `security/zeroization.py`. The OS provisioning layer backs the key directory with a **RAM-only tmpfs mount** (`/run/sentinel/keys`, `security_hardening.sh:32-41`, `size=16M,mode=0700`), and grants the `sentinel` user passwordless sudo specifically for `rm -rf /run/sentinel/keys/*` (`security_hardening.sh:26-29`). | This is software zeroization plus RAM-only residency — not a hardware secure element or fuse-based key destruction. Grepped repo-wide for any such hardware mechanism: zero hits. Whether tmpfs-RAM-residency is what "hardware-backed" is meant to describe, or whether an actual secure element/HSM is intended, isn't resolved by anything in this repo — the patent-scope PDF itself wasn't available to check its exact definition, so this is flagged as open rather than assumed either way. |
| 6 | Hold-up power | Supporting | **Nothing found.** Grepped repo-wide (case-insensitive) for `hold-up`, `capacitor`, `UPS`, `battery`, `power loss`, `supercap` — the only hits are `M2_Complete_Workflow.md`'s own task-list mention of this feature name and the report's approval-gate quote. No schematic, no code, no graceful-shutdown-on-power-loss handling anywhere. | Entire mechanism, hardware or software. This is the one row where "what M2 has today" is honestly nothing — stated as such rather than inferring something that isn't there. |
| 7 | Authenticated containment receipt | Supporting | `HashChainLedger` (`m3-ml-ledger/src/ledger.py`) — a real, working SHA-256 hash-chained append-only log, with a `verify_chain()` integrity check. Every containment action writes an entry: tamper zeroization (`sentinel_pipeline.py:321-325`), relay isolation, mesh threat broadcast (`sentinel_pipeline.py:270-276`). | Per B2 section 1c: this is a **symmetric hash chain with no key material** — no signature, no MAC, no public/private keys anywhere in the project (grepped). It proves internal tamper-evidence (retroactive edits break the chain) but not cryptographic authentication of origin — anyone able to write a plausible next entry before it's chained isn't stopped by anything keyed. "Authenticated" likely implies more than hash-chaining alone provides. |
| 8 | ML as one trusted-controller input | Supporting | Per row 2: the ML score is already structurally *one of two* independent inputs (alongside tamper), not the sole trigger — this matches "one input" rather than sole authority. | Same underlying gap as row 1, restated here: there currently is no separate *trusted controller* consulting ML as an input — the Pi's own pipeline code directly acts on the ML score and directly drives the relay. "ML as one input to a trusted controller" presupposes a controller distinct from the thing running the ML, which doesn't exist in the current wiring. |
| 9 | Multi-node quorum | **Primary** | Per B3: the mesh broadcast transport is real and functional one-way (verified this session in sim mode); the `register_peer_callback` interface exists in the HAL abstraction (`hal_base.py:104-107`, implemented in both `drivers_sim.py` and `drivers_real.py`). | Per B3 in full: receive-side is completely inert — real hardware has no read loop on the ESP32 serial port at all; sim has a working callback-dispatch loop, but nothing ever calls `register_peer_callback()`, so it never fires. Zero `quorum`/`vote` concept anywhere (grepped). No peer registry, no peer liveness tracking, no incident identity. This is a from-scratch build; B3 is the draft outline for it. |
| 10 | Final GUI visibility and recovery | Supporting | `sentinel-gui.service` (`m2-systems/os/systemd/sentinel-gui.service`) is systemd-supervised (`Restart=always`, `RestartSec=5`, depends on `sentinel-core.service`). M2's provisioning layer (`build_sentinel_os.sh`) is what installs and enables it. | Not evidenced in this session. I have not investigated `m4-gui-venture`'s actual GUI behavior, visibility content, or recovery flow beyond incidentally noticing it also constructs an `AnomalyScorer()` (per the B1 investigation's repo-wide grep). M2's role here, per the ownership table, is Supporting and appears limited to keeping the GUI process alive at the OS/systemd layer — what the GUI itself shows or how recovery works is a real gap in *this document's* coverage, not necessarily a gap in the product, and shouldn't be read as one. |

---

## Detail notes

### 1a. Why "independent controller" is currently just wiring, not architecture

The ESP32 firmware's command interface exists and is a reasonable
candidate for genuine independence (a separate chip, separate firmware,
separate failure domain from the Pi's Linux/Python stack). But
independence only has security value if the Pi *can't* bypass it — and
today it can, trivially, because nothing routes relay control through the
serial link at all. This isn't a partial gap; it's a complete
disconnect between what the ESP32 firmware supports and what the Python
control path actually calls.

### 4a. What would resolve the fail-safe relay question

Confirming the physical relay module's NO/NC wiring (or the schematic, if
one exists beyond what's in `m1-hardware/schematics/`) would resolve this
— it's not resolvable from the Python/firmware source alone, since GPIO
logic level only describes the *driven* state, not the *unpowered*
default. Listed here as a concrete, answerable question rather than left
as vague uncertainty.

---

## Cross-row pattern worth naming explicitly

Six of the ten rows (1, 2, 3, 7, 8, 9) trace back to the same root cause
in different forms: **nothing in this codebase authenticates anything**,
and in three of those (1, 8, 9) there's an additional, distinct
architectural gap — the component that's supposed to be independent,
trusted, or quorum-forming either isn't wired into the real control path
(1, 8) or doesn't react to input at all on the receive side (9). B1, B2,
and B3 already scope the authentication and quorum work; this document's
main new contribution is rows 1, 4, 5, 6, 8, and 10 — the ones B1/B2/B3
didn't directly cover, since those drafts were scoped to the
transport/crypto/quorum design specifically, not the full ownership list.

---

## Open questions for the meeting

- Row 1/8: should relay control be re-routed through the ESP32 serial
  interface as a prerequisite for B1/B3, or is direct Pi GPIO control an
  accepted interim state? This affects whether "independent controller"
  is a wiring fix or a design discussion.
- Row 4: confirm physical relay module wiring (NO vs. NC) — answerable,
  not a design question.
- Row 5: what does "hardware-backed" mean in the patent-scope report
  specifically — RAM-only volatility (already present) or an actual
  secure element (not present)? Can't be resolved without the source
  document.
- Row 6: does hold-up power exist anywhere outside this repo (a hardware
  BOM/schematic not yet checked in), or is this genuinely unstarted?
- Row 7: does "authenticated" for the containment receipt mean the same
  auth mechanism B1/B2 are designing for the transport layer, or a
  separate signing step specific to the ledger? Not resolved here.
- Row 10: this document's GUI-row coverage is admittedly thin — worth a
  short follow-up pass on `m4-gui-venture` specifically, separate from
  this draft, if the meeting wants it filled in before deciding anything
  about that row.
