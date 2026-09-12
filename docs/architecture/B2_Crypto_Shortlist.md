# B2 — auth_tag Primitive Shortlist: HMAC vs. ECDSA (DRAFT)

**Status: DRAFT FOR DISCUSSION ONLY.** Same framing as
[`B1_Authenticated_Envelope_Draft.md`](B1_Authenticated_Envelope_Draft.md)
and [`B3_Quorum_StateMachine_Draft.md`](B3_Quorum_StateMachine_Draft.md):
not an implementation plan, blocked by the same approval gate. This
document has a leaning — it's not a neutral list — but the leaning is a
starting position for the meeting to push back on, not a decision already
made.

---

## 1. What exists today (read-only investigation, no changes made)

### 1a. Target chip is ambiguous in the repo itself — flagging, not assuming

B1's draft mentioned "ESP32-S3" in passing. Checking that directly turned
up a real inconsistency, not a confirmation:

- `m1-hardware/src/esp32_coprocessor.ino:2,11` — firmware comment header
  says *"ESP32-S3 Co-Processor Firmware"* and *"Target Hardware: ESP32-S3
  DevKitC-1 / ESP32 DevKit V1"* — naming **two different chip families**
  in the same line.
- `m1-hardware/README.md:23` — top-level M1 module doc instructs Arduino
  IDE users to *"Select board: `ESP32 Dev Module`"* — the generic classic
  ESP32 board entry, no S3 mention at all.
- `m1-hardware/wokwi/diagram.json:7` — the actual configured Wokwi
  simulation part is `"board-esp32-devkit-c-v4"` — Wokwi's classic ESP32
  (Xtensa LX6 / WROOM-32-family) board type. Wokwi has a separate,
  distinctly-named part for the S3 (`board-esp32-s3-devkitc-1`), which is
  **not** what's used here.
- `m1-hardware/wokwi/README.md:6` — prose calls it *"ESP32-S3 DevKit v4"*,
  a combination that doesn't match either chip family's actual product
  naming cleanly.
- No `platformio.ini` exists anywhere in the repo (checked) — so there's
  no build-config source of truth to resolve this from either.

**Net: the repo's own documentation and firmware comments disagree with
its own simulation config about which chip this targets.** This shortlist
does not resolve that — it's flagged as the first thing to confirm with
M1 before any of the compute-cost reasoning below can be taken as final,
since classic ESP32 (Xtensa LX6) and ESP32-S3 (Xtensa LX7, dual-core,
higher clock) have different raw performance and somewhat different
crypto-acceleration hardware.

### 1b. No crypto library is imported anywhere in the firmware today

Full include list across both `.ino` files in `m1-hardware/src/`:

```cpp
#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
```

(`main.ino` only has `#include <WiFi.h>`.) No `mbedtls`, no `Crypto.h`,
no `SHA256`, no `HMAC`, no `ECDSA`, no `AES` — grepped case-insensitively
across the whole `m1-hardware` directory, zero hits beyond the includes
above. **This means both options below start from the same place: zero.**
Neither HMAC nor ECDSA is "already available" in any meaningful sense —
both require adding a library dependency to firmware that currently has
none. That said, ESP-IDF (which Arduino-ESP32 wraps) ships mbedTLS as
part of the underlying SDK on every ESP32 variant, so "adding a library"
in practice likely means enabling/linking a component that's already part
of the toolchain, not sourcing something external — but this should be
confirmed with M1 rather than assumed, since it depends on the exact
Arduino-ESP32 core version and build configuration in use, neither of
which is pinned anywhere in this repo (no `platformio.ini`, no
`arduino-cli` config found).

### 1c. Existing project-wide trust model is symmetric-hash-only, no PKI

`m3-ml-ledger/src/ledger.py`'s `HashChainLedger` — the project's existing
tamper-evidence mechanism for forensic logging, referenced by B1's
key-provisioning question — uses plain `hashlib.sha256` chaining:

```python
def _hash(self, data: str) -> str:
    """Compute SHA-256 hash of input string."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()
```

No keys, no signatures, no public/private keypairs, no certificate or PKI
concept anywhere in the ledger, or anywhere else in the repo (grepped for
`public_key`/`private_key`/`sign`/`verify` project-wide — the only
`verify_chain()` hits are the ledger's own hash-chain integrity check,
unrelated to cryptographic signature verification). The project's only
existing precedent for "trust" is a symmetric hash function with no key
material at all.

---

## 2. HMAC vs. ECDSA for `auth_tag`

### 2a. Compute cost on the actual target chip

Caveat up front, given 1a: exact cycle counts depend on which chip is
confirmed, and this draft doesn't have a benchmark to point to — this is
general, well-established behavior for the primitive classes, not a
repo-grounded measurement.

- **HMAC-SHA256**: a hash-based MAC — computationally cheap on essentially
  any 32-bit MCU, classic ESP32 or S3. Typically low-microsecond range per
  operation, dominated by SHA-256 compression rounds over a short message
  (the envelope fields, not a large payload). Both ESP32 variants have
  hardware SHA acceleration in their crypto peripheral, which mbedTLS's
  ESP32 port can use — meaning HMAC computation may not even be a
  pure-software operation on either variant. This should still be
  confirmed with M1 (whether the specific chip's SHA HW block is exposed
  and enabled in whatever build config ends up used), not assumed here.
- **ECDSA-P256** (sign and verify, both needed since every node both signs
  outgoing and verifies incoming): meaningfully more expensive — elliptic
  curve scalar multiplication is orders of magnitude more compute than a
  hash function. Without hardware curve acceleration, this is commonly in
  the single-digit-to-tens-of-milliseconds range on a Cortex-M-class or
  Xtensa-class MCU at these clock speeds; verify is typically cheaper than
  sign but still far above HMAC's cost. Neither classic ESP32 nor S3 is
  confirmed here to have a dedicated ECC/ECDSA hardware accelerator (some
  newer ESP32 variants — C2, C6 — do have one; whether S3 or classic ESP32
  do is a question for M1, not asserted here).
