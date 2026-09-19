# Project Brain: BlackBox Sentinel

## 🎯 Overview
BlackBox Sentinel is a fully integrated physical security and monitoring system deployed on Raspberry Pi 4 and Heltec ESP32 V3 hardware. It features a self-healing AI, immutable cryptographic ledger, quorum-based decision engine, and a web-based GUI dashboard.

## 🏗️ Architecture & Tech Stack
- **Tech Stack**: 
  - **Hardware**: Raspberry Pi 4 (Host) & Heltec ESP32 V3 (Microcontroller)
  - **Languages**: Python (Core Logic, ML, GUI, API), C/C++ (ESP32 Firmware)
  - **AI/ML**: Ollama, moondream (vision), qwen2.5:1.5b (remediation)
  - **Web Frontend**: Flask, HTML/JS/CSS (Dashboard on port 5000)
  - **Security/Cryptography**: Ed25519 (signed containment receipts), Hash-chain ledger
- **Structure**: 
  - **M1 (`m1-hardware`)**: Hardware, OS, & Physical ESP32 (UART5, Touch, Self-healing AI)
  - **M2 (`m2-systems`)**: Systems & Integration (Pipeline, bridge service, networking)
  - **M3 (`m3-ml-ledger`)**: ML, Ledger, & Security Contracts (QuorumStateMachine, hash-chain)
  - **M4 (`m4-gui-venture`)**: GUI & Web Dashboard

## 📜 Core Conventions
- **Hardware Integration**: Communication between Pi and ESP32 relies on verified Ed25519 signatures via UART.
- **Service Deployment**: Local AI models run as systemd services. The bridge service and pipeline must maintain a 100% passing test state.
- **Brain Maintenance**: This file (`brain.md`) must be proactively updated after significant architectural decisions or complex bug fixes.

## 🧠 Key Decisions (ADRs)
- `2026-09-18` - **[Containment Logic Fix]**: Fixed critical bug in `app_web.py` where ML signal threshold was `score < 0.0` (always false) → changed to `score > 0.85`. Also fixed `scorer.state = DeviceState.LOCKDOWN` → `scorer.trigger_lockdown()`. This was why the relay never fired on attack injection.
- `2026-09-18` - **[Web GUI V2 Overhaul]**: Rewrote the entire web frontend (`index.html`, `style.css`, `app.js`) with the V2 dark-glass design. Fixed BREACH button routing from `/api/inject` to `/api/tamper`. Added dual-axis signals graph, threat gauge, sparkline, and proper hardware check/relay trigger buttons.
- `2026-09-17` - **[System Integration Complete]**: All four modules (M1-M4) successfully integrated and deployed to the live physical Pi/ESP32 hardware. Fixed ESP32 canonical JSON bug.
- `2026-09-17` - **[Self-Healing AI]**: Deployed local self-healing AI using Ollama (moondream + qwen2.5) to autonomously remediate hardware/sensor anomalies.
- `2026-09-17` - **[Access Configuration]**: Kept SSH open and filesystem read-write to allow for future iterations and updates without friction.
- `2026-09-13` - **[M3 Phase 2 Sign-Off]**: M3 formally signed off on Phase 2 Software Validation Report (`ad0197f`). All software-boundary acceptance conditions satisfied: two-signal independence proven, real organic capture verified (~223s on eth0), containment receipts cryptographically valid. M1 officially unblocked for hardware-in-loop integration.
- `2026-09-12` - **[Independent Detection Bases Closed]**: M2's protocol-state heuristic (`half_open_ratio`, `rst_ratio`, `size_uniformity`) definitively decoupled from the model's volume-based inputs. AST assertion + behavioural test (byte-identical output at 1 pkt/s vs 100,000 pkts/s) prove volume cannot influence the heuristic signal.
- `2026-09-11` - **[Real Organic Capture Validated]**: M2 executed ~223s real capture on eth0 (Codespaces/Linux). 5 real anomalies scored by v3 model, fail-closed two-signal gate correctly held `PENDING_EVIDENCE` on all 5. Corroborated independently by hash-chained ledger matching raw stdout log exactly.
- `2026-09-11` - **[Metrics Integrity Incident]**: Hand-computed metrics committed to production JSON (`e76b63a`) were caught and reverted. Established rule: demo/mockup metrics must live in `ml/models/demo_metrics_mockup.json`, never overwrite the production `sentinel_model_v3_stratified_metrics.json`.
- `2026-09-09` - **[Quorum Veto Path — NOT PURSUED]**: Accepted design decision that quorum serves as an additional approval gate, not an independent veto mechanism. Evidence-level disagreement stops the flow before quorum is reached (fail-closed by design).

## ⚠️ Known Quirks & Gotchas
- **Hardware Dependencies**: Relies on specific physical wiring (UART5 relay) and calibration (touch calibrated).
- **Model Load Times**: Running local LLMs (moondream/qwen) on a Raspberry Pi 4 can be resource-intensive; ensure services are monitored.
- **Containment Threshold**: The ML anomaly score threshold for CONFIRM is `> 0.85`. If changed, it must be updated in BOTH `app_pi.py` and `app_web.py` or the relay won't fire.
- **BREACH Button**: The BREACH action MUST call `/api/tamper`, not `/api/inject`. The tamper path triggers key zeroization and the full containment receipt flow.
- **ML Model Metrics**: Production metrics live in `ml/models/sentinel_model_v3_stratified_metrics.json` (threshold 0.55, 91% precision, 78% recall). The demo mockup file (`demo_metrics_mockup.json`) exists separately for presentation purposes — never overwrite the production file with hand-tuned numbers.
- **Telemetry Output**: Pipeline writes live telemetry to `m3-ml-ledger/data/phase2_telemetry_live.jsonl` (gitignored). The committed synthetic reference (`phase2_telemetry_real_m2_m3.jsonl`) must not be treated as organic output. Real organic output is in `logs_and_data/phase2_telemetry_real_capture_20260911.jsonl`.
- **Quorum State**: `QuorumStateMachine` currently uses fixed peer names (simulated approval), not real distributed network voting. This is documented and consistent with the M3 "NOT PURSUED" design decision.
- **Baseline Calibration**: `predict_v3.py` defaults to 48h (`BASELINE_DURATION=172800s`) wall-clock calibration. For bounded test runs, set `SENTINEL_BASELINE_SECONDS` env var — but always revert afterward.

## 📍 Current State & Next Steps
- **Currently working on**: Web GUI V2 overhaul complete. Ready for deployment to Pi.
- **Next steps**: Deploy updated `app_web.py` and web frontend files to the Raspberry Pi, verify relay fires on attack injection, test BREACH/PIN/HW CHECK buttons end-to-end.
- **Recently completed**: Fixed critical containment logic bug (relay never firing), rewrote entire web frontend with V2 dark-glass design, fixed BREACH button routing.
- **M3 status**: All ML, ledger, and security contract work is complete and signed off. v3 model (91% precision, 78% recall, 97.7% ROC AUC) running on live hardware against `br0` bridge traffic. 57/57 test suite green.

