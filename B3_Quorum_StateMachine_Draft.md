# B3 — Quorum State Machine (DRAFT)

**Status: DRAFT FOR DISCUSSION ONLY.** Same framing as
[`B1_Authenticated_Envelope_Draft.md`](B1_Authenticated_Envelope_Draft.md):
this is not an implementation plan. Per the patent-scope report's approval
gate, actual implementation is blocked until M1 + M2 + M3 agree on the
design in the architecture meeting. This document builds on B1's proposed
message envelope rather than re-inventing message structure — where this
draft needs a new message type or reuses an existing field, it says so
explicitly rather than redefining the wire format.

---

## 1. What exists today (read-only investigation, no changes made)

### 1a. Mesh broadcast is one-way and inert on receive, everywhere

**Firmware (`m1-hardware/src/esp32_coprocessor.ino:62-77`)** — `onDataRecv()`
logs the received `MeshThreatPacket` and forwards one JSON line to the Pi
host over serial:

```cpp
Serial.printf("{\"event\":\"mesh_peer_alert\",\"origin\":\"%s\",\"type\":\"%s\",\"port\":%d,\"score\":%.3f}\n",
              pkt.origin_node, pkt.threat_type, pkt.victim_port, pkt.anomaly_score);
```

That's the entire receive-side behavior in firmware. No relay action, no
state change, nothing beyond the log line.

**Real hardware, Python side (`common/hal/drivers_real.py:165-197`,
`RealMesh`)** — this class only *writes* to the ESP32 serial port
(`broadcast_threat()`). There is no read loop, no listener thread, no
`self.ser.readline()` or equivalent anywhere in it. The `mesh_peer_alert`
JSON line the firmware emits above is never read by the host at all on
real hardware — not ignored, not mishandled, simply never consumed.

**Simulation, Python side (`common/hal/drivers_sim.py:130-197`,
`SimMesh`)** — this one *does* have a working receive mechanism:

```python
def _listen_loop(self):
    while self.running and self.sock:
        try:
            data, addr = self.sock.recvfrom(4096)
            msg = json.loads(data.decode("utf-8"))
            if msg.get("origin_node") != self.node_id:
                print(f"\n[HAL-SIM] [ESP-NOW MESH RECEIVED] Peer Threat Alert from {msg.get('origin_node')}!")
                for cb in self.peer_callbacks:
                    cb(msg.get("data", {}))
        except Exception:
            pass
```

But `register_peer_callback()` — the only way anything ever gets added to
`self.peer_callbacks` — is never called anywhere in the codebase.
Confirmed via a repo-wide grep for `register_peer_callback(`: the only
matches are the interface definition (`hal_base.py:105`) and the two
implementations (`drivers_sim.py:174`, `drivers_real.py:191`) — no call
site registering an actual callback exists. `self.peer_callbacks` is
always `[]` at runtime, so the `for cb in self.peer_callbacks:` loop body
never executes, even in simulation.

**Net effect:** receiving a peer's threat broadcast today does not cause
any node — real or simulated — to take any action whatsoever, beyond a
print/log statement. There is no existing single-vote reaction to extend
into a quorum. This draft is greenfield on the receive-action side, not a
refinement of something partially working.

### 1b. No vote/quorum concept exists anywhere

Repo-wide search for `quorum` and `vote`: zero matches, in any file, any
extension. There is also no peer registry, peer list, peer count, or
tracking of *other* nodes' liveness anywhere in the codebase — each node
only emits a heartbeat about **itself**
(`esp32_coprocessor.ino:219-226`), and nothing consumes or tracks peer
heartbeats. A node today has no way to know how many peers exist, which
are alive, or whether it missed a broadcast.

---

## 2. Relationship to B1 — this draft assumes B1's envelope, doesn't redefine it

This draft assumes B1's proposed envelope fields are the wire format
quorum votes travel over. It reuses, specifically:

- **`message_type`** — needs a new value (e.g. `QUORUM_VOTE`), distinct
  from the existing one-way notification broadcast (section 1a). A vote is
  a new, structured kind of mesh message, not a replacement for the
  existing gossip broadcast.
- **`sender_id`** — becomes the voter's node identity. This is what lets a
  tallying node (or every node, if decentralized — see 3b) tell distinct
  votes apart and avoid double-counting one node's vote.
- **`sequence/nonce`** — B1 describes this as a generic per-sender
  monotonic counter for replay protection. For quorum specifically, votes
  additionally need to be scoped **per incident**, not just per-sender —
  see 3a for why sequence alone isn't sufficient here.
- **`auth_tag`** — load-bearing, not optional, for quorum specifically.
  See 2a.

### 2a. Why quorum can't be layered on the current transport without B1's auth first

Every transport in section 1 is unauthenticated (per B1 section 1 —
`encrypt = false` on the real ESP-NOW peer, plaintext JSON on the sim UDP
path). A quorum scheme built directly on top of what exists today has
**zero protection against one attacker broadcasting N fabricated votes
under N fabricated `sender_id` strings**, single-handedly reaching any
threshold this draft might propose. This design is written assuming B1's
`auth_tag` is in place and authenticates `sender_id` per node — so a vote
can actually be trusted to represent one real node casting one real vote.
**If B1 isn't implemented first, this design doesn't stand on its own** —
it should be sequenced after B1, not built in parallel independently of
it.

---

## 3. Proposed quorum state machine — outline

### 3a. Trigger / incident identity

