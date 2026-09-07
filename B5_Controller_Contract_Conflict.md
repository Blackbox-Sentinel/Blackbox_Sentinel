# B5 — Trusted-Controller Contract Conflict: Shashwat (M3) vs. Shreyash (M4) (DRAFT)

**Status: DRAFT FOR DISCUSSION ONLY.** Same framing as
[`B1_Authenticated_Envelope_Draft.md`](B1_Authenticated_Envelope_Draft.md),
[`B2_Crypto_Shortlist.md`](B2_Crypto_Shortlist.md), and
[`B3_Quorum_StateMachine_Draft.md`](B3_Quorum_StateMachine_Draft.md): not an
implementation plan, blocked by the same approval gate. This document does
not pick a winner. It exists because two full, working implementations of
the same patent-scope feature now sit in `main` at the same time, and one of
them has to be picked (or both merged) before M2 can build the real
transport against either.

---

## 1. What exists today (read-only investigation, no changes made)

### 1a. Two independent implementations of "trusted controller + two-signal
gate + receipt", built without coordination

- **Shashwat / M3**, commit `44c983e`, four files under `m3-ml-ledger/src/`:
  - [`authenticated_envelope.py`](m3-ml-ledger/src/authenticated_envelope.py)
    — `AuthenticatedEnvelope`, `ReplayProtector` (`:189`), `SequenceAllocator`
  - [`quorum_state.py`](m3-ml-ledger/src/quorum_state.py) —
    `QuorumStateMachine`, leader-coordinated N-of-M vote collection
  - [`m3_security_contracts.py`](m3-ml-ledger/src/m3_security_contracts.py)
    — `TwoSignalGate`, `Ed25519ReceiptSigner`, `ContainmentReceiptService`,
    `SoftwareMonotonicCounter`
  - [`trusted_controller_sim.py`](m3-ml-ledger/src/trusted_controller_sim.py)
    — `SimTrustedController`, a separate class that *consumes* a receipt
    from `ContainmentReceiptService`
- **Shreyash / M4**, commit `c749f3b`, one file:
  - [`security/trusted_controller.py`](security/trusted_controller.py) —
    a single `TrustedController` class that both *issues* evidence
    signals/votes and *consumes* them to produce a receipt, all in one
    object (`:70-336`)

Both commits landed on `main` five commits apart
(`44c983e` → `c513764` → `c749f3b` → `d067767` → `b08e6c7`), both carry the
same honest "simulation scaffold, not hardware enforcement" framing in
their own docstrings
(`trusted_controller_sim.py:1-13`, `security/trusted_controller.py:1-6`),
and neither imports, references, or tests against the other. Grepped
project-wide for cross-references
(`trusted_controller|TrustedController|SimTrustedController|m3_security_contracts|authenticated_envelope|quorum_state`
across all `.py` files): the only files touching both implementations are
each one's own test file. **Zero production code bridges them.**

### 1b. M4's dashboard stack is wired exclusively to Shreyash's version

- `gui/dashboard.py:30` — `from security.trusted_controller import
  ControllerState, TrustedController`
- `m4-gui-venture/src/app.py:45` — same import
- `m4-gui-venture/hw_simulator_server.py:90` — same import, inside
  `HardwareSimEngine.__init__`

None of the three GUI entry points import anything from
`m3-ml-ledger/src/`. Shashwat's implementation — the one with Ed25519
receipts and the leader-coordinated quorum state machine — currently has
no consumer anywhere in the running system except its own test suite
(`tests/test_m3_security_contracts.py`, `tests/test_postmeeting_security_flow.py`).

### 1c. `docs/Patent_Scope_Upgrade_Implementation.md` doesn't resolve this either

That doc (added in the same `c749f3b` commit) lists "Authenticated
monotonic containment receipt" as `M3 with M1/M2 support` and
"Authenticated multi-node quorum" as `M2 with M1/M3 support`
(`docs/Patent_Scope_Upgrade_Implementation.md:20`, row 9) — ownership
assignments that match Shashwat's contracts, not Shreyash's — while the
same commit's actual code (`security/trusted_controller.py`) implements
both features itself, under M4's module path. The planning doc and the
code shipped in the same commit disagree with each other about which
team owns this.

---

## 2. Crypto choice, against B2's existing lean

B2 (`B2_Crypto_Shortlist.md:183-207`) leaned **HMAC-SHA256** for the
envelope `auth_tag`, on three grounds: compute cost on an unconfirmed
ESP32 variant, simpler key provisioning, and — its stated strongest
argument (`B2_Crypto_Shortlist.md:172-177`) — that HMAC is "the smaller
conceptual leap" from the project's only existing trust primitive, the
ledger's plain `hashlib.sha256` chain (`m3-ml-ledger/src/ledger.py`,
cited in B2 §1c), since there is **no PKI anywhere in this project**.

