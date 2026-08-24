# B1 — Authenticated Command Envelope (DRAFT)

**Status: DRAFT FOR DISCUSSION ONLY.** This is not an implementation plan and
nothing here should be coded against yet. Per the patent-scope report's
approval gate, actual implementation is blocked until M1 + M2 + M3 agree on
the design in the architecture meeting. Everything below is a starting
proposal meant to be argued with, not a spec.

---

## 1. What exists today (read-only investigation, no changes made)

Before proposing anything, here's what the host↔controller and
controller↔controller messaging actually looks like right now, across the
three places it's implemented. All three are separate, ad hoc, and
unauthenticated.

### 1a. Pi ↔ ESP32 serial (`m1-hardware/src/esp32_coprocessor.ino:108-134`)

115200 baud, plain ASCII, newline-delimited, hand-parsed with
`String.indexOf`/`startsWith`:

```cpp
void processHostCommand(String cmd) {
    cmd.trim();
    if (cmd == "ISOLATE" || cmd == "CUT") { ... }
    else if (cmd == "ENGAGE" || cmd == "RESTORE") { ... }
    else if (cmd == "ARM") { ... }
    else if (cmd == "DISARM") { ... }
    else if (cmd.startsWith("GOSSIP:")) {
        // Format: GOSSIP:EXFILTRATION:-0.088:4444
        ...
    }
    else if (cmd == "PING") { ... }
}
```

ESP32 → Pi direction is plaintext JSON event lines
(`{"event":"relay_state","state":"ISOLATED"}`) plus a heartbeat every 5s.
No version field, no sender identity beyond "whatever is on the wire", no
sequence numbers, no authentication of any kind.

### 1b. ESP32 ↔ ESP32 mesh gossip (`esp32_coprocessor.ino:31-37, 96-106, 174-177`)

A packed struct sent via `esp_now_send()` to the broadcast MAC:

```cpp
typedef struct __attribute__((packed)) {
    char origin_node[16];
    char threat_type[32];
    float anomaly_score;
    uint16_t victim_port;
    uint32_t timestamp;
} MeshThreatPacket;
```

The ESP-NOW peer is registered with encryption **explicitly disabled**:

```cpp
esp_now_peer_info_t peerInfo = {};
memcpy(peerInfo.peer_addr, broadcastMac, 6);
peerInfo.channel = 0;
peerInfo.encrypt = false;
```

`origin_node` is attacker-writable in the sense that nothing validates it —
whatever string is put in that struct field is trusted as-is by any
receiver. `timestamp` is `millis() / 1000` — seconds since the sending
ESP32's own boot, not wall-clock time, and not tied cryptographically to
the rest of the packet.

### 1c. Simulated mesh, UDP loopback (`common/hal/drivers_sim.py:130-189`)

Same conceptual message, different wire format — JSON over a UDP loopback
socket on port 39999:

```python
payload = {
    "origin_node": self.node_id,
    "timestamp": time.time(),
    "type": "ESP_NOW_CONTAINMENT_BROADCAST",
    "data": threat_payload
}
```

Note `timestamp` here is Unix-epoch float — a **different representation**
than the real firmware's boot-relative uint32 in 1b. That inconsistency
would need to be resolved as part of any real envelope, not just papered
over.

### 1d. A gap found while reading, not fixed here

`common/hal/drivers_real.py:180-189` (`RealMesh.broadcast_threat`) writes:

```python
line = f"MESH_BROADCAST:{threat_payload}\n"
self.ser.write(line.encode("utf-8"))
```

— a Python dict's `repr()` — to the ESP32's serial port. The firmware's
parser only recognizes `GOSSIP:<type>:<score>:<port>` (section 1a). These
two do not speak the same protocol today. This looks like the real-hardware
mesh-broadcast path is currently non-functional, independent of the
authentication question this draft is about. Flagging it here since it's
directly relevant context for whoever picks up the envelope work — it's
mentioned for awareness only, not being fixed as part of this task.

---

## 2. Why this matters (motivation, not a threat model)

