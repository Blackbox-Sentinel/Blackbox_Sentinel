# GAP — Quorum votes authenticated with a shared key, not per-voter keys

**Status: not gated by the B-series approval process.** This is a design
gap in code on `origin/m3-phase2-integration` at commit `cc86691`
("Wire Phase 2 vertical slice to M2 evidence transport") — not yet merged
to `main`. Documenting now so it's tracked before that branch merges,
rather than discovered after.

---

## The gap

`integration/phase2_vertical_slice.py` (on `cc86691`) constructs two
separate `M2EvidenceTransport` instances, one per quorum voter:

```python
self.m2_transport = M2EvidenceTransport(
    sender_id="node-a", key=TRANSPORT_KEY, key_id="phase2-transport-key",
    key_epoch=1, max_age_seconds=60.0, future_skew_seconds=5.0,
)
self.m2_peer_transport = M2EvidenceTransport(
    sender_id="node-b", key=TRANSPORT_KEY, key_id="phase2-transport-key",
    key_epoch=1, max_age_seconds=60.0, future_skew_seconds=5.0,
)
```

Both instances are passed the exact same `TRANSPORT_KEY` — a single
module-level constant (`TRANSPORT_KEY = b"phase2-transport-key-..."`),
also reused by the pre-existing `M2SimTransport` telemetry path. Confirmed
by direct grep, not inference: every constructor call and every
`ReplayProtector.accept()` call in that file references the same symbol.

The instance separation is real and does something useful — each
`M2EvidenceTransport` holds its own `ReplayProtector`/`SequenceAllocator`,
so `node-a`'s and `node-b`'s sequence numbers are tracked independently,
and a replay of one voter's envelope doesn't interfere with the other's.
But `ReplayProtector.accept()`'s authentication check
(`authenticated_envelope.py:206`, `envelope.verify_mac(key)`) only proves
"whoever holds `key` signed this" — it says nothing about *which* holder.
Since both `node-a` and `node-b`'s envelopes are HMAC'd with the identical
key, anyone (or any process) holding `TRANSPORT_KEY` can produce a
validly-authenticated envelope claiming to be either voter.

## Impact

The resulting `QuorumVote` objects genuinely pass through
`ReplayProtector.accept()` — `authenticated: true` in
`m3-ml-ledger/data/phase2_telemetry_real_m2_m3.jsonl` is not a scripted
label, it's a real result of a real MAC/freshness/sequence check
(verified by tracing the code path, not just reading the file). That part
is correctly built. What it does **not** yet provide is the security
property "independently authenticated" implies: that a vote attributed to
`node-a` could only have come from `node-a`, and a compromise of one
voter's key doesn't let an attacker forge votes from the other. With a
shared key, a single compromise (or, in this single-process simulation,
simply the fact that both identities live in the same Python process)
lets one party sign as both voters — the quorum's two-vote requirement
becomes a formality rather than a real independence guarantee.

This mirrors, almost exactly, the open question
`B2_Crypto_Shortlist.md` (§2b, §4) raised and explicitly left for the
team: *"shared mesh-wide key vs. per-pair keys vs. per-node keys... If
it's one shared key across the whole mesh, compromise of any single node
compromises the entire mesh's authentication simultaneously — that's a
real cost of the symmetric approach, not glossed over."* That question
was never resolved; this is the first place in the codebase where its
absence has a concrete, visible consequence rather than being purely
theoretical.

## What this note does and doesn't propose

This does **not** propose a key-provisioning design — that's still the
open B2 question, unresolved on its own terms (mesh-wide key vs.
per-node vs. per-pair, and how a key gets onto a node securely in the
first place). It also doesn't propose that `node-a` and `node-b` need
full asymmetric identity (that reopens the HMAC-vs-ECDSA question B2 was
built around).

What's in scope for a small, uncontroversial fix once someone picks this
up: give each simulated voter its own distinct key (even a second
hardcoded per-node constant, for the simulation phase) so that
`node-a`'s and `node-b`'s votes are at least distinguishable by key,
matching the minimum bar `BUG_Controller_Secret_Mismatch.md` set for the
`TrustedController` secret fix — not a full provisioning architecture,
just internal consistency for what "two voters" is supposed to mean.

---

## Related, separate finding: `m3_decision_path.py`'s message-type mismatch (dormant, not live)

Also on `cc86691`, unrelated to the shared-key gap above: the new
`m3-ml-ledger/src/m3_decision_path.py` validates incoming evidence
envelopes against a specific set —

```python
if envelope.message_type not in {"ML_EVIDENCE", "PEER_EVIDENCE"}:
```

— sourced from `m3_contract.py`'s `MESSAGE_TYPES` frozenset
(`{"ML_EVIDENCE", "PEER_EVIDENCE", "QUORUM_VOTE", "CONTAINMENT_RECEIPT",
"CONTROLLER_ACK", "RECOVERY_STATE"}`). But `m2-systems/src/evidence_transport.py`
(unchanged by this commit) builds signal envelopes with
`message_type="EVIDENCE_SIGNAL"` — a string that appears in neither
`m3_decision_path.py`'s inline set nor `MESSAGE_TYPES`. If
`m3_decision_path.py`'s validation were ever applied to an envelope
`evidence_transport.py` produced, it would be rejected on message type
alone, before any authentication check ran.

**Confirmed dormant, not a live bug today:** `phase2_vertical_slice.py`
never imports or calls `m3_decision_path.py` — grepped directly, zero
references. The vertical slice talks to `TwoSignalGate`/
`QuorumStateMachine` the same way it always has; `m3_decision_path.py`
exists in the tree but nothing currently routes through it. Flagging this
now so whoever does wire `evidence_transport.py`'s output through
`m3_decision_path.py` next reconciles the two message-type vocabularies
first, rather than debugging a silent rejection later.
