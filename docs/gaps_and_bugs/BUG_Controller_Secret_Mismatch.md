# BUG — `TrustedController` secret is mismatched/hardcoded across entry points

**Status: not gated by the B-series approval process.** This is a defect in
code already merged to `main`, independent of which contract
([`B5_Controller_Contract_Conflict.md`](B5_Controller_Contract_Conflict.md))
the team ultimately standardizes on — even Shreyash's own three call sites
into his own `TrustedController` don't agree with each other today. Needs
fixing regardless of the meeting's outcome.

Split out from `B5_Controller_Contract_Conflict.md` §3b.

---

## The bug

`security/trusted_controller.py`'s `TrustedController.__init__` takes a
`secret: bytes | None` used to key every HMAC it computes — signals, votes,
and receipts alike (`_tag()`, `security/trusted_controller.py:126-127`).
Three separate places in the codebase construct their own
`TrustedController` instance, each with a different secret:

| Call site | Secret |
|---|---|
| `gui/dashboard.py:42` | `secret=b"phase2-demo-secret"` — hardcoded literal, checked into source control |
| `m4-gui-venture/src/app.py:98` | `secret=os.urandom(32)` — fresh random value, regenerated every process start |
| `m4-gui-venture/hw_simulator_server.py:90-99` | `secret=os.urandom(32)` — fresh random value, regenerated every process start |

## Impact

Because every signal, vote, and receipt is HMAC-tagged with the issuing
controller's own `self.secret`, and `verify_receipt()` /`verify_signal()`
recompute that HMAC via the same instance's `_tag()`
(`security/trusted_controller.py:174`, `:244`, `:314-317`) rather than
against an externally-supplied key, **a receipt, signal, or vote produced
by one of these three controller instances cannot be verified by
either of the other two.** Concretely:

- `gui/dashboard.py`'s dashboard process can never verify anything issued
  by `hw_simulator_server.py`'s controller, or vice versa — they don't
  share a secret.
- The two `os.urandom(32)` call sites don't even agree with *themselves*
  across restarts — every process start invalidates every previously
  issued signal/vote/receipt for that entry point, since a fresh random
  secret is generated each time and nothing persists it.
- Today, with each entry point running as an isolated single-process demo,
  this doesn't visibly break anything — but it means cross-process/
  cross-node verification (which M2's real transport work explicitly
  needs to support, per `docs/Patent_Scope_Upgrade_Implementation.md`'s
  quorum/receipt requirements) is silently unworkable with the current
  secret handling, not just architecturally undecided.

Separately, `gui/dashboard.py:42`'s hardcoded literal is a hardcoded
secret checked into source control — a normal thing to see in an explicit
`demo-secret`-named simulation constant, but worth flagging on principle
since this module is the live scaffold for a security control, and it's
easy for a literal like this to survive unnoticed into a later build.

## What this note does and doesn't propose

This does **not** propose a full key-provisioning design — B2
(`B2_Crypto_Shortlist.md:133-158`) already identified that as a
genuinely open question (shared mesh-wide key vs. per-node vs. per-pair,
how the key gets onto each node securely), and B5 §6 leaves it explicitly
for the meeting.

What's in scope for an immediate, uncontroversial fix, independent of that
larger decision: make the three existing `TrustedController` call sites
**agree with each other** — e.g. read a single secret from one shared
source (an env var, a local config file, or a `SoftwareMonotonicCounter`-
style persisted value) instead of each inventing its own — so that within
this simulation phase, a signal/vote/receipt issued by one entry point is
at least verifiable by the others. This doesn't require deciding HMAC vs.
Ed25519, or the mesh-wide-vs-per-node question; it just stops the three
existing demo processes from being unable to talk to each other today.

## Suggested next step

Propose the specific fix (where the shared secret should live for the
simulation phase, and the diff for all three call sites) as its own
read-only-investigation-first change, separate from this note — not
included here per the standing workflow (investigate → propose → diff →
confirm before writing code).