Everything above is either:
- explicitly unencrypted (`encrypt = false`, mesh), or
- plaintext ASCII/JSON with no integrity check (serial commands, UDP sim)

Concretely, today: anything within serial reach of the Pi↔ESP32 link can
send `ISOLATE` or `DISARM` and the firmware will act on it with zero
verification of who sent it. Anything within 2.4GHz radio range can inject
a fabricated `MeshThreatPacket` claiming to be any `origin_node`, with any
`threat_type`/`anomaly_score`, and neighboring nodes will gossip-forward it
as if it were real. There is also no replay protection anywhere — a
captured, legitimate packet can be resent unmodified and will be reprocessed
as new.

This draft proposes a single envelope format meant to sit underneath all
three transports above (serial, real ESP-NOW, simulated UDP), so the
host↔controller and controller↔controller paths share one authenticated
message shape instead of three incompatible ad hoc ones.

---

## 3. Proposed envelope fields

| # | Field | Type (proposed) | Size (proposed) |
|---|---|---|---|
| 1 | `version` | uint8 | 1 byte |
| 2 | `sender_id` | fixed-length string or short int ID | 16 bytes (matches existing `origin_node[16]`) |
| 3 | `recipient/scope` | fixed-length string or ID | TBD — see 3c |
| 4 | `message_type` | uint8 enum | 1 byte |
| 5 | `sequence/nonce` | uint32 (or uint64) monotonic counter | 4–8 bytes |
| 6 | `timestamp` | uint32 or uint64, one representation, TBD | 4–8 bytes |
| 7 | `payload` | variable, per `message_type` | variable |
| 8 | `auth_tag` | MAC/signature over everything above | TBD — see 3h |

Sizes are starting proposals, not final — they need to fit within
whatever per-packet budget ESP-NOW actually gives us (the existing
`MeshThreatPacket` alone is already 16+32+4+2+4 = 58 bytes; adding a full
envelope on top needs headroom checked against ESP-NOW's real payload
ceiling, which should be confirmed with M1 rather than assumed here).

### Field-by-field reasoning

**3a. `version`** — Section 1d above is a live example of the failure mode
this field exists to catch: two components (the Python driver and the
firmware parser) already silently disagree about the wire format today,
and nothing detects that mismatch — it just fails silently/appears broken.
A version byte lets either side reject or flag a message from a protocol
revision it doesn't understand, instead of misparsing it or (worse) a
receiver silently ignoring fields it doesn't recognize.

**3b. `sender_id`** — `origin_node[16]` already exists in the real
`MeshThreatPacket` (section 1b) and `node_id`/`NODE_ID` is threaded through
`SimMesh`, `sentinel_pipeline.py`, and the HAL. This field already exists
conceptually — the proposal is to make it **authenticated** (covered by
the auth tag) rather than a bare unverified string any sender can put
anything into.

**3c. `recipient/scope`** — Today's mesh broadcast is unconditionally sent
to the ESP-NOW broadcast MAC (`FF:FF:FF:FF:FF:FF`, section 1b) — there is
no unicast option and no concept of scope at all. Given the M3 work this
session on `organization_id`-scoped detection profiles, a shared physical
mesh serving multiple organizations' nodes (e.g. adjacent racks in a
shared facility) would leak one org's threat telemetry to another org's
nodes without a scope field. Open question for the meeting: does this need
to be a real per-org identifier, or is a broadcast/unicast flag sufficient
for the current single-tenant-per-mesh deployment model? Don't have enough
context on the physical deployment topology to propose an answer here.

**3d. `message_type`** — Informally exists today as the ASCII command
keywords in `processHostCommand()` (`ISOLATE`/`ENGAGE`/`ARM`/`DISARM`/
`PING`/`GOSSIP`) and separately as the `"type"` string in `SimMesh`'s JSON
payload (`"ESP_NOW_CONTAINMENT_BROADCAST"`). Proposal folds both into one
enum so serial commands and mesh gossip share a single type vocabulary
instead of two separate parsers with no relationship to each other.

