# M4 — GUI and Venture Module

> **Owner:** M4 GUI/Venture Lead
>
> **Canonical Phase 1 demo:** `m4-gui-venture/src/app.py`
>
> **Mode:** Simulation only (`SENTINEL_HARDWARE=sim`)

## Purpose

M4 owns the laptop dashboard, the PIN override workflow, and the venture-facing project material. The canonical Phase 1 deliverable is an 800×480 Tkinter dashboard that can demonstrate the Sentinel software loop without Raspberry Pi, ESP32, relay, SIM800L, or touchscreen hardware.

The browser kiosk under `web/` is retained as a visual/kiosk prototype. The older PyQt prototype under `gui/dashboard.py` is not the canonical Phase 1 demo. Keeping one official demo path prevents the team from presenting inconsistent behavior during evaluation.

## Quick start

From the repository root, install the project dependencies and launch the canonical simulation GUI:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 m4-gui-venture/src/app.py
```

On Ubuntu/Debian, Tkinter may need to be installed through the operating system package manager:

```bash
sudo apt-get install python3-tk
```

The default simulation PIN is `1234`. For a local demonstration, it can be overridden without changing source code:

```bash
SENTINEL_PIN=2468 python3 m4-gui-venture/src/app.py
```

This PIN is a controlled simulation credential, not a production authentication design.

## Phase 1 demonstration sequence

The repeatable demo should follow this order:

1. Launch the GUI and show the `CALIBRATING` state.
2. Allow calibration to finish and show `ARMED & MONITORING` with packet and ledger counters increasing.
3. Inject `C2 ATTACK` or `SYN FLOOD`.
4. Show the anomaly, relay isolation, ledger hash, and mock SMS event.
5. Open the on-screen PIN keypad and submit an incorrect PIN. The line must remain isolated.
6. Submit the configured correct PIN. The line must return to the armed state and a tactical override event must be written.
7. Optionally activate `BREACH CASING` and show key zeroization, tamper alert, relay isolation, and ledger entry.

## Phase 1 completion checklist

- [x] Laptop dashboard runs in simulation mode.
- [x] Telemetry displays packets, anomalies, ledger blocks, uptime, relay, LED, GSM, and tamper state.
- [x] Simulated attack controls are available.
- [x] Simulated anomaly response isolates the relay and writes an event.
- [x] PIN keypad rejects incorrect values and accepts only an exact configured PIN.
- [x] GUI log updates are marshalled to Tkinter's main thread.
- [x] PIN validation has automated tests in `tests/test_m4_pin_security.py`.
- [ ] Connect the GUI to the shared M2/M3 event bus or replay stream during Phase 2.
- [ ] Replace demo-only hardcoded simulation assumptions for real hardware integration.
- [ ] Complete the patent draft, one-pager, and final pitch deck.

## Phase 2 event contract

M2/M3 should provide events to the GUI using the following minimum structure. The transport can initially be a JSON Lines file, an in-process queue, or a local HTTP/WebSocket endpoint; the GUI should not depend on M2/M3 internal classes.

```json
{
  "timestamp": "2026-08-20T12:00:00Z",
  "event_type": "anomaly_lockdown",
  "severity": 0.91,
  "anomaly_score": -0.115,
  "relay_state": "ISOLATED",
  "ledger_hash": "...",
  "sms_status": "MOCK_SENT"
}
```

The required Phase 2 loop is: traffic → detection → mock relay cut → ledger event → GUI alert → mock SMS. The same event contract should remain usable when `HARDWARE=real` is introduced.

## Directory layout

```text
m4-gui-venture/
├── src/
│   ├── app.py            # Canonical Tkinter simulation dashboard
│   └── pin_security.py   # Exact-match, configurable simulation PIN validation
├── web/                  # Optional browser kiosk and visual simulator prototype
├── pitch/
│   └── deck.md           # Venture presentation outline
├── hw_simulator_server.py
├── server.py
└── README.md
```
