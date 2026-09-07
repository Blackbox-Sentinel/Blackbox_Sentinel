# BlackBox Sentinel — One-Page Project Summary

## Overview

BlackBox Sentinel is a simulation-first physical network intrusion prevention appliance. It monitors traffic on an inline network segment, detects anomalous behavior with an Isolation Forest model, physically isolates the line through a relay, records the response in a tamper-evident hash-chained ledger, and alerts the operator through SMS or a simulation stub. Recovery is controlled through an exact on-device PIN.

## Why it matters

A conventional monitoring alert may tell an operator that an attack is occurring, but it does not necessarily stop the traffic immediately. BlackBox Sentinel combines detection with a local physical containment action. Its ledger is designed to make later modification of security events evident through hash-chain verification.

## Four-module design

| Module | Responsibility |
|---|---|
| M1 — Hardware and firmware | ESP32 firmware, relay, tamper inputs, LEDs, SIM800L, and later physical wiring |
| M2 — Systems and security | Linux bridge, traffic capture, simulation/real switch, and integration |
| M3 — ML and ledger | Feature extraction, anomaly scoring, calibration, hash-chained events, and zeroization logic |
| M4 — GUI and venture | Laptop dashboard, PIN override, pitch deck, one-pager, and invention disclosure |

## Phase 1 demonstration

The Phase 1 demo runs on a laptop without the hardware kit. Normal simulated traffic is generated during calibration and monitoring. The operator can inject a simulated attack, after which the dashboard shows an anomaly, the relay changes to isolated, the forensic ledger receives a chained event, and a mock SMS alert is emitted. An incorrect PIN keeps the line isolated; the exact configured PIN restores the simulated line and records a tactical override event.

## Design principle

The project uses one conceptual interface for simulation and real deployment:

```text
HARDWARE=sim  -> mock GPIO, mock SMS, replayed traffic, fake mesh peers
HARDWARE=real -> real GPIO, real SMS, captured traffic, physical mesh peers
```

This approach allows the team to prove the software pipeline before the limited laboratory block. Real hardware remains necessary for SIM800L power behavior, 2G availability, touchscreen drivers, ESP-NOW reliability, Pi resource limits, and physical relay switching.

## Current status

The Phase 1 M4 GUI prototype is implemented in Tkinter and includes telemetry, attack injection, tamper simulation, ledger display, and exact-match PIN override. The next integration milestone is to connect this dashboard to a shared M2/M3 event contract so the GUI consumes the same digital-twin events as the main pipeline rather than running a separate simulator.

## Project limitations

All Phase 1 hardware responses are simulated. ML accuracy, false-positive rate, end-to-end latency, real relay switching time, cellular reliability, and mesh range must be measured and reported only after the appropriate datasets or hardware tests are available.
