# BlackBox Sentinel — Phase 1 Pitch Deck Content

## Slide 1 — BlackBox Sentinel

**Real-Time Network Anomaly Detection with Physical Air-Gap Protection**

BlackBox Sentinel is a simulation-first cyber-defense appliance that detects suspicious network behavior, physically isolates the data line, records a tamper-evident event, and requires an on-device PIN to restore service.

**Team:** M1 Hardware and Firmware · M2 Systems and Security · M3 ML and Ledger · M4 GUI and Venture

**Demo status:** Software simulation complete for Phase 1; physical integration is a later laboratory milestone.

## Slide 2 — The problem

Small organizations often have monitoring tools but lack an affordable mechanism to stop a suspected intrusion immediately. A software alert alone does not guarantee containment, and logs stored on a compromised host may be altered.

BlackBox Sentinel addresses two practical gaps: rapid local containment and evidence that is difficult to rewrite without detection. The project is designed for a local network segment where a physical relay can cut the inline data path.

## Slide 3 — The solution

BlackBox Sentinel combines five coordinated actions:

1. Capture or simulate inline network traffic.
2. Extract packet features and score them with an Isolation Forest anomaly detector.
3. Isolate the physical or simulated relay when an anomaly is confirmed.
4. Append the event to a SHA-256 hash-chained forensic ledger.
5. Send an SMS or mock SMS alert and require an on-device PIN for recovery.

The same software interfaces are intended to support `HARDWARE=sim` during development and `HARDWARE=real` during lab integration.

## Slide 4 — Architecture

```text
Traffic source / replay
          |
          v
M2 capture and feature extraction
          |
          v
M3 anomaly scoring + calibration
          |
          +------ normal ------> continue monitoring
          |
          v
M1 relay isolation + LED + SMS/mesh alert
          |
          v
M3 hash-chained ledger event
          |
          v
M4 dashboard alert + PIN override
```

Phase 1 validates each subsystem independently in simulation. Phase 2 connects the event flow into a complete software digital twin.

## Slide 5 — Demonstration sequence

The laptop demo begins with baseline calibration and normal traffic. The operator then injects a simulated C2 exfiltration or SYN-flood event. The dashboard changes to lockdown, the relay changes to isolated, the ledger receives a new event hash, and the SMS response is shown as a mock alert.

An incorrect PIN leaves the line isolated. The correct configured PIN restores the simulated line and creates a tactical override ledger event. A separate tamper control demonstrates key zeroization and continued isolation.

## Slide 6 — Technical design

**Simulation-first:** The project can be developed without a lab kit by replacing GPIO, SMS, mesh, and hardware capture with simulation drivers.

**Anomaly detection:** Isolation Forest provides unsupervised anomaly scoring after a calibration window. Final performance values must be measured from the selected traffic dataset and recorded rather than invented.

**Forensic ledger:** Each event stores its predecessor hash, creating a chain that can be audited for tampering.

**Recovery control:** Recovery requires an exact PIN through the simulated on-device control. The project treats this as a controlled demonstration credential, not production-grade authentication.

## Slide 7 — Current results and limitations

| Area | Phase 1 result | Evidence to present |
|---|---|---|
| GUI | Laptop dashboard with telemetry, alerts, ledger stream, and PIN keypad | Live screen recording or screenshot |
| Detection response | Simulated attack triggers lockdown path | Demo log and state transition |
| Ledger | Event blocks are displayed and chained | Ledger viewer screenshot |
| Hardware behavior | Relay, LED, SMS, and tamper behavior are mocked | Simulation-mode label |
| Real hardware | Not yet validated | State clearly as Phase 4 laboratory work |
| Measured ML metrics | To be measured on the final selected dataset | Add accuracy/false-positive/latency values after benchmark |

The main limitation is that simulation cannot prove SIM800L power stability, touchscreen drivers, ESP-NOW range, Pi resource behavior, or real relay switching. Those risks belong to the later hardware block.

## Slide 8 — Roadmap and value

**Phase 2:** Connect traffic, detection, relay action, ledger event, dashboard alert, and mock SMS through a shared event contract.

**Phase 3:** Freeze the simulation, finalize the PCB, write real-hardware drivers, and prepare the lab runbook.

**Phase 4:** Perform risk-first hardware bring-up, integrate the physical prototype, and record a backup demo video.

**Value proposition:** a low-cost, local, simulation-verifiable defense node that can contain a suspected intrusion even when the host software environment is under pressure.

## Presentation guidance

Do not claim physical relay timing, real 2G availability, touchscreen reliability, or ML accuracy until those measurements are actually collected. Mark every Phase 1 screen as `SIMULATION` and distinguish implemented behavior from planned laboratory validation.
