# BlackBox Sentinel — Master Integration Status

*Last Updated: 2026-09-14*

| Role | Domain / Owner | Current Focus | Status | Work Done % |
| :--- | :--- | :--- | :--- | :--- |
| **M1** | **Hardware, OS & Physical ESP32**<br>*(Prajwal — Physical relay, Raspberry Pi OS, LED, tamper)* | ✅ UART5 relay physically fires (Pi→ESP32, Ed25519 signed)<br>✅ Ed25519 signing chain live end-to-end<br>✅ UART loopback verified (<1s bidirectional)<br>✅ Headless Flask kiosk running (`10.27.79.132:5000`)<br>✅ ESP32 firmware v2.1 (heartbeat, dual serial, OLED)<br>✅ Kiosk/GUI boot & touch calibration verified<br>✅ Full relay test script (`test_relay_full.py`)<br>✅ Touch calibration tool (`touch_calibrate.py`)<br>✅ Dashboard & integration refactored<br>🟡 OverlayFS read-only root (script ready, not yet run)<br>🟡 End-to-end quorum trigger from web UI | In Progress | ~90% (OS Build)<br>~80% (ESP32 Relay) |
| **M2** | **Systems & Integration**<br>*(Suhan Shetty — Pipeline, capture, routing)* | **COMPLETE**: Real organic capture (~223s) verified. Fail-closed gate held `PENDING_EVIDENCE` on live traffic. Heuristic independence proven. 57/57 tests green. Bridge service ready & deployed on Pi OS (`sentinel-bridge.service`). Physical `br0` NetworkManager profiles pre-configured for college demo. | Done | **100%** |
| **M3** | **ML, Ledger, & Security Contracts**<br>*(Shashwat Gautam — Anomaly scoring, quorum, logging)* | **COMPLETE**: v3 model delivered (91% precision, 78% recall), QuorumStateMachine integrated, Phase 2 validation report formally signed off. Model successfully executing on live hardware pipeline against `br0` traffic. | Done | **100%** |
| **M4** | **GUI & Dashboard**<br>*(Shreyash — Web UI, telemetry consumer)* | M1 migrated GUI to Flask web kiosk. Dashboard refactored in this latest push. M4 needs to verify new layout against telemetry schema. | In Progress | ~85% |

---

## 🏫 Tomorrow's Live College Demonstration Plan

The system is now fully integrated in software. Tomorrow at the college, we will complete the physical Layer-2 bridge and demonstrate the end-to-end appliance.

### 1. Hardware Bridge Assembly
* We will connect the **USB-to-Ethernet adapter** to the Raspberry Pi (this will become `eth1`).
* We will plug the college network/router into `eth0`.
* We will plug the target laptop into the USB adapter (`eth1`).
* *Outcome:* The pre-configured NetworkManager profile will instantly fuse `eth0` and `eth1` into the `br0` bridge.

### 2. Live ML Pipeline
* The `sentinel-bridge.service` (M2/M3) is already running in the background. It will automatically detect `br0` and begin scoring the laptop's organic internet traffic in real-time.

### 3. Attack Simulation & Physical Isolation
* We will launch a simulated attack from the target laptop.
* M3 will flag the anomaly, score it, and sign it with the Ed25519 key.
* The Pi will send the payload over UART to the ESP32 (M1).
* The ESP32 will verify the signature and physically snap the **Relay**, cutting the laptop off from the network instantly.

### 4. Final Immutable Lockdown
* After verifying the live trigger works perfectly, we will execute `sudo ./tools/enable_readonly.sh` to lock the Raspberry Pi filesystem into an immutable `OverlayFS`.
* This completes the hardware appliance build.