- **Why this matters beyond raw speed**: every mesh broadcast and every
  serial command would carry (and verify) an `auth_tag` per B1. If this
  runs inside the same firmware also handling `esp_now_send`/`recv`
  callbacks, the tamper interrupt ISR, and (per `m1-hardware/src/main.ino`)
  potentially a promiscuous-mode packet sniffer callback, ECDSA's
  per-message cost is the kind of thing that could visibly compete with
  time-sensitive interrupt handling, whereas HMAC's cost is unlikely to be
  noticeable at this message rate. This is a reason to lean HMAC, not a
  proven bottleneck — actual message rate under load isn't established
  anywhere in this repo.

### 2b. Key provisioning complexity

- **HMAC**: one symmetric key per node (or one shared mesh-wide key,
  or a per-pair key — a provisioning-scheme question in its own right,
  not resolved here). Simpler cryptographic math, but the operational
  problem shifts entirely to **key distribution**: however the key gets
  onto each ESP32 (flashed at build time, provisioned over serial during
  setup, etc.), that mechanism itself needs to be at least as trustworthy
  as the channel it's meant to protect — and nothing in the current
  codebase addresses secure provisioning at all (checked: no key-loading
  code, no secure-boot/flash-encryption references anywhere in
  `m1-hardware`). If it's one shared key across the whole mesh, compromise
  of any single node compromises the entire mesh's authentication
  simultaneously — that's a real cost of the symmetric approach, not
  glossed over here.
- **ECDSA**: each node holds a private key and publishes a public key.
  Compromise of one node's private key only compromises messages
  attributed to that node — other nodes' signatures remain trustworthy.
  This is a genuine security advantage over a shared symmetric key. The
  cost is provisioning and distributing public keys to every peer that
  needs to verify (or a lightweight CA/certificate scheme, which is a
  meaningfully bigger design surface than "flash a key"), plus the
  question of what happens when a node's key needs to be revoked or
  rotated — a harder problem for asymmetric schemes than symmetric ones
  in a resource-constrained, likely intermittently-connected mesh with no
  existing PKI infrastructure (1c) to build on.

### 2c. Interaction with B1's open key-provisioning/rotation question

B1 flagged key provisioning/rotation as needing M3 input specifically
because it "relates to the existing ledger/hash-chain trust model." Having
now actually read that model (1c above): it's a **pure symmetric hash
chain with no key material whatsoever**. There is no existing asymmetric
trust infrastructure anywhere in this project to extend — no CA, no
certificate handling, no public-key storage or distribution mechanism, no
existing precedent for "here's how this project manages a keypair." HMAC
is the smaller conceptual leap from what already exists (a shared secret
feeding a hash-based construction is much closer to the ledger's existing
"hash function as trust primitive" pattern than introducing keypairs,
certificates, and revocation would be). This is offered as the single
strongest argument in this document, not as a closed case — the mesh's
threat model may genuinely need per-node key compromise isolation (2b)
badly enough to justify taking on that new complexity anyway. That's a
judgment call for the meeting, not something this repo's existing code
settles on its own.

---

## 3. Leaning (for the meeting to argue with, not a decision)

**Lean HMAC-SHA256** for `auth_tag`, on these grounds:

1. Compute cost is very likely to be a non-issue on either candidate chip,
   while ECDSA's cost is more likely to interact with the firmware's other
   time-sensitive responsibilities (tamper ISR, mesh callbacks, possible
   promiscuous packet sniffing) — though this is reasoning from general
   primitive characteristics, not a measurement on the actual target
   (still unconfirmed per 1a).
2. Key provisioning is simpler to reason about and ships faster, at the
   real cost of shared-key-compromise blast radius (2b) — an explicit
   tradeoff, not a free win.
3. It's the smaller step from the project's existing trust model (2c) —
   there is no PKI to build on today, and HMAC doesn't require inventing
   one.

**Strongest counter-argument, stated plainly so it isn't buried:** if the
mesh's real threat model includes "one physically-compromised node should
not be able to forge messages from every other node," ECDSA's per-node
key isolation is a genuine security property HMAC with a shared key
cannot provide, and that may be worth the added compute cost and
provisioning complexity. Whether that threat is realistic for this
deployment (rack-mounted nodes, presumably some physical security already
per the enclosure tamper-detection hardware — `m1-hardware`'s tamper grid,
referenced throughout B1/B3) is a judgment call this draft can't make from
the code alone.

---

## 4. Open questions for the meeting

- Confirm actual target chip (1a) — classic ESP32 vs. ESP32-S3 — since
  it affects every compute-cost claim above and should be resolved before
  any benchmarking is done
- Confirm mbedTLS/crypto library availability in the actual build
  toolchain in use (1b) — Arduino IDE vs. PlatformIO, and which core
  version
- If HMAC: shared mesh-wide key vs. per-pair keys vs. per-node keys
  against a central verifier — provisioning mechanism itself is
  undesigned (2b)
- If ECDSA: certificate/public-key distribution mechanism, and
  revocation/rotation approach for a mesh with no existing PKI
- Real threat model for physical node compromise — is shared-key blast
  radius (HMAC) actually unacceptable for this deployment, or is that a
  theoretical concern not worth ECDSA's cost here?
- Whether this decision should be revisited once B1's `recipient/scope`
  question (per-org scoping) is resolved — a per-org symmetric key might
  address some of ECDSA's isolation advantage without full asymmetric
  complexity, as a middle ground not analyzed in this draft