Neither new implementation contradicts B2 on the *envelope* layer:

- Shashwat's `authenticated_envelope.py:31` — `AUTH_ALGORITHM =
  "HMAC-SHA256"`, tag computed via `hmac.new(key, ..., hashlib.sha256)`
  at `:132`. Matches B2's lean exactly.
- Shreyash's `security/trusted_controller.py` uses `hmac.new(self.secret,
  ..., hashlib.sha256)` throughout (`:127`, the shared `_tag()` helper
  used by signals, votes, *and* receipts). Also matches B2's lean, and
  goes further — it's HMAC end-to-end with **zero** new dependencies
  (imports are stdlib-only: `hashlib`, `hmac`, `json`, `secrets`, `time`
  — `security/trusted_controller.py:10-14`).

Where they diverge is the **receipt** layer, which B2 never actually
addressed (B2's scope was the mesh message `auth_tag`, not the
containment receipt specifically):

- Shashwat's `m3_security_contracts.py:39` — `RECEIPT_ALGORITHM =
  "Ed25519"`. `Ed25519ReceiptSigner` (`:214-253`) generates an ephemeral
  in-memory keypair by default (`:223` —
  `Ed25519PrivateKey.generate()`), and its own docstring
  (`:215-220`) says: *"Production M1 integration must supply a
  controller-held key and must not persist it in this Python module or
  in the repository."* This is exactly the asymmetric complexity B2
  flagged as unresolved — no keypair provisioning, distribution, or
  revocation story exists anywhere in the repo (B2 §2c) — introduced
  for receipts specifically, while B2's lean argument (no existing PKI
  to build on) applies here just as much as it did to the envelope.
  `requirements.txt:7` now pins `cryptography>=41.0.0` project-wide to
  support this.
- Shreyash's receipts use the same shared-secret HMAC as everything else
  (`security/trusted_controller.py:291-296`, `_isolate()`): fully
  consistent with B2, adds no new dependency — but see 3b below for the
  real cost of that choice.

**Net on crypto:** both implementations independently converged on HMAC
for the message/signal layer, which is a real (if accidental) point of
agreement with B2. They diverge sharply on the receipt layer, where
Shashwat's Ed25519 choice reopens a question B2 explicitly deferred to
the meeting rather than answering.

---

## 3. Interoperability

### 3a. The two receipt formats cannot verify each other

- Shashwat's receipt (`m3_security_contracts.py:297-315`) is a `{payload,
  signature, public_key}` dict; `ContainmentReceiptService.verify()`
  (`:329-345`) is a `@staticmethod` — anyone holding the receipt can
  verify it standalone, using the public key embedded in the receipt
  itself. No shared secret needed.
- Shreyash's receipt (`security/trusted_controller.py:278-296`,
  `DecisionReceipt` at `:53-67`) is authenticated with the *same*
  per-controller-instance HMAC secret used for signals and votes
  (`verify_receipt()`, `:309-319`, calls `self._tag(...)` — an instance
  method, not static). **Verifying this receipt requires possessing the
  exact `TrustedController` instance's secret.** The receipt's own
  `external_witness_status` field defaults to `"NOT_CONFIGURED"`
  (`:67`, `:289`) — and as designed, it structurally cannot become
  configured without distributing the controller's shared secret to
  whatever external witness needs to verify it, which is a materially
  different (and weaker) property than Shashwat's embedded-public-key
  design. `docs/Patent_Scope_Upgrade_Implementation.md`'s own
  requirements table calls for a receipt with "external witness" support
  (row 7) — Shashwat's design satisfies that requirement more directly
  than Shreyash's does today.

### 3b. Secret handling is already inconsistent across the three call sites
that exist for Shreyash's version

- `m4-gui-venture/hw_simulator_server.py:90-99` —
  `TrustedController(secret=os.urandom(32), ...)`, fresh random secret
  per process start.
- `m4-gui-venture/src/app.py:98` — same, `secret=os.urandom(32)`.
- `gui/dashboard.py:42` — `TrustedController(secret=b"phase2-demo-secret",
  ...)`, a **hardcoded literal secret**, different from the other two
  entry points.

None of these three in-process controllers share a secret with each
other today, which means even within Shreyash's single implementation,
a receipt issued by one entry point's controller cannot be verified by
another's. This isn't a defect in isolation (each is a standalone demo
process), but it is a preview of exactly the key-distribution problem B2
flagged as unresolved (`B2_Crypto_Shortlist.md:133-147`) — and it gets
harder, not easier, once M2's real transport needs a receipt issued on
one node to be verifiable by a different node or by M4's dashboard.

### 3c. Quorum shape differs

- Shashwat's `QuorumStateMachine` (`quorum_state.py:146-241`) is a
  leader-coordinated N-of-M state machine with explicit `COLLECTING /
  APPROVED / DENIED / CONFLICT / TIMEOUT / RECOVERY_REQUIRED` states,
  per-incident deadlines, and rejects mixed CONFIRM/DENY as `CONFLICT`
  rather than silently approving (`:222-234`, `_recompute()`).
  This is the state machine B3 originally sketched.
- Shreyash's quorum is a bare counter inside `TrustedController`
  (`security/trusted_controller.py:259-260`,
  `_evaluate()`): `quorum_ok = self.quorum_required == 0 or
  len({v.peer_id for v in votes}) >= self.quorum_required`. No explicit
  states, no deadline enforcement in `_evaluate()` itself (freshness is
  checked per-vote in `submit_vote()` at `:246`, not as a quorum-wide
  timeout), no conflict handling — a `DENY` vote type doesn't exist in
  `PeerVote.decision` at all (`:47`, plain `str`, only ever constructed
  with `decision="ISOLATE"` per `issue_vote()`'s default at `:212`).

These are not compatible representations of "quorum" — one is a richer
state machine, the other a threshold counter. A vote submitted against
one has no meaning to the other.

---

## 4. The coordination gap itself

Both commits are individually well-scoped, individually well-documented,
and individually honest about being simulation scaffolding — this is not
a criticism of either implementation's code quality. The issue is
structural: **two team members independently built full solutions to the
same patent-scope requirement in the same week, neither aware of the
other's work, and both merged into `main` without either being reviewed
against the other.** This is the second time this pattern has occurred
(the first being `44c983e` itself arriving mid-session ahead of the
approval-gate meeting this whole B-series was meant to precede). It's
raised here as a process observation for the meeting agenda, not resolved
here.

---

## 5. What this blocks

Per Shashwat's latest directive, M2 owes: (1) the real transport, (2) a
genuine second independent authenticated signal, (3) quorum vote
submission. All three require picking a contract to build against:

- The transport (M2-1) needs to know whether `AuthenticatedEnvelope`
  (HMAC, replay-protected, versioned) or `security/trusted_controller.py`'s
  inline per-message HMAC scheme is the wire format to carry.
- The second signal (M2-2) needs to know whether it's submitted as an
  `EvidenceSignal` to `TwoSignalGate.evaluate()`
  (`m3_security_contracts.py:134-180`) or as an `EvidenceSignal` to
  `TrustedController.submit_signal()`
  (`security/trusted_controller.py:186-205`) — same concept name, two
  incompatible dataclasses, two different call surfaces.
- The quorum vote (M2-3) needs to know whether it's a `QuorumVote` into
  `QuorumStateMachine.add_vote()` or a `PeerVote` into
  `TrustedController.submit_vote()`.

Building against one now, before the meeting decides, risks the same
throwaway-work outcome B1/B3 were written to avoid in the first place.

---

## 6. Open questions for the meeting

- Which implementation is the one M2/M1 build the real transport and
  signal/vote submission against — Shashwat's four-module contract, or
  Shreyash's single-file `TrustedController`? Or is the intent to merge
  them (e.g., keep Shashwat's Ed25519 receipt + `QuorumStateMachine`,
  but Shreyash's simpler single-class ergonomics)?
- Does the receipt layer stay HMAC (consistent with B2's lean and
  Shreyash's zero-dependency approach) or move to Ed25519 (satisfies the
  "standalone external witness" requirement in
  `docs/Patent_Scope_Upgrade_Implementation.md` row 7, at the cost of
  the key-provisioning problem B2 raised and never resolved)?
- If Ed25519 receipts are kept: who owns generating, distributing, and
  rotating the controller's signing key — this wasn't answered for the
  envelope layer in B1/B2 and isn't answered for receipts either.
- If HMAC receipts are kept: how does external/standalone verification
  (row 7 of the patent-scope doc) work without distributing the
  controller's shared secret — is a witness node trusted with the
  secret, or does this requirement get redefined?
- Should `docs/Patent_Scope_Upgrade_Implementation.md`'s ownership table
  be corrected to match whichever implementation is chosen, since it
  currently assigns quorum/receipt ownership to M2/M3 while the shipped
  code under that same commit implements both under M4's module path?
- Given this is the second unreviewed pre-meeting implementation
  (`44c983e`, then `c749f3b`), does the team want a lighter-weight
  "flag before merging" step for patent-scope-adjacent code between now
  and the meeting, or is that overhead not worth it for a small team?