**3e. `sequence/nonce`** — Nothing today prevents replay (section 2). A
monotonic per-sender counter lets a receiver track the last-seen sequence
number and reject anything at or below it. It would also double as the
nonce input to the auth tag computation, which matters if the authentication
scheme ends up needing a nonce to avoid tag reuse — exact algorithm choice
is out of scope for this draft (see 3h).

**3f. `timestamp`** — Already exists in two **incompatible** forms today:
`millis() / 1000` (boot-relative uint32, firmware, section 1b) vs.
`time.time()` (Unix-epoch float, sim, section 1c). This draft doesn't
resolve which representation wins — that's a decision for the meeting,
likely driven by whether the ESP32 has any reliable wall-clock source at
all (it may not, without NTP or an RTC — a question for M1). Whatever is
chosen, the point of including it in the authenticated envelope (vs. just
logging it as today) is to support a replay window check independent of
the sequence counter — e.g. reject anything older than N seconds even if
the sequence number alone looks plausible.

**3g. `payload`** — Carries what already flows today: relay commands
(no extra data needed), threat gossip (`origin_node`/`threat_type`/
`anomaly_score`/`victim_port` from section 1b, or the richer
`source_node`/`threat_score`/`organization_id`/`global_prediction`/
`local_prediction` dict sentinel_pipeline.py actually builds at
`sentinel_pipeline.py:270-276`), heartbeat, PIN override. Proposal is to
keep payload shape flexible per `message_type` rather than one rigid
struct for everything, since the sim path already needs richer fields
(`organization_id`, dual predictions) than the real firmware's
`MeshThreatPacket` currently carries — the real struct doesn't have room
for organization scoping at all right now.

**3h. `auth_tag`** — The actual gap this whole draft exists to close.
Every transport found in section 1 is either explicitly unencrypted
(`encrypt = false`) or plaintext with zero integrity checking. Proposal:
a MAC (e.g. HMAC) computed over all preceding fields
(`version‖sender_id‖recipient‖message_type‖sequence‖timestamp‖payload`),
using a key provisioned per node. Deliberately **not** specifying the exact
algorithm, key length, or provisioning/rotation mechanism here — that
needs M1 input (what crypto primitives are realistic on an ESP32's compute
budget, especially if this also has to run inside a promiscuous-mode
sniffer loop per `m1-hardware/src/main.ino`) and M3 input (how keys get
provisioned and rotated across a fleet, since that's closer to the
existing ledger/hash-chain trust model already used for forensic logging).

---

## 4. How this would layer onto what exists (illustrative, not decided)

- **Serial (1a):** Currently newline-delimited plaintext. An envelope could
  be carried as a single encoded line (e.g. hex or base64 of the binary
  envelope) after existing plaintext commands, or the ASCII commands could
  be retired in favor of the envelope entirely. Which of those — and
  whether there's a transition period supporting both — is a meeting
  decision, not proposed here.
- **Real ESP-NOW (1b):** `MeshThreatPacket` would need to become (or be
  wrapped by) the new envelope struct, respecting whatever ESP-NOW's actual
  payload ceiling turns out to be once confirmed with M1.
- **Simulated UDP (1c):** Lowest-risk place to prototype first, since JSON
  is naturally extensible and this path isn't constrained by embedded
  compute/payload-size limits the way the real firmware is. Worth
  considering as a first proving ground before touching real hardware,
  but that sequencing is a suggestion for discussion, not a plan.

---

## 5. Explicitly open questions for the meeting

- Exact auth algorithm and key length (M1: embedded crypto budget)
- Key provisioning and rotation across a node fleet (M3: relates to
  existing ledger/hash-chain trust model)
- `timestamp` representation and whether ESP32 has any wall-clock source
- Whether `recipient/scope` needs to be a real per-org identifier or a
  simpler broadcast/unicast flag
- ESP-NOW real payload ceiling on the target ESP32-S3 build, and whether
  the proposed field sizes above fit inside it
- Whether serial and mesh should share one envelope format or have two
  related-but-distinct ones (serial is point-to-point Pi↔ESP32; mesh is
  broadcast ESP32↔ESP32 — the security properties needed may not be
  identical)
- Transition/versioning plan given `1d` shows the current protocol is
  already inconsistent between components in production code
