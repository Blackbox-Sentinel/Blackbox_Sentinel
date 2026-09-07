# BlackBox Sentinel — Technical Invention Disclosure Draft

> **Status:** Semester-project technical draft for team and supervisor review. This is not legal advice, a patentability opinion, or a filing-ready patent application.

## 1. Proposed title

**Simulation-First Physical Network Intrusion Containment Appliance with Tamper-Evident Event Logging and Local PIN-Governed Recovery**

## 2. Technical field

The proposed system relates to network security appliances, inline traffic monitoring, anomaly detection, physical network isolation, tamper response, and forensic event logging.

## 3. Technical problem

Software-only intrusion detection can identify suspicious activity without immediately preventing continued communication. A compromised host may also modify local logs. Small deployments need a low-cost mechanism that combines local anomaly detection, immediate physical containment, operator-visible evidence, and controlled recovery.

## 4. Proposed system

The system is an inline network appliance with a Linux-capable controller, a hardware abstraction layer, an optional co-processor, a relay that can disconnect the data path, a tamper sensor, a cellular alert interface, and a local touchscreen or dashboard. Traffic is captured or replayed, transformed into features, scored by an anomaly detector, and evaluated against a calibrated baseline.

When an anomaly crosses the configured decision threshold, the controller performs a coordinated response:

1. It commands the relay to isolate the network line.
2. It records the features, score, action, timestamp, and predecessor hash in a hash-chained ledger.
3. It sends an out-of-band SMS or a simulation alert.
4. It can broadcast a threat message to peer nodes.
5. It changes the local interface to a lockdown state.
6. It permits restoration only through an exact local PIN action.

When the enclosure tamper sensor is triggered, the system isolates the line and zeroizes designated volatile key material before recording a tamper event.

## 5. Simulation-first implementation

The system uses a common interface with simulation and real implementations. Simulation substitutes mock GPIO, mock cellular delivery, replayed or generated traffic, and simulated mesh messages. This allows calibration, anomaly handling, ledger verification, dashboard behavior, and recovery workflow to be validated on a laptop before physical hardware is issued.

The simulation is not claimed to prove physical-only properties. Those properties include cellular power stability, 2G availability, touchscreen driver behavior, ESP-NOW range, Raspberry Pi resource limits, and physical relay switching.

## 6. Potentially distinguishing combination

The project’s potentially distinguishing combination is the coordinated use of:

- a calibrated anomaly detector;
- a physical relay response in the same decision loop;
- a tamper-evident hash-chained event record;
- out-of-band alerting;
- tamper-triggered key zeroization; and
- local PIN-governed recovery rather than remote recovery.

The team should conduct a prior-art search and obtain qualified patent counsel before making any novelty or patentability claim.

## 7. Example operating sequence

A normal baseline is collected. A packet or flow receives an anomalous score. The controller crosses the decision threshold and isolates the data line. A ledger block records the event and links to the previous block. An SMS alert is dispatched. The dashboard displays the lockdown state and ledger hash. An operator enters an incorrect PIN and the line remains isolated. The operator enters the correct local PIN and the relay re-engages; the restoration action is appended to the ledger.

## 8. Phase 1 evidence

The current M4 simulation dashboard demonstrates telemetry, attack injection, relay isolation state, ledger display, tamper simulation, mock alert status, and exact-match PIN override. Screenshots, commit identifiers, and a recorded demo should be attached to the final semester report.

## 9. Open validation items

Before presenting the design as a physical prototype, the team should measure the selected model’s false-positive behavior and detection latency, verify ledger-chain integrity after restart, test PIN failure behavior, test zeroization on the actual target platform, validate SIM800L power and network availability, confirm touchscreen and USB contention, test mesh reliability, measure Pi resource usage, and verify the real relay switching behavior under safe laboratory conditions.

## 10. Inventorship and records

The team should maintain a dated record of contributions by M1–M4, architecture revisions, source-code commits, experiment data, diagrams, and supervisor feedback. Formal inventorship and ownership should be determined by the institution and qualified counsel rather than assumed from module ownership.