Before votes can be collected, they need something to be collected
*about*. Proposal: the node that first observes a local anomaly above
threshold originates an `incident_id` — could reuse B1's `sender_id` +
`sequence` pair (`sender_id:sequence`) to form a globally-unique incident
identity without adding a new field. Every subsequent vote, and the
threshold/deadline/conflict-resolution logic below, is scoped to this
`incident_id`.

### 3b. Vote collection

- Originating node broadcasts the incident using the existing
  `broadcast_threat` mechanism (section 1a), tagged with the new
  `QUORUM_VOTE`-family `message_type` and the `incident_id`.
- Each receiving node evaluates the incident against its own local
  detection state and casts CONFIRM / DENY / ABSTAIN, referencing the same
  `incident_id`.
- **Open, unresolved, and probably the single biggest fork in this whole
  design: where do votes get tallied?** Fully decentralized (every node
  independently tallies all votes it's seen and reaches its own
  conclusion) is more resilient to any one node going down mid-vote, but
  requires every node to reach the *same* conclusion from the *same* vote
  set — which requires delivery guarantees ESP-NOW broadcast doesn't
  provide. `onDataSent()`'s callback (`esp32_coprocessor.ino:56-60`,
  referenced in B1 section 1b) only confirms local radio TX succeeded, not
  that any peer actually received it — there's no ACK, no ordering
  guarantee, no confirmation of who got what. A leader-based model
  (originating node collects and decides) is simpler to reason about but
  creates a single point of failure exactly in the node most likely to be
  under active attack. This draft does not pick one — it needs to be
  decided in the meeting.

### 3c. Threshold

What fraction or count of peers must CONFIRM before an incident is treated
as verified? This can't actually be answered yet, because — per section
1b — **no node today knows how many peers exist or are alive.** Without a
peer count, "threshold" can only be expressed as an absolute count (e.g.
"2 CONFIRMs"), not a fraction (e.g. "2-of-3"), and an absolute count
silently breaks if mesh membership changes (a node added or permanently
lost). A peer-liveness mechanism (which doesn't exist today in any form —
see 3f) is a prerequisite for a threshold definition that's meaningful
over time, not just at a single point in time.

### 3d. Deadline

How long does a node wait for votes before deciding without full
participation? Two things from earlier sections constrain this: no
delivery guarantee on broadcast (3b), and no shared reliable clock across
nodes (B1 section 3f already flags `timestamp` representation as an open
B1 question — firmware uses boot-relative `millis()`, sim uses Unix-epoch
`time.time()`, and these are two different, incompatible things today).
Proposal: deadline should be expressed as a duration relative to the
*local* observation of the incident ("N seconds after I first saw
`incident_id`"), not an absolute wall-clock cutoff, given the clock-sync
question is still open in B1 and shouldn't be assumed resolved here.

### 3e. Conflict resolution

What happens on a near-even split, or when a node's own local read
disagrees with what most peers report? The mesh's stated purpose is
"multi-node coordinated containment" (`common/hal/hal_base.py:97`,
`MeshInterface` docstring) — presumably to avoid both false-positive
lockdowns (isolating a node's network for nothing) and false-negative
under-response (failing to isolate a real, corroborated threat). This
draft flags, but does not resolve: after the deadline, with insufficient
or split votes, does a node **fail open** (do nothing, wait for more
signal) or **fail closed** (isolate anyway, treat ambiguity as a threat)?
Nothing in the current one-way, never-acted-upon broadcast (section 1a)
establishes any precedent either way — this is a security/operational
tradeoff for the meeting, not something inferable from existing code.

### 3f. Peer recovery

How does a node that missed an incident's voting window — offline,
rebooting, network partition — reconcile state afterward? Given zero
peer-tracking exists today (3b, 3c), there's currently no mechanism for a
node to even detect that it *missed* something, let alone request
catch-up. Proposal direction: a node coming online should be able to
query current mesh containment state from any live peer. The closest
existing precedent is `predict_v3.py`'s `_load_state()`, which restores
persisted state from a local `STATE_FILE` on boot — but that's
local-disk-based recovery for a single node's own prior state, not
peer-network-based recovery of the mesh's collective state. Extending that
pattern to "ask a peer" rather than "read local disk" is new design here,
not a reuse of anything that currently exists.

---

## 4. What this draft deliberately does not propose

- No specific threshold number or fraction
- No specific deadline duration
- No decision on leader-based vs. fully decentralized vote tallying
- No fail-open vs. fail-closed default
- No wire-level vote message schema beyond "reuses B1's envelope with a
  new `message_type`" — exact vote payload shape is implementation, not
  drafted here
- No implementation of any kind — same approval gate as B1

---

## 5. Open questions for the meeting

- Leader-based vs. fully decentralized vote tallying (3b) — this is the
  fork everything else in this draft depends on
- How does a node learn its peer count / peer liveness at all, given none
  exists today (3c, 3f)
- Threshold: absolute count vs. fraction, and how it adapts to mesh
  membership changes
- Deadline duration, and confirmation that "relative to local observation"
  (3d) is an acceptable substitute for wall-clock synchronization given
  B1's still-open clock-representation question
- Fail-open vs. fail-closed default on inconclusive quorum (3e) — flagged
  as a security/business decision, not a technical one
- Peer-recovery/catch-up mechanism (3f) — net-new design, no existing
  pattern to extend beyond the loose analogy to local state persistence
- Sequencing confirmation: this draft assumes B1 (specifically `auth_tag`)
  ships first — does the team agree that's a hard prerequisite, not just a
  suggestion (2a)?
